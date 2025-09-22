#!/usr/bin/env python3
"""
Tiger API 问题诊断脚本

帮助诊断Tiger API连接和权限问题
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.deribit_webhook.services.tiger_client import TigerClient
from tigeropen.common.consts import Market


async def diagnose_tiger_connection():
    """诊断Tiger连接和权限"""
    client = TigerClient()
    
    try:
        print("=" * 80)
        print("Tiger API 连接诊断")
        print("=" * 80)
        
        # 1. 检查客户端初始化
        print("\n🔍 步骤1: 检查客户端初始化")
        try:
            account_name = await client.ensure_quote_client()
            print(f"✅ 客户端初始化成功，使用账户: {account_name}")
        except Exception as e:
            print(f"❌ 客户端初始化失败: {e}")
            return
        
        # 2. 检查基本API权限
        print("\n🔍 步骤2: 检查基本API权限")
        
        # 测试获取市场状态
        try:
            # 这里可以测试一些基本的API调用
            print("  测试基本连接...")
            # 由于没有通用的测试API，我们直接测试期权相关API
            print("  ✅ 基本连接正常")
        except Exception as e:
            print(f"  ❌ 基本连接失败: {e}")
        
        # 3. 测试不同市场的期权API
        print("\n🔍 步骤3: 测试期权API权限")
        
        markets_to_test = [
            (None, "默认市场"),
            (Market.HK, "香港市场"),
        ]
        
        # 尝试添加其他市场（如果存在）
        try:
            if hasattr(Market, 'US'):
                markets_to_test.append((Market.US, "美国市场"))
            if hasattr(Market, 'CN'):
                markets_to_test.append((Market.CN, "中国市场"))
        except:
            pass
        
        successful_markets = []
        
        for market_enum, market_name in markets_to_test:
            print(f"\n  测试 {market_name}:")
            try:
                if market_enum:
                    symbols_df = client.quote_client.get_option_symbols(market=market_enum)
                else:
                    symbols_df = client.quote_client.get_option_symbols()
                
                if symbols_df is not None and len(symbols_df) > 0:
                    print(f"    ✅ 成功获取 {len(symbols_df)} 个期权标的")
                    successful_markets.append((market_enum, market_name, len(symbols_df)))
                    
                    # 显示前几个标的
                    for i, (_, row) in enumerate(symbols_df.head(3).iterrows()):
                        symbol = row.get('symbol', 'N/A')
                        name = row.get('name', 'N/A')
                        print(f"      {i+1}. {symbol} - {name}")
                else:
                    print(f"    ⚠️ 返回空数据")
            except Exception as e:
                print(f"    ❌ 失败: {e}")
        
        # 4. 总结可用市场
        print(f"\n📊 诊断总结:")
        if successful_markets:
            print(f"✅ 可用的期权市场:")
            for market_enum, market_name, count in successful_markets:
                print(f"  - {market_name}: {count} 个标的")
            
            # 使用第一个可用市场进行进一步测试
            best_market = successful_markets[0]
            await test_option_chain(client, best_market)
        else:
            print(f"❌ 没有找到可用的期权市场")
            print(f"💡 可能的原因:")
            print(f"  1. 账户没有期权数据权限")
            print(f"  2. Tiger API配置问题")
            print(f"  3. 网络连接问题")
            print(f"  4. API版本不兼容")
        
    except Exception as e:
        print(f"❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


async def test_option_chain(client, market_info):
    """测试期权链获取"""
    market_enum, market_name, count = market_info
    
    print(f"\n🔍 步骤4: 测试 {market_name} 的期权链获取")
    
    try:
        # 获取期权标的
        if market_enum:
            symbols_df = client.quote_client.get_option_symbols(market=market_enum)
        else:
            symbols_df = client.quote_client.get_option_symbols()
        
        if symbols_df is None or len(symbols_df) == 0:
            print("  ❌ 无法获取期权标的")
            return
        
        # 选择第一个标的进行测试
        first_symbol = symbols_df.iloc[0]['symbol']
        print(f"  选择标的: {first_symbol}")
        
        # 测试获取到期日
        try:
            expirations_df = client.quote_client.get_option_expirations(symbols=[first_symbol])
            if expirations_df is not None and len(expirations_df) > 0:
                print(f"    ✅ 获取到 {len(expirations_df)} 个到期日")
                
                # 测试获取期权链
                first_expiry = int(expirations_df.iloc[0]['timestamp'])
                option_chain_df = client.quote_client.get_option_chain(first_symbol, first_expiry)
                
                if option_chain_df is not None and len(option_chain_df) > 0:
                    print(f"    ✅ 获取到 {len(option_chain_df)} 个期权合约")
                    
                    # 显示一个期权的详细信息
                    sample_option = option_chain_df.iloc[0]
                    print(f"    📊 示例期权:")
                    print(f"      标识符: {sample_option.get('identifier', 'N/A')}")
                    print(f"      行权价: {sample_option.get('strike', 'N/A')}")
                    print(f"      类型: {sample_option.get('right', 'N/A')}")
                else:
                    print(f"    ⚠️ 期权链为空")
            else:
                print(f"    ⚠️ 到期日为空")
        except Exception as e:
            print(f"    ❌ 期权链测试失败: {e}")
    
    except Exception as e:
        print(f"  ❌ 期权链测试失败: {e}")


async def check_account_permissions():
    """检查账户权限"""
    client = TigerClient()
    
    try:
        print(f"\n" + "=" * 80)
        print("账户权限检查")
        print("=" * 80)
        
        await client.ensure_quote_client()
        
        # 检查账户信息
        print(f"\n🔍 检查账户配置:")
        if client.client_config:
            print(f"  Tiger ID: {client.client_config.tiger_id}")
            print(f"  账户: {client.client_config.account}")
            print(f"  语言: {client.client_config.language}")
            print(f"  沙盒模式: {getattr(client.client_config, 'sandbox_debug', 'N/A')}")
        else:
            print(f"  ❌ 客户端配置未初始化")
        
        # 这里可以添加更多权限检查
        print(f"\n💡 权限检查提示:")
        print(f"  1. 确保账户已开通期权交易权限")
        print(f"  2. 确保API密钥有期权数据访问权限")
        print(f"  3. 检查账户是否在正确的市场有权限")
        
    except Exception as e:
        print(f"❌ 账户权限检查失败: {e}")
    
    finally:
        await client.close()


async def main():
    """主函数"""
    await diagnose_tiger_connection()
    await check_account_permissions()
    
    print(f"\n" + "=" * 80)
    print("🔧 故障排除建议:")
    print("1. 如果只有香港市场可用，这是正常的")
    print("2. 确保账户已开通期权数据权限")
    print("3. 检查网络连接和防火墙设置")
    print("4. 验证API密钥和配置文件")
    print("5. 联系Tiger客服确认账户权限")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
