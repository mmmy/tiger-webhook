"""
Tiger Brokers API客户端

替换原有的Deribit客户端，使用Tiger Brokers官方SDK
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.push.push_client import PushClient
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.common.consts import Language, Market
from tigeropen.common.util.contract_utils import option_contract, stock_contract
from tigeropen.common.util.order_utils import market_order, limit_order

from ..config.config_loader import ConfigLoader
from ..config.settings import settings
from ..services.auth_service import AuthenticationService
from ..models.deribit_types import DeribitOrderResponse
from ..utils.symbol_converter import OptionSymbolConverter


class TigerClient:
    """Tiger Brokers客户端，替换DeribitClient"""
    
    def __init__(self):
        self.config_loader = ConfigLoader.get_instance()
        self.auth_service = AuthenticationService.get_instance()
        self.symbol_converter = OptionSymbolConverter()
        
        # Tiger客户端配置
        self.client_config: Optional[TigerOpenClientConfig] = None
        self.quote_client: Optional[QuoteClient] = None
        self.trade_client: Optional[TradeClient] = None
        self.push_client: Optional[PushClient] = None
        self._current_account: Optional[str] = None
    
    async def close(self):
        """关闭所有客户端连接"""
        if self.push_client:
            self.push_client.disconnect()
        # Tiger SDK的其他客户端不需要显式关闭
    
    async def _ensure_clients(self, account_name: str):
        """确保客户端已初始化"""
        if self.client_config is None or self._current_account != account_name:
            # 获取账户配置
            account = self.config_loader.get_account_by_name(account_name)
            if not account:
                raise Exception(f"Account not found: {account_name}")
            
            if not account.tiger_id or not account.private_key_path or not account.account:
                raise Exception(f"Tiger configuration incomplete for account: {account_name}")
            
            # 创建Tiger配置
            config = self.config_loader.load_config()
            use_sandbox = config.use_test_environment if hasattr(config, 'use_test_environment') else settings.use_test_environment

            # 根据错误信息，sandbox_debug应该设置为False
            self.client_config = TigerOpenClientConfig(
                sandbox_debug=False  # 设置为False避免deprecated警告
            )
            
            # 读取私钥
            if os.path.exists(account.private_key_path):
                self.client_config.private_key = read_private_key(account.private_key_path)
            else:
                # 如果是相对路径，尝试从项目根目录读取
                full_path = os.path.join(os.getcwd(), account.private_key_path)
                if os.path.exists(full_path):
                    self.client_config.private_key = read_private_key(full_path)
                else:
                    raise Exception(f"Private key file not found: {account.private_key_path}")
            
            self.client_config.tiger_id = account.tiger_id
            self.client_config.account = account.account
            self.client_config.language = Language.en_US
            
            # 初始化客户端
            self.quote_client = QuoteClient(self.client_config)
            self.trade_client = TradeClient(self.client_config)
            
            self._current_account = account_name
            
            print(f"✅ Tiger clients initialized for account: {account_name}")
    
    async def get_instruments(self, currency: str, kind: str = "option") -> List[Dict]:
        """获取期权工具列表 - 映射Deribit的get_instruments"""
        if kind != "option":
            raise ValueError("Tiger client only supports options")
        
        try:
            # 获取标的资产列表
            symbols = self._get_underlying_symbols_for_currency(currency)
            all_options = []
            
            for symbol in symbols:
                # 获取期权到期日
                expirations = self.quote_client.get_option_expirations(symbols=[symbol])
                
                for _, expiry_row in expirations.iterrows():
                    expiry_timestamp = int(expiry_row['timestamp'])
                    
                    # 获取期权链
                    option_chain = self.quote_client.get_option_chain(symbol, expiry_timestamp)
                    
                    # 转换为Deribit格式
                    for _, option in option_chain.iterrows():
                        deribit_option = self._convert_tiger_option_to_deribit(option, symbol)
                        all_options.append(deribit_option)
            
            return all_options
            
        except Exception as error:
            print(f"❌ Failed to get instruments: {error}")
            return []
    
    async def get_ticker(self, instrument_name: str) -> Optional[Dict]:
        """获取期权报价 - 映射Deribit的ticker"""
        try:
            # 转换标识符
            tiger_symbol = self.symbol_converter.deribit_to_tiger(instrument_name)
            
            # 获取期权报价
            briefs = self.quote_client.get_option_briefs([tiger_symbol])
            
            if briefs.empty:
                return None
            
            option_data = briefs.iloc[0]
            
            # 转换为Deribit格式
            return {
                "instrument_name": instrument_name,
                "best_bid_price": float(option_data.get('bid', 0)),
                "best_ask_price": float(option_data.get('ask', 0)),
                "best_bid_amount": float(option_data.get('bid_size', 0)),
                "best_ask_amount": float(option_data.get('ask_size', 0)),
                "mark_price": float(option_data.get('latest_price', 0)),
                "last_price": float(option_data.get('latest_price', 0)),
                "mark_iv": float(option_data.get('implied_vol', 0)),
                "index_price": float(option_data.get('underlying_price', 0)),
                "greeks": {
                    "delta": float(option_data.get('delta', 0)),
                    "gamma": float(option_data.get('gamma', 0)),
                    "theta": float(option_data.get('theta', 0)),
                    "vega": float(option_data.get('vega', 0))
                }
            }
            
        except Exception as error:
            print(f"❌ Failed to get ticker for {instrument_name}: {error}")
            return None
    
    def _get_underlying_symbols_for_currency(self, currency: str) -> List[str]:
        """根据货币获取对应的标的资产"""
        # 映射表：Deribit货币 -> Tiger标的资产
        currency_mapping = {
            "BTC": ["AAPL", "MSFT", "GOOGL"],
            "ETH": ["TSLA", "NVDA", "META"],
            "USD": ["SPY", "QQQ", "IWM"]
        }
        
        return currency_mapping.get(currency, ["AAPL"])  # 默认返回AAPL
    
    def _convert_tiger_option_to_deribit(self, tiger_option: Any, underlying: str) -> Dict:
        """转换Tiger期权数据到Deribit格式"""
        try:
            # 构造Deribit格式的标识符
            tiger_symbol = tiger_option.get('identifier', '')
            deribit_symbol = self.symbol_converter.tiger_to_deribit(tiger_symbol)
            
            return {
                "instrument_name": deribit_symbol,
                "kind": "option",
                "option_type": tiger_option.get('right', '').lower(),
                "strike": float(tiger_option.get('strike', 0)),
                "expiration_timestamp": int(tiger_option.get('expiry', 0)),
                "tick_size": 0.01,  # Tiger期权最小价格变动
                "min_trade_amount": 1,
                "contract_size": 100,  # 美股期权合约大小
                "base_currency": "USD",
                "quote_currency": "USD",
                "settlement_currency": "USD"
            }
        except Exception as error:
            print(f"❌ Failed to convert Tiger option to Deribit format: {error}")
            return {}

    async def place_buy_order(
        self,
        account_name: str,
        instrument_name: str,
        amount: float,
        **kwargs
    ) -> Optional[DeribitOrderResponse]:
        """下买单 - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            # 转换期权标识符
            tiger_symbol = self.symbol_converter.deribit_to_tiger(instrument_name)

            # 创建期权合约
            contract = option_contract(identifier=tiger_symbol)

            # 创建订单
            if kwargs.get('type') == 'limit' and 'price' in kwargs:
                order = limit_order(
                    account=self.client_config.account,
                    contract=contract,
                    action='BUY',
                    quantity=int(amount),
                    limit_price=float(kwargs['price'])
                )
            else:
                order = market_order(
                    account=self.client_config.account,
                    contract=contract,
                    action='BUY',
                    quantity=int(amount)
                )

            # 下单
            result = self.trade_client.place_order(order)

            # 转换为Deribit响应格式
            return self._convert_to_deribit_order_response(order, instrument_name)

        except Exception as error:
            print(f"❌ Failed to place buy order: {error}")
            return None

    async def place_sell_order(
        self,
        account_name: str,
        instrument_name: str,
        amount: float,
        **kwargs
    ) -> Optional[DeribitOrderResponse]:
        """下卖单 - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            # 转换期权标识符
            tiger_symbol = self.symbol_converter.deribit_to_tiger(instrument_name)

            # 创建期权合约
            contract = option_contract(identifier=tiger_symbol)

            # 创建订单
            if kwargs.get('type') == 'limit' and 'price' in kwargs:
                order = limit_order(
                    account=self.client_config.account,
                    contract=contract,
                    action='SELL',
                    quantity=int(amount),
                    limit_price=float(kwargs['price'])
                )
            else:
                order = market_order(
                    account=self.client_config.account,
                    contract=contract,
                    action='SELL',
                    quantity=int(amount)
                )

            # 下单
            result = self.trade_client.place_order(order)

            # 转换为Deribit响应格式
            return self._convert_to_deribit_order_response(order, instrument_name)

        except Exception as error:
            print(f"❌ Failed to place sell order: {error}")
            return None

    async def get_positions(self, account_name: str, currency: str = "USD") -> List[Dict]:
        """获取持仓 - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            # 获取持仓
            positions = self.trade_client.get_positions(account=self.client_config.account)

            # 转换为Deribit格式
            deribit_positions = []
            for _, position in positions.iterrows():
                if position.get('sec_type') == 'OPT':  # 只返回期权持仓
                    deribit_position = self._convert_tiger_position_to_deribit(position)
                    if deribit_position:
                        deribit_positions.append(deribit_position)

            return deribit_positions

        except Exception as error:
            print(f"❌ Failed to get positions: {error}")
            return []

    def _convert_to_deribit_order_response(self, tiger_order: Any, instrument_name: str) -> DeribitOrderResponse:
        """转换Tiger订单响应为Deribit格式"""
        try:
            order_dict = {
                "order_id": str(tiger_order.id),
                "instrument_name": instrument_name,
                "direction": tiger_order.action.lower(),
                "amount": float(tiger_order.quantity),
                "price": float(tiger_order.limit_price or 0),
                "order_type": "limit" if tiger_order.order_type == "LMT" else "market",
                "order_state": self._convert_tiger_order_status(tiger_order.status),
                "filled_amount": float(tiger_order.filled or 0),
                "average_price": float(tiger_order.avg_fill_price or 0),
                "creation_timestamp": int(datetime.now().timestamp() * 1000),
                "last_update_timestamp": int(datetime.now().timestamp() * 1000)
            }

            return DeribitOrderResponse({
                "order": order_dict,
                "trades": []
            })

        except Exception as error:
            print(f"❌ Failed to convert order response: {error}")
            return None

    def _convert_tiger_position_to_deribit(self, tiger_position: Any) -> Optional[Dict]:
        """转换Tiger持仓为Deribit格式"""
        try:
            # 转换标识符
            tiger_symbol = tiger_position.get('contract', {}).get('identifier', '')
            if not tiger_symbol:
                return None

            deribit_symbol = self.symbol_converter.tiger_to_deribit(tiger_symbol)

            return {
                "instrument_name": deribit_symbol,
                "size": float(tiger_position.get('quantity', 0)),
                "direction": "buy" if float(tiger_position.get('quantity', 0)) > 0 else "sell",
                "average_price": float(tiger_position.get('average_cost', 0)),
                "mark_price": float(tiger_position.get('market_price', 0)),
                "delta": float(tiger_position.get('delta', 0)),
                "gamma": float(tiger_position.get('gamma', 0)),
                "theta": float(tiger_position.get('theta', 0)),
                "vega": float(tiger_position.get('vega', 0)),
                "floating_profit_loss": float(tiger_position.get('unrealized_pnl', 0)),
                "realized_profit_loss": float(tiger_position.get('realized_pnl', 0))
            }

        except Exception as error:
            print(f"❌ Failed to convert position: {error}")
            return None

    def _convert_tiger_order_status(self, tiger_status: str) -> str:
        """转换Tiger订单状态为Deribit格式"""
        status_mapping = {
            "NEW": "open",
            "FILLED": "filled",
            "CANCELLED": "cancelled",
            "REJECTED": "rejected",
            "PARTIALLY_FILLED": "open"
        }
        return status_mapping.get(tiger_status, "open")
