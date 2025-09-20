#!/usr/bin/env python3
"""
Tiger Brokers集成测试脚本

测试Tiger Brokers API集成的各个功能模块
完全替换Deribit，只使用Tiger Brokers
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.deribit_webhook.services.tiger_client import TigerClient
from src.deribit_webhook.services.trading_client_factory import TradingClientFactory
from src.deribit_webhook.utils.symbol_converter import OptionSymbolConverter
from src.deribit_webhook.config.config_loader import ConfigLoader


async def test_configuration():
    """测试配置加载"""
    print("🔧 Testing configuration loading...")
    
    try:
        config_loader = ConfigLoader.get_instance()
        config = config_loader.load_config()
        
        print(f"✅ Configuration loaded successfully")
        print(f"   - Test environment: {config.use_test_environment}")
        print(f"   - Accounts: {len(config.accounts)}")
        
        # 查找Tiger账户
        tiger_accounts = [acc for acc in config.accounts if acc.tiger_id]
        if tiger_accounts:
            account = tiger_accounts[0]
            print(f"   - Tiger account found: {account.name}")
            print(f"   - Tiger ID: {account.tiger_id}")
            print(f"   - Account: {account.account}")
            return account.name
        else:
            print("❌ No Tiger accounts found in configuration")
            return None
            
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return None


async def test_client_factory():
    """测试客户端工厂"""
    print("\n🏭 Testing client factory...")
    
    try:
        broker_type = TradingClientFactory.get_broker_type()
        print(f"✅ Broker type: {broker_type}")

        client = TradingClientFactory.create_client()
        print(f"✅ Tiger client created: {type(client).__name__}")
        
        return client
        
    except Exception as e:
        print(f"❌ Client factory test failed: {e}")
        return None


async def test_symbol_converter():
    """测试标识符转换器"""
    print("\n🔄 Testing symbol conversion...")
    
    converter = OptionSymbolConverter()
    
    test_cases = [
        "BTC-25DEC21-50000-C",
        "ETH-31DEC21-4000-P",
        "BTC-15JAN22-60000-C"
    ]
    
    success_count = 0
    
    for deribit_symbol in test_cases:
        try:
            tiger_symbol = converter.deribit_to_tiger(deribit_symbol)
            back_to_deribit = converter.tiger_to_deribit(tiger_symbol)
            
            print(f"✅ {deribit_symbol} -> {tiger_symbol} -> {back_to_deribit}")
            
            if deribit_symbol == back_to_deribit:
                print("   ✅ Round-trip conversion successful")
                success_count += 1
            else:
                print("   ❌ Round-trip conversion failed")
                
        except Exception as e:
            print(f"❌ Conversion failed for {deribit_symbol}: {e}")
    
    print(f"✅ Symbol conversion test completed: {success_count}/{len(test_cases)} successful")


async def test_tiger_client_initialization(account_name: str):
    """测试Tiger客户端初始化"""
    print(f"\n🐅 Testing Tiger client initialization for account: {account_name}...")
    
    try:
        tiger_client = TigerClient()
        await tiger_client._ensure_clients(account_name)
        
        print("✅ Tiger client initialized successfully")
        print(f"   - Quote client: {tiger_client.quote_client is not None}")
        print(f"   - Trade client: {tiger_client.trade_client is not None}")
        print(f"   - Current account: {tiger_client._current_account}")
        
        return tiger_client
        
    except Exception as e:
        print(f"❌ Tiger client initialization failed: {e}")
        return None


async def test_market_data(tiger_client: TigerClient):
    """测试市场数据获取"""
    print("\n📊 Testing market data retrieval...")
    
    try:
        # 测试期权工具列表获取
        print("   Testing instruments retrieval...")
        instruments = await tiger_client.get_instruments("BTC", "option")
        print(f"   ✅ Retrieved {len(instruments)} option instruments")
        
        if instruments:
            # 测试第一个期权的报价
            first_instrument = instruments[0]
            instrument_name = first_instrument.get('instrument_name')
            
            if instrument_name:
                print(f"   Testing ticker for: {instrument_name}")
                ticker = await tiger_client.get_ticker(instrument_name)
                
                if ticker:
                    print("   ✅ Ticker data retrieved successfully")
                    print(f"      - Best bid: {ticker.get('best_bid_price')}")
                    print(f"      - Best ask: {ticker.get('best_ask_price')}")
                    print(f"      - Mark price: {ticker.get('mark_price')}")
                else:
                    print("   ❌ Failed to retrieve ticker data")
        
    except Exception as e:
        print(f"❌ Market data test failed: {e}")


async def test_positions(tiger_client: TigerClient, account_name: str):
    """测试持仓获取"""
    print(f"\n📈 Testing positions retrieval for account: {account_name}...")
    
    try:
        positions = await tiger_client.get_positions(account_name)
        print(f"✅ Retrieved {len(positions)} positions")
        
        for i, position in enumerate(positions[:3]):  # 只显示前3个
            print(f"   Position {i+1}:")
            print(f"      - Instrument: {position.get('instrument_name')}")
            print(f"      - Size: {position.get('size')}")
            print(f"      - Direction: {position.get('direction')}")
            print(f"      - P&L: {position.get('floating_profit_loss')}")
        
    except Exception as e:
        print(f"❌ Positions test failed: {e}")


async def test_paper_trading(tiger_client: TigerClient, account_name: str):
    """测试模拟交易"""
    print(f"\n📝 Testing paper trading for account: {account_name}...")
    
    try:
        # 获取一个期权进行测试
        instruments = await tiger_client.get_instruments("BTC", "option")
        
        if not instruments:
            print("❌ No instruments available for testing")
            return
        
        test_instrument = instruments[0]['instrument_name']
        print(f"   Testing with instrument: {test_instrument}")
        
        # 测试买单（使用很低的价格，不会成交）
        buy_result = await tiger_client.place_buy_order(
            account_name=account_name,
            instrument_name=test_instrument,
            amount=1,
            type='limit',
            price=0.01
        )
        
        if buy_result:
            print("✅ Buy order placed successfully")
            print(f"   - Order ID: {buy_result.order.get('order_id')}")
            print(f"   - Status: {buy_result.order.get('order_state')}")
        else:
            print("❌ Failed to place buy order")
        
    except Exception as e:
        print(f"❌ Paper trading test failed: {e}")


async def main():
    """主测试函数"""
    print("🚀 Starting Tiger Brokers integration tests...\n")
    
    # 1. 测试配置
    account_name = await test_configuration()
    if not account_name:
        print("\n❌ Configuration test failed. Exiting.")
        return
    
    # 2. 测试客户端工厂
    client = await test_client_factory()
    if not client:
        print("\n❌ Client factory test failed. Exiting.")
        return
    
    # 3. 测试标识符转换
    await test_symbol_converter()
    
    # 4. 测试Tiger客户端初始化
    tiger_client = await test_tiger_client_initialization(account_name)
    if not tiger_client:
        print("\n❌ Tiger client initialization failed. Exiting.")
        return
    
    # 5. 测试市场数据
    await test_market_data(tiger_client)
    
    # 6. 测试持仓
    await test_positions(tiger_client, account_name)
    
    # 7. 测试模拟交易
    await test_paper_trading(tiger_client, account_name)
    
    # 清理
    await tiger_client.close()
    
    print("\n🎉 Tiger Brokers integration tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
