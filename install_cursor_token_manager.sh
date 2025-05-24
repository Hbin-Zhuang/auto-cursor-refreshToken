#!/bin/bash

# Cursor Token 自动刷新工具安装脚本

echo "🚀 开始安装 Cursor Token 自动刷新工具..."

# 检查 Python 是否已安装
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装 Python3"
    exit 1
fi

# 创建工作目录
INSTALL_DIR="$HOME/.cursor-token-manager"
mkdir -p "$INSTALL_DIR"

echo "📁 创建工作目录: $INSTALL_DIR"

# 安装依赖
echo "📦 安装 Python 依赖..."
pip3 install requests schedule

# 创建 Python 脚本
cat > "$INSTALL_DIR/cursor_token_refresh.py" << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import time
import requests
import schedule
import logging
from datetime import datetime, timedelta
from pathlib import Path
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / '.cursor-token-manager' / 'cursor_token_refresh.log'),
        logging.StreamHandler()
    ]
)

class CursorTokenManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # 默认数据库路径
            self.db_path = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
        else:
            self.db_path = Path(db_path)
        
        self.api_base = "https://api2.cursor.sh/api"
        
    def get_current_tokens(self):
        """从数据库获取当前的 token 信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询 auth 相关的数据
            cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%auth%' OR key LIKE '%token%'")
            rows = cursor.fetchall()
            
            auth_data = {}
            for key, value in rows:
                try:
                    auth_data[key] = json.loads(value) if value else None
                except json.JSONDecodeError:
                    auth_data[key] = value
            
            conn.close()
            
            logging.info(f"找到 {len(auth_data)} 个认证相关的条目")
            
            # 寻找包含 accessToken 和 refreshToken 的数据
            access_token = None
            refresh_token = None
            expires_at = None
            
            for key, data in auth_data.items():
                if isinstance(data, dict):
                    if 'accessToken' in data:
                        access_token = data['accessToken']
                        logging.info(f"从 {key} 找到 accessToken")
                    if 'refreshToken' in data:
                        refresh_token = data['refreshToken']
                        logging.info(f"从 {key} 找到 refreshToken")
                    if 'expiresAt' in data:
                        expires_at = data['expiresAt']
                    elif 'expires_at' in data:
                        expires_at = data['expires_at']
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_at': expires_at,
                'raw_data': auth_data
            }
            
        except Exception as e:
            logging.error(f"获取 token 失败: {e}")
            return None
    
    def refresh_access_token(self, refresh_token):
        """使用 refreshToken 获取新的 accessToken"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Cursor/1.0'
            }
            
            data = {
                'refresh_token': refresh_token
            }
            
            response = requests.post(
                f"{self.api_base}/auth/refresh",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logging.info("Token 刷新成功")
                return result
            else:
                logging.error(f"Token 刷新失败: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"刷新 token 时发生错误: {e}")
            return None
    
    def update_token_in_db(self, new_token_data):
        """将新的 token 更新到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取当前所有认证相关的数据
            cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%auth%' OR key LIKE '%token%'")
            rows = cursor.fetchall()
            
            updated_count = 0
            
            for key, value in rows:
                try:
                    data = json.loads(value) if value else {}
                    
                    # 如果这个条目包含 accessToken，则更新它
                    if isinstance(data, dict) and 'accessToken' in data:
                        old_token = data['accessToken'][:20] + "..." if data['accessToken'] else "None"
                        
                        # 更新 token 信息
                        data['accessToken'] = new_token_data.get('access_token', data['accessToken'])
                        
                        if 'refresh_token' in new_token_data:
                            data['refreshToken'] = new_token_data['refresh_token']
                        
                        # 更新过期时间
                        if 'expires_in' in new_token_data:
                            # expires_in 是秒数，转换为毫秒时间戳
                            expires_at = int((datetime.now() + timedelta(seconds=new_token_data['expires_in'])).timestamp() * 1000)
                            data['expiresAt'] = expires_at
                        
                        # 更新数据库
                        cursor.execute("UPDATE ItemTable SET value = ? WHERE key = ?", 
                                     (json.dumps(data), key))
                        
                        new_token = data['accessToken'][:20] + "..." if data['accessToken'] else "None"
                        logging.info(f"更新 {key}: {old_token} -> {new_token}")
                        updated_count += 1
                
                except json.JSONDecodeError:
                    continue
            
            conn.commit()
            conn.close()
            
            logging.info(f"成功更新了 {updated_count} 个条目")
            return updated_count > 0
            
        except Exception as e:
            logging.error(f"更新数据库失败: {e}")
            return False
    
    def check_token_expiry(self, expires_at):
        """检查 token 是否需要刷新"""
        if not expires_at:
            logging.warning("无法获取 token 过期时间")
            return True
        
        try:
            # expires_at 可能是毫秒时间戳
            if expires_at > 10**12:  # 毫秒时间戳
                expire_time = datetime.fromtimestamp(expires_at / 1000)
            else:  # 秒时间戳
                expire_time = datetime.fromtimestamp(expires_at)
            
            now = datetime.now()
            time_left = expire_time - now
            
            logging.info(f"Token 过期时间: {expire_time}")
            logging.info(f"剩余时间: {time_left}")
            
            # 如果剩余时间少于 10 天，则需要刷新
            return time_left < timedelta(days=10)
            
        except Exception as e:
            logging.error(f"检查过期时间失败: {e}")
            return True
    
    def refresh_if_needed(self):
        """检查并在需要时刷新 token"""
        logging.info("开始检查 token 状态...")
        
        # 获取当前 token
        token_info = self.get_current_tokens()
        if not token_info:
            logging.error("无法获取当前 token 信息")
            return False
        
        access_token = token_info['access_token']
        refresh_token = token_info['refresh_token']
        expires_at = token_info['expires_at']
        
        if not refresh_token:
            logging.error("未找到 refresh token")
            return False
        
        # 检查是否需要刷新
        if not self.check_token_expiry(expires_at):
            logging.info("Token 还未过期，无需刷新")
            return True
        
        logging.info("Token 即将过期，开始刷新...")
        
        # 刷新 token
        new_token_data = self.refresh_access_token(refresh_token)
        if not new_token_data:
            logging.error("Token 刷新失败")
            return False
        
        # 更新数据库
        if self.update_token_in_db(new_token_data):
            logging.info("Token 刷新并更新成功!")
            return True
        else:
            logging.error("Token 刷新成功但更新数据库失败")
            return False
    
    def start_auto_refresh(self, check_interval_days=5):
        """启动自动刷新服务"""
        logging.info(f"启动自动 token 刷新服务，检查间隔: {check_interval_days} 天")
        
        # 立即执行一次检查
        self.refresh_if_needed()
        
        # 设置定时任务
        schedule.every(check_interval_days).days.do(self.refresh_if_needed)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(3600)  # 每小时检查一次调度
            except KeyboardInterrupt:
                logging.info("收到停止信号，退出程序")
                break
            except Exception as e:
                logging.error(f"调度器错误: {e}")
                time.sleep(60)

def main():
    # 创建 token 管理器
    manager = CursorTokenManager()
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "check":
            # 只检查一次
            success = manager.refresh_if_needed()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "daemon":
            # 启动守护进程模式
            manager.start_auto_refresh()
    else:
        # 默认行为：检查一次
        print("使用方法:")
        print("  python3 cursor_token_refresh.py check    # 检查并刷新一次")
        print("  python3 cursor_token_refresh.py daemon   # 启动自动刷新守护进程")
        
        manager.refresh_if_needed()

if __name__ == "__main__":
    main()
EOF

# 使脚本可执行
chmod +x "$INSTALL_DIR/cursor_token_refresh.py"

# 创建 launchd plist 文件（macOS 系统服务）
cat > "$HOME/Library/LaunchAgents/com.cursor.token.refresh.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cursor.token.refresh</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/cursor_token_refresh.py</string>
        <string>daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$INSTALL_DIR/cursor_token_refresh.log</string>
    <key>StandardErrorPath</key>
    <string>$INSTALL_DIR/cursor_token_refresh_error.log</string>
</dict>
</plist>
EOF

# 创建便捷命令脚本
cat > "$INSTALL_DIR/cursor-token" << EOF
#!/bin/bash

SCRIPT_DIR="\$HOME/.cursor-token-manager"

case "\$1" in
    "start")
        echo "🚀 启动 Cursor Token 自动刷新服务..."
        launchctl load "\$HOME/Library/LaunchAgents/com.cursor.token.refresh.plist"
        echo "✅ 服务已启动"
        ;;
    "stop")
        echo "🛑 停止 Cursor Token 自动刷新服务..."
        launchctl unload "\$HOME/Library/LaunchAgents/com.cursor.token.refresh.plist"
        echo "✅ 服务已停止"
        ;;
    "restart")
        echo "🔄 重启 Cursor Token 自动刷新服务..."
        launchctl unload "\$HOME/Library/LaunchAgents/com.cursor.token.refresh.plist" 2>/dev/null
        launchctl load "\$HOME/Library/LaunchAgents/com.cursor.token.refresh.plist"
        echo "✅ 服务已重启"
        ;;
    "status")
        if launchctl list | grep -q "com.cursor.token.refresh"; then
            echo "✅ Cursor Token 刷新服务正在运行"
        else
            echo "❌ Cursor Token 刷新服务未运行"
        fi
        ;;
    "check")
        echo "🔍 手动检查并刷新 Token..."
        python3 "\$SCRIPT_DIR/cursor_token_refresh.py" check
        ;;
    "log")
        echo "📋 显示最近的日志:"
        tail -n 50 "\$SCRIPT_DIR/cursor_token_refresh.log"
        ;;
    *)
        echo "🔧 Cursor Token 自动刷新工具"
        echo ""
        echo "用法: cursor-token [命令]"
        echo ""
        echo "命令:"
        echo "  start    启动自动刷新服务"
        echo "  stop     停止自动刷新服务"
        echo "  restart  重启自动刷新服务"
        echo "  status   查看服务状态"
        echo "  check    手动检查并刷新一次"
        echo "  log      查看最近的日志"
        ;;
esac
EOF

chmod +x "$INSTALL_DIR/cursor-token"

# 添加到 PATH（如果需要）
if ! grep -q "cursor-token-manager" "$HOME/.zshrc" 2>/dev/null; then
    echo "" >> "$HOME/.zshrc"
    echo "# Cursor Token Manager" >> "$HOME/.zshrc"
    echo "export PATH=\"\$PATH:\$HOME/.cursor-token-manager\"" >> "$HOME/.zshrc"
fi

if ! grep -q "cursor-token-manager" "$HOME/.bash_profile" 2>/dev/null; then
    echo "" >> "$HOME/.bash_profile"
    echo "# Cursor Token Manager" >> "$HOME/.bash_profile"
    echo "export PATH=\"\$PATH:\$HOME/.cursor-token-manager\"" >> "$HOME/.bash_profile"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "使用方法："
echo "1. 启动自动刷新服务:"
echo "   $INSTALL_DIR/cursor-token start"
echo ""
echo "2. 手动检查一次:"
echo "   $INSTALL_DIR/cursor-token check"
echo ""
echo "3. 查看服务状态:"
echo "   $INSTALL_DIR/cursor-token status"
echo ""
echo "4. 查看日志:"
echo "   $INSTALL_DIR/cursor-token log"
echo ""
echo "重新加载终端或运行 'source ~/.zshrc' 后可以直接使用 'cursor-token' 命令"