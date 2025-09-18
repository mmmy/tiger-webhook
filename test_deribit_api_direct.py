#!/usr/bin/env python3
"""
直接测试 Deribit API 调用
"""

import asyncio
import sys
import os
import httpx
from dotenv import load_dotenv

# 切换到 src 目录
src_dir = os.path.join(os.path.dirname(__file__), 'src')
os.chdir(src_dir)

# 加载环境变量
load_dotenv('../.env.test')

# 添加 src 目录到路径
sys.path.insert(0, '.')

from services.auth_service import AuthenticationService
from config.settings import settings

async def test_deribit_api_direct():
    """直接测试 Deribit API"""
    
    print("🧪 直接测试 Deribit API...")
    print("=" * 60)
    print(f"🔧 Mock Mode: {settings.use_mock_mode}")
    print(f"🔧 Test Environment: {settings.use_test_environment}")
    print(f"🔧 API Key File: {settings.api_key_file}")
    print(f"🔧 Current Working Directory: {os.getcwd()}")
    
    # 初始化认证服务
    auth_service = AuthenticationService()
    
    # 认证账户
    account_name = "yq2024"
    print(f"🔐 认证账户: {account_name}")
    
    try:
        auth_result = await auth_service.ensure_authenticated(account_name)
        if not auth_result:
            print(f"❌ 认证失败")
            return
        
        print("✅ 认证成功")
        print(f"🔑 Access Token: {auth_result.access_token[:20]}...")
        
        # 测试参数
        params = {
            "instrument_name": "BTC-18SEP25-116000-C",
            "amount": 0.1,
            "type": "limit",
            "price": 0.0090  # 测试简单价格
        }
        
        print(f"\n📋 测试参数:")
        for key, value in params.items():
            print(f"   - {key}: {value}")
        
        # 直接调用 Deribit API
        base_url = "https://test.deribit.com"
        url = f"{base_url}/api/v2/private/buy"
        
        headers = {
            "Authorization": f"Bearer {auth_result.access_token}",
            "Content-Type": "application/json"
        }
        
        print(f"\n📡 发送请求到: {url}")
        print(f"🔑 Headers: Authorization: Bearer {auth_result.access_token[:20]}...")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                
                print(f"📊 响应状态码: {response.status_code}")
                print(f"📋 响应头: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.json()
                    print("✅ 下单成功!")
                    print(f"📋 响应数据:")
                    print(f"   - 结果: {result}")
                else:
                    print("❌ 下单失败!")
                    try:
                        error_data = response.json()
                        print(f"📋 错误详情:")
                        print(f"   - 错误代码: {error_data.get('error', {}).get('code')}")
                        print(f"   - 错误消息: {error_data.get('error', {}).get('message')}")
                        print(f"   - 错误数据: {error_data.get('error', {}).get('data')}")
                    except:
                        print(f"📋 原始响应: {response.text}")
                        
            except httpx.TimeoutException:
                print("❌ 请求超时")
            except Exception as e:
                print(f"❌ 请求失败: {e}")
        
        # 尝试获取账户信息
        print(f"\n🔍 检查账户信息...")
        account_url = f"{base_url}/api/v2/private/get_account_summary"
        account_params = {"currency": "BTC", "extended": True}
        
        async with httpx.AsyncClient() as client:
            try:
                account_response = await client.get(account_url, params=account_params, headers=headers, timeout=30.0)
                
                if account_response.status_code == 200:
                    account_data = account_response.json()
                    result = account_data.get('result', {})
                    print(f"✅ 账户信息:")
                    print(f"   - 余额: {result.get('balance', 0)} BTC")
                    print(f"   - 可用余额: {result.get('available_funds', 0)} BTC")
                    print(f"   - 权益: {result.get('equity', 0)} BTC")
                    print(f"   - 维持保证金: {result.get('maintenance_margin', 0)} BTC")
                else:
                    print(f"❌ 无法获取账户信息: {account_response.status_code}")
                    print(f"   - 响应: {account_response.text}")
                    
            except Exception as e:
                print(f"❌ 获取账户信息失败: {e}")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deribit_api_direct())
