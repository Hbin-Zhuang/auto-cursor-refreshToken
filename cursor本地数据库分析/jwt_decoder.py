#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JWT Token Decoder and Analyzer
解码和分析JWT token的工具
"""

import base64
import json
from datetime import datetime


class JWTAnalyzer:
    @staticmethod
    def decode_jwt_payload(jwt_token):
        """解码JWT token的payload部分"""
        try:
            # JWT格式: header.payload.signature
            parts = jwt_token.split('.')
            if len(parts) != 3:
                return None, "不是有效的JWT格式"
            
            # 解码payload (第二部分)
            payload = parts[1]
            
            # 添加必要的padding
            payload += '=' * (4 - len(payload) % 4)
            
            # Base64解码
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded_json = json.loads(decoded_bytes.decode('utf-8'))
            
            return decoded_json, None
            
        except Exception as e:
            return None, f"解码失败: {str(e)}"
    
    @staticmethod
    def analyze_token_expiry(payload):
        """分析token过期时间"""
        if not payload:
            return None
        
        exp_timestamp = payload.get('exp')
        iat_timestamp = payload.get('iat') 
        
        result = {}
        
        if exp_timestamp:
            exp_time = datetime.fromtimestamp(exp_timestamp)
            now = datetime.now()
            result['expires_at'] = exp_time.strftime('%Y-%m-%d %H:%M:%S')
            result['is_expired'] = exp_time < now
            result['time_until_expiry'] = str(exp_time - now) if exp_time > now else "已过期"
        
        if iat_timestamp:
            iat_time = datetime.fromtimestamp(iat_timestamp)
            result['issued_at'] = iat_time.strftime('%Y-%m-%d %H:%M:%S')
            result['age'] = str(datetime.now() - iat_time)
        
        return result
    
    @staticmethod
    def analyze_cursor_tokens():
        """分析Cursor的token"""
        print("🔍 JWT Token 分析工具")
        print("="*50)
        
        print("\n请提供要分析的JWT token:")
        print("1. 输入 refreshToken (长效token)")
        print("2. 输入 accessToken (短效token)")
        print("3. 或者输入任何其他JWT token")
        print("\n注意: token只用于本地分析，不会发送到任何服务器")
        
        token_types = ['refreshToken', 'accessToken']
        
        for token_type in token_types:
            print(f"\n📝 请输入 {token_type} (回车跳过):")
            token = input().strip()
            
            if not token:
                print(f"⏭️  跳过 {token_type}")
                continue
            
            payload, error = JWTAnalyzer.decode_jwt_payload(token)
            
            if error:
                print(f"❌ {token_type} 解码失败: {error}")
                continue
            
            print(f"\n🎯 {token_type} 分析结果:")
            print("-" * 30)
            
            # 基本信息
            print("📋 Token 内容:")
            for key, value in payload.items():
                if key in ['sub', 'aud', 'iss', 'jti']:
                    print(f"   {key}: {value}")
                elif key in ['exp', 'iat', 'nbf']:
                    readable_time = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"   {key}: {value} ({readable_time})")
                else:
                    # 截断长值
                    str_value = str(value)
                    if len(str_value) > 50:
                        str_value = str_value[:50] + "..."
                    print(f"   {key}: {str_value}")
            
            # 过期分析
            expiry_info = JWTAnalyzer.analyze_token_expiry(payload)
            if expiry_info:
                print(f"\n⏰ 时间分析:")
                for key, value in expiry_info.items():
                    print(f"   {key}: {value}")
            
            # Token类型推断
            print(f"\n🔍 Token 类型推断:")
            if 'exp' in payload and 'iat' in payload:
                duration_seconds = payload['exp'] - payload['iat']
                duration_hours = duration_seconds / 3600
                duration_days = duration_hours / 24
                
                print(f"   有效期: {duration_seconds}秒 ({duration_hours:.1f}小时, {duration_days:.1f}天)")
                
                if duration_days > 30:
                    print(f"   🔹 可能是长效token (>30天)")
                elif duration_hours < 24:
                    print(f"   🔸 可能是短效token (<24小时)")
                else:
                    print(f"   🔶 中等有效期token")
            
            print()

if __name__ == "__main__":
    analyzer = JWTAnalyzer()
    analyzer.analyze_cursor_tokens()
