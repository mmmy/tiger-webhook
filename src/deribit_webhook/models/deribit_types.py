"""
Deribit API-related type definitions
"""

from typing import Optional, Literal, List, Any
from pydantic import BaseModel, Field


class DeribitOrder(BaseModel):
    """Deribit order interface"""
    order_id: str = Field(..., description="Order ID")
    instrument_name: str = Field(..., description="Contract name")
    direction: Literal["buy", "sell"] = Field(..., description="Order direction")
    amount: float = Field(..., description="Order amount")
    price: float = Field(..., description="Order price")
    order_type: Literal["limit", "market", "stop_limit", "stop_market"] = Field(..., description="Order type")
    order_state: Literal["open", "filled", "rejected", "cancelled", "untriggered"] = Field(..., description="Order state")
    filled_amount: Optional[float] = Field(default=None, description="Filled amount")
    average_price: Optional[float] = Field(default=None, description="Average fill price")
    creation_timestamp: int = Field(..., description="Creation timestamp")
    last_update_timestamp: int = Field(..., description="Last update timestamp")
    label: Optional[str] = Field(default=None, description="Order label")
    time_in_force: Optional[Literal["good_til_cancelled", "fill_or_kill", "immediate_or_cancel"]] = Field(
        default=None, description="Time in force"
    )
    post_only: Optional[bool] = Field(default=None, description="Post only flag")
    reduce_only: Optional[bool] = Field(default=None, description="Reduce only flag")
    trigger_price: Optional[float] = Field(default=None, description="Trigger price (stop orders)")
    commission: Optional[float] = Field(default=None, description="Commission")
    profit_loss: Optional[float] = Field(default=None, description="Profit/Loss")
    implv: Optional[float] = Field(default=None, description="Implied volatility")
    usd: Optional[float] = Field(default=None, description="USD value")
    api: Optional[bool] = Field(default=None, description="Created via API")
    mmp: Optional[bool] = Field(default=None, description="Market maker protection")


class DeribitPosition(BaseModel):
    """Deribit position information interface"""
    instrument_name: str = Field(..., description="Instrument name")
    size: float = Field(..., description="Position size (positive for long, negative for short)")
    size_currency: Optional[float] = Field(default=None, description="Position size in currency")
    direction: Literal["buy", "sell"] = Field(..., description="Position direction")
    average_price: float = Field(..., description="Average opening price")
    average_price_usd: Optional[float] = Field(default=None, description="Average opening price in USD")
    mark_price: float = Field(..., description="Mark price")
    index_price: Optional[float] = Field(default=None, description="Index price")
    estimated_liquidation_price: Optional[float] = Field(default=None, description="Estimated liquidation price")
    unrealized_pnl: float = Field(..., description="Unrealized PnL")
    realized_pnl: Optional[float] = Field(default=None, description="Realized PnL")
    total_profit_loss: float = Field(..., description="Total profit/loss")
    maintenance_margin: float = Field(..., description="Maintenance margin")
    initial_margin: float = Field(..., description="Initial margin")
    settlement_price: Optional[float] = Field(default=None, description="Settlement price")
    delta: Optional[float] = Field(default=None, description="Delta value (options)")
    gamma: Optional[float] = Field(default=None, description="Gamma value (options)")
    theta: Optional[float] = Field(default=None, description="Theta value (options)")
    vega: Optional[float] = Field(default=None, description="Vega value (options)")
    floating_profit_loss: Optional[float] = Field(default=None, description="Floating profit/loss")
    floating_profit_loss_usd: Optional[float] = Field(default=None, description="Floating profit/loss in USD")
    kind: Literal["option", "future", "spot"] = Field(..., description="Instrument type")
    leverage: Optional[float] = Field(default=None, description="Leverage")
    open_orders_margin: Optional[float] = Field(default=None, description="Open orders margin")
    interest_value: Optional[float] = Field(default=None, description="Interest value")


class TickSizeStep(BaseModel):
    """Tick size step interface - for tiered tick size rules"""
    above_price: float = Field(..., description="Price threshold")
    tick_size: float = Field(..., description="Corresponding tick size")


class DeribitOptionInstrument(BaseModel):
    """Deribit option instrument information interface"""
    instrument_name: str = Field(..., description="Option contract name (e.g., 'BTC-25JUL25-50000-C')")
    base_currency: str = Field(..., description="Base currency (e.g., 'BTC')")

    @property
    def currency(self) -> str:
        """Compatibility property for currency access"""
        return self.base_currency
    kind: str = Field(..., description="Instrument type ('option')")
    option_type: Literal["call", "put"] = Field(..., description="Option type: call or put")
    strike: float = Field(..., description="Strike price")
    expiration_timestamp: int = Field(..., description="Expiration timestamp (milliseconds)")
    tick_size: float = Field(..., description="Base minimum price increment")
    tick_size_steps: Optional[List[TickSizeStep]] = Field(default=None, description="Tiered tick size rules")
    min_trade_amount: float = Field(..., description="Minimum trade amount")
    contract_size: float = Field(..., description="Contract size")
    is_active: bool = Field(..., description="Whether active")
    settlement_period: str = Field(..., description="Settlement period")
    creation_timestamp: int = Field(..., description="Creation timestamp")
    quote_currency: str = Field(..., description="Quote currency")
    settlement_currency: Optional[str] = Field(None, description="Settlement currency")


class OptionGreeks(BaseModel):
    """Option Greeks interface"""
    delta: float = Field(..., description="Delta value")
    gamma: float = Field(..., description="Gamma value")
    theta: float = Field(..., description="Theta value")
    vega: float = Field(..., description="Vega value")
    rho: Optional[float] = Field(default=None, description="Rho value (optional)")


class OptionDetails(BaseModel):
    """Option detailed information interface (including Greeks and price info)"""
    instrument_name: str = Field(..., description="Option contract name")
    underlying_index: str = Field(..., description="Underlying index")
    underlying_price: float = Field(..., description="Underlying price")
    timestamp: int = Field(..., description="Timestamp")
    state: str = Field(..., description="State")
    settlement_price: Optional[float] = Field(None, description="Settlement price")
    open_interest: float = Field(..., description="Open interest")
    min_price: float = Field(..., description="Minimum price")
    max_price: float = Field(..., description="Maximum price")
    mark_price: float = Field(..., description="Mark price")
    mark_iv: float = Field(..., description="Mark implied volatility")
    last_price: float = Field(..., description="Last price")
    interest_rate: float = Field(..., description="Interest rate")
    instrument_type: Optional[str] = Field(None, description="Instrument type")
    index_price: float = Field(..., description="Index price")
    greeks: OptionGreeks = Field(..., description="Option Greeks")
    bid_iv: float = Field(..., description="Bid implied volatility")
    best_bid_price: float = Field(..., description="Best bid price")
    best_bid_amount: float = Field(..., description="Best bid amount")
    best_ask_price: float = Field(..., description="Best ask price")
    best_ask_amount: float = Field(..., description="Best ask amount")
    ask_iv: float = Field(..., description="Ask implied volatility")


class DeltaFilterResult(BaseModel):
    """Delta filter result interface"""
    instrument: DeribitOptionInstrument = Field(..., description="Option instrument info")
    details: OptionDetails = Field(..., description="Option detailed info")
    delta_distance: float = Field(..., description="Delta distance from target")
    spread_ratio: float = Field(..., description="Spread ratio")


class OptionListResult(BaseModel):
    """Option list query result interface"""
    success: bool = Field(..., description="Whether the query was successful")
    message: str = Field(..., description="Result message")
    data: Optional[dict] = Field(default=None, description="Result data")
    error: Optional[str] = Field(default=None, description="Error message")
    
    class OptionListData(BaseModel):
        """Option list data structure"""
        instruments: List[DeribitOptionInstrument] = Field(..., description="List of instruments")
        total: int = Field(..., description="Total count")
        filtered: int = Field(..., description="Filtered count")
        underlying: str = Field(..., description="Underlying asset")
        direction: Literal["long", "short"] = Field(..., description="Direction")


# Deribit order response types
class DeribitTrade(BaseModel):
    """Deribit trade information"""
    trade_id: str = Field(..., description="Trade ID")
    instrument_name: str = Field(..., description="Instrument name")
    order_id: str = Field(..., description="Order ID")
    direction: Literal["buy", "sell"] = Field(..., description="Trade direction")
    amount: float = Field(..., description="Trade amount")
    price: float = Field(..., description="Trade price")
    timestamp: int = Field(..., description="Trade timestamp")
    role: Literal["maker", "taker"] = Field(..., description="Trade role")
    fee: float = Field(..., description="Trade fee")
    fee_currency: str = Field(..., description="Fee currency")


class DeribitOrderResponse(BaseModel):
    """Deribit order response"""
    order: DeribitOrder = Field(..., description="Order information")
    trades: List[DeribitTrade] = Field(default_factory=list, description="Associated trades")
