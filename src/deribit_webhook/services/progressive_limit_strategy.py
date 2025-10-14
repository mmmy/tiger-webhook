"""Progressive limit strategy implementation for adjusting Deribit orders."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from .tiger_client import TigerClient
from ..utils.price_utils import round_to_tick_size
from ..utils.logging_config import get_global_logger

logger = get_global_logger()


@dataclass
class ProgressiveLimitParams:
    order_id: str
    instrument_name: str
    direction: Literal['buy', 'sell']
    quantity: float
    initial_price: float
    account_name: str
    tick_size: float
    max_steps: int = 3
    step_timeout: float = 8.0  # seconds


@dataclass
class ProgressiveLimitResult:
    success: bool
    order_id: str
    final_order_state: Optional[str]
    executed_quantity: Optional[float]
    average_price: Optional[float]
    attempt_count: int
    message: str
    order_type: str = "limit"
    position_info: Optional[Dict[str, Any]] = None

    def to_order_result(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "order_state": self.final_order_state,
            "filled_amount": self.executed_quantity,
            "average_price": self.average_price,
            "order_type": self.order_type,
            "attempt": self.attempt_count,
        }


def _calculate_progressive_price(
    direction: Literal['buy', 'sell'],
    initial_price: float,
    best_bid: float,
    best_ask: float,
    step_index: int,
    max_steps: int,
) -> float:
    """Interpolate price from initial value toward the best side."""
    if max_steps <= 0:
        return best_ask if direction == 'buy' else best_bid

    ratio = step_index / max_steps

    if direction == 'buy':
        target = initial_price + (best_ask - initial_price) * ratio
        return min(target, best_ask)

    target = initial_price - (initial_price - best_bid) * ratio
    return max(target, best_bid)


async def execute_progressive_limit_strategy(
    params: ProgressiveLimitParams,
    tiger_client: TigerClient,
) -> ProgressiveLimitResult:
    """执行分段限价委托的动态调整流程。

    协程会周期性检查实时委托状态与盘口行情，在满足最小跳动价位的
    前提下逐步把工作价格向当前最佳买/卖价逼近；若订单仍保持开启，则
    会按最新最优价再做一次调整。返回结果包含执行摘要与轻量仓位上下文，
    便于后续观测。
    """
    last_price = params.initial_price
    attempt_count = 0

    for step in range(1, params.max_steps + 1):
        await asyncio.sleep(max(params.step_timeout, 0.1))
        attempt_count = step

        order_status = await tiger_client.get_order_state(params.account_name, params.order_id)
        if not order_status or order_status.get("order_state") != "open":
            break

        filled_amount = float(order_status.get('filled_amount'))
        
        option_details = await tiger_client.get_ticker(params.instrument_name)
        if not option_details:
            continue

        best_bid = option_details.best_bid_price or 0.0
        best_ask = option_details.best_ask_price or 0.0
        if best_bid <= 0 or best_ask <= 0:
            continue

        new_price = _calculate_progressive_price(
            params.direction,
            params.initial_price,
            best_bid,
            best_ask,
            step,
            params.max_steps,
        )
        new_price = round_to_tick_size(new_price, params.tick_size)
        amount = float(order_status.get("amount") or params.quantity) - filled_amount

        progress = f"{step}/{params.max_steps}"

        # Log progressive price adjustment details
        logger.info(
            f"📈 Progressive limit price adjustment (progress {progress}, filled_amount={filled_amount})",
            order_id=params.order_id,
            instrument_name=params.instrument_name,
            direction=params.direction,
            step=step,
            max_steps=params.max_steps,
            initial_price=params.initial_price,
            new_price=new_price,
            amount=amount,
            best_bid=best_bid,
            best_ask=best_ask,
            tick_size=params.tick_size,
            progress=progress,
            filled_amount=filled_amount,
        )

        edit_result = await tiger_client.edit_order(
            params.account_name,
            params.order_id,
            amount,
            new_price,
        )
        if edit_result is None:
            # If edit failed, stop adjusting to avoid hammering the API.
            break

        last_price = new_price

    # Final adjustment to best price if still open
    final_status = await tiger_client.get_order_state(params.account_name, params.order_id)
    if final_status and final_status.get("order_state") == "open":
        option_details = await tiger_client.get_ticker(params.instrument_name)
        if option_details:
            best_bid = option_details.best_bid_price or last_price
            best_ask = option_details.best_ask_price or last_price
            final_price = best_ask if params.direction == 'buy' else best_bid
            final_price = round_to_tick_size(final_price, params.tick_size)
            amount = float(final_status.get("amount") or params.quantity)
            await tiger_client.edit_order(
                params.account_name,
                params.order_id,
                amount,
                final_price,
            )
            final_status = await tiger_client.get_order_state(params.account_name, params.order_id)
            last_price = final_price

    final_state = final_status.get("order_state") if final_status else None
    executed_quantity = final_status.get("filled_amount") if final_status else None
    average_price = final_status.get("average_price") if final_status else None
    success = bool(executed_quantity and executed_quantity > 0) or final_state in {"filled", "closed"}

    message = "Progressive strategy completed successfully" if success else "Progressive strategy completed"
    if not final_status:
        message = "Progressive strategy completed but final order state unavailable"

    # Collect light-weight position snapshot for observability
    try:
        open_orders = await tiger_client.get_open_orders_by_instrument(
            params.account_name,
            params.instrument_name,
        )
    except Exception:
        open_orders = []

    try:
        currency = params.instrument_name.split('-')[0]
        positions = await tiger_client.get_positions(params.account_name, currency=currency)
    except Exception:
        positions = []

    position_info: Dict[str, Any] = {
        "open_orders": open_orders,
        "positions": positions,
        "last_price": last_price,
        "attempts": attempt_count,
    }

    return ProgressiveLimitResult(
        success=success,
        order_id=params.order_id,
        final_order_state=final_state,
        executed_quantity=executed_quantity,
        average_price=average_price,
        attempt_count=attempt_count,
        message=message,
        order_type="limit",
        position_info=position_info,
    )


