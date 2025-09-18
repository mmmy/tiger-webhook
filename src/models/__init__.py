"""
Type definitions for Deribit Webhook Python

Provides Pydantic models and type definitions equivalent to the original TypeScript interfaces.
"""

from .config_types import *
from .auth_types import *
from .webhook_types import *
from .trading_types import *
from .deribit_types import *

__all__ = [
    # Config types
    "ApiKeyConfig",
    "GlobalSettings", 
    "DeribitConfig",
    "WeChatBotConfig",
    
    # Auth types
    "DeribitAuthResult",
    "AuthResponse",
    "DeribitError",
    "AuthToken",
    "DeribitGrantType",
    "DeribitScope",
    "DeribitAuthParams",
    
    # Webhook types
    "WebhookSignalPayload",
    "WebhookResponse",
    
    # Trading types
    "OptionTradingAction",
    "OptionTradingParams",
    "PlaceOptionOrderParams",
    "OptionTradingResult",
    "PositionAdjustmentResult",
    
    # Deribit types
    "DeribitOrder",
    "DeribitPosition",
    "DeribitOptionInstrument",
    "OptionDetails",
    "OptionGreeks",
    "DeltaFilterResult",
    "TickSizeStep",
    "OptionListParams",
    "OptionListResult",
    "DetailedPositionInfo",
]
