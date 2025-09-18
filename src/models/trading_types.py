"""
Trading-related type definitions
"""

from typing import Optional, Literal, Any, List
from pydantic import BaseModel, Field


# Option trading action types
OptionTradingAction = Literal[
    "open_long",     # 开多仓
    "open_short",    # 开空仓
    "close_long",    # 平多仓
    "close_short",   # 平空仓
    "reduce_long",   # 减多仓
    "reduce_short",  # 减空仓
    "stop_long",     # 止损多仓
    "stop_short"     # 止损空仓
]


class OptionTradingParams(BaseModel):
    """Option trading parameters interface"""
    account_name: str = Field(..., description="Account name")
    direction: Literal["buy", "sell"] = Field(..., description="Trading direction")
    action: OptionTradingAction = Field(..., description="Detailed trading action")
    symbol: str = Field(..., description="Original trading pair")
    quantity: float = Field(..., description="Trading quantity")
    price: Optional[float] = Field(default=None, description="Limit price (optional)")
    order_type: Literal["market", "limit"] = Field(..., description="Order type")
    instrument_name: Optional[str] = Field(default=None, description="Deribit option contract name")
    qty_type: Optional[Literal["fixed", "cash"]] = Field(default="fixed", description="Quantity type")
    delta1: Optional[float] = Field(default=None, description="Option Delta value for opening positions")
    delta2: Optional[float] = Field(default=None, description="Target Delta value for delta database")
    n: Optional[int] = Field(default=None, description="Minimum expiry days for option selection")
    tv_id: Optional[int] = Field(default=None, description="TradingView signal ID for delta database")
    close_ratio: Optional[float] = Field(default=None, description="Close ratio (0-1, 1 means full close)")


class PlaceOptionOrderParams(BaseModel):
    """Simplified option order parameters - only required for placeOptionOrder"""
    account_name: str = Field(..., description="Account name (required)")
    direction: Literal["buy", "sell"] = Field(..., description="Trading direction (required)")
    quantity: float = Field(..., description="Trading quantity (required)")
    action: OptionTradingAction = Field(..., description="Trading action (required, for notifications)")
    price: Optional[float] = Field(default=None, description="Limit price (optional, smart pricing if not provided)")
    qty_type: Optional[Literal["fixed", "cash"]] = Field(default="fixed", description="Quantity type (optional, default fixed)")
    delta2: Optional[float] = Field(default=None, description="Target Delta value (optional, for delta database)")


class DetailedPositionInfo(BaseModel):
    """Detailed position information"""
    related_orders: List[Any] = Field(default_factory=list, description="Related orders")
    total_open_orders: int = Field(default=0, description="Total open orders")
    positions: List[Any] = Field(default_factory=list, description="Positions")
    total_positions: int = Field(default=0, description="Total positions")
    execution_stats: Any = Field(default=None, description="Execution statistics")
    summary: Any = Field(default=None, description="Summary")
    metadata: Any = Field(default=None, description="Metadata")
    error: Optional[str] = Field(default=None, description="Error message")
    warnings: Optional[List[str]] = Field(default=None, description="Warning messages")


class OptionTradingResult(BaseModel):
    """Option trading result interface"""
    success: bool = Field(..., description="Whether the operation was successful")
    order_id: Optional[str] = Field(default=None, description="Order ID")
    message: str = Field(..., description="Result message")
    instrument_name: Optional[str] = Field(default=None, description="Instrument name")
    executed_quantity: Optional[float] = Field(default=None, description="Executed quantity")
    executed_price: Optional[float] = Field(default=None, description="Executed price")
    order_label: Optional[str] = Field(default=None, description="Order label")
    final_order_state: Optional[str] = Field(default=None, description="Final order state")
    position_info: Optional[DetailedPositionInfo] = Field(default=None, description="Detailed position information")
    error: Optional[str] = Field(default=None, description="Error message")


class PositionAdjustmentSummary(BaseModel):
    """Position adjustment summary"""
    old_size: float = Field(..., description="Old position size")
    old_delta: float = Field(..., description="Old delta")
    new_direction: Literal["buy", "sell"] = Field(..., description="New direction")
    new_quantity: float = Field(..., description="New quantity")
    target_delta: float = Field(..., description="Target delta")


class PositionAdjustmentResult(BaseModel):
    """Position adjustment result interface"""
    success: bool = Field(..., description="Whether the adjustment was successful")
    message: Optional[str] = Field(default=None, description="Result message")
    reason: Optional[str] = Field(default=None, description="Reason for adjustment")
    error: Optional[str] = Field(default=None, description="Error message")
    old_instrument: Optional[str] = Field(default=None, description="Old instrument name")
    new_instrument: Optional[str] = Field(default=None, description="New instrument name")
    adjustment_summary: Optional[PositionAdjustmentSummary] = Field(default=None, description="Adjustment summary")


class OptionListParams(BaseModel):
    """Option list query parameters interface"""
    underlying: str = Field(..., description="Option underlying (e.g., 'BTC', 'ETH')")
    direction: Literal["long", "short"] = Field(..., description="Direction: long (call) or short (put)")
    expired: Optional[bool] = Field(default=False, description="Include expired options")
    min_strike: Optional[float] = Field(default=None, description="Minimum strike price")
    max_strike: Optional[float] = Field(default=None, description="Maximum strike price")
    min_expiry: Optional[str] = Field(default=None, description="Minimum expiry time (ISO format)")
    max_expiry: Optional[str] = Field(default=None, description="Maximum expiry time (ISO format)")
