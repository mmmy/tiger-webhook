#!/usr/bin/env python3
"""
测试 Deribit 下单 API
"""

import asyncio
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from deribit_webhook.services.deribit_client import DeribitClient
from deribit_webhook.services.auth_service import AuthenticationService

async def test_deribit_order():
    """测试 Deribit 下单"""
    
    print("🧪 测试 Deribit 下单 API...")
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
        
        # 测试参数
        instrument_name = "BTC-18SEP25-116000-C"
        amount = 1.0  # 先测试 1 个合约
        price = 0.0088
        
        print(f"\n📋 测试下单参数:")
        print(f"   - 合约: {instrument_name}")
        print(f"   - 数量: {amount}")
        print(f"   - 价格: {price}")
        
        # 尝试下单
        print(f"\n📡 发送买单...")
        try:
            response = await client.place_buy_order(
                instrument_name=instrument_name,
                amount=amount,
                account_name=account_name,
                type='limit',
                price=price
            )
            
            if response:
                print("✅ 下单成功!")
                print(f"📋 订单响应:")
                if hasattr(response, 'order'):
                    order = response.order
                    print(f"   - 订单ID: {order.get('order_id')}")
                    print(f"   - 状态: {order.get('order_state')}")
                    print(f"   - 合约: {order.get('instrument_name')}")
                    print(f"   - 数量: {order.get('amount')}")
                    print(f"   - 价格: {order.get('price')}")
                else:
                    print(f"   - 响应: {response}")
            else:
                print("❌ 下单失败: 无响应")
                
        except Exception as e:
            print(f"❌ 下单失败: {e}")
            
            # 尝试获取更多错误信息
            if "400" in str(e):
                print("\n🔍 可能的原因:")
                print("   - 数量不符合最小交易单位")
                print("   - 价格超出允许范围")
                print("   - 合约不存在或已过期")
                print("   - 账户余额不足")
                
                # 尝试获取合约信息
                print(f"\n📊 检查合约信息...")
                try:
                    instruments = await client.get_instruments("BTC", "option")
                    target_instrument = None
                    for inst in instruments:
                        if inst.instrument_name == instrument_name:
                            target_instrument = inst
                            break
                    
                    if target_instrument:
                        print(f"✅ 合约存在:")
                        print(f"   - 最小交易量: {target_instrument.min_trade_amount}")
                        print(f"   - 合约大小: {target_instrument.contract_size}")
                        print(f"   - Tick大小: {target_instrument.tick_size}")
                        print(f"   - 是否活跃: {target_instrument.is_active}")
                    else:
                        print(f"❌ 合约不存在: {instrument_name}")
                        
                except Exception as e2:
                    print(f"❌ 无法获取合约信息: {e2}")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deribit_order())
