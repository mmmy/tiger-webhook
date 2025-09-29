"""
Position adjustment service - functional programming approach

Independent position adjustment logic to avoid circular dependencies.
Based on ../deribit_webhook/src/services/position-adjustment.ts
"""

from typing import Optional, Dict, Any, List
import asyncio

from ..config import ConfigLoader
from ..database import DeltaManager, get_delta_manager
from ..database.types import DeltaRecord, DeltaRecordType
from ..models.trading_types import (
    OptionTradingParams,
    PositionAdjustmentResult,
    PositionAdjustmentSummary,
    OptionTradingResult
)
from ..models.deribit_types import DeribitPosition
from .auth_service import AuthenticationService
from .tiger_client import TigerClient
from .trading_client_factory import get_trading_client
from ..utils.spread_calculation import (
    is_spread_reasonable,
    calculate_spread_ratio,
    format_spread_ratio_as_percentage
)
from ..utils.price_utils import correct_order_amount, correct_smart_price
from ..utils.logging_config import get_global_logger

logger = get_global_logger()

# ---- Services typing: give services a detailed definition ----
from typing import TypedDict, Protocol

class TradingClientProtocol(Protocol):
    async def get_positions(self, account_name: str, **kwargs) -> List[Dict]: ...
    async def get_instrument_by_delta(
        self,
        currency: str,
        min_expired_days: int,
        delta: float,
        long_side: bool,
        underlying_asset: str
    ) -> Optional[Any]: ...
    async def get_option_details(self, option_name: str) -> Optional[Dict[str, Any]]: ...
    async def get_instrument(self, instrument_name: str) -> Optional[Dict[str, Any]]: ...
    async def place_buy_order(self, account_name: str, instrument_name: str, amount: float, **kwargs) -> Any: ...
    async def place_sell_order(self, account_name: str, instrument_name: str, amount: float, **kwargs) -> Any: ...

class Services(TypedDict, total=False):
    # Core singletons
    config_loader: ConfigLoader
    delta_manager: DeltaManager
    auth_service: AuthenticationService

    # Trading client (TigerClient implements this protocol; legacy Deribit-style clients also compatible)
    deribit_client: TradingClientProtocol

    # Optional, for mock/testing
    mock_client: Any

    # Direct Tiger client access when needed
    tiger_client: TigerClient




async def execute_position_adjustment_by_tv_id(
    account_name: str,
    tv_id: int,
    services: Services
) -> OptionTradingResult:
    """
    Execute position adjustment based on tv_id

    Args:
        account_name: Account name
        tv_id: TradingView signal ID
        services: Service dependencies

    Returns:
        Option trading result
    """
    try:
        logger.info(f"🔍 Executing position adjustment for account: {account_name}, tv_id: {tv_id}")

        config_loader = services.get('config_loader') or ConfigLoader.get_instance()
        delta_manager = services.get('delta_manager') or get_delta_manager()
        auth_service = services.get('auth_service') or AuthenticationService.get_instance()
        deribit_client = services.get('deribit_client') or DeribitClient()
        mock_client = services.get('mock_client') or MockDeribitClient()

        # 1. Query Delta database records for tv_id
        delta_records = await delta_manager.get_records_by_tv_id(account_name, tv_id)

        if not delta_records:
            logger.warning(f"⚠️ No delta records found for tv_id: {tv_id}")
            return OptionTradingResult(
                success=False,
                message=f"No delta records found for tv_id: {tv_id}"
            )

        logger.info(f"📊 Found {len(delta_records)} delta record(s) for tv_id: {tv_id}")

        # 2. Get account configuration
        account = config_loader.get_account_by_name(account_name)
        if not account:
            return OptionTradingResult(
                success=False,
                message=f"Account not found: {account_name}"
            )

        # 3. Get access token
        auth_result = await auth_service.authenticate(account_name)
        if not auth_result.success:
            return OptionTradingResult(
                success=False,
                message=f"Failed to authenticate account: {account_name}",
                error=auth_result.error
            )

        # 4. Get current positions - all option positions
        positions = await deribit_client.get_positions(
            account_name=account_name,
            kind='option'
        )

        # Find positions that need adjustment
        positions_to_adjust = [
            pos for pos in positions
            if any(record.instrument_name == pos.instrument_name for record in delta_records)
            and pos.size != 0
        ]

        # 5. Execute adjustment for each position
        adjustment_results = []

        if not positions_to_adjust:
            logger.warning(f"⚠️ No positions to adjust for tv_id: {tv_id}")
            return OptionTradingResult(
                success=False,
                message=f"No active positions found for tv_id: {tv_id}"
            )

        for current_position in positions_to_adjust:
            # Find corresponding Delta record
            delta_record = next(
                (record for record in delta_records
                 if record.instrument_name == current_position.get('instrument_name')),
                None
            )

            if delta_record:
                logger.info(f"🔄 Executing adjustment for instrument: {current_position.get('instrument_name')}")

                adjustment_result = await execute_position_adjustment(
                    request_id=f"tv_{tv_id}_{int(asyncio.get_event_loop().time())}",
                    account_name=account_name,
                    current_position=current_position,
                    delta_record=delta_record,
                    services={
                        'config_loader': config_loader,
                        'delta_manager': delta_manager,
                        'auth_service': auth_service,
                        'deribit_client': deribit_client,
                        'mock_client': mock_client
                    }
                )

                adjustment_results.append(adjustment_result)
            else:
                logger.warning(f"⚠️ No delta record found for position: {current_position.get('instrument_name')}")
                adjustment_results.append(PositionAdjustmentResult(
                    success=False,
                    message=f"No delta record found for position: {current_position.get('instrument_name')}"
                ))

        # 6. Summarize results
        success_count = sum(1 for r in adjustment_results if r.success)
        failure_count = len(adjustment_results) - success_count
        total_count = len(adjustment_results)

        # Generate detailed result message
        message = f"Position adjustment completed: {success_count}/{total_count} successful"

        if failure_count > 0:
            failures = [r for r in adjustment_results if not r.success]
            failure_details = "; ".join([
                f"{f.reason}: {f.error or f.message or 'Unknown error'}" if f.reason
                else f.message or 'Unknown error'
                for f in failures
            ])
            message += f". Failures ({failure_count}): {failure_details}"

        return OptionTradingResult(
            success=success_count > 0,
            message=message,
            order_id=f"tv_adjustment_{tv_id}",
            executed_quantity=float(success_count)
        )

    except Exception as error:
        logger.error(f"❌ Position adjustment failed for tv_id {tv_id}: {error}")
        return OptionTradingResult(
            success=False,
            message=f"Position adjustment failed: {str(error)}"
        )


async def execute_position_adjustment(
    request_id: str,
    account_name: str,
    current_position: Dict,  # Changed type hint to Dict
    delta_record: DeltaRecord,
    services: Services
) -> PositionAdjustmentResult:
    """
    Execute position adjustment for a single position

    Args:
        request_id: Request ID for tracking
        account_name: Account name
        current_position: Current position
        delta_record: Delta record
        services: Service dependencies

    Returns:
        Position adjustment result
    """
    try:
        logger.info(f"🔄 [{request_id}] Starting position adjustment for {current_position.get('instrument_name')}")

        config_loader = services['config_loader']
        delta_manager = services['delta_manager']
        deribit_client = services['deribit_client']

        # Extract currency and underlying asset information
        currency, underlying = parse_instrument_for_options(current_position.get('instrument_name'))

        # 1. Get new option instrument based on move_position_delta
        logger.info(f"📊 [{request_id}] Getting instrument by delta: currency={currency}, "
                   f"underlying={underlying}, delta={delta_record.move_position_delta}")

        # Determine direction: positive move_position_delta selects call options, negative selects put options
        is_call = delta_record.move_position_delta > 0

        # Get spread thresholds from settings
        from ..config.settings import settings
        spread_ratio_threshold = settings.spread_ratio_threshold
        spread_tick_threshold = settings.spread_tick_multiple_threshold

        # Get new option instrument
        delta_result = await deribit_client.get_instrument_by_delta(
            currency=currency,
            min_expired_days=delta_record.min_expire_days or 7,
            delta=abs(delta_record.move_position_delta),
            long_side=is_call,
            underlying_asset=underlying
        )

        if not delta_result or not delta_result.instrument:
            raise Exception("Failed to get instrument by delta: No suitable instrument found")

        # If selected instrument is the same as current position, no adjustment needed
        if delta_result.instrument.instrument_name == current_position.get('instrument_name'):
            logger.warning(f"⚠️ [{request_id}] Selected instrument is the same as current position: "
                          f"{current_position.get('instrument_name')}")
            return PositionAdjustmentResult(
                success=False,
                reason="无需调整：目标合约与当前持仓合约相同",
                error=f"当前持仓: {current_position.get('instrument_name')} "
                      f"目标合约: {delta_result.instrument.instrument_name} 状态: 合约名称完全相同"
            )

        # Check if spread is reasonable
        tick_size = getattr(delta_result.instrument, 'tick_size', 0.0001)
        is_reasonable = is_spread_reasonable(
            delta_result.details.best_bid_price,
            delta_result.details.best_ask_price,
            tick_size,
            spread_ratio_threshold,
            spread_tick_threshold
        )

        if not is_reasonable:
            spread_ratio_formatted = format_spread_ratio_as_percentage(delta_result.spread_ratio)
            threshold_formatted = format_spread_ratio_as_percentage(spread_ratio_threshold)
            tick_multiple = ((delta_result.details.best_ask_price - delta_result.details.best_bid_price)
                           / tick_size)

            logger.error(f"❌ [{request_id}] Spread too wide for {delta_result.instrument.instrument_name}: "
                        f"ratio={spread_ratio_formatted} > {threshold_formatted}, "
                        f"tick_multiple={tick_multiple:.1f} > {spread_tick_threshold}")

            return PositionAdjustmentResult(
                success=False,
                reason=f"换仓价差过大：比率{spread_ratio_formatted} > {threshold_formatted} "
                      f"且 步进倍数{tick_multiple:.1f} > {spread_tick_threshold}",
                error=f"合约: {delta_result.instrument.instrument_name}\n"
                      f"买价: {delta_result.details.best_bid_price}\n"
                      f"卖价: {delta_result.details.best_ask_price}\n"
                      f"价差比例: {spread_ratio_formatted}\n"
                      f"步进倍数: {tick_multiple:.1f}\n"
                      f"比率阈值: {threshold_formatted}\n"
                      f"步进阈值: {spread_tick_threshold}"
            )

        logger.info(f"🎯 [{request_id}] Selected new instrument: {delta_result.instrument.instrument_name}")

        # 2. Close current position using progressive strategy
        close_direction = "sell" if current_position.get('direction') == "buy" else "buy"
        close_quantity = abs(current_position.get('size', 0))

        logger.info(f"📉 [{request_id}] Closing current position: {close_direction} {close_quantity} "
                   f"contracts of {current_position.get('instrument_name')}")

        close_result = await execute_position_close(
            request_id=f"{request_id}_close",
            account_name=account_name,
            current_position=current_position,
            delta_record=delta_record,
            close_ratio=1.0,  # Full close
            is_market_order=False,  # Use limit order + progressive strategy
            services={
                'config_loader': config_loader,
                'delta_manager': delta_manager,
                'deribit_client': deribit_client
            }
        )

        if not close_result.success:
            raise Exception(f"Failed to close position: {close_result.error or 'Unknown error'}")

        logger.info(f"✅ [{request_id}] Current position closed successfully using progressive strategy")

        # 3. Open new position
        new_direction = current_position.get('direction')
        new_quantity = abs(current_position.get('size', 0))
        instrument_name = delta_result.instrument.instrument_name

        logger.info(f"📈 [{request_id}] Opening new position: {new_direction} {new_quantity} "
                   f"contracts of {instrument_name}")

        # Use place_option_order for better execution
        from .option_trading_service import OptionTradingService

        trading_params = OptionTradingParams(
            account_name=account_name,
            direction=new_direction,
            action="open_long" if new_direction == "buy" else "open_short",
            symbol=currency,
            quantity=new_quantity,
            order_type="limit",
            instrument_name=instrument_name,
            delta1=delta_record.move_position_delta,
            delta2=delta_record.target_delta,
            n=delta_record.min_expire_days,
            tv_id=delta_record.tv_id
        )

        option_service = OptionTradingService(
            config_loader=config_loader,
            delta_manager=delta_manager,
            deribit_client=deribit_client
        )

        new_order_result = await option_service._place_real_option_order(
            instrument_name=instrument_name,
            direction=new_direction,
            quantity=new_quantity,
            account_name=account_name,
            delta_result=delta_result,
            params=trading_params,
            payload=None  # No original payload for adjustment
        )

        if not new_order_result or not new_order_result.success:
            logger.error(f"❌ [{request_id}] Failed to open new position, but old position was closed")
            raise Exception(f"Failed to open new position: {new_order_result.message if new_order_result else 'No response received'}")

        logger.info(f"✅ [{request_id}] New position opened successfully: {new_order_result.order_id}")

        # Return success result
        return PositionAdjustmentResult(
            success=True,
            old_instrument=current_position.get('instrument_name'),
            new_instrument=instrument_name,
            adjustment_summary=PositionAdjustmentSummary(
                old_size=current_position.get('size', 0),
                old_delta=current_position.get('delta', 0),
                new_direction=new_direction,
                new_quantity=new_quantity,
                target_delta=delta_record.move_position_delta
            )
        )

    except Exception as error:
        logger.error(f"💥 [{request_id}] Position adjustment failed: {error}")
        return PositionAdjustmentResult(
            success=False,
            reason="Exception during adjustment",
            error=str(error)
        )


async def execute_position_close_by_tv_id(
    account_name: str,
    tv_id: int,
    close_ratio: float,
    is_market_order: bool,
    services: Services
) -> OptionTradingResult:
    """
    Execute position close based on tv_id

    Args:
        account_name: Account name
        tv_id: TradingView signal ID
        close_ratio: Close ratio (0-1, 1 means full close)
        is_market_order: Whether to use market order
        services: Service dependencies

    Returns:
        Option trading result
    """
    try:
        logger.info(f"🔍 Executing position close for account: {account_name}, tv_id: {tv_id}, ratio: {close_ratio}")

        # Validate close ratio
        if close_ratio <= 0 or close_ratio > 1:
            return OptionTradingResult(
                success=False,
                message=f"Invalid close ratio: {close_ratio}. Must be between 0 and 1"
            )

        config_loader = services.get('config_loader') or ConfigLoader.get_instance()
        delta_manager = services.get('delta_manager') or get_delta_manager()
        auth_service = services.get('auth_service') or AuthenticationService.get_instance()
        # deribit_client = services.get('deribit_client') or DeribitClient()
        tiger_client = services.get('deribit_client')

        # 1. Query Delta database records for tv_id
        delta_records = await delta_manager.get_records_by_tv_id(account_name, tv_id)

        if not delta_records:
            logger.warning(f"⚠️ No delta records found for tv_id: {tv_id}")
            return OptionTradingResult(
                success=False,
                message=f"No delta records found for tv_id: {tv_id}"
            )

        logger.info(f"📊 Found {len(delta_records)} delta record(s) for tv_id: {tv_id}")

        # 2. Get account configuration
        account = config_loader.get_account_by_name(account_name)
        if not account:
            return OptionTradingResult(
                success=False,
                message=f"Account not found: {account_name}"
            )

        # 3. Get access token
        auth_result = await auth_service.authenticate(account_name)
        if not auth_result.success:
            return OptionTradingResult(
                success=False,
                message=f"Failed to authenticate account: {account_name}",
                error=auth_result.error
            )

        # 4. Get current positions - all option positions
        positions = await tiger_client.get_positions(
            account_name=account_name
        ) or []

        # 5. Execute close for each Delta record
        close_results = []
        for delta_record in delta_records:
            current_position = next(
                (pos for pos in positions
                 if pos.get('instrument_name') == delta_record.instrument_name and pos.get('size', 0) != 0),
                None
            )

            if current_position:
                logger.info(f"🔄 Executing close for instrument: {delta_record.instrument_name}")

                close_result = await execute_position_close(
                    request_id=f"tv_close_{tv_id}_{int(asyncio.get_event_loop().time())}",
                    account_name=account_name,
                    current_position=current_position,
                    delta_record=delta_record,
                    close_ratio=close_ratio,
                    is_market_order=is_market_order,
                    services={
                        'config_loader': config_loader,
                        'delta_manager': delta_manager,
                        'deribit_client': tiger_client
                    }
                )

                close_results.append(close_result)
            else:
                # logger.warning(f"⚠️ No active position found for instrument: {delta_record.instrument_name}")
                close_results.append({
                    'success': False,
                    'message': f"No active position found for instrument: {delta_record.instrument_name}"
                })

        # 6. Summarize results
        success_count = sum(1 for r in close_results if r.get('success', False))
        total_count = len(close_results)

        # Collect successfully closed instruments
        closed_instruments = [
            r.get('instrument') for r in close_results
            if r.get('success', False) and 'instrument' in r
        ]

        # 7. If there are successful closes, delete Delta records for tv_id
        if success_count > 0:
            try:
                deleted_count = await delta_manager.delete_records_by_tv_id(tv_id)
                logger.info(f"🗑️ Deleted {deleted_count} delta records for tv_id: {tv_id} after successful position close")
            except Exception as error:
                logger.error(f"❌ Failed to delete delta records for tv_id {tv_id}: {error}")
                # Deletion failure doesn't affect close result, just log error

        return OptionTradingResult(
            success=success_count > 0,
            message=f"Position close completed: {success_count}/{total_count} successful",
            order_id=f"tv_close_{tv_id}",
            executed_quantity=float(success_count),
            # Add closed instruments info
            instrument_name=", ".join(closed_instruments) if closed_instruments else None
        )

    except Exception as error:
        logger.error(f"❌ Position close failed for tv_id {tv_id}: {error}")
        return OptionTradingResult(
            success=False,
            message=f"Position close failed: {str(error)}"
        )


async def execute_position_close(
    request_id: str,
    account_name: str,
    current_position: Dict,  # Changed type hint to Dict
    delta_record: Optional[DeltaRecord],
    close_ratio: float,
    is_market_order: bool,
    services: Services
) -> Dict[str, Any]:
    """
    Execute single position close operation

    Args:
        request_id: Request ID for tracking
        account_name: Account name
        current_position: Current position
        delta_record: Delta record (optional)
        close_ratio: Close ratio
        is_market_order: Whether to use market order
        services: Service dependencies

    Returns:
        Close result dictionary
    """
    try:
        logger.info(f"🔄 [{request_id}] Starting position close for {current_position.get('instrument_name')} "
                   f"(ratio: {close_ratio})")

        config_loader = services['config_loader']
        delta_manager = services['delta_manager']
        deribit_client = services['deribit_client']

        # Get spread thresholds from settings
        from ..config.settings import settings
        spread_ratio_threshold = settings.spread_ratio_threshold
        spread_tick_threshold = settings.spread_tick_multiple_threshold

        # Check current position's spread
        option_details = await deribit_client.get_option_details(current_position.get('instrument_name'))
        if not option_details:
            return {
                'success': False,
                'error': f"Failed to get option details for {current_position.get('instrument_name')}"
            }

        # Get instrument info for tick_size
        # instrument_info = await deribit_client.get_instrument(current_position.get('instrument_name'))
        # if not instrument_info:
        #     return {
        #         'success': False,
        #         'error': f"Failed to get instrument details for {current_position.get('instrument_name')}"
        #     }

        current_spread_ratio = calculate_spread_ratio(
            option_details.best_bid_price,
            option_details.best_ask_price
        )

        # Use comprehensive spread judgment logic
        tick_size = 0.01
        is_reasonable = is_spread_reasonable(
            option_details.best_bid_price,
            option_details.best_ask_price,
            0.01,
            spread_ratio_threshold,
            spread_tick_threshold
        )

        if not is_reasonable:
            current_spread_formatted = format_spread_ratio_as_percentage(current_spread_ratio)
            threshold_formatted = format_spread_ratio_as_percentage(spread_ratio_threshold)
            tick_multiple = ((option_details.best_ask_price - option_details.best_bid_price) / tick_size)

            logger.error(f"❌ [{request_id}] Position spread too wide for {current_position.get('instrument_name')}: "
                        f"ratio={current_spread_formatted} > {threshold_formatted}, "
                        f"tick_multiple={tick_multiple:.1f} > {spread_tick_threshold}")

            return {
                'success': False,
                'error': f"平仓价差过大：比率{current_spread_formatted} > {threshold_formatted} "
                        f"且 步进倍数{tick_multiple:.1f} > {spread_tick_threshold}"
            }

        logger.info(f"✅ [{request_id}] Spread acceptable for {current_position.get('instrument_name')}, proceeding with close")

        # Calculate close quantity
        total_size = abs(current_position.get('size', 0))
        raw_close_quantity = total_size * close_ratio

        # Correct close quantity using utility function
        close_direction = "sell" if current_position.get('direction') == "buy" else "buy"
        close_quantity = correct_order_amount(raw_close_quantity)

        logger.info(f"📉 [{request_id}] Closing position: {close_direction} {close_quantity} contracts "
                   f"({close_ratio * 100:.1f}% of {total_size})")

        price = None
        if not is_market_order:
            # Use smart pricing for limit orders
            smart_price_result = correct_smart_price(
                close_direction,
                option_details.best_bid_price,
                option_details.best_ask_price,
                0.2  # 20% spread ratio
            )
            price = smart_price_result

        # Execute close order
        if close_direction == "buy":
            close_result = await deribit_client.place_buy_order(
                instrument_name=current_position.get('instrument_name'),
                amount=close_quantity,
                account_name=account_name,
                type="market" if is_market_order else "limit",
                price=price
            )
        else:
            close_result = await deribit_client.place_sell_order(
                instrument_name=current_position.get('instrument_name'),
                amount=close_quantity,
                account_name=account_name,
                type="market" if is_market_order else "limit",
                price=price
            )

        if not close_result:
            raise Exception("Failed to close position: No response received")
        else:
            logger.info(f"✅ [{request_id}] Position closed successfully: {close_result.order.get('order_id')}")

        # If full close (close_ratio = 1) and has Delta record, delete Delta record
        delta_record_deleted = False
        if close_ratio == 1 and delta_record and delta_record.id:
            delta_record_deleted = await delta_manager.delete_record(delta_record.id)
            logger.info(f"🗑️ [{request_id}] Delta record deletion: {'success' if delta_record_deleted else 'failed'} "
                       f"(ID: {delta_record.id})")
        elif close_ratio == 1:
            logger.info(f"📝 [{request_id}] Full close completed, but no delta record to delete")
        else:
            logger.info(f"📝 [{request_id}] Partial close ({close_ratio * 100:.1f}%), keeping delta record")

        # Return success result
        return {
            'success': True,
            'close_result': close_result,
            'delta_record_deleted': delta_record_deleted,
            'instrument': current_position.get('instrument_name'),
            'close_summary': {
                'original_size': current_position.get('size', 0),
                'close_quantity': close_quantity,
                'close_ratio': close_ratio,
                'remaining_size': total_size - close_quantity,
                'close_direction': close_direction
            }
        }

    except Exception as error:
        logger.error(f"💥 [{request_id}] Position close failed: {error}")
        return {
            'success': False,
            'reason': 'Exception during close',
            'error': str(error),
            'delta_record': delta_record
        }


def parse_instrument_for_options(instrument_name: str) -> tuple[str, str]:
    """
    Parse option instrument name to extract currency and underlying parameters
    Supports coin-margined options (BTC-XXX) and USDC options (SOL_USDC-XXX)

    Args:
        instrument_name: Option instrument name

    Returns:
        Tuple of (currency, underlying)
    """
    upper_instrument = instrument_name.upper()

    # Check for USDC option format: SOL_USDC-DDMMMYY-STRIKE-C/P
    if '_USDC-' in upper_instrument:
        underlying = upper_instrument.split('_USDC-')[0]
        return 'USDC', underlying
    else:
        # Coin-margined option format: BTC-DDMMMYY-STRIKE-C/P or ETH-DDMMMYY-STRIKE-C/P
        parts = upper_instrument.split('-')
        if len(parts) >= 4:
            underlying = parts[0]
            return underlying, underlying
        else:
            raise ValueError(f"Invalid instrument name format: {instrument_name}")
