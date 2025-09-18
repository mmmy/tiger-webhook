"""
Utility functions module for Deribit Webhook Python

Provides common utility functions for price calculations, formatting, and data processing.
"""

from .price_utils import (
    correct_price,
    calculate_spread,
    format_price,
    round_to_tick_size,
    get_tick_size,
    calculate_mid_price
)
from .response_utils import (
    format_success_response,
    format_error_response,
    format_trading_response,
    format_position_response,
    create_request_id,
    get_timestamp
)
from .validation_utils import (
    validate_symbol,
    validate_quantity,
    validate_price,
    validate_account_name,
    is_valid_instrument_name,
    sanitize_string
)
from .calculation_utils import (
    calculate_option_delta,
    calculate_portfolio_delta,
    calculate_position_value,
    calculate_pnl,
    calculate_greeks_summary
)
from .spread_calculation import (
    calculate_spread_ratio,
    calculate_absolute_spread,
    calculate_mid_price,
    format_spread_ratio_as_percentage,
    calculate_spread_tick_multiple,
    is_spread_too_wide,
    is_spread_too_wide_by_ticks,
    is_spread_reasonable,
    get_spread_quality_description,
    get_spread_info,
    SpreadInfo
)
from .logging_config import (
    init_logging,
    get_logger,
    get_global_logger,
    setup_logging,
    debug,
    info,
    warning,
    error,
    critical
)

__all__ = [
    # Price utilities
    "correct_price",
    "calculate_spread",
    "format_price",
    "round_to_tick_size",
    "get_tick_size",
    "calculate_mid_price",
    
    # Response utilities
    "format_success_response",
    "format_error_response",
    "format_trading_response",
    "format_position_response",
    "create_request_id",
    "get_timestamp",
    
    # Validation utilities
    "validate_symbol",
    "validate_quantity",
    "validate_price",
    "validate_account_name",
    "is_valid_instrument_name",
    "sanitize_string",
    
    # Calculation utilities
    "calculate_option_delta",
    "calculate_portfolio_delta",
    "calculate_position_value",
    "calculate_pnl",
    "calculate_greeks_summary",

    # Spread calculation utilities
    "calculate_spread_ratio",
    "calculate_absolute_spread",
    "calculate_mid_price",
    "format_spread_ratio_as_percentage",
    "calculate_spread_tick_multiple",
    "is_spread_too_wide",
    "is_spread_too_wide_by_ticks",
    "is_spread_reasonable",
    "get_spread_quality_description",
    "get_spread_info",
    "SpreadInfo",

    # Logging utilities
    "init_logging",
    "get_logger",
    "get_global_logger",
    "setup_logging",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
]
