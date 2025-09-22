#!/usr/bin/env python3
"""
Tiger Brokers 美股期权品种获取示例

展示如何获取Tiger支持的美股期权标的列表和具体期权合约
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.deribit_webhook.services.tiger_client import TigerClient


async def get_option_underlyings():
    """获取所有期权标的列表"""
    client = TigerClient()
    
    try:
        print("🔍 获取美股期权标的列表...")
        
        # 获取美股期权标的
        underlyings = await client.get_option_underlyings(market="US")
        
        print(f"✅ 找到 {len(underlyings)} 个期权标的:")
        print("-" * 60)
        
        # 显示前20个标的作为示例
        for i, underlying in enumerate(underlyings[:20]):
            print(f"{i+1:2d}. {underlying['symbol']:6s} - {underlying['name']}")
        
        if len(underlyings) > 20:
            print(f"... 还有 {len(underlyings) - 20} 个标的")
        
        return underlyings
        
    except Exception as e:
        print(f"❌ 获取期权标的失败: {e}")
        return []
    finally:
        await client.close()


async def get_option_expirations(symbol: str):
    """获取指定标的的期权到期日"""
    client = TigerClient()
    
    try:
        print(f"\n🔍 获取 {symbol} 的期权到期日...")
        
        expirations = await client.get_option_expirations(symbol)
        
        print(f"✅ 找到 {len(expirations)} 个到期日:")
        print("-" * 40)
        
        for exp in expirations[:10]:  # 显示前10个到期日
            print(f"  {exp['date']} (时间戳: {exp['timestamp']})")
        
        return expirations
        
    except Exception as e:
        print(f"❌ 获取到期日失败: {e}")
        return []
    finally:
        await client.close()


async def get_option_chain(symbol: str, expiry_timestamp: int = None):
    """获取期权链"""
    client = TigerClient()
    
    try:
        if expiry_timestamp:
            print(f"\n🔍 获取 {symbol} 指定到期日的期权链...")
            options = await client.get_instruments(symbol, expiry_timestamp=expiry_timestamp)
        else:
            print(f"\n🔍 获取 {symbol} 所有期权合约...")
            options = await client.get_instruments(symbol)
        
        print(f"✅ 找到 {len(options)} 个期权合约:")
        print("-" * 80)
        
        # 按类型分组显示
        calls = [opt for opt in options if opt.get('option_type') == 'call']
        puts = [opt for opt in options if opt.get('option_type') == 'put']
        
        print(f"看涨期权 (Calls): {len(calls)} 个")
        print(f"看跌期权 (Puts): {len(puts)} 个")
        
        # 显示前5个看涨期权作为示例
        if calls:
            print("\n前5个看涨期权:")
            for i, call in enumerate(calls[:5]):
                print(f"  {i+1}. {call['instrument_name']} - 行权价: ${call['strike']}")
        
        # 显示前5个看跌期权作为示例
        if puts:
            print("\n前5个看跌期权:")
            for i, put in enumerate(puts[:5]):
                print(f"  {i+1}. {put['instrument_name']} - 行权价: ${put['strike']}")
        
        return options
        
    except Exception as e:
        print(f"❌ 获取期权链失败: {e}")
        return []
    finally:
        await client.close()


async def main():
    """主函数 - 演示完整的期权数据获取流程"""
    print("=" * 80)
    print("Tiger Brokers 美股期权品种获取示例")
    print("=" * 80)
    
    # 1. 获取期权标的列表
    underlyings = await get_option_underlyings()
    
    if not underlyings:
        print("❌ 无法获取期权标的，程序退出")
        return
    
    # 2. 选择一个热门标的进行演示 (如AAPL)
    demo_symbol = "AAPL"
    print(f"\n📊 以 {demo_symbol} 为例演示期权数据获取...")
    
    # 3. 获取该标的的到期日
    expirations = await get_option_expirations(demo_symbol)
    
    if expirations:
        # 4. 获取最近到期日的期权链
        nearest_expiry = expirations[0]['timestamp']
        await get_option_chain(demo_symbol, nearest_expiry)
    
    print("\n" + "=" * 80)
    print("演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
