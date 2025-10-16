"""
Tiger Brokers API客户端

替换原有的Deribit客户端，使用Tiger Brokers官方SDK
"""

import os
import math
import time
import re
import asyncio
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.push.push_client import PushClient
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.common.consts import Language, Market, SecurityType
from tigeropen.common.util.contract_utils import option_contract, stock_contract
from tigeropen.common.util.order_utils import market_order, limit_order
from tigeropen.common.exceptions import ApiException
from tigeropen.trade.domain.position import Position

from types import SimpleNamespace

from ..config.config_loader import ConfigLoader
from ..config.settings import settings
from ..services.auth_service import AuthenticationService
from ..models.deribit_types import DeribitOrderResponse
from ..utils.symbol_converter import OptionSymbolConverter
from ..utils.logging_config import get_global_logger


# todo: 实现一个get_option_details函数,参数:symbol, 调用get_option_briefs
class TigerClient:
    """Tiger Brokers客户端，替换DeribitClient"""

    def __init__(self):
        self.config_loader = ConfigLoader.get_instance()
        self.auth_service = AuthenticationService.get_instance()
        self.symbol_converter = OptionSymbolConverter()
        self.logger = get_global_logger().bind(component="tiger_client")

        # Tiger客户端配置
        self.client_config: Optional[TigerOpenClientConfig] = None
        self.quote_client: Optional[QuoteClient] = None
        self.trade_client: Optional[TradeClient] = None
        self.push_client: Optional[PushClient] = None
        self._current_account: Optional[str] = None

        # 简单内存缓存：期权链，按标的缓存，TTL 秒
        self._instruments_cache: Dict[str, Dict[str, Any]] = {}
        self._instruments_cache_ttl_sec: int = 60
        self._expirations_cache: Dict[str, Dict[str, Any]] = {}
        self._expirations_cache_ttl_sec: int = 60
        self._underlyings_cache: Dict[str, Dict[str, Any]] = {}
        self._underlyings_cache_ttl_sec: int = 300

        # 标的价格缓存：避免短时间内重复API调用
        self._underlying_price_cache: Dict[str, Dict[str, Any]] = {}
        self._underlying_price_cache_ttl_sec: int = 60  # 1分钟有效期

        # Market status cache (5 min TTL)
        self._market_status_cache: Dict[str, Dict[str, Any]] = {}
        self._market_status_cache_ttl_sec: int = 300

        # 美股品种缓存：每24小时更新一次
        self._us_symbols_cache: Dict[str, Dict[str, Any]] = {}
        self._us_symbols_cache_ttl_sec: int = 24 * 3600  # 24小时有效期


    # --- helpers ------------------------------------------------------------
    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safely get attr/key from dict or object."""
        try:
            if obj is None:
                return default
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)
        except Exception:
            return default

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """Best-effort convert an object to dict."""
        if obj is None:
            return {}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            try:
                d = obj.to_dict()
                if isinstance(d, dict):
                    return d
            except Exception:
                pass
        result: Dict[str, Any] = {}
        for name in dir(obj):
            if name.startswith('_'):
                continue
            try:
                value = getattr(obj, name)
            except Exception:
                continue
            if callable(value):
                continue
            result[name] = value
        return result

    def _safe_float(self, value: Any) -> Optional[float]:
        """Convert value to float, ensuring it's JSON-compliant.

        Returns None for inf, -inf, nan, or invalid values that cannot be serialized to JSON.
        """
        if value is None:
            return None

        try:
            float_val = float(value)
            # Check if the float value is finite (not inf, -inf, or nan)
            if math.isfinite(float_val):
                return float_val
            else:
                # self.logger.warning(f"Invalid float value detected: {float_val}, converting to None")
                return None
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to convert value to float: {value}, converting to None")
            return None

    def _sanitize_json_data(self, data: Any) -> Any:
        """Ensure the provided data structure only contains JSON-serializable values."""
        if data is None:
            return None

        # Handle numpy/pandas scalar types that expose the ``item`` method
        if hasattr(data, "item") and callable(getattr(data, "item")):
            try:
                return self._sanitize_json_data(data.item())
            except Exception:
                return None

        if isinstance(data, (str, bool)):
            return data

        if isinstance(data, bytes):
            try:
                return data.decode("utf-8")
            except Exception:
                return None

        if isinstance(data, (datetime, date)):
            return data.isoformat()

        if isinstance(data, int):
            return int(data)

        if isinstance(data, float):
            return self._safe_float(data)

        if isinstance(data, dict):
            sanitized_dict: Dict[str, Any] = {}
            for key, value in data.items():
                sanitized_dict[str(key)] = self._sanitize_json_data(value)
            return sanitized_dict

        if isinstance(data, (list, tuple, set)):
            return [self._sanitize_json_data(item) for item in data]

        # Fallback: attempt string conversion so the value is not lost entirely
        try:
            return str(data)
        except Exception:
            return None

    def _get_cached_market_status(self, cache_key: str) -> Optional[Any]:
        """Return cached market status if available and fresh."""
        entry = self._market_status_cache.get(cache_key)
        if not entry:
            return None

        timestamp = entry.get("timestamp", 0)
        if (time.time() - timestamp) > self._market_status_cache_ttl_sec:
            return None

        return entry.get("data")

    def _set_cached_market_status(self, cache_key: str, data: Any) -> None:
        """Store market status result in cache."""
        self._market_status_cache[cache_key] = {
            "timestamp": time.time(),
            "data": data
        }

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

    async def ensure_quote_client(self, account_name: Optional[str] = None) -> str:
        """确保行情客户端已准备好并返回已使用的账户名"""
        # 如果显式指定账户且当前不是该账户，则切换
        if account_name and account_name != self._current_account:
            await self._ensure_clients(account_name)
            return account_name

        # 如果未初始化客户端，则选择第一个启用账户
        if self.quote_client is None or self._current_account is None:
            enabled_accounts = self.config_loader.get_enabled_accounts()
            if not enabled_accounts:
                raise RuntimeError("No enabled accounts available for Tiger client")

            default_account = enabled_accounts[0].name
            await self._ensure_clients(default_account)
            return default_account

        return self._current_account

    def invalidate_instruments_cache(self, underlying_symbol: Optional[str] = None) -> None:
        """清理期权链缓存"""
        if underlying_symbol:
            self._instruments_cache.pop(underlying_symbol.upper(), None)
            self._expirations_cache.pop(underlying_symbol.upper(), None)
            self._underlying_price_cache.pop(underlying_symbol.upper(), None)
            return
        self._instruments_cache.clear()
        self._expirations_cache.clear()
        self._underlyings_cache.clear()
        self._underlying_price_cache.clear()

    async def get_option_underlyings(
        self,
        account_name: Optional[str] = None,
        market: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取期权可选标的列表

        注意: Tiger目前主要支持香港市场(HK)的期权数据
        """
        used_account = await self.ensure_quote_client(account_name)

        cache_key = f"{used_account}:{(market or 'ALL').upper()}"
        cache = self._underlyings_cache.get(cache_key)
        if cache:
            ts = cache.get('ts'); items = cache.get('items')
            if ts and (datetime.now().timestamp() - ts) < self._underlyings_cache_ttl_sec:
                return items or []

        market_enum = None
        if market:
            try:
                market_enum = getattr(Market, market.upper())
            except AttributeError:
                print(f"⚠️ 未找到市场枚举 {market}，使用默认市场")
                market_enum = None

        # 首先尝试指定市场，如果失败则尝试默认市场
        symbols_df = None
        error_messages = []

        # 如果指定了市场，先尝试该市场
        if market_enum:
            try:
                symbols_df = self.quote_client.get_option_symbols(market=market_enum)
            except Exception as error:
                error_messages.append(f"市场 {market}: {error}")

        # 如果指定市场失败或未指定市场，尝试默认调用
        if symbols_df is None or len(symbols_df) == 0:
            try:
                symbols_df = self.quote_client.get_option_symbols()
            except Exception as error:
                error_messages.append(f"默认市场: {error}")

        # 如果还是失败，尝试HK市场（Tiger主要支持的市场）
        if symbols_df is None or len(symbols_df) == 0:
            try:
                symbols_df = self.quote_client.get_option_symbols(market=Market.HK)
            except Exception as error:
                error_messages.append(f"HK市场: {error}")

        if symbols_df is None or len(symbols_df) == 0:
            print(f"❌ 所有市场尝试都失败:")
            for msg in error_messages:
                print(f"  - {msg}")
            print(f"💡 提示: Tiger目前主要支持香港市场(HK)的期权数据")
            return []

        if symbols_df is None or len(symbols_df) == 0:
            return []

        underlyings: Dict[str, Dict[str, Any]] = {}

        for _, row in symbols_df.iterrows():
            symbol = (row.get('symbol') or row.get('code') or '').strip()
            if not symbol:
                continue

            key = symbol.upper()
            if key in underlyings:
                continue

            underlyings[key] = {
                "symbol": symbol.upper(),
                "name": row.get('name') or row.get('description') or symbol.upper(),
                "market": str(row.get('market') or (market_enum.name if market_enum else '')).upper(),
                "currency": row.get('currency') or 'USD'
            }

        result = sorted(underlyings.values(), key=lambda item: item['symbol'])

        self._underlyings_cache[cache_key] = {
            'ts': datetime.now().timestamp(),
            'items': result,
        }

        return result

    async def get_option_expirations(self, underlying_symbol: str) -> List[Dict[str, Any]]:
        """获取指定标的的期权到期日列表"""
        await self.ensure_quote_client()

        symbol = underlying_symbol.upper()

        cache = self._expirations_cache.get(symbol)
        if cache:
            ts = cache.get('ts'); items = cache.get('items')
            if ts and (datetime.now().timestamp() - ts) < self._expirations_cache_ttl_sec:
                return items or []

        expirations_df = self.quote_client.get_option_expirations(symbols=[symbol])
        if expirations_df is None or len(expirations_df) == 0:
            return []

        now_ms = int(datetime.now().timestamp() * 1000)
        expirations: List[Dict[str, Any]] = []

        for _, row in expirations_df.iterrows():
            raw_ts = int(row.get('timestamp') or 0)
            # Tiger 返回秒；转换为毫秒维护一致性
            ts_ms = raw_ts * 1000 if raw_ts and raw_ts < 10**12 else raw_ts
            if ts_ms <= 0:
                continue

            days_left = max(0, int((ts_ms - now_ms) / (24 * 3600 * 1000)))

            # 过滤掉已到期的日期（只保留未来的到期日）
            if ts_ms <= now_ms:
                continue  # 跳过已到期的日期

            expirations.append({
                "timestamp": ts_ms,
                "date": row.get('date') or datetime.fromtimestamp(ts_ms / 1000).strftime('%Y-%m-%d'),
                "days_to_expiry": days_left
            })

        expirations.sort(key=lambda item: item["timestamp"])

        self._expirations_cache[symbol] = {
            'ts': datetime.now().timestamp(),
            'items': expirations,
        }

        return expirations

    async def get_instruments(
        self,
        underlying_symbol: str,
        kind: str = "option",
        expiry_timestamp: Optional[int] = None
    ) -> List[Dict]:
        """获取期权工具列表 - 直接使用Tiger格式"""
        if kind != "option":
            raise ValueError("Tiger client only supports options")

        try:
            await self.ensure_quote_client()

            # 直接使用传入的标的符号，不进行货币映射
            symbol = underlying_symbol.upper()

            cache_key = symbol if expiry_timestamp is None else f"{symbol}:{int(expiry_timestamp)}"

            # 缓存命中则直接返回
            cache = self._instruments_cache.get(cache_key)
            if cache:
                ts = cache.get('ts'); items = cache.get('items')
                if ts and (datetime.now().timestamp() - ts) < self._instruments_cache_ttl_sec:
                    self.logger.info("✅ 命中缓存的期权链",
                                   symbol=symbol,
                                   ttl_seconds=self._instruments_cache_ttl_sec)
                    return items or []

            all_options = []

            self.logger.info("获取期权工具", symbol=symbol)

            def convert_timestamp(value: Optional[int]) -> Optional[int]:
                if value is None:
                    return None
                return value * 1000 if value < 10**12 else value

            if expiry_timestamp is not None:
                expiry_ts_ms = convert_timestamp(int(expiry_timestamp))
                if expiry_ts_ms is None:
                    return []

                self.logger.debug("处理单一到期日", expiry_timestamp_ms=expiry_ts_ms)
                option_chain = await self.get_option_chain(symbol, int(expiry_ts_ms))

                if option_chain is None or len(option_chain) == 0:
                    self.logger.warning("⚠️ 指定到期日没有期权数据")
                else:
                    for option in option_chain:
                        tiger_option = self._prepare_tiger_option_data(option, symbol)
                        if tiger_option:
                            all_options.append(tiger_option)
            else:
                # 获取所有到期日（向后兼容）
                expirations = self.quote_client.get_option_expirations(symbols=[symbol])

                if expirations is None or len(expirations) == 0:
                    self.logger.warning("⚠️ 没有找到期权到期日", symbol=symbol)
                    return []

                self.logger.debug("找到期权到期日", symbol=symbol, expiration_count=len(expirations))

                for _, expiry_row in expirations.iterrows():
                    expiry_ts = convert_timestamp(int(expiry_row['timestamp']))
                    expiry_date = expiry_row.get('date', 'N/A')

                    self.logger.debug("处理到期日", expiry_date=expiry_date)

                    # 获取期权链
                    option_chain = await self.get_option_chain(symbol, int(expiry_ts or 0))

                    if option_chain is None or len(option_chain) == 0:
                        self.logger.warning("⚠️ 到期日没有期权数据", expiry_date=expiry_date)
                        continue

                    # 直接使用Tiger格式，保留所有原始数据
                    for option in option_chain:
                        tiger_option = self._prepare_tiger_option_data(option, symbol)
                        if tiger_option:
                            all_options.append(tiger_option)

            self.logger.info("✅ 总共获取到期权工具",
                            symbol=symbol,
                            option_count=len(all_options))
            # 写入缓存
            self._instruments_cache[cache_key] = {
                'ts': datetime.now().timestamp(),
                'items': all_options,
            }
            return all_options

        except Exception as error:
            self.logger.error("❌ Failed to get instruments", symbol=symbol, error=str(error))
            return []

    async def get_ticker(self, instrument_name: str) -> Optional[Dict]:
        """获取期权报价 - 直接使用Tiger格式"""
        try:
            await self.ensure_quote_client()

            # 直接使用Tiger格式的标识符
            tiger_symbol = instrument_name

            self.logger.debug("获取期权报价", tiger_symbol=tiger_symbol)

            # 获取期权报价
            briefs = self.quote_client.get_option_briefs([tiger_symbol])

            if briefs is None or len(briefs) == 0:
                self.logger.warning("⚠️ 未获取到期权报价数据", tiger_symbol=tiger_symbol)
                return None

            option_data = briefs.iloc[0]

            # 直接返回Tiger格式数据，使用safe_float确保JSON兼容性
            ticker_data = {
                "instrument_name": instrument_name,
                "symbol": tiger_symbol,
                "best_bid_price": self._safe_float(option_data.get('bid_price', 0) or 0),
                "best_ask_price": self._safe_float(option_data.get('ask_price', 0) or 0),
                "best_bid_amount": self._safe_float(option_data.get('bid_size', 0) or 0),
                "best_ask_amount": self._safe_float(option_data.get('ask_size', 0) or 0),
                "mark_price": self._safe_float(option_data.get('latest_price', 0) or 0),
                "last_price": self._safe_float(option_data.get('latest_price', 0) or 0),
                "mark_iv": self._safe_float(option_data.get('implied_vol', 0) or 0),
                "index_price": self._safe_float(option_data.get('underlying_price', 0) or 0),
                "volume": self._safe_float(option_data.get('volume', 0) or 0),
                "open_interest": self._safe_float(option_data.get('open_interest', 0) or 0),
                "timestamp": int(datetime.now().timestamp() * 1000)
            }


            print(f"   ✅ 报价获取成功: 买价={ticker_data['best_bid_price']}, 卖价={ticker_data['best_ask_price']}")
            return SimpleNamespace(**ticker_data)

        except Exception as error:
            print(f"❌ Failed to get ticker for {instrument_name}: {error}")
            return None

    async def get_instrument_by_delta(
        self,
        currency: str,
        min_expired_days: int,
        delta: float,
        long_side: bool,
        underlying_asset: str
    ) -> Optional[SimpleNamespace]:
        """Select an option instrument by target delta with better precision.
        Strategy:
        1) Filter by option type and min expiry
        2) Prefer candidates with available delta, pick closest to |target|
        3) If delta missing, narrow to strikes nearest to underlying and batch-fetch briefs to get delta
        4) Return chosen instrument with latest bid/ask and computed spread
        """
        try:
            # Ensure quote client is initialized (use first enabled account if not set)
            if not hasattr(self, 'quote_client') or self.quote_client is None:
                account = ConfigLoader.get_instance().get_enabled_accounts()[0]
                await self._ensure_clients(account.name)
                self.logger.info("get_instrument_by_delta",
                           account=account.name,
                           underlying_asset=underlying_asset,
                           min_expired_days=min_expired_days,
                           target_delta=delta)

            self.logger.info("get_instrument_by_delta: 开始查找期权",
                           underlying_asset=underlying_asset,
                           min_expired_days=min_expired_days,
                           target_delta=delta)

            options = await self.get_instruments_min_days(underlying_asset, min_expired_days)
            if not options:
                self.logger.warning("get_instrument_by_delta: 没有找到期权", underlying_asset=underlying_asset)
                return None

            opt_type = "call" if delta > 0 else "put"
            target_delta = abs(delta) * 1.1  # Use absolute value for comparison
            self.logger.info("get_instrument_by_delta: 筛选期权",
                            option_type=opt_type,
                            target_delta=target_delta,
                            buffer_ratio=0.1)

            # 1. 根据opt_type过滤options，并筛选出delta接近目标值的期权
            filtered_options = []
            self.logger.info("get_instrument_by_delta: 开始筛选期权",
                            option_count=len(options))

            for i, option in enumerate(options):
                if option.get('option_type', '').lower() != opt_type:
                    continue

                # 获取期权的delta值
                option_delta = option.get('delta')
                if option_delta is None or option_delta == "":
                    continue

                try:
                    delta_val = abs(float(option_delta))
                    # 筛选出delta值小于目标delta的期权（留有余地）
                    if delta_val <= target_delta:
                        filtered_options.append(option)

                except (ValueError, TypeError):
                    self.logger.warning("get_instrument_by_delta: 筛选失败",
                                         option_name=option.get('instrument_name'),
                                         reason="无效的delta值")
                    continue

            if not filtered_options:
                self.logger.warning("get_instrument_by_delta: 没有找到符合条件的期权",
                                        opt_type=opt_type)
                return None

            self.logger.info("get_instrument_by_delta: 筛选完成",
                            total=len(filtered_options),
                            opt_type=opt_type,
                            target_delta=target_delta)

            # 2. 然后根据|delta - option.delta|的绝对值排序, 选出3个小的
            # First, separate options with and without delta values
            options_with_delta = []
            options_without_delta = []

            for option in filtered_options:
                # 这里
                option_delta = option.get('delta')
                if option_delta is not None and option_delta != "" and abs(option_delta) > 0:
                    try:
                        delta_val = abs(float(option_delta))
                        delta_distance = abs(target_delta - delta_val)
                        options_with_delta.append((option, delta_distance, delta_val))
                    except (ValueError, TypeError):
                        options_without_delta.append(option)
                else:
                    options_without_delta.append(option)

            # Sort options with delta by delta distance and take top 3
            options_with_delta.sort(key=lambda x: x[1])  # Sort by delta_distance
            top_candidates = options_with_delta[:3]

            self.logger.info("get_instrument_by_delta: 候选排序",
                            with_delta=len(options_with_delta),
                            without_delta=len(options_without_delta))

            if not top_candidates:
                self.logger.warning("get_instrument_by_delta: 未找到候选期权")
                return None

            self.logger.info("get_instrument_by_delta: 候选期权详情",
                            candidate_count=len(top_candidates))

            for i, (option, delta_dist, delta_val) in enumerate(top_candidates):
                self.logger.info("get_instrument_by_delta: 候选期权",
                            index=i+1,
                            instrument_name=option.get('instrument_name'),
                            delta=delta_val,
                            distance=delta_dist)

            # 3. 从3个中选一个: 盘口价差最小的
            best_option = None
            best_spread_ratio = float('inf')

            self.logger.info("get_instrument_by_delta: 开始评估盘口价差")
            for option, delta_distance, delta_val in top_candidates:
                instrument_name = option.get('instrument_name')
                if not instrument_name:
                    continue

                # Get ticker data for spread calculation
                bid = option.get('bid_price', 0)
                ask = option.get('ask_price', 0)

                if bid <= 0 or ask <= 0:
                    self.logger.warning("get_instrument_by_delta: 报价无效",
                                         instrument_name=instrument_name,
                                         bid=bid,
                                         ask=ask)
                    continue

                # Calculate spread ratio
                spread_ratio = (ask - bid) / ((bid + ask) / 2) if (bid + ask) > 0 else float('inf')

                self.logger.debug("get_instrument_by_delta: 评估价差",
                             instrument_name=instrument_name,
                             bid=bid,
                             ask=ask,
                             spread_ratio=spread_ratio)

                if spread_ratio < best_spread_ratio:
                    best_spread_ratio = spread_ratio
                    best_option = option

            if not best_option:
                self.logger.warning("get_instrument_by_delta: 未找到合适的期权")
                return None

            # Create result in expected format
            result = SimpleNamespace()
            # Convert dictionary to SimpleNamespace so it can be accessed with dot notation
            result.instrument = SimpleNamespace(**best_option)

            # Create details object with market data
            result.details = SimpleNamespace()
            result.details.best_bid_price = best_option.get('bid_price', 0) or best_option.get('bid', 0)
            result.details.best_ask_price = best_option.get('ask_price', 0) or best_option.get('ask', 0)
            result.details.index_price = best_option.get('underlying_price', 0)
            result.details.mark_price = (result.details.best_bid_price + result.details.best_ask_price) / 2 if result.details.best_bid_price and result.details.best_ask_price else 0

            result.spread_ratio = best_spread_ratio
            result.delta_distance = min(delta_distance for _, delta_distance, _ in top_candidates if delta_distance != float('inf')) if any(d != float('inf') for _, d, _ in top_candidates) else None

            self.logger.info("get_instrument_by_delta: 选择完成",
                           instrument_name=result.instrument.instrument_name,
                           delta=best_option.get('delta'),
                           spread_ratio=result.spread_ratio,
                           delta_distance=result.delta_distance)

            return result

        except Exception as e:
            self.logger.error("get_instrument_by_delta failed",
                           error=str(e))
            return None

    async def get_instruments_by_target_days(self, underlying_symbol: str, target_expired_days: int, take_expirations: int = 1) -> List[Dict]:
        """获取距离目标到期天数最近的期权链，减少接口调用以避免限流

        Args:
            underlying_symbol: 标的符号
            target_expired_days: 目标到期天数
            take_expirations: 取最近的几个到期日，默认1个

        Returns:
            期权列表
        """
        symbol = underlying_symbol.upper()
        try:
            print(f"   获取 {symbol} 的期权工具（目标 {target_expired_days} 天, 取前 {take_expirations} 个最近到期）...")
            expirations = self.quote_client.get_option_expirations(symbols=[symbol])
            if expirations is None or len(expirations) == 0:
                print(f"   ⚠️ 没有找到 {symbol} 的期权到期日")
                return []

            now_ms = int(datetime.now().timestamp() * 1000)

            # 选取距离目标到期日绝对值最近的到期日
            target_expiry_ms = now_ms + int((target_expired_days or 0) * 24 * 3600 * 1000)
            rows = []
            for _, r in expirations.iterrows():
                ts = int(r['timestamp'])
                # 计算与目标到期日的绝对差值（以毫秒为单位）
                abs_diff = abs(ts - target_expiry_ms)
                rows.append((ts, r.get('date', 'N/A'), abs_diff))

            # 按绝对差值排序，取最近的几个
            rows.sort(key=lambda x: x[2])  # 按绝对差值排序
            rows = rows[:max(1, int(take_expirations))]

            all_options: List[Dict] = []
            for ts, date_str, abs_diff in rows:
                days_diff = abs_diff / (24 * 3600 * 1000)  # Convert to days for logging
                print(f"   处理到期日: {date_str} (距离目标 {days_diff:.1f} 天)")
                option_chain = await self.get_option_chain(symbol, ts)
                if option_chain is None or len(option_chain) == 0:
                    print(f"   ⚠️ 到期日 {date_str} 没有期权数据")
                    continue
                for option in option_chain:
                    # 直接使用Tiger期权链数据，添加必要的兼容性字段
                    tiger_option = self._prepare_tiger_option_data(option, symbol)
                    if tiger_option:
                        all_options.append(tiger_option)

            print(f"   ✅ 总共获取到 {len(all_options)} 个期权工具 (目标天数模式)")
            return all_options
        except Exception as error:
            print(f"❌ Failed to get instruments (target_days): {error}")
            return []
        
    async def get_option_chain(self, underlying_symbol: str, expiry_timestamp: int) -> List[Dict]:
        """获取指定到期日的期权链，并计算希腊字母"""
        await self.ensure_quote_client()

        symbol = underlying_symbol.upper()
        option_chain = self.quote_client.get_option_chain(symbol, expiry_timestamp)
        if option_chain is None or len(option_chain) == 0:
            return []

        # 导入期权计算器
        try:
            from deribit_webhook.utils.option_calculator import calculate_option_greeks
        except ImportError:
            self.logger.warning("期权计算器不可用，将跳过希腊字母计算")
            calculate_option_greeks = None

        result_options = []

        for _, option in option_chain.iterrows():
            option_data = option.to_dict()

            # 如果期权计算器可用且有必要的数据，计算希腊字母
            # todo: option中没有underlying_price字段, 请看: https://quant.itigerup.com/openapi/zh/python/operation/quotation/option.html#get-option-chain-%E8%8E%B7%E5%8F%96%E6%9C%9F%E6%9D%83%E9%93%BE
            # 问题: latest_price是不是underlying_price?
            if calculate_option_greeks and self._has_required_option_data(option_data):
                try:
                    calculated_greeks = await self._calculate_option_greeks_for_chain(
                        option_data, underlying_symbol, expiry_timestamp
                    )
                    if calculated_greeks:
                        # 将计算的希腊字母添加到期权数据中
                        option_data.update({
                            'calculated_delta': calculated_greeks.get('delta'),
                            'calculated_gamma': calculated_greeks.get('gamma'),
                            'calculated_theta': calculated_greeks.get('theta'),
                            'calculated_vega': calculated_greeks.get('vega'),
                            'calculated_rho': calculated_greeks.get('rho'),
                            'calculated_value': calculated_greeks.get('value'),
                            'calculation_method': 'quantlib'
                        })
                except Exception as e:
                    self.logger.warning(f"计算期权希腊字母失败: {e}", option_identifier=option_data.get('identifier'))

            result_options.append(option_data)

        return result_options

    def _has_required_option_data(self, option_data: Dict) -> bool:
        """检查期权数据是否包含计算希腊字母所需的字段"""
        required_fields = [
            'strike',           # 行权价
            'implied_vol',      # 隐含波动率
            'put_call',         # 期权类型
            'expiry'            # 到期时间戳
        ]

        for field in required_fields:
            if field not in option_data or option_data[field] is None:
                return False

        # 检查数值字段是否为有效数值
        numeric_fields = ['strike', 'implied_vol']
        for field in numeric_fields:
            try:
                float(option_data[field])
            except (ValueError, TypeError):
                return False

        return True
    
    async def _calc_option_greeks_by_instrument(self, instrument_name: str):
        try:
            await self.ensure_quote_client()

            briefs = self.quote_client.get_option_briefs([instrument_name])
            if briefs is None or len(briefs) == 0:
                self.logger.warning("未获取到期权详情", instrument_name=instrument_name)
                return None

            option_brief = briefs.iloc[0].to_dict()

            parts = instrument_name.strip().split()
            if len(parts) != 2:
                self.logger.warning("无法解析期权名称", instrument_name=instrument_name)
                return None

            underlying_symbol = parts[0]
            option_part = parts[1]
            if len(option_part) < 9:
                self.logger.warning("期权标识格式不正确", option_name=instrument_name)
                return None

            expiry_str = option_part[:6]
            option_type_char = option_part[6].upper()
            strike_str = option_part[7:]

            try:
                strike_price = float(int(strike_str)) / 1000.0
                expiry_date = datetime.strptime(f"20{expiry_str}", "%Y%m%d")
            except ValueError as error:
                self.logger.warning("解析期权基本信息失败", instrument_name=instrument_name, error=str(error))
                return None

            expiry_timestamp = int(expiry_date.timestamp() * 1000)

            underlying_price = await self._get_underlying_price(underlying_symbol)
            if underlying_price is None:
                self.logger.warning("无法获取标的价格", underlying=underlying_symbol)
                return None

            option_data = {
                'identifier': instrument_name,
                'strike': strike_price,
                'put_call': option_type_char,
                'expiry': expiry_timestamp // 1000,
                'bid_price': option_brief.get('bid_price'),
                'ask_price': option_brief.get('ask_price'),
                'latest_price': option_brief.get('latest_price'),
                'implied_vol': float(option_brief.get('implied_vol') or 0.0)
            }

            greeks = await self._calculate_option_greeks_for_chain(
                option_data,
                underlying_symbol,
                expiry_timestamp
            )

            if greeks:
                greeks.setdefault('underlying_price', underlying_price)
            return greeks

        except Exception as error:
            self.logger.error("计算期权希腊字母失败", instrument_name=instrument_name, error=str(error))
            return None

    async def _calculate_option_greeks_for_chain(
        self, option_data: Dict, underlying_symbol: str, expiry_timestamp: int
    ) -> Optional[Dict]:
        """为期权链中的单个期权计算希腊字母"""
        try:
            from deribit_webhook.utils.option_calculator import calculate_option_greeks
            from datetime import datetime, date

            # 获取标的价格（期权数据中没有underlying_price字段）
            underlying_price = await self._get_underlying_price(underlying_symbol)
            if underlying_price is None:
                self.logger.warning(f"无法获取标的价格: {underlying_symbol}")
                return None

            # 提取期权参数
            strike_price = float(option_data['strike'])

            # 确定期权类型
            put_call = option_data.get('put_call', '').upper()
            if put_call in ['CALL', 'C']:
                option_type = 'call'
            elif put_call in ['PUT', 'P']:
                option_type = 'put'
            else:
                self.logger.warning(f"未知的期权类型: {put_call}")
                return None

            # 转换到期时间戳为日期
            expiry_date = datetime.fromtimestamp(expiry_timestamp / 1000).date()
            settlement_date = date.today()

            # 检查期权是否已过期
            if expiry_date < settlement_date:
                self.logger.warning(f"期权已过期，无法计算希腊字母: 到期日期 {expiry_date} < 今天 {settlement_date}")
                return None

            # 确保结算日期不等于到期日期（避免美式期权的日期冲突）
            if settlement_date >= expiry_date:
                # 如果期权今天到期，将结算日期设为昨天
                settlement_date = expiry_date - timedelta(days=1)
                # self.logger.warning(f"期权今天到期，调整结算日期: {settlement_date} -> 到期日期: {expiry_date}")

                # 再次检查调整后的日期是否合理
                if settlement_date >= expiry_date:
                    self.logger.warning(f"无法找到合适的结算日期，跳过计算")
                    return None

            # 使用默认的无风险利率和股息率
            # 在实际应用中，这些值应该从市场数据获取
            risk_free_rate = 0.03  # 3% 默认无风险利率
            dividend_rate = 0.005    # 0.5% 默认股息率

            implied_vol = float(option_data['implied_vol'])

            # 如果隐含波动率为0或接近0，尝试从期权价格重新计算
            if implied_vol <= 0.001:  # 小于0.1%认为是无效值
                # If latest_price is not available, use average of bid and ask prices
                market_price = option_data.get('latest_price')
                bid_price = float(option_data.get('bid_price', 0) or 0)
                ask_price = float(option_data.get('ask_price', 0) or 0)
                if market_price is None or float(market_price) == 0 or math.isnan(market_price):
                    if bid_price > 0 and ask_price > 0:
                        market_price = (bid_price + ask_price) / 2
                    else:
                        market_price = None
                if market_price and float(market_price) > 0:
                    try:
                        # self.logger.info(f"隐含波动率为0，尝试从市场价格重新计算: {market_price}")
                        calculated_vol = await self._calculate_implied_volatility(
                            option_type=option_type,
                            underlying_price=underlying_price,
                            strike_price=strike_price,
                            risk_free_rate=risk_free_rate,
                            dividend_rate=dividend_rate,
                            market_price=float(market_price),
                            settlement_date=settlement_date,
                            expiry_date=expiry_date
                        )
                        if calculated_vol and calculated_vol > 0:
                            implied_vol = calculated_vol
                            # self.logger.info(f"重新计算的隐含波动率: {implied_vol:.4f}")
                        else:
                            self.logger.warning(f"无法计算隐含波动率")
                            implied_vol = 0.2  # 使用20%作为默认波动率
                    except Exception as e:
                        self.logger.warning(f"计算隐含波动率失败: {e}")
                        implied_vol = None
                else:
                    self.logger.warning(f"无市场价格数据 market_price: {market_price} {bid_price} {ask_price}")
                    implied_vol = None
            if implied_vol is None:
                return None
            # 计算希腊字母
            greeks = calculate_option_greeks(
                option_type=option_type,
                underlying_price=underlying_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                volatility=implied_vol,
                settlement_date=settlement_date.strftime('%Y-%m-%d'),
                expiration_date=expiry_date.strftime('%Y-%m-%d'),
                dividend_rate=dividend_rate,
                evaluation_date=settlement_date.strftime('%Y-%m-%d'),
                option_style='american'  # 假设为美式期权
            )

            # 将标的价格添加到结果中
            greeks['underlying_price'] = underlying_price

            return greeks

        except Exception as e:
            self.logger.error(f"计算期权希腊字母时发生错误: {e}")
            return None

    async def _calculate_implied_volatility(
        self, option_type: str, underlying_price: float, strike_price: float,
        risk_free_rate: float, dividend_rate: float, market_price: float,
        settlement_date, expiry_date
    ) -> Optional[float]:
        """
        根据期权市场价格计算隐含波动率

        参考Tiger API文档的实现方式，使用期权计算器来反推波动率
        """
        try:
            from deribit_webhook.utils.option_calculator import calculate_implied_volatility

            self.logger.debug(f"计算隐含波动率参数: 类型={option_type}, 标的={underlying_price}, "
                            f"行权价={strike_price}, 市场价格={market_price}")

            # 预先验证参数合理性
            if market_price <= 0:
                self.logger.warning(f"期权价格无效: {market_price}")
                return None

            if underlying_price <= 0:
                self.logger.warning(f"标的价格无效: {underlying_price}")
                return None

            if strike_price <= 0:
                self.logger.warning(f"行权价无效: {strike_price}")
                return None

            # 检查期权是否已到期
            from datetime import datetime
            today = datetime.now().date()
            if expiry_date < today:
                self.logger.warning(f"期权已到期: {expiry_date}")
                return None

            # 计算内在价值用于后续的默认波动率判断
            if option_type.lower() == 'call':
                intrinsic_value = max(0, underlying_price - strike_price)
            else:
                intrinsic_value = max(0, strike_price - underlying_price)

            # 记录期权基本信息用于调试
            self.logger.debug(f"期权信息: 类型={option_type}, 内在价值={intrinsic_value:.4f}, "
                            f"市场价格={market_price:.4f}, 时间价值={market_price - intrinsic_value:.4f}")

            # 计算时间价值和到期天数，用于后续的默认波动率判断
            time_value = market_price - intrinsic_value
            days_to_expiry = (expiry_date - today).days

            # 使用期权计算器计算隐含波动率
            implied_vol = calculate_implied_volatility(
                option_type=option_type,
                underlying_price=underlying_price,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                dividend_rate=dividend_rate,
                option_price=market_price,  # 参数名是option_price，不是market_price
                settlement_date=settlement_date.strftime('%Y-%m-%d'),
                expiration_date=expiry_date.strftime('%Y-%m-%d'),
                evaluation_date=settlement_date.strftime('%Y-%m-%d'),
                option_style='american'  # 假设为美式期权
            )
            return implied_vol
            # 验证计算结果的合理性
            if implied_vol and 0.005 <= implied_vol <= 5.0:  # 0.5%到500%的合理范围
                return implied_vol
            else:
                self.logger.warning(f"计算的隐含波动率超出合理范围: {implied_vol}")
                # 对于边界情况，返回一个基于期权特征的合理默认值
                if intrinsic_value == 0 and days_to_expiry <= 7:
                    return 1.0  # 短期深度价外期权使用100%波动率
                elif intrinsic_value == 0:
                    return 0.5  # 深度价外期权使用50%波动率
                else:
                    return 0.2  # 其他情况使用20%波动率

        except ValueError as e:
            # 这是预期的错误，记录详细信息但不打印堆栈
            error_msg = str(e)
            if "root not bracketed" in error_msg:
                self.logger.warning(f"隐含波动率计算失败 - 无法找到合适的波动率范围: "
                                  f"期权={option_type}, 标的={underlying_price}, 行权价={strike_price}, "
                                  f"市场价格={market_price}")
            elif "低于内在价值" in error_msg:
                self.logger.warning(f"期权价格异常: {error_msg}")
            elif "数值方法计算隐含波动率失败" in error_msg:
                self.logger.warning(f"数值计算失败，使用默认波动率: {error_msg}")
                # 对于数值计算失败的情况，返回基于期权特征的默认值
                if intrinsic_value == 0 and days_to_expiry <= 7:
                    return 1.0  # 短期深度价外期权使用100%波动率
                elif intrinsic_value == 0:
                    return 0.5  # 深度价外期权使用50%波动率
                else:
                    return 0.2  # 其他情况使用20%波动率
            else:
                self.logger.warning(f"隐含波动率计算失败: {error_msg}")
            return None
        except Exception as e:
            self.logger.error(f"计算隐含波动率时发生未预期错误: {e}")
            return None

    async def _get_underlying_price(self, underlying_symbol: str) -> Optional[float]:
        """获取标的资产的当前价格

        使用get_stock_briefs接口获取股票的latest_price字段，
        这个字段是股票的最新价格，也就是期权的标的价格。

        实现1分钟缓存机制，避免短时间内重复API调用。
        """
        try:
            # 检查缓存
            cache_key = underlying_symbol.upper()
            current_time = time.time()

            if cache_key in self._underlying_price_cache:
                cache_entry = self._underlying_price_cache[cache_key]
                cache_time = cache_entry.get('timestamp', 0)
                cache_price = cache_entry.get('price')

                # 检查缓存是否在有效期内（1分钟）
                if current_time - cache_time < self._underlying_price_cache_ttl_sec:
                    if cache_price is not None:
                        self.logger.debug(f"从缓存获取标的价格: {underlying_symbol} = ${cache_price:.2f} (缓存时间: {current_time - cache_time:.1f}秒前)")
                        return cache_price

            await self.ensure_quote_client()

            # 尝试多种方法获取标的价格
            underlying_price = None

            # 方法1: 使用get_stock_briefs (实时行情，需要权限)
            # try:
            #     brief = self.quote_client.get_stock_briefs([underlying_symbol])
            #     if brief is not None and len(brief) > 0:
            #         latest_price = brief.iloc[0].get('latest_price')
            #         if latest_price is not None:
            #             underlying_price = float(latest_price)
            #             # 存储到缓存
            #             self._underlying_price_cache[cache_key] = {
            #                 'price': underlying_price,
            #                 'timestamp': current_time,
            #                 'method': 'get_stock_briefs'
            #             }
            #             self.logger.debug(f"通过get_stock_briefs获取到标的价格: {underlying_symbol} = ${underlying_price:.2f}")
            #             return underlying_price
            # except Exception as e:
            #     self.logger.warning(f"get_stock_briefs失败: {e}")

            # 方法2: 使用get_stock_delay_briefs (延迟行情，免费)
            try:
                delay_brief = self.quote_client.get_stock_delay_briefs([underlying_symbol])
                if delay_brief is not None and len(delay_brief) > 0:
                    close_price = delay_brief.iloc[0].get('close')
                    if close_price is not None:
                        underlying_price = float(close_price)
                        # 存储到缓存
                        self._underlying_price_cache[cache_key] = {
                            'price': underlying_price,
                            'timestamp': current_time,
                            'method': 'get_stock_delay_briefs'
                        }
                        self.logger.debug(f"通过get_stock_delay_briefs获取到标的价格: {underlying_symbol} = ${underlying_price:.2f}")
                        return underlying_price
            except Exception as e:
                self.logger.warning(f"get_stock_delay_briefs失败: {e}")

            # 方法3: 使用get_bars获取最新K线数据
            try:
                bars = self.quote_client.get_bars([underlying_symbol], limit=1)
                if bars is not None and len(bars) > 0:
                    close_price = bars.iloc[0].get('close')
                    if close_price is not None:
                        underlying_price = float(close_price)
                        # 存储到缓存
                        self._underlying_price_cache[cache_key] = {
                            'price': underlying_price,
                            'timestamp': current_time,
                            'method': 'get_bars'
                        }
                        self.logger.debug(f"通过get_bars获取到标的价格: {underlying_symbol} = ${underlying_price:.2f}")
                        return underlying_price
            except Exception as e:
                self.logger.warning(f"get_bars失败: {e}")

            self.logger.error(f"所有方法都无法获取标的价格: {underlying_symbol}")
            return None

        except Exception as e:
            self.logger.error(f"获取标的价格时发生错误: {e}")
            return None

    async def calculate_delta_by_option_name(self, option_name: str) -> Optional[float]:
        """根据期权名称计算delta值

        Args:
            option_name: Tiger期权名称，格式如 "QQQ 250926C00599000"

        Returns:
            计算得到的delta值，如果计算失败则返回None

        Example:
            delta = await client.calculate_delta_by_option_name("QQQ 250926C00599000")
            if delta is not None:
                print(f"Delta: {delta:.4f}")
        """
        try:
            await self.ensure_quote_client()

            self.logger.info("计算期权Delta", option_name=option_name)

            # 1. 通过get_option_briefs获取期权信息
            briefs = self.quote_client.get_option_briefs([option_name])

            if briefs is None or len(briefs) == 0:
                self.logger.warning("未获取到期权信息", option_name=option_name)
                return None

            option_brief = briefs.iloc[0]

            # 2. 解析期权名称获取基本信息
            try:
                # 解析Tiger格式: "QQQ 250926C00599000"
                parts = option_name.strip().split()
                if len(parts) != 2:
                    raise ValueError(f"Invalid option name format: {option_name}")

                underlying_symbol = parts[0]
                option_part = parts[1]

                # 解析期权部分: 250926C00599000
                if len(option_part) < 9:
                    raise ValueError(f"Invalid option part: {option_part}")

                expiry_str = option_part[:6]  # 250926
                option_type_char = option_part[6]  # C or P
                strike_str = option_part[7:]  # 00599000

                # 转换期权类型
                option_type = 'call' if option_type_char.upper() == 'C' else 'put'

                # 转换行权价 (Tiger使用千分之一为单位)
                strike_price = float(int(strike_str)) / 1000

                # 转换到期日
                from datetime import datetime
                expiry_date = datetime.strptime(f"20{expiry_str}", "%Y%m%d")
                expiry_timestamp = int(expiry_date.timestamp() * 1000)

            except Exception as e:
                self.logger.error("解析期权名称失败", option_name=option_name, error=str(e))
                return None

            # 3. 构造期权数据字典
            option_data = {
                'identifier': option_name,
                'strike': strike_price,
                'put_call': option_type_char.upper(),
                'expiry': expiry_timestamp // 1000,  # 转换为秒
                'bid_price': option_brief.get('bid_price'),
                'ask_price': option_brief.get('ask_price'),
                'latest_price': option_brief.get('latest_price'),
                'implied_vol': 0 #option_brief.get('implied_vol')
            }

            # 4. 使用现有的希腊字母计算方法
            greeks = await self._calculate_option_greeks_for_chain(
                option_data, underlying_symbol, expiry_timestamp
            )

            if greeks and 'delta' in greeks:
                delta = greeks['delta']
                self.logger.info("Delta计算成功",
                               option_name=option_name,
                               delta=f"{delta:.4f}",
                               underlying=underlying_symbol,
                               strike=strike_price,
                               option_type=option_type)
                return delta
            else:
                self.logger.warning("Delta计算失败", option_name=option_name)
                return None

        except Exception as error:
            self.logger.error("计算Delta时发生错误",
                            option_name=option_name,
                            error=str(error))
            return None

    async def get_instruments_min_days(self, underlying_symbol: str, min_expired_days: int, take_expirations: int = 1) -> List[Dict]:
        """获取满足最小到期天数的有限期权链，减少接口调用以避免限流

        此方法为向后兼容保留，内部调用新的 get_instruments_by_target_days 方法

        Args:
            underlying_symbol: 标的符号
            min_expired_days: 最小到期天数（现在作为目标天数处理）
            take_expirations: 取最近的几个到期日，默认1个

        Returns:
            期权列表
        """
        # 为了向后兼容，将 min_expired_days 作为目标天数处理
        return await self.get_instruments_by_target_days(underlying_symbol, min_expired_days, take_expirations)

    def _prepare_tiger_option_data(self, tiger_option: Any, underlying: str) -> Dict:
        """直接使用Tiger期权数据，添加必要的兼容性字段

        这个方法替代了 _convert_tiger_option_to_native，直接返回Tiger数据
        同时添加下游代码期望的字段名以保持兼容性
        """
        try:
            # 获取Tiger原始数据
            tiger_symbol = tiger_option.get('identifier', '')
            if not tiger_symbol:
                return None

            # 推断期权类型
            right_val = (tiger_option.get('right')
                         or tiger_option.get('put_call')
                         or tiger_option.get('cp_flag')
                         or tiger_option.get('option_right')
                         or '')
            opt = str(right_val).strip().lower()
            if opt in ('c', 'call'):
                opt = 'call'
            elif opt in ('p', 'put'):
                opt = 'put'
            else:
                # 从标识符推断
                ident = tiger_option.get('identifier', '')
                last_token = ident.split()[-1] if ident else ''
                if 'C' in last_token:
                    opt = 'call'
                elif 'P' in last_token:
                    opt = 'put'
                else:
                    opt = ''

            # 归一化到期时间为毫秒
            expiry_raw = int(tiger_option.get('expiry', 0) or 0)
            expiry_ms = expiry_raw * 1000 if expiry_raw and expiry_raw < 10**12 else expiry_raw

            # 创建包含Tiger原始数据和兼容性字段的字典
            result = dict(tiger_option)  # 保留所有Tiger原始字段

            # 添加下游代码期望的兼容性字段
            result.update({
                "instrument_name": tiger_symbol,
                "symbol": tiger_symbol,
                "underlying": underlying,
                "kind": "option",
                "option_type": opt,
                "strike": float(tiger_option.get('strike', 0) or 0),
                "expiration_timestamp": int(expiry_ms),
                "expiration_date": tiger_option.get('expiry_date', ''),
                "tick_size": 0.01,
                # "min_trade_amount": 1,
                # "contract_size": 100,
                # "currency": "USD",
                # 保持delta和underlying_price的原始值，如果存在的话，但需要验证是否为有效的JSON兼容值
                "delta": self._safe_float(tiger_option.get('calculated_delta') if tiger_option.get('delta') not in (None, "") else None),
                "underlying_price": self._safe_float(tiger_option.get('underlying_price') if tiger_option.get('underlying_price') not in (None, "") else None)
            })

            return self._sanitize_json_data(result)

        except Exception as error:
            print(f"❌ Failed to prepare Tiger option data: {error}")
            return None

    def _convert_tiger_option_to_native(self, tiger_option: Any, underlying: str) -> Dict:
        """转换Tiger期权数据到原生格式（不转换为Deribit）"""
        try:
            # 直接使用Tiger的标识符
            tiger_symbol = tiger_option.get('identifier', '')
            if not tiger_symbol:
                return None

            # 推断期权类型
            right_val = (tiger_option.get('right')
                         or tiger_option.get('put_call')
                         or tiger_option.get('cp_flag')
                         or tiger_option.get('option_right')
                         or '')
            opt = str(right_val).strip().lower()
            if opt in ('c', 'call'):
                opt = 'call'
            elif opt in ('p', 'put'):
                opt = 'put'
            else:
                ident = tiger_option.get('identifier', '')
                last_token = ident.split()[-1] if ident else ''
                if 'C' in last_token:
                    opt = 'call'
                elif 'P' in last_token:
                    opt = 'put'
                else:
                    opt = ''

            # 归一化到期时间为毫秒
            expiry_raw = int(tiger_option.get('expiry', 0) or 0)
            expiry_ms = expiry_raw * 1000 if expiry_raw and expiry_raw < 10**12 else expiry_raw

            return {
                "instrument_name": tiger_symbol,
                "symbol": tiger_symbol,
                "underlying": underlying,
                "kind": "option",
                "option_type": opt,
                "strike": float(tiger_option.get('strike', 0) or 0),
                "expiration_timestamp": int(expiry_ms),
                "expiration_date": tiger_option.get('expiry_date', ''),
                "tick_size": 0.01,
                "min_trade_amount": 1,
                "contract_size": 100,
                "currency": "USD",
                "delta": (float(tiger_option.get('delta', 0)) if tiger_option.get('delta') not in (None, "") else None),
                "underlying_price": (float(tiger_option.get('underlying_price', 0)) if tiger_option.get('underlying_price') not in (None, "") else None)
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

            # 推断期权类型
            right_val = (tiger_option.get('right')
                         or tiger_option.get('put_call')
                         or tiger_option.get('cp_flag')
                         or tiger_option.get('option_right')
                         or '')
            opt = str(right_val).strip().lower()
            if opt in ('c', 'call'):
                opt = 'call'
            elif opt in ('p', 'put'):
                opt = 'put'
            else:
                last_token = tiger_symbol.split()[-1] if tiger_symbol else ''
                if 'C' in last_token:
                    opt = 'call'
                elif 'P' in last_token:
                    opt = 'put'
                else:
                    opt = ''

            expiry_raw = int(tiger_option.get('expiry', 0) or 0)
            expiry_ms = expiry_raw * 1000 if expiry_raw and expiry_raw < 10**12 else expiry_raw

            return {
                "instrument_name": deribit_symbol,
                "kind": "option",
                "option_type": opt,
                "strike": float(tiger_option.get('strike', 0)),
                "expiration_timestamp": int(expiry_ms),
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

    async def get_order_state(self, account_name: str, order_id: str) -> Optional[Dict[str, Any]]:
        """获取订单状态 - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            # 获取订单详情
            tiger_order = self.trade_client.get_order(account=self.client_config.account, id=order_id)

            if not tiger_order:
                self.logger.warning("⚠️ 未找到订单", order_id=order_id)
                return None

            # 转换为Deribit格式
            order_state = {
                "order_id": str(tiger_order.id),
                "order_state": self._convert_tiger_order_status(tiger_order.status),
                "amount": float(tiger_order.quantity or 0),
                "filled_amount": float(tiger_order.filled or 0),
                "average_price": float(tiger_order.avg_fill_price or 0),
                "price": float(tiger_order.limit_price or tiger_order.avg_fill_price or 0),
                "creation_timestamp": tiger_order.order_time,
                "last_update_timestamp": tiger_order.update_time
            }

            self.logger.debug("✅ 获取订单状态成功",
                            order_id=order_id,
                            order_state=order_state["order_state"],
                            filled_amount=order_state["filled_amount"])

            return order_state

        except Exception as error:
            print(f"❌ Failed to get order state: {error}")
            self.logger.error("❌ 获取订单状态失败", order_id=order_id, error=str(error))
            return None

    async def edit_order(
        self,
        account_name: str,
        order_id: str,
        amount: float,
        new_price: float
    ) -> Optional[Dict[str, Any]]:
        """修改订单 - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            # 先获取原订单信息
            original_order_state = await self.get_order_state(account_name, order_id)
            if not original_order_state:
                self.logger.error("❌ 无法获取原订单信息", order_id=order_id)
                return None

            # 检查订单状态是否可以修改
            if original_order_state.get("order_state") != "open":
                self.logger.warning("⚠️ 订单状态不允许修改",
                                  order_id=order_id,
                                  current_state=original_order_state.get("order_state"))
                return None

            tiger_order = self.trade_client.get_order(account=self.client_config.account, id=order_id)

            # 使用Tiger API修改订单
            result = self.trade_client.modify_order(
                # account=self.client_config.account,
                order=tiger_order,
                quantity=int(amount),
                limit_price=float(new_price)
            )

            if result:
                self.logger.info("✅ 订单修改成功",
                               order_id=order_id,
                               new_amount=amount,
                               new_price=new_price)

                # 返回修改后的订单状态
                return await self.get_order_state(account_name, order_id)
            else:
                self.logger.error("❌ 订单修改失败", order_id=order_id)
                return None

        except Exception as error:
            self.logger.error("❌ 修改订单异常",
                            order_id=order_id,
                            amount=amount,
                            new_price=new_price,
                            error=str(error))
            return None

    async def get_open_orders_by_instrument(
        self,
        account_name: str,
        instrument_name: str
    ) -> List[Dict[str, Any]]:
        """获取特定合约的未成交订单 - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            # 获取所有未成交订单
            orders = self.trade_client.get_open_orders(
                account=self.client_config.account,
            )

            if not orders:
                return []

            # 过滤指定合约的订单
            filtered_orders = []
            for tiger_order in orders:
                # 检查合约标识符是否匹配
                if hasattr(tiger_order, 'contract') and tiger_order.contract:
                    order_symbol = getattr(tiger_order.contract, 'identifier', '') or getattr(tiger_order.contract, 'symbol', '')
                    if order_symbol == instrument_name:
                        # 转换为Deribit格式
                        order_dict = {
                            "order_id": str(tiger_order.id),
                            "instrument_name": instrument_name,
                            "direction": tiger_order.action.lower() if tiger_order.action else "unknown",
                            "amount": float(tiger_order.quantity or 0),
                            "price": float(tiger_order.limit_price or 0),
                            "order_type": "limit" if tiger_order.order_type == "LMT" else "market",
                            "order_state": self._convert_tiger_order_status(tiger_order.status),
                            "filled_amount": float(tiger_order.filled or 0),
                            "average_price": float(tiger_order.avg_fill_price or 0),
                            "creation_timestamp": int(datetime.now().timestamp() * 1000),
                            "last_update_timestamp": int(datetime.now().timestamp() * 1000)
                        }
                        filtered_orders.append(order_dict)

            self.logger.debug("✅ 获取合约未成交订单",
                            instrument_name=instrument_name,
                            order_count=len(filtered_orders))

            return filtered_orders

        except Exception as error:
            self.logger.error("❌ 获取合约未成交订单失败",
                            instrument_name=instrument_name,
                            error=str(error))
            return []

    async def get_open_orders(self, account_name: str) -> List[Dict[str, Any]]:
        """获取账户的所有未成交订单（Open Orders） - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            # 获取所有未成交订单
            orders = self.trade_client.get_open_orders(
                account=self.client_config.account,
            )

            if not orders:
                return []

            normalized_orders: List[Dict[str, Any]] = []
            for tiger_order in orders:
                instrument_name = None
                if hasattr(tiger_order, 'contract') and tiger_order.contract:
                    instrument_name = getattr(tiger_order.contract, 'identifier', '') or getattr(tiger_order.contract, 'symbol', '')

                order_dict = {
                    "order_id": str(getattr(tiger_order, 'id', '')),
                    "instrument_name": instrument_name or "",
                    "direction": (getattr(tiger_order, 'action', '') or '').lower() or "unknown",
                    "amount": float(getattr(tiger_order, 'quantity', 0) or 0),
                    "price": float(getattr(tiger_order, 'limit_price', 0) or 0),
                    "order_type": "limit" if getattr(tiger_order, 'order_type', None) == "LMT" else "market",
                    "order_state": self._convert_tiger_order_status(getattr(tiger_order, 'status', 'NEW')),
                    "filled_amount": float(getattr(tiger_order, 'filled', 0) or 0),
                    "average_price": float(getattr(tiger_order, 'avg_fill_price', 0) or 0),
                    "creation_timestamp": int(datetime.now().timestamp() * 1000),
                    "last_update_timestamp": int(datetime.now().timestamp() * 1000)
                }
                normalized_orders.append(order_dict)

            self.logger.debug("✅ 获取账户未成交订单", order_count=len(normalized_orders))
            return normalized_orders

        except Exception as error:
            self.logger.error("❌ 获取账户未成交订单失败", error=str(error))
            return []

    async def get_positions(self, account_name: str, currency: str = "USD") -> List[Dict]:
        """获取持仓 - 使用Tiger API实现"""
        try:
            await self._ensure_clients(account_name)

            raw_positions = self.trade_client.get_positions(account=self.client_config.account, sec_type=SecurityType.OPT)
            if raw_positions is None:
                return []

            deribit_positions = []
            for position in raw_positions:
                deribit_position = self._convert_tiger_position_to_deribit(position)
                if deribit_position:
                    deribit_positions.append(deribit_position)

            self.logger.debug("✅ 获取期权持仓", total=len(deribit_positions), options=len(deribit_positions))
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

            return SimpleNamespace(order=order_dict, trades=[])

        except Exception as error:
            print(f"❌ Failed to convert order response: {error}")
            return None
    def _convert_tiger_position_to_deribit(self, tiger_position: Position) -> Optional[Dict]:
        """将 Tiger 的 Position 对象转换为内部使用的 DeribitPosition 字典结构。

        参考 Tiger 文档: get_positions 返回的 Position 属性包括:
        - contract, quantity, average_cost, market_price, market_value,
          realized_pnl, unrealized_pnl, ...
        Greeks 通常不在 Position 上，若可获取则尽量读取；否则置为 None。
        """
        try:
            # 合约与标识符（例如："QQQ   250925C00603000"）
            contract = self._get(tiger_position, 'contract', None)
            tiger_symbol = (
                self._get(contract, 'identifier', '')
                or self._get(contract, 'symbol', '')
                or self._get(tiger_position, 'symbol', '')
            )
            if not tiger_symbol:
                return None

            # deribit_symbol = self.symbol_converter.tiger_to_deribit(tiger_symbol)

            # 基础数值
            qty = float(self._get(tiger_position, 'quantity', 0) or 0)
            avg_cost = float(self._get(tiger_position, 'average_cost', 0) or 0)
            mark_price = float(self._get(tiger_position, 'market_price', 0) or 0)
            market_value = float(self._get(tiger_position, 'market_value', 0) or 0)
            realized = float(self._get(tiger_position, 'realized_pnl', 0) or 0)
            unrealized = float(self._get(tiger_position, 'unrealized_pnl', 0) or 0)
            total_pl = realized + unrealized
            pnl_percent = float(self._get(tiger_position, 'unrealized_pnl_percent_by_cost_of_carry', 0) or 0)

            # Greeks（如果可以取得）
            greeks_obj = (
                self._get(tiger_position, 'greeks', None)
                or self._get(tiger_position, 'option_greeks', None)
                or self._get(contract, 'greeks', None)
            )
            delta = float(self._get(greeks_obj, 'delta', None)) if greeks_obj and self._get(greeks_obj, 'delta', None) is not None else None
            gamma = float(self._get(greeks_obj, 'gamma', None)) if greeks_obj and self._get(greeks_obj, 'gamma', None) is not None else None
            theta = float(self._get(greeks_obj, 'theta', None)) if greeks_obj and self._get(greeks_obj, 'theta', None) is not None else None
            vega = float(self._get(greeks_obj, 'vega', None)) if greeks_obj and self._get(greeks_obj, 'vega', None) is not None else None

            # 组装为 DeribitPosition 所需字段（必填字段全部给出）
            return {
                "instrument_name": tiger_symbol,
                "size": qty,
                "direction": "buy" if qty > 0 else "sell",
                "average_price": avg_cost,
                "mark_price": mark_price,
                "unrealized_pnl": unrealized,
                "realized_pnl": realized,
                "total_profit_loss": total_pl,
                # Tiger Position 未提供保证金细项，这里置 0
                "maintenance_margin": 0.0,
                "initial_margin": 0.0,
                # 可选/推断字段
                "index_price": None,
                "estimated_liquidation_price": None,
                "settlement_price": None,
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega,
                # 兼容字段（与 unrealized_pnl 含义一致）
                "floating_profit_loss": unrealized,
                "floating_profit_loss_usd": None,
                # 当前系统仅处理期权
                "kind": "option",
                # 其余可选字段
                "leverage": None,
                "open_orders_margin": None,
                "interest_value": None,
                "size_currency": market_value if market_value else None,
                "average_price_usd": None,
                "pnl_percent": pnl_percent,
            }

        except Exception as error:
            print(f"❌ Failed to convert position: {error}")
            return None

    def _convert_tiger_order_status(self, tiger_status: Any) -> str:
        """转换Tiger订单状态为Deribit格式，兼容Tiger枚举与字符串值。"""
        if tiger_status is None:
            self.logger.warning("Received empty Tiger order status")
            return "unknown"

        raw_status = tiger_status.name if isinstance(tiger_status, Enum) else str(tiger_status)
        normalized = raw_status.replace("-", "_").replace(" ", "_")
        normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", normalized)
        normalized = normalized.upper()

        status_mapping = {
            "PENDING_NEW": "open",
            "NEW": "open",
            "INITIAL": "open",
            "HELD": "open",
            "SUBMITTED": "open",
            "PARTIALLY_FILLED": "open",
            "PENDING_CANCEL": "open",
            "FILLED": "filled",
            "CANCELLED": "cancelled",
            "CANCELED": "cancelled",
            "REJECTED": "rejected",
            "INACTIVE": "rejected",
            "EXPIRED": "cancelled",
            "INVALID": "cancelled",
        }

        mapped_status = status_mapping.get(normalized)
        if mapped_status is not None:
            return mapped_status

        alt_normalized = normalized.replace("_", "")
        mapped_status = status_mapping.get(alt_normalized)
        if mapped_status is not None:
            return mapped_status

        self.logger.warning("Unknown Tiger order status", status=raw_status, normalized_status=normalized)
        return "unknown"
    
    async def get_option_details(self, option_name: str) :
        return await self.get_ticker(option_name)

    async def get_us_symbols_cache(self, account_name: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """获取美股品种缓存，每24小时更新一次
        
        Args:
            account_name: 账户名称，可选
            force_refresh: 是否强制刷新缓存
            
        Returns:
            美股品种列表
        """
        try:
            used_account = await self.ensure_quote_client(account_name)
            cache_key = f"{used_account}:US_SYMBOLS"
            current_time = datetime.now().timestamp()
            
            # 检查缓存是否存在且未过期
            if not force_refresh and cache_key in self._us_symbols_cache:
                cache_entry = self._us_symbols_cache[cache_key]
                cache_time = cache_entry.get('timestamp', 0)
                cached_symbols = cache_entry.get('symbols', [])
                
                # 检查缓存是否在有效期内（24小时）
                if current_time - cache_time < self._us_symbols_cache_ttl_sec:
                    # self.logger.info("✅ 命中美股品种缓存", 
                    #                account=used_account,
                    #                symbol_count=len(cached_symbols),
                    #                cache_age_hours=(current_time - cache_time) / 3600)
                    return cached_symbols
            
            # 缓存过期或强制刷新，重新获取数据
            # self.logger.info("🔄 获取美股品种数据", account=used_account, force_refresh=force_refresh)
            
            # 使用 QuoteClient.get_symbols 获取美股品种
            symbols_data = self.quote_client.get_symbols(market=Market.ALL, include_otc=False)
            
            if symbols_data is None or len(symbols_data) == 0:
                self.logger.warning("⚠️ 未获取到美股品种数据")
                return []
            
            # 转换为标准格式
            symbols_list = []
            
            # 检查返回的数据类型
            if hasattr(symbols_data, 'iterrows'):
                # DataFrame 类型
                for _, row in symbols_data.iterrows():
                    symbol_info = self._extract_symbol_info(row)
                    if symbol_info:
                        symbols_list.append(symbol_info)
            elif isinstance(symbols_data, list):
                # 列表类型
                for item in symbols_data:
                    symbol_info = self._extract_symbol_info(item)
                    if symbol_info:
                        symbols_list.append(symbol_info)
            else:
                self.logger.warning("⚠️ 未知的数据格式", data_type=type(symbols_data))
                return []
            
            # 按符号排序
            symbols_list.sort(key=lambda x: x['symbol'])
            
            # 更新缓存
            self._us_symbols_cache[cache_key] = {
                'timestamp': current_time,
                'symbols': symbols_list,
                'account': used_account
            }
            
            # self.logger.info("✅ 美股品种缓存更新成功", 
            #                account=used_account,
            #                symbol_count=len(symbols_list),
            #                cache_ttl_hours=self._us_symbols_cache_ttl_sec / 3600)
            
            return symbols_list
            
        except Exception as error:
            self.logger.error("❌ 获取美股品种缓存失败", 
                            account=account_name,
                            error=str(error))
            # 返回空列表而不是抛出异常，保持系统稳定性
            return []

    def invalidate_us_symbols_cache(self, account_name: Optional[str] = None) -> None:
        """清理美股品种缓存
        
        Args:
            account_name: 账户名称，如果为None则清理所有账户的缓存
        """
        if account_name:
            cache_key = f"{account_name}:US_SYMBOLS"
            self._us_symbols_cache.pop(cache_key, None)
            self.logger.info("🗑️ 已清理账户美股品种缓存", account=account_name)
        else:
            self._us_symbols_cache.clear()
            self.logger.info("🗑️ 已清理所有美股品种缓存")

    def get_us_symbols_cache_info(self, account_name: Optional[str] = None) -> Dict[str, Any]:
        """获取美股品种缓存信息
        
        Args:
            account_name: 账户名称，如果为None则返回所有账户的缓存信息
            
        Returns:
            缓存信息字典
        """
        current_time = datetime.now().timestamp()
        
        if account_name:
            cache_key = f"{account_name}:US_SYMBOLS"
            if cache_key in self._us_symbols_cache:
                cache_entry = self._us_symbols_cache[cache_key]
                cache_time = cache_entry.get('timestamp', 0)
                symbols = cache_entry.get('symbols', [])
                
                return {
                    'account': account_name,
                    'symbol_count': len(symbols),
                    'cache_timestamp': cache_time,
                    'cache_age_seconds': current_time - cache_time,
                    'cache_age_hours': (current_time - cache_time) / 3600,
                    'is_valid': (current_time - cache_time) < self._us_symbols_cache_ttl_sec,
                    'ttl_hours': self._us_symbols_cache_ttl_sec / 3600
                }
            else:
                return {
                    'account': account_name,
                    'symbol_count': 0,
                    'cache_timestamp': None,
                    'cache_age_seconds': None,
                    'cache_age_hours': None,
                    'is_valid': False,
                    'ttl_hours': self._us_symbols_cache_ttl_sec / 3600
                }
        else:
            # 返回所有账户的缓存信息
            cache_info = {}
            for cache_key, cache_entry in self._us_symbols_cache.items():
                if ':US_SYMBOLS' in cache_key:
                    account = cache_key.replace(':US_SYMBOLS', '')
                    cache_time = cache_entry.get('timestamp', 0)
                    symbols = cache_entry.get('symbols', [])
                    
                    cache_info[account] = {
                        'symbol_count': len(symbols),
                        'cache_timestamp': cache_time,
                        'cache_age_seconds': current_time - cache_time,
                        'cache_age_hours': (current_time - cache_time) / 3600,
                        'is_valid': (current_time - cache_time) < self._us_symbols_cache_ttl_sec,
                        'ttl_hours': self._us_symbols_cache_ttl_sec / 3600
                    }
            
            return cache_info

    def _extract_symbol_info(self, data: Any) -> Optional[Dict[str, Any]]:
        """从数据项中提取品种信息
        
        Args:
            data: 数据项，可能是字典、对象或其他格式
            
        Returns:
            品种信息字典，如果提取失败则返回None
        """
        try:
            # 提取符号
            symbol = None
            if isinstance(data, dict):
                symbol = (data.get('symbol') or data.get('code') or '').strip()
            elif hasattr(data, 'symbol'):
                symbol = getattr(data, 'symbol', '').strip()
            elif hasattr(data, 'code'):
                symbol = getattr(data, 'code', '').strip()
            
            if not symbol:
                return None
            
            # 提取其他字段
            name = None
            market = 'US'
            currency = 'USD'
            sector = ''
            industry = ''
            market_cap = None
            price = None
            volume = None
            
            if isinstance(data, dict):
                name = data.get('name') or data.get('description') or symbol.upper()
                market = str(data.get('market', 'US')).upper()
                currency = data.get('currency') or 'USD'
                sector = data.get('sector') or ''
                industry = data.get('industry') or ''
                market_cap = data.get('market_cap')
                price = data.get('latest_price') or data.get('close')
                volume = data.get('volume')
            else:
                # 尝试从对象属性获取
                name = getattr(data, 'name', None) or getattr(data, 'description', None) or symbol.upper()
                market = str(getattr(data, 'market', 'US')).upper()
                currency = getattr(data, 'currency', None) or 'USD'
                sector = getattr(data, 'sector', None) or ''
                industry = getattr(data, 'industry', None) or ''
                market_cap = getattr(data, 'market_cap', None)
                price = getattr(data, 'latest_price', None) or getattr(data, 'close', None)
                volume = getattr(data, 'volume', None)
            
            symbol_info = {
                "symbol": symbol.upper(),
                "name": name,
                "market": market,
                "currency": currency,
                "sector": sector,
                "industry": industry,
                "market_cap": self._safe_float(market_cap),
                "price": self._safe_float(price),
                "volume": self._safe_float(volume),
                "is_otc": False  # 明确标记为非OTC股票
            }
            
            return symbol_info
            
        except Exception as error:
            self.logger.warning("提取品种信息失败", data=str(data), error=str(error))
            return None

    def is_us_stock_symbol(self, symbol: str) -> bool:
        """判断symbol是否是美股品种
        
        Args:
            symbol: 股票代码，如 "AAPL", "GOOGL", "MSFT" 等
            
        Returns:
            bool: 如果是美股品种返回True，否则返回False
            
        Examples:
            >>> client = TigerClient()
            >>> client.is_us_stock_symbol("AAPL")
            True
            >>> client.is_us_stock_symbol("00700.HK")
            False
            >>> client.is_us_stock_symbol("BTC")
            False
        """
        try:
            if not symbol or not isinstance(symbol, str):
                return False
            
            symbol = symbol.strip().upper()
            
            # 1. 检查是否包含美股后缀标识
            # 有些系统可能使用 .US, .NYSE, .NASDAQ 等后缀
            if any(symbol.endswith(suffix) for suffix in ['.US', '.NYSE', '.NASDAQ', '.AMEX']):
                return True
            
            # 2. 检查是否包含港股后缀
            if any(symbol.endswith(suffix) for suffix in ['.HK', '.HS', '.HKG']):
                return False
            
            # 3. 检查是否包含A股后缀
            if any(symbol.endswith(suffix) for suffix in ['.SS', '.SZ', '.SH']):
                return False
            
            # 4. 检查是否包含其他市场后缀
            if any(symbol.endswith(suffix) for suffix in ['.L', '.T', '.DE', '.PA', '.TO']):
                return False
            
            # 5. 检查加密货币标识
            if symbol.startswith(('BTC', 'ETH', 'USDT', 'BNB', 'XRP', 'ADA', 'SOL', 'DOGE')):
                return False
            
            # 6. 检查是否为数字开头的港股代码（如 00700, 00941）
            if len(symbol) >= 4 and symbol[:4].isdigit():
                return False
            
            # 7. 检查美股股票代码格式
            # 美股代码通常为2-5个字母，不包含数字
            import re
            if re.match(r'^[A-Z]{2,5}$', symbol):
                # 进一步排除一些明显的非美股代码
                excluded_patterns = [
                    r'^[A-Z]\d+',  # 字母+数字组合
                    r'^\d+[A-Z]+',  # 数字+字母组合
                    r'USD[A-Z]+',   # USD开头的货币对
                    r'[A-Z]+USD$',  # USD结尾的货币对
                ]
                
                for pattern in excluded_patterns:
                    if re.match(pattern, symbol):
                        return False
                
                # 排除已知的非美股代码
                excluded_codes = {
                    # 中概股ADR
                    'TCEHY', 'BIDU', 'NIO', 'XPEV', 'LI', 'BILI', 'JD', 'PDD', 'BZ', 'WB', 'IQ', 'LU', 'YY', 'ZTO',
                    # 日本股票ADR
                    'TM', 'SONY', 'NTDOY', 'HMC', 'MZDAY', 'SNE', 'FUJHY', 'KYOCY', 'NMR', 'MFG',
                    # 欧洲股票ADR
                    'SAP', 'ASML', 'NESR', 'NOK', 'SI', 'ERIC', 'DB', 'VOW3', 'BAYRY', 'BMW', 'DAI',
                    # 其他国际股票ADR
                    'BHP', 'RIO', 'BP', 'SHEL', 'TOT', 'ENI', 'REP', 'SAN', 'CS', 'IBN', 'INFY',
                    # 货币代码
                    'USD', 'EUR', 'JPY', 'GBP', 'CNY', 'AUD', 'CAD', 'CHF', 'SEK', 'NOK', 'DKK',
                    'SGD', 'HKD', 'KRW', 'INR', 'MXN', 'BRL', 'ZAR', 'RUB', 'TRY', 'PLN', 'CZK',
                    'HUF', 'RON', 'BGN', 'HRK', 'ISK', 'EEK', 'LVL', 'LTL', 'MKD', 'ALL',
                    # 商品
                    'GOLD', 'SILVER', 'OIL', 'COPPER', 'GAS', 'WHEAT', 'CORN', 'SOYBEAN', 'SUGAR',
                    'COFFEE', 'COTTON', 'COCOA', 'PLATINUM', 'PALLADIUM', 'RARE', 'LUMBER',
                    # 指数
                    'SPX', 'DJI', 'IXIC', 'RUT', 'VIX', 'FTSE', 'DAX', 'CAC', 'NIKKEI', 'SHANGHAI',
                    'HANGSENG', 'SENSEX', 'BOVESPA', 'TSX', 'ASX', 'NZX', 'STI', 'KOSPI', 'TAIWAN'
                }
                
                if symbol in excluded_codes:
                    return False
                
                return True
            
            # 8. 特殊情况：检查一些知名的美股代码
            known_us_stocks = {
                'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 
                'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'XOM', 'CVX', 'LLY', 'PFE',
                'ABBV', 'TMO', 'ABT', 'CRM', 'ACN', 'MRK', 'COST', 'NKE', 'KO', 'PEP',
                'T', 'DIS', 'INTC', 'VZ', 'ADBE', 'NFLX', 'PYPL', 'CSCO', 'CMCSA', 'AVGO',
                'TXN', 'QCOM', 'AMD', 'INTU', 'HON', 'IBM', 'GS', 'CAT', 'RTX', 'GE',
                'BA', 'MMM', 'DOW', 'WMT', 'MCD', 'HD', 'LOW', 'TGT', 'COST', 'WBA'
            }
            
            if symbol in known_us_stocks:
                return True
            
            return False
            
        except Exception as error:
            self.logger.warning("判断美股品种时发生错误", symbol=symbol, error=str(error))
            return False

    async def is_us_stock_symbol_with_cache(self, symbol: str) -> bool:
        """使用缓存判断symbol是否是美股品种
        
        这个方法会先检查美股品种缓存，如果缓存中有该品种则返回True，
        如果缓存中没有，则使用启发式方法判断，并可选择性地更新缓存。
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 如果是美股品种返回True，否则返回False
        """
        try:
            if not symbol or not isinstance(symbol, str):
                return False
            
            symbol = symbol.strip().upper()
            
            # 1. 首先检查美股品种缓存
            cache_info = self.get_us_symbols_cache_info()
            
            # 如果有缓存数据，检查symbol是否在缓存中
            if cache_info and isinstance(cache_info, dict):
                for account, info in cache_info.items():
                    if info.get('is_valid', False):
                        # 这里可以进一步优化，实际查询缓存中的品种列表
                        # 但为了简单起见，先使用启发式方法
                        break
            
            # 2. 使用启发式方法判断
            is_us_stock = self.is_us_stock_symbol(symbol)
            
            # 3. 如果判断为美股品种，可以选择性地预热缓存
            if is_us_stock:
                # 异步预热缓存（不等待结果）
                try:
                    asyncio.create_task(self.get_us_symbols_cache())
                except Exception:
                    # 忽略缓存预热失败
                    pass
            
            return is_us_stock
            
        except Exception as error:
            self.logger.warning("使用缓存判断美股品种时发生错误", symbol=symbol, error=str(error))
            # 降级到基础判断方法
            return self.is_us_stock_symbol(symbol)

    async def is_symbol_trading(self, symbol: str) -> bool:
        """判断symbol是否正在实盘交易状态
        
        逻辑如下：
        1. 用is_us_stock_symbol_with_cache判断是否是美股，否则就当作港股
        2. 调用QuoteClient.get_market_status判断市场是否是交易中(trading_status)
        
        Args:
            symbol: 股票代码，如 "AAPL", "00700.HK" 等
            
        Returns:
            bool: 如果正在交易中返回True，否则返回False
            
        Examples:
            >>> client = TigerClient()
            >>> await client.is_symbol_trading("AAPL")
            True  # 如果美股市场正在交易中
            >>> await client.is_symbol_trading("00700.HK")
            False  # 如果港股市场未交易或休市
        """
        try:
            if not symbol or not isinstance(symbol, str):
                return False
            
            symbol = symbol.strip().upper()
            
            # 1. 用is_us_stock_symbol_with_cache判断是否是美股
            is_us_stock = await self.is_us_stock_symbol_with_cache(symbol)
            
            # 2. 获取市场状态
            await self.ensure_quote_client()
            
            try:
                # 获取市场状态 - 根据反馈，应该传入Market枚举而不是symbol
                market_status = None
                
                # 判断市场类型并传入对应的Market枚举
                if is_us_stock:
                    # 美股市场
                    try:
                        market_status = self.quote_client.get_market_status(market=Market.US)
                        self.logger.debug(f"获取美股市场状态成功")
                    except Exception as e1:
                        self.logger.debug(f"get_market_status(Market.US) 调用失败: {e1}")
                        # 尝试不带参数调用
                        try:
                            market_status = self.quote_client.get_market_status()
                            self.logger.debug(f"get_market_status() 无参数调用成功")
                        except Exception as e2:
                            self.logger.debug(f"get_market_status() 无参数调用也失败: {e2}")
                else:
                    # 港股市场
                    try:
                        market_status = self.quote_client.get_market_status(market=Market.HK)
                        self.logger.debug(f"获取港股市场状态成功")
                    except Exception as e1:
                        self.logger.debug(f"get_market_status(Market.HK) 调用失败: {e1}")
                        # 尝试不带参数调用
                        try:
                            market_status = self.quote_client.get_market_status()
                            self.logger.debug(f"get_market_status() 无参数调用成功")
                        except Exception as e2:
                            self.logger.debug(f"get_market_status() 无参数调用也失败: {e2}")
                
                if market_status is None or len(market_status) == 0:
                    self.logger.warning(f"未获取到市场状态信息: {symbol}")
                    return False
                
                # 处理不同类型的返回数据
                if hasattr(market_status, 'iloc'):
                    # DataFrame类型
                    if len(market_status) > 0:
                        status_data = market_status.iloc[0]
                    else:
                        status_data = None
                elif isinstance(market_status, list):
                    # 列表类型
                    if len(market_status) > 0:
                        status_data = market_status[0]
                    else:
                        status_data = None
                elif isinstance(market_status, dict):
                    # 字典类型
                    status_data = market_status
                else:
                    # 其他类型，尝试直接使用
                    status_data = market_status
                
                if status_data is None:
                    self.logger.warning(f"市场状态数据为空: {symbol}")
                    return False
                
                # 检查交易状态字段
                trading_status = None
                
                # 尝试不同的字段名
                possible_fields = ['trading_status', 'status', 'market_status', 'is_trading']
                for field in possible_fields:
                    if hasattr(status_data, field):
                        trading_status = getattr(status_data, field)
                        break
                    elif isinstance(status_data, dict) and field in status_data:
                        trading_status = status_data[field]
                        break
                
                if trading_status is None:
                    # 尝试从字典中获取
                    if isinstance(status_data, dict):
                        for key, value in status_data.items():
                            if 'trading' in key.lower() or 'status' in key.lower():
                                trading_status = value
                                break
                
                if trading_status is None:
                    self.logger.warning(f"未找到交易状态字段: {symbol}")
                    return False
                
                # 判断是否在交易中
                if isinstance(trading_status, str):
                    # 检查是否为交易状态
                    trading_indicators = [
                        'trading', 'open', 'active', 'normal', 'trading_halt', 
                        'trading_resume', 'pre_open', 'post_market', 'continuous'
                    ]
                    status_lower = trading_status.lower().strip()
                    
                    # 检查是否包含交易相关关键词
                    for indicator in trading_indicators:
                        if indicator in status_lower:
                            # 如果是停牌状态，需要进一步检查
                            if 'halt' in status_lower:
                                # 检查是否为交易恢复状态
                                if 'resume' in status_lower:
                                    return True
                                continue
                            return True
                    
                    # 特殊处理：如果明确表示非交易状态
                    non_trading_indicators = [
                        'closed', 'market_closed', 'halted', 'suspended', 
                        'inactive', 'offline', 'unavailable', 'pre_market_closed',
                        'post_market_closed', 'holiday', 'weekend'
                    ]
                    for indicator in non_trading_indicators:
                        if indicator in status_lower:
                            return False
                    
                    # 如果状态包含"market"且不是"market_closed"，认为在交易
                    if 'market' in status_lower and 'closed' not in status_lower:
                        return True
                
                elif isinstance(trading_status, bool):
                    return trading_status
                
                elif isinstance(trading_status, (int, float)):
                    # 如果是数值，通常1表示交易中，0表示休市
                    return bool(trading_status)
                
                # 如果是其他类型，尝试转换为字符串再判断
                try:
                    status_str = str(trading_status).lower()
                    return 'trading' in status_str or 'open' in status_str
                except Exception:
                    pass
                
                return False
                
            except Exception as e:
                self.logger.error(f"获取市场状态时发生错误: {symbol}, {e}")
                return False
                
        except Exception as error:
            self.logger.error("判断symbol交易状态时发生错误", symbol=symbol, error=str(error))
            return False

    async def get_symbol_trading_status(self, symbol: str) -> Dict[str, Any]:
        """获取symbol的详细交易状态信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            包含交易状态信息的字典
        """
        try:
            if not symbol or not isinstance(symbol, str):
                return {"symbol": symbol, "is_trading": False, "error": "Invalid symbol"}
            
            symbol = symbol.strip().upper()
            
            # 判断是否为美股
            is_us_stock = await self.is_us_stock_symbol_with_cache(symbol)
            
            # 获取市场状态
            await self.ensure_quote_client()
            
            try:
                # 获取市场状态 - 使用与基础方法相同的Market枚举策略
                market_status = None
                
                primary_market = Market.US if is_us_stock else Market.HK
                cache_key = f"MARKET:{'US' if is_us_stock else 'HK'}"
                fallback_cache_key = "MARKET:DEFAULT"

                market_status = self._get_cached_market_status(cache_key)

                if market_status is None:
                    try:
                        market_status = self.quote_client.get_market_status(market=primary_market)
                        if market_status is not None:
                            self._set_cached_market_status(cache_key, market_status)
                    except Exception as e1:
                        if is_us_stock:
                            self.logger.debug(f"get_market_status(Market.US) 调用失败: {e1}")
                        else:
                            self.logger.debug(f"get_market_status(Market.HK) 调用失败: {e1}")
                        market_status = None

                if market_status is None:
                    market_status = self._get_cached_market_status(fallback_cache_key)

                if market_status is None:
                    try:
                        market_status = self.quote_client.get_market_status()
                        if market_status is not None:
                            self._set_cached_market_status(fallback_cache_key, market_status)
                            self.logger.debug("get_market_status() 无参数调用成功 (详细状态)")
                    except Exception as e2:
                        self.logger.debug(f"get_market_status() 无参数调用也失败: {e2}")
                        market_status = None
                
                if market_status is None or len(market_status) == 0:
                    return {
                        "symbol": symbol,
                        "is_trading": False,
                        "is_us_stock": is_us_stock,
                        "market": "US" if is_us_stock else "HK",
                        "error": "No market status data available"
                    }
                
                # 处理不同类型的返回数据
                if hasattr(market_status, 'iloc'):
                    # DataFrame类型
                    if len(market_status) > 0:
                        status_data = market_status.iloc[0]
                    else:
                        status_data = None
                elif isinstance(market_status, list):
                    # 列表类型
                    if len(market_status) > 0:
                        status_data = market_status[0]
                    else:
                        status_data = None
                elif isinstance(market_status, dict):
                    # 字典类型
                    status_data = market_status
                else:
                    # 其他类型，尝试直接使用
                    status_data = market_status
                
                if status_data is None:
                    return {
                        "symbol": symbol,
                        "is_trading": False,
                        "is_us_stock": is_us_stock,
                        "market": "US" if is_us_stock else "HK",
                        "error": "Empty market status data"
                    }
                
                # 提取所有可能的状态信息
                status_info = {}
                if isinstance(status_data, dict):
                    status_info = {k: v for k, v in status_data.items()}
                else:
                    # 如果是对象，转换为字典
                    status_info = self._to_dict(status_data)
                
                # 判断交易状态
                trading_status = status_info.get('trading_status') or status_info.get('status') or status_info.get('market_status')
                is_trading = False
                
                if trading_status is not None:
                    trading_status_str = str(trading_status).lower().strip()
                    trading_indicators = ['trading', 'open', 'active', 'normal']
                    is_trading = trading_status_str in trading_indicators
                
                return {
                    "symbol": symbol,
                    "is_trading": is_trading,
                    "is_us_stock": is_us_stock,
                    "market": "US" if is_us_stock else "HK",
                    "trading_status": trading_status,
                    "status_info": status_info,
                    "error": None
                }
                
            except Exception as e:
                self.logger.error(f"获取symbol交易状态信息时发生错误: {symbol}, {e}")
                return {
                    "symbol": symbol,
                    "is_trading": False,
                    "is_us_stock": is_us_stock,
                    "market": "US" if is_us_stock else "HK",
                    "error": str(e)
                }
                
        except Exception as error:
            self.logger.error("获取symbol交易状态信息时发生错误", symbol=symbol, error=str(error))
            return {
                "symbol": symbol,
                "is_trading": False,
                "is_us_stock": False,
                "error": str(error)
            }

# todo: 写一个函数判读symbol是否正在实盘交易状态, 逻辑如下:
# 1. 用is_us_stock_symbol_with_cache判读是否是美股, 否则就是就当港股
# 2. 调用QuoteClient.get_market_status判读市场是否是交易中(trading_status)
