#!/usr/bin/env python3
"""
检查合约信息
"""

import asyncio
import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.deribit_client import DeribitClient
from services.auth_service import AuthenticationService

async def check_contract_info():
    """检查合约信息"""
    
    print("🔍 检查合约信息...")
    print("=" * 60)
    
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
        
        # 创建 Deribit 客户端
        client = DeribitClient()
        
        # 目标合约
        target_instrument = "BTC-18SEP25-116000-C"
        
        print(f"\n📋 检查合约: {target_instrument}")
        
        # 获取所有 BTC 期权
        instruments = await client.get_instruments("BTC", "option")
        
        found_instrument = None
        for inst in instruments:
            if inst.instrument_name == target_instrument:
                found_instrument = inst
                break
        
        if found_instrument:
            print(f"✅ 找到合约: {target_instrument}")
            print(f"📊 合约信息:")
            print(f"   - 合约名称: {found_instrument.instrument_name}")
            print(f"   - 基础货币: {found_instrument.base_currency}")
            print(f"   - 计价货币: {found_instrument.quote_currency}")
            print(f"   - 期权类型: {found_instrument.option_type}")
            print(f"   - 行权价: {found_instrument.strike}")
            print(f"   - 到期时间: {found_instrument.expiration_timestamp}")
            print(f"   - 最小交易量: {found_instrument.min_trade_amount}")
            print(f"   - 合约大小: {found_instrument.contract_size}")
            print(f"   - Tick大小: {found_instrument.tick_size}")
            print(f"   - 是否活跃: {found_instrument.is_active}")
            
            # 获取详细信息
            print(f"\n📊 获取详细市场数据...")
            details = await client.get_option_details(target_instrument)
            if details:
                print(f"   - 标记价格: {details.mark_price}")
                print(f"   - 最佳买价: {details.best_bid_price}")
                print(f"   - 最佳卖价: {details.best_ask_price}")
                print(f"   - Delta: {details.greeks.delta}")
                print(f"   - 指数价格: {details.index_price}")
                
                # 计算合理的交易量
                min_amount = found_instrument.min_trade_amount
                print(f"\n💡 建议:")
                print(f"   - 最小交易量: {min_amount}")
                print(f"   - 建议使用 {min_amount} 或其倍数")
                
                # 计算价格范围
                tick_size = found_instrument.tick_size
                bid = details.best_bid_price
                ask = details.best_ask_price
                
                if bid > 0 and ask > 0:
                    mid_price = (bid + ask) / 2
                    # 调整到 tick size
                    adjusted_price = round(mid_price / tick_size) * tick_size
                    print(f"   - 中间价: {mid_price}")
                    print(f"   - 调整后价格: {adjusted_price}")
                    print(f"   - Tick大小: {tick_size}")
            else:
                print("❌ 无法获取详细信息")
        else:
            print(f"❌ 未找到合约: {target_instrument}")
            print(f"📋 可用的类似合约:")
            similar_contracts = [inst for inst in instruments if "116000-C" in inst.instrument_name][:5]
            for inst in similar_contracts:
                print(f"   - {inst.instrument_name} (活跃: {inst.is_active})")
        
    except Exception as e:
        print(f"❌ 检查过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_contract_info())
