#!/usr/bin/env python3
"""
调试 Deribit API 返回的数据结构
"""

import asyncio
import json
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.deribit_client import DeribitClient
from services.auth_service import AuthenticationService

async def debug_deribit_api():
    """调试 Deribit API 数据结构"""
    
    print("🔍 调试 Deribit API 数据结构...")
    print("=" * 60)
    
    # 初始化认证服务
    auth_service = AuthenticationService()
    
    # 认证账户
    account_name = "yq2024"
    print(f"🔐 认证账户: {account_name}")
    
    try:
        auth_result = await auth_service.authenticate_account(account_name)
        if not auth_result.success:
            print(f"❌ 认证失败: {auth_result.message}")
            return
        
        print("✅ 认证成功")
        
        # 创建 Deribit 客户端
        client = DeribitClient(auth_result.access_token, test_environment=True)
        
        # 获取 BTC 期权工具
        print("\n🔍 获取 BTC 期权工具...")
        instruments_response = await client.get_instruments("BTC", "option")
        
        if not instruments_response:
            print("❌ 无法获取期权工具")
            return
        
        print(f"📊 获取到 {len(instruments_response)} 个期权工具")
        
        # 检查前几个工具的数据结构
        print("\n📋 前 3 个期权工具的原始数据结构:")
        for i, instrument in enumerate(instruments_response[:3]):
            print(f"\n--- 工具 {i+1}: {instrument.get('instrument_name', 'Unknown')} ---")
            print(json.dumps(instrument, indent=2, ensure_ascii=False))
            
            # 检查关键字段
            print(f"🔍 关键字段检查:")
            print(f"   - instrument_name: {instrument.get('instrument_name')}")
            print(f"   - currency: {instrument.get('currency')}")  # 这个可能不存在
            print(f"   - base_currency: {instrument.get('base_currency')}")  # 可能是这个
            print(f"   - quote_currency: {instrument.get('quote_currency')}")  # 或者这个
            print(f"   - underlying_currency: {instrument.get('underlying_currency')}")  # 或者这个
            print(f"   - kind: {instrument.get('kind')}")
            print(f"   - option_type: {instrument.get('option_type')}")
            print(f"   - strike: {instrument.get('strike')}")
            print(f"   - expiration_timestamp: {instrument.get('expiration_timestamp')}")
            
        # 尝试解析一个工具
        print("\n🧪 尝试解析第一个工具...")
        if instruments_response:
            first_instrument = instruments_response[0]
            try:
                from models.deribit_types import DeribitOptionInstrument
                
                # 尝试直接解析
                parsed = DeribitOptionInstrument(**first_instrument)
                print("✅ 解析成功!")
                print(f"   - 工具名称: {parsed.instrument_name}")
                print(f"   - 货币: {parsed.currency}")
                print(f"   - 类型: {parsed.kind}")
                print(f"   - 期权类型: {parsed.option_type}")
                
            except Exception as e:
                print(f"❌ 解析失败: {e}")
                
                # 尝试添加缺失的字段
                print("\n🔧 尝试修复数据...")
                fixed_data = first_instrument.copy()
                
                # 如果没有 currency 字段，尝试从其他字段推导
                if 'currency' not in fixed_data:
                    if 'base_currency' in fixed_data:
                        fixed_data['currency'] = fixed_data['base_currency']
                        print(f"   - 从 base_currency 设置 currency: {fixed_data['currency']}")
                    elif 'underlying_currency' in fixed_data:
                        fixed_data['currency'] = fixed_data['underlying_currency']
                        print(f"   - 从 underlying_currency 设置 currency: {fixed_data['currency']}")
                    elif fixed_data.get('instrument_name', '').startswith('BTC-'):
                        fixed_data['currency'] = 'BTC'
                        print(f"   - 从工具名称推导 currency: BTC")
                
                try:
                    parsed = DeribitOptionInstrument(**fixed_data)
                    print("✅ 修复后解析成功!")
                    print(f"   - 工具名称: {parsed.instrument_name}")
                    print(f"   - 货币: {parsed.currency}")
                    print(f"   - 类型: {parsed.kind}")
                    print(f"   - 期权类型: {parsed.option_type}")
                except Exception as e2:
                    print(f"❌ 修复后仍然解析失败: {e2}")
        
    except Exception as e:
        print(f"❌ 调试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_deribit_api())
