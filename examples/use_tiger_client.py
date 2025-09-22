#!/usr/bin/env python3
"""
使用现有TigerClient类获取期权数据的完整示例
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.deribit_webhook.services.tiger_client import TigerClient


async def demo_tiger_client():
    """演示TigerClient的期权数据获取功能"""
    client = TigerClient()
    
    try:
        print("=" * 80)
        print("TigerClient 期权数据获取演示")
        print("=" * 80)
        
        # 1. 获取期权标的列表 (Tiger主要支持香港市场)
        print("\n🔍 步骤1: 获取期权标的列表")
        print("💡 注意: Tiger目前主要支持香港市场(HK)的期权数据")
        underlyings = await client.get_option_underlyings(market="HK")
        
        if underlyings:
            print(f"✅ 成功获取 {len(underlyings)} 个期权标的")
            print("\n📊 可用期权标的 (前15个):")
            for i, underlying in enumerate(underlyings[:15]):
                print(f"  {i+1:2d}. {underlying['symbol']:8s} - {underlying['name']}")
        else:
            print("❌ 未能获取期权标的列表")
            return

        # 2. 选择一个标的获取到期日 (使用香港市场的股票)
        # 常见的香港期权标的: 腾讯(700), 阿里巴巴(9988), 美团(3690), 小米(1810)等
        demo_symbols = ["700", "9988", "3690", "1810", "2318", "1299"]  # 香港股票代码
        available_symbol = None

        for symbol in demo_symbols:
            if any(u['symbol'] == symbol for u in underlyings):
                available_symbol = symbol
                break

        if not available_symbol:
            available_symbol = underlyings[0]['symbol']
        
        print(f"\n🔍 步骤2: 获取 {available_symbol} 的期权到期日")
        expirations = await client.get_option_expirations(available_symbol)
        
        if expirations:
            print(f"✅ 找到 {len(expirations)} 个到期日")
            print("\n📅 近期到期日 (前8个):")
            for i, exp in enumerate(expirations[:8]):
                print(f"  {i+1}. {exp['date']} (时间戳: {exp['timestamp']})")
        else:
            print(f"❌ 未能获取 {available_symbol} 的到期日")
            return
        
        # 3. 获取指定到期日的期权链
        target_expiry = expirations[0]['timestamp']
        print(f"\n🔍 步骤3: 获取 {available_symbol} 到期日 {expirations[0]['date']} 的期权链")
        
        options = await client.get_instruments(
            underlying_symbol=available_symbol,
            expiry_timestamp=target_expiry
        )
        
        if options:
            print(f"✅ 获取到 {len(options)} 个期权合约")
            
            # 分析期权数据
            calls = [opt for opt in options if opt.get('option_type') == 'call']
            puts = [opt for opt in options if opt.get('option_type') == 'put']
            
            print(f"\n📊 期权合约统计:")
            print(f"  看涨期权 (Calls): {len(calls)} 个")
            print(f"  看跌期权 (Puts):  {len(puts)} 个")
            
            # 显示部分看涨期权
            if calls:
                print(f"\n📈 部分看涨期权 (前5个):")
                for i, call in enumerate(calls[:5]):
                    strike = call.get('strike', 0)
                    name = call.get('instrument_name', 'N/A')
                    print(f"  {i+1}. {name} - 行权价: ${strike:.2f}")
            
            # 显示部分看跌期权
            if puts:
                print(f"\n📉 部分看跌期权 (前5个):")
                for i, put in enumerate(puts[:5]):
                    strike = put.get('strike', 0)
                    name = put.get('instrument_name', 'N/A')
                    print(f"  {i+1}. {name} - 行权价: ${strike:.2f}")
        else:
            print(f"❌ 未能获取期权链数据")
        
        # 4. 获取期权报价 (如果有期权合约)
        if options:
            sample_option = options[0]
            option_name = sample_option.get('instrument_name')
            
            print(f"\n🔍 步骤4: 获取期权报价示例")
            print(f"获取 {option_name} 的实时报价...")
            
            ticker = await client.get_ticker(option_name)
            
            if ticker:
                print(f"✅ 报价获取成功:")
                print(f"  买价: ${ticker.get('best_bid_price', 0):.4f}")
                print(f"  卖价: ${ticker.get('best_ask_price', 0):.4f}")
                print(f"  最新价: ${ticker.get('last_price', 0):.4f}")
                print(f"  隐含波动率: {ticker.get('mark_iv', 0):.2%}")
                
                greeks = ticker.get('greeks', {})
                if greeks:
                    print(f"  希腊字母:")
                    print(f"    Delta: {greeks.get('delta', 0):.4f}")
                    print(f"    Gamma: {greeks.get('gamma', 0):.4f}")
                    print(f"    Theta: {greeks.get('theta', 0):.4f}")
                    print(f"    Vega:  {greeks.get('vega', 0):.4f}")
            else:
                print(f"❌ 未能获取期权报价")
        
        print("\n" + "=" * 80)
        print("✅ 演示完成!")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


async def search_specific_options():
    """搜索特定条件的期权"""
    client = TigerClient()
    
    try:
        print("\n" + "=" * 80)
        print("🔍 搜索特定条件的期权示例")
        print("=" * 80)
        
        # 搜索香港股票的期权，最少7天到期，delta接近0.3的看涨期权
        print("\n搜索条件:")
        print("- 标的: 700 (腾讯控股)")
        print("- 最少到期天数: 7天")
        print("- 目标Delta: 0.3")
        print("- 类型: 看涨期权")

        result = await client.get_instrument_by_delta(
            currency="HKD",
            min_expired_days=7,
            delta=0.3,
            long_side=True,  # True=看涨, False=看跌
            underlying_asset="700"  # 腾讯控股
        )
        
        if result:
            instrument = result.instrument
            details = result.details
            
            print(f"\n✅ 找到匹配的期权:")
            print(f"  合约名称: {instrument.instrument_name}")
            print(f"  最小价格变动: ${instrument.tick_size}")
            print(f"  最小交易数量: {instrument.min_trade_amount}")
            print(f"  计价货币: {instrument.quote_currency}")
            
            print(f"\n📊 市场数据:")
            print(f"  买价: ${details.best_bid_price:.4f}")
            print(f"  卖价: ${details.best_ask_price:.4f}")
            print(f"  标的价格: ${details.index_price:.2f}")
            print(f"  买卖价差比例: {result.spread_ratio:.2%}")
        else:
            print("❌ 未找到符合条件的期权")
    
    except Exception as e:
        print(f"❌ 搜索期权时发生错误: {e}")
    
    finally:
        await client.close()


async def main():
    """主函数"""
    # 运行基本演示
    await demo_tiger_client()
    
    # 运行特定搜索演示
    await search_specific_options()


if __name__ == "__main__":
    asyncio.run(main())
