"""
Database-related type definitions
"""

from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from models.trading_types import OptionTradingAction


class DeltaRecordType(str, Enum):
    """Delta record type enumeration"""
    POSITION = "position"  # Position
    ORDER = "order"        # Unfilled order


class DeltaRecord(BaseModel):
    """Delta record interface"""
    id: Optional[int] = Field(default=None, description="Auto-increment primary key")
    account_id: str = Field(..., description="Account ID")
    instrument_name: str = Field(..., description="Contract name (e.g., BTC-8AUG25-113000-C)")
    order_id: Optional[str] = Field(default=None, description="Order ID (null for positions)")
    target_delta: float = Field(..., description="Target Delta value (-1 to 1)", ge=-1, le=1)
    move_position_delta: float = Field(default=0, description="Move position Delta value (-1 to 1)", ge=-1, le=1)
    min_expire_days: Optional[int] = Field(default=None, description="Minimum expiry days (positive integer, can be null)")
    tv_id: Optional[int] = Field(default=None, description="TradingView signal ID (optional)")
    action: Optional[OptionTradingAction] = Field(default=None, description="Trading action (optional)")
    record_type: DeltaRecordType = Field(..., description="Record type")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")


class CreateDeltaRecordInput(BaseModel):
    """Input parameters for creating Delta record"""
    account_id: str = Field(..., description="Account ID")
    instrument_name: str = Field(..., description="Contract name")
    order_id: Optional[str] = Field(default=None, description="Order ID")
    target_delta: float = Field(..., description="Target Delta value", ge=-1, le=1)
    move_position_delta: float = Field(default=0, description="Move position Delta value", ge=-1, le=1)
    min_expire_days: Optional[int] = Field(default=None, description="Minimum expiry days")
    tv_id: Optional[int] = Field(default=None, description="TradingView signal ID")
    action: Optional[OptionTradingAction] = Field(default=None, description="Trading action")
    record_type: DeltaRecordType = Field(..., description="Record type")


class UpdateDeltaRecordInput(BaseModel):
    """Input parameters for updating Delta record"""
    target_delta: Optional[float] = Field(default=None, description="Target Delta value", ge=-1, le=1)
    move_position_delta: Optional[float] = Field(default=None, description="Move position Delta value", ge=-1, le=1)
    min_expire_days: Optional[int] = Field(default=None, description="Minimum expiry days")
    order_id: Optional[str] = Field(default=None, description="Order ID")
    tv_id: Optional[int] = Field(default=None, description="TradingView signal ID")
    action: Optional[OptionTradingAction] = Field(default=None, description="Trading action")


class DeltaRecordQuery(BaseModel):
    """Query conditions interface"""
    account_id: Optional[str] = Field(default=None, description="Account ID")
    instrument_name: Optional[str] = Field(default=None, description="Contract name")
    order_id: Optional[str] = Field(default=None, description="Order ID")
    tv_id: Optional[int] = Field(default=None, description="TradingView signal ID")
    action: Optional[OptionTradingAction] = Field(default=None, description="Trading action")
    record_type: Optional[DeltaRecordType] = Field(default=None, description="Record type")


class DeltaRecordStats(BaseModel):
    """Database statistics information"""
    total_records: int = Field(..., description="Total records")
    position_records: int = Field(..., description="Position records")
    order_records: int = Field(..., description="Order records")
    accounts: List[str] = Field(..., description="Account list")
    instruments: List[str] = Field(..., description="Instrument list")


class AccountDeltaSummary(BaseModel):
    """Delta summary grouped by account"""
    account_id: str = Field(..., description="Account ID")
    total_delta: float = Field(..., description="Total Delta")
    position_delta: float = Field(..., description="Position Delta")
    order_delta: float = Field(..., description="Order Delta")
    record_count: int = Field(..., description="Record count")


class InstrumentDeltaSummary(BaseModel):
    """Delta summary grouped by instrument"""
    instrument_name: str = Field(..., description="Instrument name")
    total_delta: float = Field(..., description="Total Delta")
    position_delta: float = Field(..., description="Position Delta")
    order_delta: float = Field(..., description="Order Delta")
    record_count: int = Field(..., description="Record count")
    accounts: List[str] = Field(..., description="Account list")
