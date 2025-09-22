#!/usr/bin/env python3
"""
检查Tiger支持的市场和期权数据
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.deribit_webhook.services.tiger_client import TigerClient
from tigeropen.common.consts import Market


async def check_available_markets():
    """检查Tiger支持的市场"""
    client = TigerClient()
    
    try:
        print("=" * 80)
        print("检查Tiger支持的市场和期权数据")
        print("=" * 80)
        
        # 检查Market枚举中的所有市场
        print("\n📊 Tiger SDK中定义的市场:")
        for attr_name in dir(Market):
            if not attr_name.startswith('_'):
                market_value = getattr(Market, attr_name)
                print(f"  {attr_name}: {market_value}")
        
        # 测试不同市场的期权数据
        markets_to_test = [
            ("HK", "香港市场"),
            ("US", "美国市场"), 
            ("CN", "中国市场"),
            (None, "默认市场")
        ]
        
        for market_code, market_name in markets_to_test:
            print(f"\n🔍 测试 {market_name} ({market_code}):")
            try:
                underlyings = await client.get_option_underlyings(market=market_code)
                if underlyings:
                    print(f"  ✅ 成功获取 {len(underlyings)} 个期权标的")
                    # 显示前5个标的
                    for i, underlying in enumerate(underlyings[:5]):
                        print(f"    {i+1}. {underlying['symbol']} - {underlying['name']}")
                    if len(underlyings) > 5:
                        print(f"    ... 还有 {len(underlyings) - 5} 个标的")
                else:
                    print(f"  ⚠️ 未获取到期权标的")
            except Exception as e:
                print(f"  ❌ 错误: {e}")
        
        # 如果HK市场有数据，进一步测试
        print(f"\n🔍 详细测试香港市场期权数据:")
        try:
            hk_underlyings = await client.get_option_underlyings(market="HK")
            if hk_underlyings:
                # 选择第一个标的进行详细测试
                test_symbol = hk_underlyings[0]['symbol']
                print(f"  选择 {test_symbol} 进行详细测试...")
                
                # 获取到期日
                expirations = await client.get_option_expirations(test_symbol)
                if expirations:
                    print(f"  ✅ 找到 {len(expirations)} 个到期日")
                    for i, exp in enumerate(expirations[:3]):
                        print(f"    {i+1}. {exp['date']} (时间戳: {exp['timestamp']})")
                    
                    # 获取期权链
                    if expirations:
                        target_expiry = expirations[0]['timestamp']
                        options = await client.get_instruments(test_symbol, expiry_timestamp=target_expiry)
                        if options:
                            calls = [opt for opt in options if opt.get('option_type') == 'call']
                            puts = [opt for opt in options if opt.get('option_type') == 'put']
                            print(f"  ✅ 期权链: {len(calls)} 个看涨期权, {len(puts)} 个看跌期权")
                            
                            # 显示一个期权的详细信息
                            if options:
                                sample_option = options[0]
                                print(f"  📊 示例期权: {sample_option['instrument_name']}")
                                print(f"    类型: {sample_option.get('option_type')}")
                                print(f"    行权价: {sample_option.get('strike')}")
                                print(f"    到期日: {sample_option.get('expiration_date')}")
                        else:
                            print(f"  ⚠️ 未获取到期权链数据")
                else:
                    print(f"  ⚠️ 未获取到到期日数据")
        except Exception as e:
            print(f"  ❌ 香港市场测试失败: {e}")
        
    except Exception as e:
        print(f"❌ 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


async def test_direct_api():
    """直接测试Tiger API"""
    print(f"\n" + "=" * 80)
    print("直接测试Tiger API")
    print("=" * 80)
    
    client = TigerClient()
    
    try:
        # 确保客户端初始化
        await client.ensure_quote_client()
        
        # 测试不带market参数的调用
        print(f"\n🔍 测试不指定市场参数:")
        try:
            symbols_df = client.quote_client.get_option_symbols()
            if symbols_df is not None and len(symbols_df) > 0:
                print(f"  ✅ 成功获取 {len(symbols_df)} 个期权标的")
                print(f"  📊 数据列: {list(symbols_df.columns)}")
                
                # 显示前几行数据
                for i, (_, row) in enumerate(symbols_df.head().iterrows()):
                    symbol = row.get('symbol', 'N/A')
                    name = row.get('name', 'N/A')
                    market = row.get('market', 'N/A')
                    print(f"    {i+1}. {symbol} - {name} (市场: {market})")
            else:
                print(f"  ⚠️ 未获取到数据")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
        
        # 测试指定HK市场
        print(f"\n🔍 测试指定HK市场:")
        try:
            symbols_df = client.quote_client.get_option_symbols(market=Market.HK)
            if symbols_df is not None and len(symbols_df) > 0:
                print(f"  ✅ 成功获取 {len(symbols_df)} 个期权标的")
                
                # 显示前几行数据
                for i, (_, row) in enumerate(symbols_df.head().iterrows()):
                    symbol = row.get('symbol', 'N/A')
                    name = row.get('name', 'N/A')
                    market = row.get('market', 'N/A')
                    print(f"    {i+1}. {symbol} - {name} (市场: {market})")
            else:
                print(f"  ⚠️ 未获取到数据")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    except Exception as e:
        print(f"❌ 直接API测试失败: {e}")
    
    finally:
        await client.close()


async def main():
    """主函数"""
    await check_available_markets()
    await test_direct_api()


if __name__ == "__main__":
    asyncio.run(main())
