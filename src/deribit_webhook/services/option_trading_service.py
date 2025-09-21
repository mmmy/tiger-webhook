"""
Option trading service

Handles TradingView webhook signals and executes option trades.
"""

from typing import Optional, Dict, Any

import time

from ..config.config_loader import ConfigLoader
from ..config.settings import settings
from ..database import DeltaManager, get_delta_manager
from ..models.webhook_types import WebhookSignalPayload
from ..models.trading_types import (
    OptionTradingAction,
    OptionTradingParams,
    OptionTradingResult,
    PlaceOptionOrderParams
)
from .auth_service import AuthenticationService
from .tiger_client import TigerClient
from .trading_client_factory import get_trading_client, TradingClientFactory
from .option_service import OptionService
from .wechat_notification import wechat_notification_service, OrderNotificationPayload
from .progressive_limit_strategy import ProgressiveLimitParams, execute_progressive_limit_strategy
from ..utils.logging_config import get_global_logger

logger = get_global_logger()


class OptionTradingService:
    """Option trading service for processing webhook signals and executing trades"""
    
    def __init__(
        self,
        auth_service: Optional[AuthenticationService] = None,
        config_loader: Optional[ConfigLoader] = None,
        trading_client: Optional[TigerClient] = None,
        delta_manager: Optional[DeltaManager] = None,
        option_service: Optional[OptionService] = None
    ):
        # Support dependency injection while maintaining backward compatibility
        self.auth_service = auth_service or AuthenticationService.get_instance()
        self.config_loader = config_loader or ConfigLoader.get_instance()

        # 使用工厂模式创建Tiger交易客户端
        self.trading_client = trading_client or get_trading_client()

        # 为了向后兼容，保留deribit_client属性
        self.deribit_client = self.trading_client

        self.delta_manager = delta_manager or get_delta_manager()
        self.option_service = option_service or OptionService()

        # 记录当前使用的broker类型
        broker_type = TradingClientFactory.get_broker_type()
        logger.info(f"🔧 OptionTradingService initialized with {broker_type} client")
    
    async def close(self):
        """Close service and cleanup resources"""
        await self.trading_client.close()
        await self.option_service.close()
    
    async def process_webhook_signal(self, payload: WebhookSignalPayload) -> OptionTradingResult:
        """
        Process TradingView webhook signal
        
        Args:
            payload: Webhook signal payload
            
        Returns:
            Option trading result
        """
        try:
            # 1. Validate account
            account = self.config_loader.get_account_by_name(payload.account_name)
            if not account:
                raise Exception(f"Account not found: {payload.account_name}")
            
            if not account.enabled:
                raise Exception(f"Account disabled: {payload.account_name}")
            
            print(f"✅ Account validation successful: {account.name} (enabled: {account.enabled})")
            
            # 2. Unified authentication handling (automatically handles Mock/Real mode)
            auth_result = await self.auth_service.authenticate(payload.account_name)
            
            if not auth_result.success:
                raise Exception(auth_result.error or "Authentication failed")
            
            print(f"✅ Authentication successful for account: {payload.account_name} (Mock: {auth_result.is_mock})")
            
            # 3. Parse trading signal
            trading_params = self._parse_signal_to_trading_params(payload)
            print("📊 Parsed trading parameters:", trading_params.model_dump())
            
            # 4. Execute option trade
            result = await self._execute_option_trade(trading_params, payload)

            # 5. Send WeChat notification
            try:
                await wechat_notification_service.send_trading_notification(
                    account_name=payload.account_name,
                    trading_result=result,
                    additional_info={
                        "信号来源": "TradingView",
                        "交易方向": trading_params.direction,
                        "交易动作": trading_params.action.value if trading_params.action else "未知",
                        "数量": trading_params.quantity,
                        "TV ID": payload.tv_id or "无"
                    }
                )
            except Exception as wechat_error:
                print(f"⚠️ WeChat notification failed: {wechat_error}")
                # Don't fail the trade because of notification failure

            return result
            
        except Exception as error:
            print(f"❌ Failed to process webhook signal: {error}")
            return OptionTradingResult(
                success=False,
                message="Failed to process trading signal",
                error=str(error)
            )
    
    def _parse_signal_to_trading_params(self, payload: WebhookSignalPayload) -> OptionTradingParams:
        """
        Convert webhook signal to option trading parameters
        
        Args:
            payload: Webhook signal payload
            
        Returns:
            Option trading parameters
        """
        # Determine trading direction
        direction = "buy" if payload.side.lower() == "buy" else "sell"
        
        # Determine detailed trading action
        action = self._determine_detailed_action(
            payload.market_position,
            payload.prev_market_position,
            payload.side,
            payload.comment
        )
        
        # Parse quantity
        quantity = float(payload.size) if payload.size else 1.0
        
        # Parse price if provided
        price = float(payload.price) if payload.price else None
        
        return OptionTradingParams(
            account_name=payload.account_name,
            direction=direction,
            action=action,
            symbol=payload.symbol,
            quantity=quantity,
            price=price,
            order_type="limit" if price else "market",
            qty_type=payload.qty_type,
            delta1=payload.delta1,
            delta2=payload.delta2,
            n=payload.n,
            tv_id=payload.tv_id
        )
    
    def _determine_detailed_action(
        self,
        market_position: str,
        prev_market_position: str,
        side: str,
        comment: Optional[str] = None
    ) -> OptionTradingAction:
        """
        Determine detailed trading action based on position changes
        
        Args:
            market_position: Current market position
            prev_market_position: Previous market position
            side: Trading side
            comment: Optional comment
            
        Returns:
            Detailed trading action
        """
        # Normalize positions
        current = market_position.lower()
        previous = prev_market_position.lower()
        direction = side.lower()
        
        # Check for stop loss in comment
        if comment and "stop" in comment.lower():
            if current == "flat" and previous == "long":
                return "stop_long"
            elif current == "flat" and previous == "short":
                return "stop_short"
        
        # Determine action based on position transitions
        if previous == "flat":
            # Opening new position
            if current == "long":
                return "open_long"
            elif current == "short":
                return "open_short"
        elif current == "flat":
            # Closing position
            if previous == "long":
                return "close_long"
            elif previous == "short":
                return "close_short"
        elif previous == "long" and current == "long":
            # Adjusting long position
            if direction == "buy":
                return "open_long"  # Adding to long
            else:
                return "reduce_long"  # Reducing long
        elif previous == "short" and current == "short":
            # Adjusting short position
            if direction == "sell":
                return "open_short"  # Adding to short
            else:
                return "reduce_short"  # Reducing short
        
        # Default fallback
        return "open_long" if direction == "buy" else "open_short"
    
    async def _execute_option_trade(
        self,
        params: OptionTradingParams,
        payload: WebhookSignalPayload
    ) -> OptionTradingResult:
        """
        Execute option trade
        
        Args:
            params: Trading parameters
            payload: Original webhook payload
            
        Returns:
            Trading result
        """
        try:
            print(f"🔄 Executing {params.action} for {params.account_name}")
            
            # For now, this is a placeholder implementation
            # In a real implementation, you would:
            # 1. Find the best option contract based on delta1/n parameters
            # 2. Calculate optimal price
            # 3. Place the order
            # 4. Handle position adjustments
            # 5. Record to delta database
            
            if settings.use_mock_mode:
                # Mock execution
                order_id = f"mock_order_{int(time.time())}"
                instrument_name = f"{params.symbol}-MOCK-50000-C"

                print(f"🎭 Mock mode - simulated {params.action} execution")

                # Create Delta record in database
                try:
                    await self._create_delta_record(params, payload, order_id, instrument_name)
                    print(f"✅ Delta record created for {instrument_name}")
                except Exception as delta_error:
                    print(f"⚠️ Failed to create Delta record: {type(delta_error).__name__}: {delta_error}")
                    import traceback
                    traceback.print_exc()
                    # Don't fail the trade because of delta record failure

                return OptionTradingResult(
                    success=True,
                    order_id=order_id,
                    message=f"Mock {params.action} executed successfully",
                    instrument_name=instrument_name,
                    executed_quantity=params.quantity,
                    executed_price=0.05,
                    order_label=f"tv_{payload.tv_id}" if payload.tv_id else None,
                    final_order_state="filled"
                )
            else:
                # Real execution - implement actual option trading logic
                return await self._execute_real_option_trade(params, payload)
                
        except Exception as error:
            print(f"❌ Failed to execute option trade: {error}")
            return OptionTradingResult(
                success=False,
                message="Failed to execute option trade",
                error=str(error)
            )

    async def _create_delta_record(
        self,
        params: OptionTradingParams,
        payload: WebhookSignalPayload,
        order_id: str,
        instrument_name: str
    ):
        """Create Delta record in database"""
        from ..database.types import CreateDeltaRecordInput, DeltaRecordType
        from ..database.delta_manager import get_delta_manager

        # Determine record type based on action
        record_type = DeltaRecordType.POSITION if params.action in [
            "open_long",
            "open_short",
            "close_long",
            "close_short"
        ] else DeltaRecordType.ORDER

        # Create delta record input
        delta_input = CreateDeltaRecordInput(
            account_id=params.account_name,
            instrument_name=instrument_name,
            order_id=order_id if record_type == DeltaRecordType.ORDER else None,
            target_delta=payload.delta1 or 0.0,  # Use delta1 as target_delta
            move_position_delta=payload.delta2 or 0.0,  # Use delta2 as move_position_delta
            min_expire_days=payload.n,  # Use n as min_expire_days
            tv_id=payload.tv_id,
            action=params.action,
            record_type=record_type
        )

        # Save to database
        delta_manager = get_delta_manager()
        await delta_manager.create_record(delta_input)
    
    async def place_option_order(self, params: PlaceOptionOrderParams) -> OptionTradingResult:
        """
        Place option order
        
        Args:
            params: Order parameters
            
        Returns:
            Trading result
        """
        try:
            print(f"📝 Placing {params.direction} order for {params.account_name}")
            
            if settings.use_mock_mode:
                # Use mock client
                if params.direction == "buy":
                    response = await self.mock_client.place_buy_order(
                        params.account_name,
                        "MOCK-INSTRUMENT",
                        params.quantity,
                        price=params.price,
                        type="limit" if params.price else "market"
                    )
                else:
                    response = await self.mock_client.place_sell_order(
                        params.account_name,
                        "MOCK-INSTRUMENT", 
                        params.quantity,
                        price=params.price,
                        type="limit" if params.price else "market"
                    )
                
                if response:
                    return OptionTradingResult(
                        success=True,
                        order_id=response.order["order_id"],
                        message=f"Mock {params.direction} order placed successfully",
                        instrument_name=response.order["instrument_name"],
                        executed_quantity=response.order["filled_amount"],
                        executed_price=response.order["average_price"],
                        final_order_state=response.order["order_state"]
                    )
            
            return OptionTradingResult(
                success=False,
                message="Real order placement not yet implemented",
                error="Implementation pending"
            )
            
        except Exception as error:
            print(f"❌ Failed to place option order: {error}")
            return OptionTradingResult(
                success=False,
                message="Failed to place option order",
                error=str(error)
            )

    async def _execute_real_option_trade(
        self,
        params: OptionTradingParams,
        payload: WebhookSignalPayload
    ) -> OptionTradingResult:
        """Execute real option trading using Tiger Brokers API"""
        try:
            print(f"🚀 Executing real option trade: {params.action}")

            # 1. Determine if this is an opening action that needs delta-based selection
            is_opening_action = params.action in ["open_long", "open_short"]

            if is_opening_action and payload.delta1 is not None and payload.n is not None:
                # Use delta-based option selection for opening positions
                return await self._execute_opening_trade_with_delta(params, payload)
            else:
                # Handle other types of trades (reduce, close, stop)
                return await self._execute_other_trade_types(params, payload)

        except Exception as error:
            print(f"❌ Failed to execute real option trade: {error}")
            return OptionTradingResult(
                success=False,
                message=f"Failed to execute {params.action}",
                error=str(error)
            )

    async def _execute_opening_trade_with_delta(
        self,
        params: OptionTradingParams,
        payload: WebhookSignalPayload
    ) -> OptionTradingResult:
        """Execute opening trade using delta-based option selection"""
        try:
            print(f"🎯 Using delta-based option selection: delta={payload.delta1}, minExpiredDays={payload.n}")

            # Parse symbol to determine currency and underlying
            currency, underlying = self._parse_symbol_for_options(params.symbol)
            print(f"📊 Parsed symbol {params.symbol} → currency: {currency}, underlying: {underlying}")

            # Determine option type and trading direction
            delta1 = payload.delta1 or 0
            is_call = delta1 > 0

            # Determine actual trading direction based on option type and action
            if is_call:
                # Call option: open_long = buy, open_short = sell
                actual_direction = "buy" if params.action == "open_long" else "sell"
            else:
                # Put option: open_short = buy, open_long = sell
                actual_direction = "buy" if params.action == "open_short" else "sell"

            print(f"🎯 Option selection: delta1={delta1} → {'call' if is_call else 'put'} option, "
                  f"action={params.action} → {actual_direction}")

            # Use Tiger client
            tiger_client = self.trading_client

            try:
                # Find best option using delta
                delta_result = await tiger_client.get_instrument_by_delta(
                    currency=currency,
                    min_expired_days=payload.n,
                    delta=payload.delta1,
                    long_side=is_call,
                    underlying_asset=underlying
                )

                if not delta_result:
                    return OptionTradingResult(
                        success=False,
                        message=f"No suitable option found for delta={payload.delta1}, minExpiredDays={payload.n}"
                    )

                instrument_name = delta_result.instrument.instrument_name
                print(f"✅ Selected option instrument: {instrument_name}")

                # Execute the order
                order_result = await self._place_real_option_order(
                    instrument_name=instrument_name,
                    direction=actual_direction,
                    quantity=params.quantity,
                    account_name=params.account_name,
                    delta_result=delta_result,
                    params=params,
                    payload=payload
                )

                return order_result

            finally:
                await tiger_client.close()

        except Exception as error:
            print(f"❌ Failed to execute opening trade with delta: {error}")
            return OptionTradingResult(
                success=False,
                message=f"Failed to execute opening trade",
                error=str(error)
            )

    def _parse_symbol_for_options(self, symbol: str) -> tuple[str, str]:
        """Parse trading symbol to determine currency and underlying asset"""
        symbol_upper = symbol.upper()

        # Handle different symbol formats
        if symbol_upper.startswith('BTC'):
            return 'BTC', 'BTC'
        elif symbol_upper.startswith('ETH'):
            return 'ETH', 'ETH'
        elif symbol_upper.startswith('SOL'):
            return 'SOL', 'SOL'
        elif 'USDC' in symbol_upper:
            # For USDC options, extract underlying asset
            if symbol_upper.startswith('BTC'):
                return 'USDC', 'BTC'
            elif symbol_upper.startswith('ETH'):
                return 'USDC', 'ETH'
            elif symbol_upper.startswith('SOL'):
                return 'USDC', 'SOL'
            else:
                return 'USDC', 'BTC'  # Default to BTC
        else:
            # Assume US equity/ETF symbol for Tiger Brokers
            return 'USD', symbol_upper

    async def _place_real_option_order(
        self,
        instrument_name: str,
        direction: str,
        quantity: float,
        account_name: str,
        delta_result,
        params: OptionTradingParams,
        payload: WebhookSignalPayload
    ) -> OptionTradingResult:
        """Place a real option order on Tiger Brokers"""
        try:
            print(f"?? Placing real order for instrument: {instrument_name}")
            print(f"?? Direction: {direction}, Quantity: {quantity}")

            # Use Tiger client
            tiger_client = self.trading_client

            try:
                entry_price = (delta_result.details.best_bid_price + delta_result.details.best_ask_price) / 2
                print(
                    f"?? Entry price calculated: {entry_price} "
                    f"(bid: {delta_result.details.best_bid_price}, ask: {delta_result.details.best_ask_price})"
                )

                final_quantity, final_price = self._calculate_order_parameters(
                    params, delta_result, entry_price
                )
                print(f"?? Final parameters: quantity={final_quantity}, price={final_price}")

                from ..config.settings import settings
                from ..utils.spread_calculation import is_spread_reasonable, format_spread_ratio_as_percentage

                spread_ratio = delta_result.spread_ratio
                spread_ratio_threshold = settings.spread_ratio_threshold
                spread_tick_threshold = settings.spread_tick_multiple_threshold
                tick_size = getattr(delta_result.instrument, 'tick_size', 0.0001)

                is_reasonable = is_spread_reasonable(
                    delta_result.details.best_bid_price,
                    delta_result.details.best_ask_price,
                    tick_size,
                    spread_ratio_threshold,
                    spread_tick_threshold
                )

                spread_percentage = format_spread_ratio_as_percentage(spread_ratio)
                tick_multiple = (delta_result.details.best_ask_price - delta_result.details.best_bid_price) / tick_size

                print(
                    f"?? Spread analysis: ratio={spread_percentage}, "
                    f"tick_multiple={tick_multiple:.1f}, reasonable={is_reasonable}"
                )
                print(
                    f"?? Thresholds: ratio_threshold={spread_ratio_threshold * 100:.1f}%, "
                    f"tick_threshold={spread_tick_threshold}"
                )

                strategy = 'progressive' if is_reasonable else 'direct'

                if not is_reasonable:
                    print("?? Wide spread detected, using direct order")
                    order_result = await self._place_direct_order(
                        tiger_client,
                        instrument_name,
                        direction,
                        final_quantity,
                        final_price,
                        account_name
                    )
                else:
                    print("?? Reasonable spread, using progressive strategy")
                    order_result = await self._place_progressive_order(
                        tiger_client,
                        instrument_name,
                        direction,
                        final_quantity,
                        final_price,
                        delta_result,
                        account_name
                    )

                if order_result:
                    await self._send_order_notification(
                        account_name=account_name,
                        instrument_name=instrument_name,
                        direction=direction,
                        requested_quantity=final_quantity,
                        requested_price=final_price,
                        delta_result=delta_result,
                        strategy=strategy,
                        order_result=order_result,
                        message=None
                    )

                    try:
                        await self._create_delta_record(
                            params,
                            payload,
                            order_result.get('order_id', ''),
                            instrument_name
                        )
                        print(f"? Delta record created for {instrument_name}")
                    except Exception as delta_error:
                        print(f"?? Failed to create Delta record: {type(delta_error).__name__}: {delta_error}")

                    return OptionTradingResult(
                        success=True,
                        order_id=order_result.get('order_id', ''),
                        message=f"Successfully placed {direction} order for {final_quantity} contracts",
                        instrument_name=instrument_name,
                        executed_quantity=order_result.get('filled_amount', final_quantity),
                        executed_price=order_result.get('average_price', final_price),
                        order_label=f"tv_{payload.tv_id}" if payload.tv_id else None,
                        final_order_state=order_result.get('order_state', 'open')
                    )

                await self._send_order_notification(
                    account_name=account_name,
                    instrument_name=instrument_name,
                    direction=direction,
                    requested_quantity=final_quantity,
                    requested_price=final_price,
                    delta_result=delta_result,
                    strategy=strategy,
                    order_result=None,
                    message="Failed to place order - no response from exchange"
                )

                return OptionTradingResult(
                    success=False,
                    message="Failed to place order - no response from exchange"
                )

            finally:
                await tiger_client.close()

        except Exception as error:
            print(f"? Failed to place real option order: {error}")
            await self._send_order_notification(
                account_name=account_name,
                instrument_name=instrument_name,
                direction=direction,
                requested_quantity=quantity,
                requested_price=params.price or 0.0,
                delta_result=delta_result,
                strategy='direct',
                order_result=None,
                message=str(error)
            )
            return OptionTradingResult(
                success=False,
                message=f"Failed to place {direction} order",
                error=str(error)
            )

    def _calculate_order_parameters(self, params: OptionTradingParams, delta_result, entry_price: float) -> tuple[float, float]:
        """Calculate final order quantity and price"""
        order_quantity = params.quantity

        # Handle different quantity types
        settlement_currency = getattr(delta_result.instrument, 'settlement_currency', None) or delta_result.instrument.quote_currency

        if params.qty_type == 'cash':
            # Convert cash amount to contracts
            if settlement_currency == 'USDC':
                # USDC options: cash value divided by option price
                order_quantity = params.quantity / entry_price
            else:
                # Traditional options: consider index price
                index_price = delta_result.details.index_price or 50000  # fallback
                order_quantity = params.quantity / (entry_price * index_price)
            print(f"💰 Cash mode: converting ${params.quantity} to {order_quantity} contracts")
        elif params.qty_type == 'fixed':
            # Fixed contract quantity - for options, this is typically the number of contracts
            order_quantity = params.quantity
            print(f"💰 Fixed mode: using {order_quantity} contracts")

        # Ensure minimum quantity
        if order_quantity <= 0:
            order_quantity = 1.0

        # Apply tick size corrections using Decimal for precision
        from decimal import Decimal, ROUND_HALF_UP
        tick_size = delta_result.instrument.tick_size or 0.0001

        # Use Decimal for precise calculation
        price_decimal = Decimal(str(entry_price))
        tick_decimal = Decimal(str(tick_size))

        # Round to nearest tick
        ticks = (price_decimal / tick_decimal).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        corrected_price = float(ticks * tick_decimal)

        # Apply minimum trade amount
        min_trade_amount = delta_result.instrument.min_trade_amount or 1.0
        corrected_quantity = max(order_quantity, min_trade_amount)

        return corrected_quantity, corrected_price

    async def _place_direct_order(
        self,
        tiger_client,
        instrument_name: str,
        direction: str,
        quantity: float,
        price: float,
        account_name: str
    ) -> Optional[Dict[str, Any]]:
        """Place a direct limit order"""
        try:
            if direction == 'buy':
                response = await tiger_client.place_buy_order(
                    instrument_name=instrument_name,
                    amount=quantity,
                    account_name=account_name,
                    type='limit',
                    price=price
                )
            else:
                response = await tiger_client.place_sell_order(
                    instrument_name=instrument_name,
                    amount=quantity,
                    account_name=account_name,
                    type='limit',
                    price=price
                )

            if response and hasattr(response, 'order'):
                return {
                    'order_id': response.order.get('order_id'),
                    'order_state': response.order.get('order_state'),
                    'filled_amount': response.order.get('filled_amount', 0),
                    'average_price': response.order.get('average_price', price),
                    'order_type': 'limit'
                }
            return None

        except Exception as error:
            print(f"❌ Failed to place direct order: {error}")
            return None

    async def _place_progressive_order(
        self,
        tiger_client,
        instrument_name: str,
        direction: str,
        quantity: float,
        initial_price: float,
        delta_result,
        account_name: str
    ) -> Optional[Dict[str, Any]]:
        """Place initial limit order then run progressive limit adjustments"""
        try:
            tick_size = getattr(delta_result.instrument, 'tick_size', 0.0001)

            initial_order = await self._place_direct_order(
                tiger_client,
                instrument_name,
                direction,
                quantity,
                initial_price,
                account_name
            )

            if not initial_order or not initial_order.get('order_id'):
                return initial_order

            progressive_params = ProgressiveLimitParams(
                order_id=initial_order['order_id'],
                instrument_name=instrument_name,
                direction=direction,
                quantity=quantity,
                initial_price=initial_price,
                account_name=account_name,
                tick_size=tick_size,
                max_steps=getattr(settings, 'progressive_limit_max_steps', 3),
                step_timeout=float(getattr(settings, 'progressive_limit_step_timeout', 8.0)),
            )

            progressive_result = await execute_progressive_limit_strategy(
                progressive_params,
                tiger_client,
            )

            order_result = progressive_result.to_order_result()
            if progressive_result.position_info is not None:
                order_result['position_info'] = progressive_result.position_info

            return order_result

        except Exception as error:
            print(f"[Progressive] Error executing strategy: {error}")
            return None


    async def _execute_other_trade_types(
        self,
        params: OptionTradingParams,
        payload: WebhookSignalPayload
    ) -> OptionTradingResult:
        """Handle non-opening trade types (reduce, close, stop)"""
        try:
            is_reducing_action = params.action in ["reduce_long", "reduce_short"]
            is_close_action = params.action in ["close_long", "close_short"]
            is_stop_action = params.action in ["stop_long", "stop_short"]

            if is_reducing_action:
                if params.tv_id:
                    logger.info(f"✅ Reduce action detected, executing position adjustment for tv_id={params.tv_id}")

                    # Send position adjustment start notification
                    await self._send_position_adjustment_notification(
                        params.account_name,
                        params.tv_id,
                        'START',
                        {
                            'symbol': params.symbol,
                            'action': params.action,
                            'direction': params.direction
                        }
                    )

                    # Execute position adjustment based on tv_id
                    from .position_adjustment import execute_position_adjustment_by_tv_id

                    adjustment_result = await execute_position_adjustment_by_tv_id(
                        params.account_name,
                        params.tv_id,
                        {
                            'config_loader': self.config_loader,
                            'delta_manager': self.delta_manager,
                            'auth_service': self.auth_service,
                            'deribit_client': self.deribit_client,
                            'mock_client': self.mock_client
                        }
                    )

                    # Send position adjustment result notification
                    await self._send_position_adjustment_notification(
                        params.account_name,
                        params.tv_id,
                        'SUCCESS' if adjustment_result.success else 'FAILED',
                        {
                            'symbol': params.symbol,
                            'action': params.action,
                            'direction': params.direction,
                            'result': adjustment_result
                        }
                    )

                    return adjustment_result
                else:
                    logger.error('❌ Reduce action detected, but no tv_id provided, skipping order placement')
                    return OptionTradingResult(
                        success=False,
                        message='Reduce action detected, but no tv_id provided'
                    )

            elif is_close_action:
                if params.tv_id:
                    logger.info(f"✅ Close action detected, executing position close for tv_id={params.tv_id}")

                    # Determine close ratio, default to full close
                    close_ratio = params.close_ratio or 1.0

                    # Send profit close start notification
                    await self._send_profit_close_notification(
                        params.account_name,
                        params.tv_id,
                        'START',
                        {
                            'symbol': params.symbol,
                            'action': params.action,
                            'direction': params.direction,
                            'close_ratio': close_ratio
                        }
                    )

                    # Execute position close based on tv_id
                    from .position_adjustment import execute_position_close_by_tv_id

                    close_result = await execute_position_close_by_tv_id(
                        params.account_name,
                        params.tv_id,
                        close_ratio,
                        False,  # Use limit order + progressive strategy
                        {
                            'config_loader': self.config_loader,
                            'delta_manager': self.delta_manager,
                            'auth_service': self.auth_service,
                            'deribit_client': self.deribit_client
                        }
                    )

                    # Send profit close result notification
                    await self._send_profit_close_notification(
                        params.account_name,
                        params.tv_id,
                        'SUCCESS' if close_result.success else 'FAILED',
                        {
                            'symbol': params.symbol,
                            'action': params.action,
                            'direction': params.direction,
                            'close_ratio': close_ratio,
                            'result': close_result
                        }
                    )

                    return close_result
                else:
                    logger.error('❌ Close action detected, but no tv_id provided, skipping order placement')
                    return OptionTradingResult(
                        success=False,
                        message='Close action detected, but no tv_id provided'
                    )

            elif is_stop_action:
                if params.tv_id:
                    logger.info(f"✅ Stop action detected, executing position stop for tv_id={params.tv_id}")

                    # Send stop loss start notification
                    await self._send_stop_loss_notification(
                        params.account_name,
                        params.tv_id,
                        'START',
                        {
                            'symbol': params.symbol,
                            'action': params.action,
                            'direction': params.direction
                        }
                    )

                    # Execute stop loss logic: use position close with 50% ratio
                    from .position_adjustment import execute_position_close_by_tv_id

                    stop_result = await execute_position_close_by_tv_id(
                        params.account_name,
                        params.tv_id,
                        0.5,  # Close 50%
                        False,  # Use limit order + progressive strategy for stop loss
                        {
                            'config_loader': self.config_loader,
                            'delta_manager': self.delta_manager,
                            'auth_service': self.auth_service,
                            'deribit_client': self.deribit_client
                        }
                    )

                    # Send stop loss result notification
                    await self._send_stop_loss_notification(
                        params.account_name,
                        params.tv_id,
                        'SUCCESS' if stop_result.success else 'FAILED',
                        {
                            'symbol': params.symbol,
                            'action': params.action,
                            'direction': params.direction,
                            'result': stop_result
                        }
                    )

                    return stop_result
                else:
                    logger.error('❌ Stop action detected, but no tv_id provided, skipping order placement')
                    return OptionTradingResult(
                        success=False,
                        message='Stop action detected, but no tv_id provided'
                    )

            # Default case
            return OptionTradingResult(
                success=False,
                message=f"Trade type {params.action} not supported",
                error="Unsupported trade action"
            )

        except Exception as error:
            logger.error(f"❌ Failed to execute {params.action}: {error}")
            return OptionTradingResult(
                success=False,
                message=f"Failed to execute {params.action}",
                error=str(error)
            )
    def _extract_result_attr(self, result: Any, field: str) -> Optional[Any]:
        """Safely extract field from OptionTradingResult-like objects or dicts."""
        if result is None:
            return None
        if isinstance(result, dict):
            return result.get(field)
        return getattr(result, field, None)

    def _get_action_text(self, action: Optional[str]) -> str:
        mapping = {
            'open_long': 'open long',
            'open_short': 'open short',
            'close_long': 'close long',
            'close_short': 'close short',
            'reduce_long': 'reduce long',
            'reduce_short': 'reduce short',
            'stop_long': 'stop long',
            'stop_short': 'stop short'
        }
        return mapping.get(action or '', action or 'unknown')

    def _get_direction_text(self, direction: Optional[str]) -> str:
        if direction == 'buy':
            return 'buy'
        if direction == 'sell':
            return 'sell'
        return direction or 'unknown'

    async def _send_order_notification(
        self,
        account_name: str,
        instrument_name: str,
        direction: str,
        requested_quantity: float,
        requested_price: Optional[float],
        delta_result,
        strategy: str,
        order_result: Optional[Dict[str, Any]],
        message: Optional[str]
    ) -> None:
        if not wechat_notification_service.is_available(account_name):
            return

        payload: OrderNotificationPayload = {
            'success': False,
            'instrument_name': instrument_name,
            'direction': direction,
            'quantity': requested_quantity,
            'strategy': strategy,
        }

        if requested_price is not None:
            payload['requested_price'] = requested_price

        details = getattr(delta_result, 'details', None)
        instrument = getattr(delta_result, 'instrument', None)
        if details is not None:
            best_bid = getattr(details, 'best_bid_price', None)
            best_ask = getattr(details, 'best_ask_price', None)
            if best_bid is not None:
                payload['best_bid_price'] = best_bid
            if best_ask is not None:
                payload['best_ask_price'] = best_ask
        if instrument is not None:
            tick_size = getattr(instrument, 'tick_size', None)
            if tick_size is not None:
                payload['tick_size'] = tick_size
        spread_ratio = getattr(delta_result, 'spread_ratio', None)
        if spread_ratio is not None:
            payload['spread_ratio'] = spread_ratio

        if order_result:
            payload['order_id'] = order_result.get('order_id')
            payload['order_state'] = order_result.get('order_state')
            payload['executed_quantity'] = order_result.get('filled_amount')
            payload['executed_price'] = order_result.get('average_price')
            order_type = order_result.get('order_type')
            if order_type:
                payload['order_type'] = order_type
            attempt = order_result.get('attempt')
            if attempt:
                payload['attempt'] = attempt
            payload['success'] = order_result.get('order_state') not in {None, 'rejected'}
        else:
            payload['order_state'] = 'failed'
            payload['success'] = False

        if message:
            payload['message'] = message

        await wechat_notification_service.send_order_notification(account_name, payload)

    async def _send_position_adjustment_notification(
        self,
        account_name: str,
        tv_id: int,
        status: str,
        details: Dict[str, Any]
    ) -> None:
        if not wechat_notification_service.is_available(account_name):
            return

        status_titles = {
            'START': 'Position adjustment started',
            'SUCCESS': 'Position adjustment completed',
            'FAILED': 'Position adjustment failed'
        }
        title = status_titles.get(status, 'Position adjustment update')

        lines = [
            f"**{title}**",
            '',
            f"- account: {account_name}",
            f"- tv id: {tv_id}"
        ]

        symbol = details.get('symbol')
        if symbol:
            lines.append(f"- symbol: {symbol}")

        lines.append(f"- action: {self._get_action_text(details.get('action'))}")
        lines.append(f"- direction: {self._get_direction_text(details.get('direction'))}")

        result = details.get('result')
        if result is not None:
            success_flag = self._extract_result_attr(result, 'success')
            if success_flag is not None:
                lines.append(f"- result: {'success' if success_flag else 'failed'}")
            result_msg = self._extract_result_attr(result, 'message')
            if result_msg:
                lines.append(f"- note: {result_msg}")
            executed_quantity = self._extract_result_attr(result, 'executed_quantity')
            if executed_quantity:
                lines.append(f"- executed quantity: {executed_quantity}")

        await wechat_notification_service.send_custom_markdown(account_name, '\n'.join(lines))

    async def _send_profit_close_notification(
        self,
        account_name: str,
        tv_id: int,
        status: str,
        details: Dict[str, Any]
    ) -> None:
        if not wechat_notification_service.is_available(account_name):
            return

        status_titles = {
            'START': 'Profit close started',
            'SUCCESS': 'Profit close finished',
            'FAILED': 'Profit close failed'
        }
        title = status_titles.get(status, 'Profit close update')

        lines = [
            f"**{title}**",
            '',
            f"- account: {account_name}",
            f"- tv id: {tv_id}",
            f"- symbol: {details.get('symbol', 'n/a')}",
            f"- action: {self._get_action_text(details.get('action'))}",
            f"- direction: {self._get_direction_text(details.get('direction'))}"
        ]

        close_ratio = details.get('close_ratio')
        if close_ratio is not None:
            lines.append(f"- close ratio: {close_ratio * 100:.1f}%")

        instruments = details.get('instrumentNames') or details.get('instrument_names')
        if instruments:
            if isinstance(instruments, list):
                instrument_list = ', '.join(str(item) for item in instruments)
            else:
                instrument_list = str(instruments)
            lines.append(f"- instruments: {instrument_list}")

        result = details.get('result')
        if result is not None:
            result_msg = self._extract_result_attr(result, 'message')
            if result_msg:
                lines.append(f"- note: {result_msg}")
            executed_quantity = self._extract_result_attr(result, 'executed_quantity')
            if executed_quantity:
                lines.append(f"- executed quantity: {executed_quantity}")

        await wechat_notification_service.send_custom_markdown(account_name, '\n'.join(lines))

    async def _send_stop_loss_notification(
        self,
        account_name: str,
        tv_id: int,
        status: str,
        details: Dict[str, Any]
    ) -> None:
        if not wechat_notification_service.is_available(account_name):
            return

        status_titles = {
            'START': 'Stop loss started',
            'SUCCESS': 'Stop loss completed',
            'FAILED': 'Stop loss failed'
        }
        title = status_titles.get(status, 'Stop loss update')

        lines = [
            f"**{title}**",
            '',
            f"- account: {account_name}",
            f"- tv id: {tv_id}",
            f"- symbol: {details.get('symbol', 'n/a')}",
            f"- action: {self._get_action_text(details.get('action'))}",
            f"- direction: {self._get_direction_text(details.get('direction'))}"
        ]

        result = details.get('result')
        if result is not None:
            result_msg = self._extract_result_attr(result, 'message')
            if result_msg:
                lines.append(f"- note: {result_msg}")
            executed_quantity = self._extract_result_attr(result, 'executed_quantity')
            if executed_quantity:
                lines.append(f"- executed quantity: {executed_quantity}")

        await wechat_notification_service.send_custom_markdown(account_name, '\n'.join(lines))
