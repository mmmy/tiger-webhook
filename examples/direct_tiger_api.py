#!/usr/bin/env python3
"""
直接使用Tiger SDK获取期权数据的示例

展示如何不通过封装类直接使用Tiger SDK
"""

import os
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Language, Market
from tigeropen.common.util.signature_utils import read_private_key


def setup_tiger_client():
    """设置Tiger客户端"""
    # 配置信息 - 请替换为您的实际配置
    config = TigerOpenClientConfig(
        sandbox_debug=False  # 生产环境设为False，测试环境设为True
    )
    
    # 请替换为您的实际配置
    config.tiger_id = "your_tiger_id"  # 您的Tiger ID
    config.account = "your_account"    # 您的账户号
    
    # 私钥文件路径 - 请替换为您的实际路径
    private_key_path = "path/to/your/private_key.pem"
    if os.path.exists(private_key_path):
        config.private_key = read_private_key(private_key_path)
    else:
        raise FileNotFoundError(f"私钥文件未找到: {private_key_path}")
    
    config.language = Language.en_US
    
    return QuoteClient(config)


def get_option_symbols(quote_client, market=Market.US):
    """获取期权标的列表"""
    try:
        print(f"🔍 获取 {market.name} 市场的期权标的...")
        
        # 获取期权标的列表
        symbols_df = quote_client.get_option_symbols(market=market)
        
        if symbols_df is None or len(symbols_df) == 0:
            print("❌ 未获取到期权标的数据")
            return []
        
        print(f"✅ 获取到 {len(symbols_df)} 个期权标的")
        
        # 转换为字典列表
        symbols = []
        for _, row in symbols_df.iterrows():
            symbol_info = {
                'symbol': row.get('symbol', ''),
                'name': row.get('name', ''),
                'market': row.get('market', ''),
                'currency': row.get('currency', 'USD')
            }
            symbols.append(symbol_info)
        
        return symbols
        
    except Exception as e:
        print(f"❌ 获取期权标的失败: {e}")
        return []


def get_option_expirations(quote_client, symbol):
    """获取期权到期日"""
    try:
        print(f"🔍 获取 {symbol} 的期权到期日...")
        
        expirations_df = quote_client.get_option_expirations(symbols=[symbol])
        
        if expirations_df is None or len(expirations_df) == 0:
            print(f"❌ 未获取到 {symbol} 的期权到期日")
            return []
        
        print(f"✅ 获取到 {len(expirations_df)} 个到期日")
        
        # 转换为字典列表
        expirations = []
        for _, row in expirations_df.iterrows():
            exp_info = {
                'date': row.get('date', ''),
                'timestamp': int(row.get('timestamp', 0))
            }
            expirations.append(exp_info)
        
        return expirations
        
    except Exception as e:
        print(f"❌ 获取期权到期日失败: {e}")
        return []


def get_option_chain(quote_client, symbol, expiry_timestamp):
    """获取期权链"""
    try:
        print(f"🔍 获取 {symbol} 到期日 {expiry_timestamp} 的期权链...")
        
        option_chain_df = quote_client.get_option_chain(symbol, expiry_timestamp)
        
        if option_chain_df is None or len(option_chain_df) == 0:
            print(f"❌ 未获取到期权链数据")
            return []
        
        print(f"✅ 获取到 {len(option_chain_df)} 个期权合约")
        
        # 转换为字典列表
        options = []
        for _, row in option_chain_df.iterrows():
            option_info = {
                'identifier': row.get('identifier', ''),
                'symbol': row.get('symbol', ''),
                'strike': float(row.get('strike', 0)),
                'right': row.get('right', ''),  # 'C' for Call, 'P' for Put
                'expiry': int(row.get('expiry', 0)),
                'expiry_date': row.get('expiry_date', ''),
                'underlying_price': float(row.get('underlying_price', 0) or 0)
            }
            options.append(option_info)
        
        return options
        
    except Exception as e:
        print(f"❌ 获取期权链失败: {e}")
        return []


def main():
    """主函数"""
    print("=" * 80)
    print("直接使用Tiger SDK获取期权数据示例")
    print("=" * 80)
    
    try:
        # 1. 设置客户端
        quote_client = setup_tiger_client()
        print("✅ Tiger客户端初始化成功")
        
        # 2. 获取美股期权标的
        symbols = get_option_symbols(quote_client, Market.US)
        
        if symbols:
            print(f"\n📊 前10个期权标的:")
            for i, symbol_info in enumerate(symbols[:10]):
                print(f"  {i+1:2d}. {symbol_info['symbol']:6s} - {symbol_info['name']}")
        
        # 3. 以AAPL为例获取期权数据
        demo_symbol = "AAPL"
        if any(s['symbol'] == demo_symbol for s in symbols):
            print(f"\n📈 获取 {demo_symbol} 的期权数据...")
            
            # 获取到期日
            expirations = get_option_expirations(quote_client, demo_symbol)
            
            if expirations:
                print(f"\n📅 前5个到期日:")
                for i, exp in enumerate(expirations[:5]):
                    print(f"  {i+1}. {exp['date']} (时间戳: {exp['timestamp']})")
                
                # 获取最近到期日的期权链
                nearest_expiry = expirations[0]['timestamp']
                options = get_option_chain(quote_client, demo_symbol, nearest_expiry)
                
                if options:
                    calls = [opt for opt in options if opt['right'].upper() == 'C']
                    puts = [opt for opt in options if opt['right'].upper() == 'P']
                    
                    print(f"\n📊 期权统计:")
                    print(f"  看涨期权: {len(calls)} 个")
                    print(f"  看跌期权: {len(puts)} 个")
                    
                    if calls:
                        print(f"\n📈 前3个看涨期权:")
                        for i, call in enumerate(calls[:3]):
                            print(f"  {i+1}. {call['identifier']} - 行权价: ${call['strike']}")
        
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
    
    print("\n" + "=" * 80)
    print("示例完成!")


if __name__ == "__main__":
    main()
