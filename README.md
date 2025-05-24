# Cursor Token Auto-Refresh

> **Cursor IDE Token 自动刷新工具**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

一个用于自动刷新 Cursor IDE 认证令牌的智能工具，包含数据库分析和令牌管理功能。无需手动重新登录，保持 Cursor 持续可用。

## ✨ 核心功能

### 🔄 自动令牌刷新
- **智能检测**：自动识别即将过期的访问令牌（剩余时间 < 10天）
- **无感刷新**：后台自动刷新，无需用户干预
- **系统集成**：作为 macOS LaunchAgent 运行，开机自启
- **定时检查**：每5天自动检查一次令牌状态

### 🔍 数据库分析工具
- **结构分析**：分析 Cursor 的 SQLite 数据库结构
- **认证提取**：智能提取和分析认证相关数据
- **JWT 解码**：解析 JWT 令牌内容和过期时间
- **安全性评估**：检测潜在的安全风险

## 🚀 快速开始

### 前置要求

- macOS 系统
- Python 3.7 或更高版本
- 已安装并登录 Cursor IDE

### 一键安装

```bash
# 克隆项目
git clone https://github.com/your-username/auto-cursor-refreshToken.git
cd auto-cursor-refreshToken

# 执行安装脚本
chmod +x install_cursor_token_manager.sh
./install_cursor_token_manager.sh
```

### 手动安装依赖

```bash
pip3 install requests schedule
```

## 📖 使用指南

### 服务管理

```bash
# 启动自动刷新服务
~/.cursor-token-manager/cursor-token start

# 查看服务状态
~/.cursor-token-manager/cursor-token status

# 停止服务
~/.cursor-token-manager/cursor-token stop

# 重启服务
~/.cursor-token-manager/cursor-token restart

# 手动检查一次
~/.cursor-token-manager/cursor-token check

# 查看日志
~/.cursor-token-manager/cursor-token log
```

### 数据库分析工具

```bash
# 进入分析工具目录
cd cursor本地数据库分析

# 运行数据库结构分析
python3 cursor_db_analyzer.py

# 提取认证数据
python3 cursor_auth_extractor.py

# 解码 JWT 令牌
python3 jwt_decoder.py
```

## 📁 项目结构

```
auto-cursor-refreshToken/
├── README.md                           # 项目说明文档
├── cursor_token_refresh.py             # 核心刷新脚本
├── install_cursor_token_manager.sh     # 自动安装脚本
└── cursor本地数据库分析/
    ├── cursor_db_analyzer.py           # 数据库结构分析器
    ├── cursor_auth_extractor.py        # 认证数据提取器
    └── jwt_decoder.py                  # JWT 令牌解码器
```

## ⚙️ 工作原理

1. **令牌检测**：读取 `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` 数据库
2. **过期检查**：分析访问令牌的过期时间，判断是否需要刷新
3. **自动刷新**：使用 refreshToken 调用 Cursor API 获取新的 accessToken
4. **数据库更新**：将新令牌信息安全地更新回数据库
5. **持续监控**：定时执行检查，确保令牌始终有效

## 🛡️ 安全特性

- **本地处理**：所有令牌处理都在本地进行，不会发送到第三方服务器
- **备份保护**：支持使用数据库备份文件进行安全分析
- **最小权限**：只读取和更新必要的令牌字段
- **完整日志**：详细记录所有操作，便于审计和调试
- **错误处理**：完善的异常处理机制，防止数据损坏

## 🔧 配置选项

### 修改检查间隔

编辑 `cursor_token_refresh.py` 中的 `check_interval_days` 参数：

```python
def start_auto_refresh(self, check_interval_days=5):  # 默认5天
```

### 修改过期阈值

修改 `check_token_expiry` 方法中的阈值：

```python
return time_left < timedelta(days=10)  # 默认10天
```

## 📋 常见问题

**Q: 首次运行提示找不到令牌？**
A: 确保 Cursor 已经正常登录，并且存在有效的 refresh token。

**Q: 服务启动失败？**
A: 检查 Python 依赖是否安装完整，以及是否有数据库文件访问权限。

**Q: 令牌刷新失败？**
A: 检查网络连接，确保可以访问 Cursor 的 API 服务器。

## ⚠️ 注意事项

1. **首次运行**：确保 Cursor 已经正常登录，数据库中存在有效的 refresh token
2. **权限要求**：脚本需要读写 Cursor 数据库文件的权限
3. **网络要求**：需要能够访问 Cursor 的 API 服务器
4. **版本兼容**：如果 Cursor 更新后改变了数据库结构或 API，可能需要相应调整脚本
