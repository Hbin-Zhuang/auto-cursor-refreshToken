#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor State Database Analyzer
分析 Cursor 编辑器的 state.vscdb 数据库文件
"""

import sqlite3
import os
import json
import base64
from pathlib import Path


class CursorDBAnalyzer:
    def __init__(self, use_backup=True):
        base_path = "~/Library/Application Support/Cursor/User/globalStorage/"
        if use_backup:
            self.db_path = os.path.expanduser(base_path + "state.vscdb.backup")
        else:
            self.db_path = os.path.expanduser(base_path + "state.vscdb")
        self.conn = None
    
    def connect(self):
        """连接到数据库"""
        if not os.path.exists(self.db_path):
            print(f"❌ 数据库文件不存在: {self.db_path}")
            return False
        
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"✅ 成功连接到数据库: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")
            return False
    
    def get_tables(self):
        """获取所有表名"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            return tables
        except Exception as e:
            print(f"❌ 获取表名失败: {e}")
            return []
    
    def get_table_schema(self, table_name):
        """获取表结构"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            return columns
        except Exception as e:
            print(f"❌ 获取表结构失败: {e}")
            return []
    
    def get_table_data(self, table_name, limit=10):
        """获取表数据"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
            data = cursor.fetchall()
            return data
        except Exception as e:
            print(f"❌ 获取表数据失败: {e}")
            return []
    
    def analyze_data_content(self, data):
        """分析数据内容，检测可能的加密或编码"""
        analysis = {
            'has_json': False,
            'has_base64': False,
            'has_binary': False,
            'has_encrypted': False,
            'token_like': False
        }
        
        for row in data:
            for cell in row:
                if cell is None:
                    continue
                
                cell_str = str(cell)
                
                # 检测 JSON
                if cell_str.startswith('{') or cell_str.startswith('['):
                    try:
                        json.loads(cell_str)
                        analysis['has_json'] = True
                    except:
                        pass
                
                # 检测 Base64
                if len(cell_str) > 20 and cell_str.replace('=', '').replace('+', '').replace('/', '').isalnum():
                    try:
                        base64.b64decode(cell_str)
                        analysis['has_base64'] = True
                    except:
                        pass
                
                # 检测二进制数据
                if isinstance(cell, bytes):
                    analysis['has_binary'] = True
                
                # 检测可能的 token
                if len(cell_str) > 50 and ('token' in cell_str.lower() or 
                                         cell_str.startswith('ey') or  # JWT 特征
                                         'bearer' in cell_str.lower()):
                    analysis['token_like'] = True
                
                # 检测可能的加密数据（随机字符串）
                if len(cell_str) > 30 and not any(c.isspace() for c in cell_str):
                    if sum(c.isalnum() for c in cell_str) / len(cell_str) > 0.8:
                        analysis['has_encrypted'] = True
        
        return analysis
    
    def search_auth_data(self):
        """搜索认证相关数据"""
        auth_keywords = ['token', 'auth', 'login', 'session', 'bearer', 'jwt', 'refresh']
        results = []
        
        tables = self.get_tables()
        for table in tables:
            try:
                cursor = self.conn.cursor()
                # 搜索键名包含认证关键词的数据
                for keyword in auth_keywords:
                    cursor.execute(f"SELECT * FROM {table} WHERE key LIKE '%{keyword}%' OR value LIKE '%{keyword}%';")
                    rows = cursor.fetchall()
                    if rows:
                        results.append({
                            'table': table,
                            'keyword': keyword,
                            'count': len(rows),
                            'data': rows[:3]  # 只显示前3条
                        })
            except Exception as e:
                continue
        
        return results
    
    def run_analysis(self):
        """运行完整分析"""
        if not self.connect():
            return
        
        print("\n" + "="*50)
        print("🔍 Cursor State Database 分析报告")
        print("="*50)
        
        # 1. 基本信息
        file_size = os.path.getsize(self.db_path)
        print(f"\n📁 文件信息:")
        print(f"   路径: {self.db_path}")
        print(f"   大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # 2. 表结构
        tables = self.get_tables()
        print(f"\n📊 数据库结构:")
        print(f"   表数量: {len(tables)}")
        print(f"   表名: {', '.join(tables)}")
        
        # 3. 详细分析每个表
        for table in tables:
            print(f"\n🔸 表: {table}")
            
            # 表结构
            schema = self.get_table_schema(table)
            print("   列结构:")
            for col in schema:
                print(f"     - {col[1]} ({col[2]})")
            
            # 数据样本
            data = self.get_table_data(table, 5)
            print(f"   数据行数: {len(data)}")
            
            if data:
                # 分析数据内容
                analysis = self.analyze_data_content(data)
                print("   数据特征:")
                for feature, has_feature in analysis.items():
                    if has_feature:
                        print(f"     ✓ {feature}")
                
                # 显示部分数据（脱敏）
                print("   数据样本:")
                for i, row in enumerate(data[:3]):
                    masked_row = []
                    for cell in row:
                        if cell is None:
                            masked_row.append("NULL")
                        elif len(str(cell)) > 50:
                            masked_row.append(f"{str(cell)[:20]}...({len(str(cell))} chars)")
                        else:
                            masked_row.append(str(cell))
                    print(f"     {i+1}: {masked_row}")
        
        # 4. 搜索认证数据
        print(f"\n🔐 认证数据搜索:")
        auth_results = self.search_auth_data()
        if auth_results:
            for result in auth_results:
                print(f"   在表 '{result['table']}' 中发现 {result['count']} 条包含 '{result['keyword']}' 的记录")
        else:
            print("   未发现明显的认证相关数据")
        
        # 5. 安全性评估
        print(f"\n🛡️  安全性评估:")
        print("   - 数据库未加密（SQLite 明文存储）")
        print("   - 敏感数据可能存在，建议谨慎处理")
        print("   - 建议备份后再进行任何修改操作")
        
        self.conn.close()


if __name__ == "__main__":
    print("选择要分析的文件:")
    print("1. state.vscdb.backup (推荐，更安全)")
    print("2. state.vscdb (当前文件)")
    
    choice = input("请选择 (1/2，默认1): ").strip() or "1"
    use_backup = choice == "1"
    
    analyzer = CursorDBAnalyzer(use_backup=use_backup)
    analyzer.run_analysis()
