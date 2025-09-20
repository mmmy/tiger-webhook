"""
Tiger Brokers API客户端

替换原有的Deribit客户端，使用Tiger Brokers官方SDK
"""

import os
import math
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.push.push_client import PushClient
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.common.consts import Language, Market
from tigeropen.common.util.contract_utils import option_contract, stock_contract
from tigeropen.common.util.order_utils import market_order, limit_order
from tigeropen.common.exceptions import ApiException

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
            if account.user_token:
                self.client_config.token = account.user_token
            self.client_config.language = Language.en_US
            
            # 初始化客户端
            self.quote_client = QuoteClient(self.client_config)
            self.trade_client = TradeClient(self.client_config)
            
            self._current_account = account_name
            
            print(f"✅ Tiger clients initialized for account: {account_name}")
    
    async def get_instruments(self, underlying_symbol: str, kind: str = "option") -> List[Dict]:
        """获取期权工具列表 - 直接使用Tiger格式"""
        if kind != "option":
            raise ValueError("Tiger client only supports options")

        try:
            # 直接使用传入的标的符号，不进行货币映射
            symbol = underlying_symbol.upper()
            all_options = []

            print(f"   获取 {symbol} 的期权工具...")

            # 获取期权到期日
            expirations = self.quote_client.get_option_expirations(symbols=[symbol])

            if expirations is None or len(expirations) == 0:
                print(f"   ⚠️ 没有找到 {symbol} 的期权到期日")
                return []

            print(f"   找到 {len(expirations)} 个到期日")

            for _, expiry_row in expirations.iterrows():
                expiry_timestamp = int(expiry_row['timestamp'])
                expiry_date = expiry_row.get('date', 'N/A')

                print(f"   处理到期日: {expiry_date}")

                # 获取期权链
                option_chain = self.quote_client.get_option_chain(symbol, expiry_timestamp)

                if option_chain is None or len(option_chain) == 0:
                    print(f"   ⚠️ 到期日 {expiry_date} 没有期权数据")
                    continue

                # 直接使用Tiger格式，不转换
                for _, option in option_chain.iterrows():
                    tiger_option = self._convert_tiger_option_to_native(option, symbol)
                    if tiger_option:
                        all_options.append(tiger_option)

            print(f"   ✅ 总共获取到 {len(all_options)} 个期权工具")
            return all_options

        except Exception as error:
            print(f"❌ Failed to get instruments: {error}")
            return []
    
    async def get_ticker(self, instrument_name: str) -> Optional[Dict]:
        """获取期权报价 - 直接使用Tiger格式"""
        try:
            # 直接使用Tiger格式的标识符
            tiger_symbol = instrument_name

            print(f"   获取期权报价: {tiger_symbol}")

            # 获取期权报价
            briefs = self.quote_client.get_option_briefs([tiger_symbol])

            if briefs is None or len(briefs) == 0:
                print(f"   ⚠️ 未获取到期权报价数据")
                return None

            option_data = briefs.iloc[0]

            # 直接返回Tiger格式数据
            ticker_data = {
                "instrument_name": instrument_name,
                "symbol": tiger_symbol,
                "best_bid_price": float(option_data.get('bid', 0) or 0),
                "best_ask_price": float(option_data.get('ask', 0) or 0),
                "best_bid_amount": float(option_data.get('bid_size', 0) or 0),
                "best_ask_amount": float(option_data.get('ask_size', 0) or 0),
                "mark_price": float(option_data.get('latest_price', 0) or 0),
                "last_price": float(option_data.get('latest_price', 0) or 0),
                "mark_iv": float(option_data.get('implied_vol', 0) or 0),
                "index_price": float(option_data.get('underlying_price', 0) or 0),
                "volume": float(option_data.get('volume', 0) or 0),
                "open_interest": float(option_data.get('open_interest', 0) or 0),
                "greeks": {
                    "delta": float(option_data.get('delta', 0) or 0),
                    "gamma": float(option_data.get('gamma', 0) or 0),
                    "theta": float(option_data.get('theta', 0) or 0),
                    "vega": float(option_data.get('vega', 0) or 0)
                },
                "timestamp": int(datetime.now().timestamp() * 1000)
            }

            print(f"   ✅ 报价获取成功: 买价={ticker_data['best_bid_price']}, 卖价={ticker_data['best_ask_price']}")
            return ticker_data

        except Exception as error:
            print(f"❌ Failed to get ticker for {instrument_name}: {error}")
            return None
    
    def _convert_tiger_option_to_native(self, tiger_option: Any, underlying: str) -> Dict:
        """转换Tiger期权数据到原生格式（不转换为Deribit）"""
        try:
            # 直接使用Tiger的标识符
            tiger_symbol = tiger_option.get('identifier', '')
            if not tiger_symbol:
                return None

            return {
                "instrument_name": tiger_symbol,
                "symbol": tiger_symbol,
                "underlying": underlying,
                "kind": "option",
                "option_type": tiger_option.get('right', '').lower(),
                "strike": float(tiger_option.get('strike', 0) or 0),
                "expiration_timestamp": int(tiger_option.get('expiry', 0) or 0),
                "expiration_date": tiger_option.get('expiry_date', ''),
                "tick_size": 0.01,
                "min_trade_amount": 1,
                "contract_size": 100,
                "currency": "USD"
            }
        except Exception as error:
            print(f"❌ Failed to convert Tiger option: {error}")
            return None
    
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

            # 直接使用Tiger格式标识符
            tiger_symbol = instrument_name

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

            # 直接使用Tiger格式标识符
            tiger_symbol = instrument_name

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

            raw_positions = self.trade_client.get_positions(account=self.client_config.account)
            if raw_positions is None:
                return []

            records: List[Dict[str, Any]] = []

            if hasattr(raw_positions, 'iterrows'):
                for _, row in raw_positions.iterrows():
                    if hasattr(row, 'to_dict'):
                        records.append(row.to_dict())
                    else:
                        try:
                            records.append(dict(row))
                        except Exception:
                            continue
            elif isinstance(raw_positions, list):
                for item in raw_positions:
                    if hasattr(item, 'to_dict'):
                        records.append(item.to_dict())
                    elif isinstance(item, dict):
                        records.append(item)
                    else:
                        try:
                            records.append(dict(item))
                        except Exception:
                            continue
            elif hasattr(raw_positions, 'to_dict'):
                try:
                    records = raw_positions.to_dict('records')  # type: ignore[arg-type]
                except Exception:
                    pass
            elif isinstance(raw_positions, dict):
                records = [raw_positions]

            if not records and raw_positions is not None:
                try:
                    for item in raw_positions:  # type: ignore[arg-type]
                        if hasattr(item, 'to_dict'):
                            records.append(item.to_dict())
                        elif isinstance(item, dict):
                            records.append(item)
                except Exception:
                    pass

            deribit_positions = []
            for position in records:
                if not isinstance(position, dict):
                    continue
                if position.get('sec_type') == 'OPT':  # 只处理期权持仓
                    deribit_position = self._convert_tiger_position_to_deribit(position)
                    if deribit_position:
                        deribit_positions.append(deribit_position)

            return deribit_positions

        except Exception as error:
            print(f"? Failed to get positions: {error}")
            return []

    async def get_account_summary(self, account_name: str, currency: str = "USD") -> Dict[str, Any]:
        """构建Tiger账户汇总信息"""
        await self._ensure_clients(account_name)

        positions = await self.get_positions(account_name, currency)

        summary: Dict[str, Any] = {
            "account_name": account_name,
            "account": getattr(self.client_config, 'account', account_name) if self.client_config else account_name,
            "currency": currency,
            "timestamp": datetime.utcnow().isoformat(),
            "option_position_count": len(positions),
            "option_total_delta": 0.0,
            "option_total_gamma": 0.0,
            "option_total_theta": 0.0,
            "option_total_vega": 0.0,
            "total_unrealized_pnl": 0.0,
            "total_realized_pnl": 0.0,
            "total_mark_value": 0.0
        }

        contract_size = 100.0

        for position in positions:
            size = float(position.get('size', 0.0))
            mark_price = float(position.get('mark_price', 0.0))
            summary["option_total_delta"] += float(position.get('delta', 0.0)) * size
            summary["option_total_gamma"] += float(position.get('gamma', 0.0)) * size
            summary["option_total_theta"] += float(position.get('theta', 0.0)) * size
            summary["option_total_vega"] += float(position.get('vega', 0.0)) * size
            summary["total_unrealized_pnl"] += float(position.get('floating_profit_loss', 0.0))
            summary["total_realized_pnl"] += float(position.get('realized_profit_loss', 0.0))
            summary["total_mark_value"] += mark_price * size * contract_size

        return summary

    async def get_account_assets(self, account_name: str) -> List[Dict[str, Any]]:
        'Fetch Tiger account asset information.'
        await self._ensure_clients(account_name)

        if not self.trade_client or not self.client_config:
            return []

        try:
            asset_accounts = self.trade_client.get_assets(
                account=self.client_config.account,
                market_value=True
            )
        except Exception as error:
            print(f'? Failed to get account assets: {error}')
            raise

        if not asset_accounts:
            return []

        return [self._serialize_portfolio_account(asset) for asset in asset_accounts]

    async def get_managed_accounts_info(self, account_name: str) -> List[Dict[str, Any]]:
        'Fetch Tiger managed account profiles.'
        await self._ensure_clients(account_name)

        if not self.trade_client or not self.client_config:
            return []

        profiles = None
        last_error: Optional[Exception] = None
        for kwargs in ({'account': self.client_config.account}, {}):
            try:
                filtered_kwargs = {key: value for key, value in kwargs.items() if value}
                profiles = self.trade_client.get_managed_accounts(**filtered_kwargs)
                if profiles is not None:
                    break
            except ApiException as error:
                last_error = error
                print(f"? Failed to get managed accounts with params {kwargs}: {error}")
            except Exception as error:
                last_error = error
                print(f"? Failed to get managed accounts with params {kwargs}: {error}")

        if profiles is None:
            if last_error is not None:
                raise last_error
            return []

        if not profiles:
            return []

        managed_accounts: List[Dict[str, Any]] = []
        for profile in profiles:
            data = self._serialize_object(profile)
            # Ensure core fields exist even if _serialize_object filtered them out
            for attr in ('account', 'capability', 'status', 'account_type'):
                value = getattr(profile, attr, None)
                if attr not in data and value is not None:
                    if attr == 'capability' and not isinstance(value, (list, tuple)):
                        data[attr] = [value]
                    else:
                        data[attr] = value
            if isinstance(data.get('capability'), tuple):
                data['capability'] = list(data['capability'])
            managed_accounts.append(data)

        return managed_accounts

    def _serialize_portfolio_account(self, asset: Any) -> Dict[str, Any]:
        'Serialize Tiger PortfolioAccount into JSON-ready structure.'
        if asset is None:
            return {}

        summary_data = self._serialize_object(getattr(asset, 'summary', None))

        market_values_data = []
        market_values = getattr(asset, 'market_values', None)
        if market_values:
            for currency, market_value in market_values.items():
                mv_data = self._serialize_object(market_value)
                if currency and not mv_data.get('currency'):
                    mv_data['currency'] = currency
                market_values_data.append(mv_data)

        segments_data = []
        segments = getattr(asset, 'segments', None)
        if segments:
            for segment_name, segment_obj in segments.items():
                segment_data = self._serialize_object(segment_obj)
                segment_data['segment'] = segment_name
                segments_data.append(segment_data)

        return {
            'account': getattr(asset, 'account', None),
            'summary': summary_data or None,
            'market_values': market_values_data or None,
            'segments': segments_data or None,
        }

    def _serialize_object(self, obj: Any) -> Dict[str, Any]:
        'Convert Tiger SDK objects to JSON-safe dictionaries.'
        if obj is None:
            return {}

        data: Dict[str, Any] = {}
        for key, value in vars(obj).items():
            normalized = self._normalize_value(value)
            if normalized is not None:
                data[key] = normalized
        return data

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        'Normalize Tiger numeric/date values to JSON-safe primitives.'
        if isinstance(value, (int, float)):
            value = float(value)
            if math.isfinite(value):
                return value
            return None
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if hasattr(value, 'isoformat'):
            try:
                return value.isoformat()
            except Exception:  # pragma: no cover - defensive
                return str(value)
        return value

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
