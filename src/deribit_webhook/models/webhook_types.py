"""
Webhook-related type definitions
"""

from typing import Optional, Literal, Any
from pydantic import BaseModel, Field


class WebhookSignalPayload(BaseModel):
    """TradingView webhook signal payload"""
    account_name: str = Field(..., alias="accountName", description="Account name from apikeys configuration")
    side: str = Field(..., description="Trading direction: buy/sell")
    exchange: str = Field(..., description="Exchange name")
    period: str = Field(..., description="K-line period")
    market_position: str = Field(..., alias="marketPosition", description="Current market position: long/short/flat")
    prev_market_position: str = Field(..., alias="prevMarketPosition", description="Previous market position")
    symbol: str = Field(..., description="Trading pair symbol")
    price: str = Field(..., description="Current price")
    timestamp: str = Field(..., description="Timestamp")
    size: str = Field(..., description="Order quantity/contracts")
    position_size: str = Field(..., alias="positionSize", description="Current position size")
    id: str = Field(..., description="Strategy order ID")
    tv_id: int = Field(..., description="TradingView signal ID")
    alert_message: Optional[str] = Field(default=None, alias="alertMessage", description="Alert message")
    comment: Optional[str] = Field(default=None, description="Comment")
    qty_type: Literal["fixed", "cash"] = Field(..., alias="qtyType", description="Quantity type")
    delta1: Optional[float] = Field(default=None, description="Option Delta value for opening positions")
    n: Optional[int] = Field(default=None, description="Minimum expiry days for option selection")
    delta2: Optional[float] = Field(default=None, description="Target Delta value for delta database recording")
    
    class Config:
        allow_population_by_field_name = True


class WebhookResponse(BaseModel):
    """Webhook response interface"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: str = Field(..., description="Response timestamp")
    request_id: Optional[str] = Field(default=None, alias="requestId", description="Request ID for tracking")
    
    class Config:
        allow_population_by_field_name = True
