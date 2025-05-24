#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Authentication Data Extractor
专门提取和分析 Cursor 的认证相关数据
"""

import sqlite3
import os
import json
import re
from datetime import datetime


class CursorAuthExtractor:
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
            print(f"✅ 成功连接到数据库")
            return True
        except Exception as e:
            print(f"❌ 连接数据库失败: {e}")
            return False

    def extract_auth_tokens(self):
        """提取认证token"""
        print("\n🔐 提取认证 Tokens...")

        # 搜索可能包含token的键
        token_patterns = [
            'token', 'accessToken', 'access_token', 'refreshToken', 'refresh_token',
            'authToken', 'auth_token', 'bearerToken', 'bearer_token', 'jwt'
        ]

        results = {}

        for table in ['ItemTable', 'cursorDiskKV']:
            print(f"\n📊 分析表: {table}")
            results[table] = {}

            try:
                cursor = self.conn.cursor()
                cursor.execute(f"SELECT key, value FROM {table}")
                rows = cursor.fetchall()

                for key, value in rows:
                    key_lower = key.lower()

                    # 检查键名是否包含token相关词汇
                    for pattern in token_patterns:
                        if pattern in key_lower:
                            token_info = self.analyze_token_value(key, value)
                            if token_info:
                                results[table][key] = token_info
                            break

                    # 检查值是否为JSON并包含token
                    if isinstance(value, (str, bytes)):
                        try:
                            if isinstance(value, bytes):
                                value_str = value.decode('utf-8', errors='ignore')
                            else:
                                value_str = value

                            if value_str.strip().startswith('{'):
                                json_data = json.loads(value_str)
                                token_info = self.extract_tokens_from_json(key, json_data)
                                if token_info:
                                    results[table][key] = token_info
                        except:
                            pass

            except Exception as e:
                print(f"❌ 分析表 {table} 失败: {e}")

        return results

    def analyze_token_value(self, key, value):
        """分析token值"""
        try:
            if isinstance(value, bytes):
                value_str = value.decode('utf-8', errors='ignore')
            else:
                value_str = str(value)

            # 尝试解析为JSON
            if value_str.strip().startswith('{'):
                try:
                    json_data = json.loads(value_str)
                    return {
                        'type': 'json',
                        'length': len(value_str),
                        'preview': value_str[:100] + '...' if len(value_str) > 100 else value_str,
                        'json_keys': list(json_data.keys()) if isinstance(json_data, dict) else None
                    }
                except:
                    pass

            # 直接token值
            return {
                'type': 'direct',
                'length': len(value_str),
                'preview': value_str[:50] + '...' if len(value_str) > 50 else value_str,
                'looks_like_jwt': value_str.startswith('ey') and value_str.count('.') >= 2,
                'looks_like_bearer': 'bearer' in value_str.lower()
            }

        except Exception as e:
            return None

    def extract_tokens_from_json(self, key, json_data):
        """从JSON数据中提取token"""
        if not isinstance(json_data, dict):
            return None

        found_tokens = {}
        token_keys = ['token', 'accessToken', 'access_token', 'refreshToken', 'refresh_token',
                     'authToken', 'auth_token', 'bearerToken', 'bearer_token', 'jwt']

        def search_dict(data, path=""):
            if isinstance(data, dict):
                for k, v in data.items():
                    current_path = f"{path}.{k}" if path else k
                    if k.lower() in [tk.lower() for tk in token_keys]:
                        found_tokens[current_path] = {
                            'value': str(v)[:100] + '...' if len(str(v)) > 100 else str(v),
                            'length': len(str(v)),
                            'looks_like_jwt': str(v).startswith('ey') and str(v).count('.') >= 2
                        }
                    elif isinstance(v, (dict, list)):
                        search_dict(v, current_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    search_dict(item, f"{path}[{i}]")

        search_dict(json_data)

        if found_tokens:
            return {
                'type': 'json_with_tokens',
                'tokens_found': found_tokens,
                'json_size': len(str(json_data))
            }

        return None

    def find_cursor_specific_auth(self):
        """查找 Cursor 特定的认证信息"""
        print("\n🎯 查找 Cursor 特定认证信息...")

        cursor_patterns = [
            'cursor', 'openai', 'anthropic', 'copilot', 'auth', 'user', 'account'
        ]

        results = []

        try:
            cursor = self.conn.cursor()

            for pattern in cursor_patterns:
                cursor.execute(f"SELECT key, value FROM ItemTable WHERE key LIKE '%{pattern}%'")
                rows = cursor.fetchall()

                for key, value in rows:
                    if 'token' in str(value).lower() or 'auth' in str(value).lower():
                        results.append({
                            'table': 'ItemTable',
                            'key': key,
                            'pattern': pattern,
                            'value_preview': str(value)[:200] + '...' if len(str(value)) > 200 else str(value)
                        })

        except Exception as e:
            print(f"❌ 搜索失败: {e}")

        return results

    def run_extraction(self):
        """运行完整提取"""
        if not self.connect():
            return

        print("\n" + "="*60)
        print("🔐 Cursor 认证数据提取报告")
        print("="*60)

        # 1. 提取所有认证tokens
        auth_results = self.extract_auth_tokens()

        for table, tokens in auth_results.items():
            if tokens:
                print(f"\n📋 表 {table} 中的认证数据:")
                for key, info in list(tokens.items())[:10]:  # 限制显示前10个
                    print(f"   🔑 {key}")
                    print(f"      类型: {info['type']}")
                    if info['type'] == 'json_with_tokens':
                        print(f"      JSON大小: {info['json_size']} 字符")
                        print(f"      发现的tokens:")
                        for token_path, token_info in info['tokens_found'].items():
                            print(f"        - {token_path}: {token_info['value']} (长度: {token_info['length']})")
                    else:
                        print(f"      长度: {info['length']}")
                        print(f"      预览: {info['preview']}")
                        if info.get('looks_like_jwt'):
                            print(f"      ✓ 疑似JWT token")
                        if info.get('looks_like_bearer'):
                            print(f"      ✓ 疑似Bearer token")
                    print()

        # 2. 查找 Cursor 特定认证
        cursor_auth = self.find_cursor_specific_auth()
        if cursor_auth:
            print(f"\n🎯 Cursor 特定认证信息:")
            for item in cursor_auth[:5]:  # 限制显示前5个
                print(f"   🔸 {item['key']}")
                print(f"      匹配模式: {item['pattern']}")
                print(f"      内容: {item['value_preview']}")
                print()

        # 3. 统计总结
        total_tokens = sum(len(tokens) for tokens in auth_results.values())
        print(f"\n📊 统计总结:")
        print(f"   发现认证相关条目: {total_tokens} 条")
        print(f"   Cursor特定认证: {len(cursor_auth)} 条")
        print(f"   建议重点关注: ItemTable 中的基础认证和 cursorDiskKV 中的详细token")

        self.conn.close()


if __name__ == "__main__":
    print("🔍 Cursor 认证数据提取工具")
    print("这个工具会专门搜索和分析认证相关的数据")

    choice = input("\n使用备份文件? (y/n, 默认y): ").strip().lower()
    use_backup = choice != 'n'

    extractor = CursorAuthExtractor(use_backup=use_backup)
    extractor.run_extraction()
