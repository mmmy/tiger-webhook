#!/usr/bin/env python3
"""
Tiger Brokers 香港期权完整指南

Tiger目前主要支持香港市场的期权数据，本示例展示如何获取和使用香港期权数据
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.deribit_webhook.services.tiger_client import TigerClient


async def get_hk_option_underlyings():
    """获取香港期权标的列表"""
    client = TigerClient()
    
    try:
        print("=" * 80)
        print("Tiger Brokers 香港期权标的获取")
        print("=" * 80)
        
        print("🔍 获取香港市场期权标的...")
        
        # 尝试不同的方式获取期权标的
        methods = [
            ("HK", "指定香港市场"),
            (None, "默认市场")
        ]
        
        underlyings = None
        for market, desc in methods:
            try:
                print(f"\n📊 尝试方法: {desc}")
                underlyings = await client.get_option_underlyings(market=market)
                if underlyings:
                    print(f"✅ 成功获取 {len(underlyings)} 个期权标的")
                    break
                else:
                    print(f"⚠️ 该方法未获取到数据")
            except Exception as e:
                print(f"❌ 该方法失败: {e}")
        
        if not underlyings:
            print("❌ 所有方法都失败，无法获取期权标的")
            return []
        
        print(f"\n📈 香港期权标的列表 (共 {len(underlyings)} 个):")
        print("-" * 80)
        
        # 按类别显示
        categories = {
            "蓝筹股": ["700", "9988", "1299", "2318", "3690", "1810", "2020", "1024"],
            "科技股": ["700", "9988", "1024", "1810", "3690", "2382"],
            "金融股": ["1299", "2318", "2388", "1398", "3988"],
            "其他": []
        }
        
        # 分类显示
        for category, known_symbols in categories.items():
            if category == "其他":
                # 显示不在已知分类中的股票
                other_stocks = [u for u in underlyings if u['symbol'] not in sum(categories.values(), [])]
                if other_stocks:
                    print(f"\n{category}:")
                    for i, underlying in enumerate(other_stocks[:10]):
                        print(f"  {underlying['symbol']:6s} - {underlying['name']}")
            else:
                # 显示已知分类的股票
                category_stocks = [u for u in underlyings if u['symbol'] in known_symbols]
                if category_stocks:
                    print(f"\n{category}:")
                    for underlying in category_stocks:
                        print(f"  {underlying['symbol']:6s} - {underlying['name']}")
        
        return underlyings
        
    except Exception as e:
        print(f"❌ 获取香港期权标的失败: {e}")
        return []
    finally:
        await client.close()


async def analyze_hk_option(symbol: str, symbol_name: str):
    """分析指定香港股票的期权数据"""
    client = TigerClient()
    
    try:
        print(f"\n" + "=" * 80)
        print(f"分析 {symbol} ({symbol_name}) 的期权数据")
        print("=" * 80)
        
        # 1. 获取到期日
        print(f"\n🔍 步骤1: 获取 {symbol} 的期权到期日")
        expirations = await client.get_option_expirations(symbol)
        
        if not expirations:
            print(f"❌ 未找到 {symbol} 的期权到期日")
            return
        
        print(f"✅ 找到 {len(expirations)} 个到期日:")
        for i, exp in enumerate(expirations[:8]):
            print(f"  {i+1:2d}. {exp['date']} (时间戳: {exp['timestamp']})")
        
        # 2. 获取最近到期日的期权链
        nearest_expiry = expirations[0]
        print(f"\n🔍 步骤2: 获取最近到期日 {nearest_expiry['date']} 的期权链")
        
        options = await client.get_instruments(symbol, expiry_timestamp=nearest_expiry['timestamp'])
        
        if not options:
            print(f"❌ 未获取到期权链数据")
            return
        
        # 分析期权数据
        calls = [opt for opt in options if opt.get('option_type') == 'call']
        puts = [opt for opt in options if opt.get('option_type') == 'put']
        
        print(f"✅ 期权链分析:")
        print(f"  总期权数: {len(options)} 个")
        print(f"  看涨期权: {len(calls)} 个")
        print(f"  看跌期权: {len(puts)} 个")
        
        # 显示行权价分布
        if options:
            strikes = sorted(set(opt.get('strike', 0) for opt in options))
            print(f"  行权价范围: ${min(strikes):.2f} - ${max(strikes):.2f}")
            print(f"  行权价数量: {len(strikes)} 个")
        
        # 3. 显示部分期权详情
        print(f"\n📊 部分看涨期权详情:")
        for i, call in enumerate(calls[:5]):
            name = call.get('instrument_name', 'N/A')
            strike = call.get('strike', 0)
            print(f"  {i+1}. {name} - 行权价: ${strike:.2f}")
        
        print(f"\n📊 部分看跌期权详情:")
        for i, put in enumerate(puts[:5]):
            name = put.get('instrument_name', 'N/A')
            strike = put.get('strike', 0)
            print(f"  {i+1}. {name} - 行权价: ${strike:.2f}")
        
        # 4. 获取一个期权的实时报价
        if options:
            sample_option = options[len(options)//2]  # 选择中间的期权
            option_name = sample_option.get('instrument_name')
            
            print(f"\n🔍 步骤3: 获取期权实时报价")
            print(f"选择期权: {option_name}")
            
            ticker = await client.get_ticker(option_name)
            
            if ticker:
                print(f"✅ 实时报价:")
                print(f"  买价: ${ticker.get('best_bid_price', 0):.4f}")
                print(f"  卖价: ${ticker.get('best_ask_price', 0):.4f}")
                print(f"  最新价: ${ticker.get('last_price', 0):.4f}")
                print(f"  成交量: {ticker.get('volume', 0)}")
                print(f"  未平仓量: {ticker.get('open_interest', 0)}")
                
                # 希腊字母
                greeks = ticker.get('greeks', {})
                if any(greeks.values()):
                    print(f"  希腊字母:")
                    print(f"    Delta: {greeks.get('delta', 0):.4f}")
                    print(f"    Gamma: {greeks.get('gamma', 0):.4f}")
                    print(f"    Theta: {greeks.get('theta', 0):.4f}")
                    print(f"    Vega:  {greeks.get('vega', 0):.4f}")
                
                # 隐含波动率
                iv = ticker.get('mark_iv', 0)
                if iv > 0:
                    print(f"  隐含波动率: {iv:.2%}")
            else:
                print(f"❌ 未能获取实时报价")
        
    except Exception as e:
        print(f"❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


async def main():
    """主函数"""
    # 1. 获取香港期权标的列表
    underlyings = await get_hk_option_underlyings()
    
    if not underlyings:
        print("\n❌ 无法获取期权标的，程序退出")
        return
    
    # 2. 分析几个热门股票的期权
    popular_stocks = [
        ("700", "腾讯控股"),
        ("9988", "阿里巴巴-SW"),
        ("3690", "美团-W"),
        ("1810", "小米集团-W")
    ]
    
    for symbol, name in popular_stocks:
        # 检查该股票是否有期权
        if any(u['symbol'] == symbol for u in underlyings):
            await analyze_hk_option(symbol, name)
            break  # 只分析第一个找到的股票
    
    print(f"\n" + "=" * 80)
    print("💡 使用提示:")
    print("1. Tiger目前主要支持香港市场的期权")
    print("2. 香港期权以港币(HKD)计价")
    print("3. 常见的期权标的包括腾讯(700)、阿里巴巴(9988)等")
    print("4. 期权合约规格可能与美股期权不同")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
