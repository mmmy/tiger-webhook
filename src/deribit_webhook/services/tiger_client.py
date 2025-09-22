"""
Tiger Brokers API客户端

替换原有的Deribit客户端，使用Tiger Brokers官方SDK
"""

import os
import math
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
from tigeropen.push.push_client import PushClient
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.common.consts import Language, Market
from tigeropen.common.util.contract_utils import option_contract, stock_contract
from tigeropen.common.util.order_utils import market_order, limit_order
from tigeropen.common.exceptions import ApiException

from types import SimpleNamespace

from ..config.config_loader import ConfigLoader
from ..config.settings import settings
from ..services.auth_service import AuthenticationService
from ..models.deribit_types import DeribitOrderResponse
from ..utils.symbol_converter import OptionSymbolConverter
from ..utils.logging_config import get_global_logger



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
            return
        self._instruments_cache.clear()
        self._expirations_cache.clear()
        self._underlyings_cache.clear()

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
                option_chain = self.quote_client.get_option_chain(symbol, int(expiry_ts_ms), return_greek_value=True)

                if option_chain is None or len(option_chain) == 0:
                    self.logger.warning("⚠️ 指定到期日没有期权数据")
                else:
                    for _, option in option_chain.iterrows():
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
                    option_chain = self.quote_client.get_option_chain(symbol, int(expiry_ts or 0))

                    if option_chain is None or len(option_chain) == 0:
                        self.logger.warning("⚠️ 到期日没有期权数据", expiry_date=expiry_date)
                        continue

                    # 直接使用Tiger格式，保留所有原始数据
                    for _, option in option_chain.iterrows():
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

            # 直接返回Tiger格式数据
            ticker_data = {
                "instrument_name": instrument_name,
                "symbol": tiger_symbol,
                "best_bid_price": float(option_data.get('bid_price', 0) or 0),
                "best_ask_price": float(option_data.get('ask_price', 0) or 0),
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

            options = await self.get_instruments_min_days(underlying_asset, min_expired_days)
            if not options:
                print(f"⚠️ No options returned for {underlying_asset}")
                return None
            print(f"   候选期权数量: {len(options)}，示例类型: {[ (o.get('option_type'), o.get('expiration_timestamp')) for o in options[:3] ]}")

            opt_type = "call" if delta > 0 else "put"
            target_delta = abs(delta)  # Use absolute value for comparison

            # 1. 根据opt_type过滤options
            filtered_options = [
                option for option in options
                if option.get('option_type', '').lower() == opt_type
            ]

            if not filtered_options:
                print(f"⚠️ No {opt_type} options found")
                return None

            print(f"   过滤后的{opt_type}期权数量: {len(filtered_options)}")

            # 2. 然后根据|delta - option.delta|的绝对值排序, 选出3个小的
            # First, separate options with and without delta values
            options_with_delta = []
            options_without_delta = []

            for option in filtered_options:
                option_delta = option.get('delta')
                if option_delta is not None and option_delta != "":
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

            print(f"   有delta值的期权: {len(options_with_delta)}, 无delta值的期权: {len(options_without_delta)}")

            if not top_candidates:
                print("⚠️ No suitable candidates found")
                return None

            print(f"   候选期权数量: {len(top_candidates)}")
            for i, (option, delta_dist, delta_val) in enumerate(top_candidates):
                print(f"     {i+1}. {option.get('instrument_name')} - delta: {delta_val}, distance: {delta_dist:.4f}")

            # 3. 从3个中选一个: 盘口价差最小的
            best_option = None
            best_spread_ratio = float('inf')

            for option, delta_distance, delta_val in top_candidates:
                instrument_name = option.get('instrument_name')
                if not instrument_name:
                    continue

                # Get ticker data for spread calculation

                bid = option.get('bid_price', 0)
                ask = option.get('ask_price', 0)

                if bid <= 0 or ask <= 0:
                    print(f"   ⚠️ {instrument_name} 报价无效: bid={bid}, ask={ask}")
                    continue

                # Calculate spread ratio
                spread_ratio = (ask - bid) / ((bid + ask) / 2) if (bid + ask) > 0 else float('inf')

                print(f"   {instrument_name}: bid={bid}, ask={ask}, spread_ratio={spread_ratio:.4f}")

                if spread_ratio < best_spread_ratio:
                    best_spread_ratio = spread_ratio
                    best_option = option

            if not best_option:
                print("⚠️ 未找到合适的期权")
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

            print(f"✅ 选择期权: {result.instrument.instrument_name}, spread_ratio: {result.spread_ratio:.4f}")
            return result

        except Exception as e:
            print(f"❌ get_instrument_by_delta failed: {e}")
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
                option_chain = self.quote_client.get_option_chain(symbol, ts, return_greek_value=True)
                if option_chain is None or len(option_chain) == 0:
                    print(f"   ⚠️ 到期日 {date_str} 没有期权数据")
                    continue
                for _, option in option_chain.iterrows():
                    # 直接使用Tiger期权链数据，添加必要的兼容性字段
                    tiger_option = self._prepare_tiger_option_data(option, symbol)
                    if tiger_option:
                        all_options.append(tiger_option)

            print(f"   ✅ 总共获取到 {len(all_options)} 个期权工具 (目标天数模式)")
            return all_options
        except Exception as error:
            print(f"❌ Failed to get instruments (target_days): {error}")
            return []

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
                # 保持delta和underlying_price的原始值，如果存在的话
                "delta": (float(tiger_option.get('delta', 0)) if tiger_option.get('delta') not in (None, "") else None),
                "underlying_price": (float(tiger_option.get('underlying_price', 0)) if tiger_option.get('underlying_price') not in (None, "") else None)
            })

            return result

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

            # 使用Tiger API修改订单
            result = self.trade_client.modify_order(
                account=self.client_config.account,
                order_id=order_id,
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
            orders = self.trade_client.get_orders(
                account=self.client_config.account,
                status='NEW'  # 只获取新订单状态
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

            return SimpleNamespace(order=order_dict, trades=[])

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
