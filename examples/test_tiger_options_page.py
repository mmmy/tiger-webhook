#!/usr/bin/env python3
"""
测试Tiger期权页面的手动输入功能

验证/tiger/options页面的标的代码输入框改为手动输入后是否正常工作
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.deribit_webhook.services.tiger_client import TigerClient


async def test_manual_input_symbols():
    """测试手动输入的标的代码是否能正常获取期权数据"""
    client = TigerClient()
    
    # 常见的香港股票代码
    test_symbols = [
        ("700", "腾讯控股"),
        ("9988", "阿里巴巴-SW"),
        ("3690", "美团-W"),
        ("1810", "小米集团-W"),
        ("1299", "友邦保险"),
        ("2318", "中国平安")
    ]
    
    print("=" * 80)
    print("测试Tiger期权页面手动输入功能")
    print("=" * 80)
    
    try:
        await client.ensure_quote_client()
        print("✅ Tiger客户端连接成功")
        
        for symbol, name in test_symbols:
            print(f"\n🔍 测试标的: {symbol} ({name})")
            
            try:
                # 测试获取到期日
                expirations = await client.get_option_expirations(symbol)
                
                if expirations:
                    print(f"  ✅ 找到 {len(expirations)} 个到期日")
                    
                    # 测试获取期权链
                    if len(expirations) > 0:
                        first_expiry = expirations[0]['timestamp']
                        options = await client.get_instruments(symbol, expiry_timestamp=first_expiry)
                        
                        if options:
                            calls = [opt for opt in options if opt.get('option_type') == 'call']
                            puts = [opt for opt in options if opt.get('option_type') == 'put']
                            print(f"  ✅ 期权链: {len(calls)} 个看涨, {len(puts)} 个看跌")
                        else:
                            print(f"  ⚠️ 期权链为空")
                else:
                    print(f"  ⚠️ 未找到到期日")
                    
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
        
        print(f"\n" + "=" * 80)
        print("✅ 测试完成！")
        print("💡 页面使用说明:")
        print("1. 访问 http://localhost:8000/tiger/options")
        print("2. 在'标的代码'输入框中手动输入股票代码，如: 700")
        print("3. 输入完成后按回车或点击其他地方，系统会自动获取到期日")
        print("4. 选择到期日后点击'查询'按钮获取期权链")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


async def test_api_endpoints():
    """测试相关的API端点"""
    print(f"\n" + "=" * 80)
    print("测试API端点")
    print("=" * 80)
    
    import aiohttp
    
    base_url = "http://localhost:8000"
    test_symbol = "700"
    
    async with aiohttp.ClientSession() as session:
        # 测试获取到期日API
        print(f"\n🔍 测试到期日API: /api/tiger/options/expirations")
        try:
            url = f"{base_url}/api/tiger/options/expirations?underlying={test_symbol}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"  ✅ 成功获取 {data.get('count', 0)} 个到期日")
                else:
                    print(f"  ❌ API调用失败: {response.status}")
        except Exception as e:
            print(f"  ❌ API测试失败: {e}")
        
        # 测试期权链API (需要先获取到期日)
        print(f"\n🔍 测试期权链API: /api/tiger/options")
        try:
            # 先获取到期日
            url = f"{base_url}/api/tiger/options/expirations?underlying={test_symbol}"
            async with session.get(url) as response:
                if response.status == 200:
                    exp_data = await response.json()
                    if exp_data.get('expirations'):
                        first_expiry = exp_data['expirations'][0]['timestamp']
                        
                        # 获取期权链
                        options_url = f"{base_url}/api/tiger/options?underlying={test_symbol}&expiryTs={first_expiry}"
                        async with session.get(options_url) as options_response:
                            if options_response.status == 200:
                                options_data = await options_response.json()
                                print(f"  ✅ 成功获取 {options_data.get('count', 0)} 个期权合约")
                            else:
                                print(f"  ❌ 期权链API调用失败: {options_response.status}")
                    else:
                        print(f"  ⚠️ 没有可用的到期日")
                else:
                    print(f"  ❌ 到期日API调用失败: {response.status}")
        except Exception as e:
            print(f"  ❌ 期权链API测试失败: {e}")


async def main():
    """主函数"""
    await test_manual_input_symbols()
    
    # 如果服务器正在运行，测试API端点
    try:
        await test_api_endpoints()
    except Exception as e:
        print(f"\n💡 API端点测试跳过 (服务器可能未运行): {e}")
        print("如需测试API，请先启动服务器: python -m uvicorn src.deribit_webhook.main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
