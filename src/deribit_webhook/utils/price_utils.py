"""
Price calculation and formatting utilities
"""

import math
from typing import Optional, Dict, Any, List
from decimal import Decimal, ROUND_HALF_UP


def correct_price(price: float, tick_size: float = 0.0005) -> float:
    """
    Correct price to valid tick size
    
    Args:
        price: Original price
        tick_size: Minimum tick size (default: 0.0005 for options)
        
    Returns:
        Corrected price rounded to tick size
    """
    if price <= 0:
        return tick_size
    
    # Round to nearest tick
    ticks = round(price / tick_size)
    corrected_price = ticks * tick_size
    
    # Ensure minimum tick size
    if corrected_price < tick_size:
        corrected_price = tick_size
    
    return round(corrected_price, 4)


def calculate_spread(bid: float, ask: float) -> Dict[str, float]:
    """
    Calculate bid-ask spread information
    
    Args:
        bid: Bid price
        ask: Ask price
        
    Returns:
        Dictionary with spread information
    """
    if bid <= 0 or ask <= 0 or ask <= bid:
        return {
            "spread": 0.0,
            "spread_percentage": 0.0,
            "mid_price": 0.0,
            "valid": False
        }
    
    spread = ask - bid
    mid_price = (bid + ask) / 2
    spread_percentage = (spread / mid_price) * 100 if mid_price > 0 else 0.0
    
    return {
        "spread": round(spread, 4),
        "spread_percentage": round(spread_percentage, 2),
        "mid_price": round(mid_price, 4),
        "valid": True
    }


def format_price(price: float, decimals: int = 4) -> str:
    """
    Format price for display
    
    Args:
        price: Price to format
        decimals: Number of decimal places
        
    Returns:
        Formatted price string
    """
    if price == 0:
        return "0.0000"
    
    return f"{price:.{decimals}f}"


def round_to_tick_size(value: float, tick_size: float) -> float:
    """
    Round value to nearest tick size
    
    Args:
        value: Value to round
        tick_size: Tick size
        
    Returns:
        Rounded value
    """
    if tick_size <= 0:
        return value
    
    return round(round(value / tick_size) * tick_size, 8)


def get_tick_size(instrument_name: str) -> float:
    """
    Get tick size for instrument
    
    Args:
        instrument_name: Deribit instrument name
        
    Returns:
        Tick size for the instrument
    """
    # Default tick sizes for different instrument types
    if "-" in instrument_name:
        parts = instrument_name.split("-")
        if len(parts) >= 3:
            # Option instrument (e.g., BTC-25DEC21-50000-C)
            return 0.0005
        elif len(parts) == 2:
            # Future instrument (e.g., BTC-25DEC21)
            return 0.5
    
    # Perpetual or spot (e.g., BTC-PERPETUAL)
    if "PERPETUAL" in instrument_name:
        return 0.5
    
    # Default tick size
    return 0.0005


def calculate_mid_price(bid: float, ask: float) -> Optional[float]:
    """
    Calculate mid price from bid and ask
    
    Args:
        bid: Bid price
        ask: Ask price
        
    Returns:
        Mid price or None if invalid
    """
    if bid <= 0 or ask <= 0 or ask <= bid:
        return None
    
    return round((bid + ask) / 2, 4)


def calculate_mark_price_adjustment(
    mark_price: float,
    bid: float,
    ask: float,
    adjustment_factor: float = 0.1
) -> float:
    """
    Calculate adjusted mark price based on bid-ask spread
    
    Args:
        mark_price: Current mark price
        bid: Bid price
        ask: Ask price
        adjustment_factor: Adjustment factor (0.0 to 1.0)
        
    Returns:
        Adjusted mark price
    """
    if bid <= 0 or ask <= 0 or ask <= bid:
        return mark_price
    
    mid_price = (bid + ask) / 2
    
    # If mark price is outside bid-ask range, adjust towards mid
    if mark_price < bid:
        adjustment = (mid_price - mark_price) * adjustment_factor
        return mark_price + adjustment
    elif mark_price > ask:
        adjustment = (mark_price - mid_price) * adjustment_factor
        return mark_price - adjustment
    
    # Mark price is within range, no adjustment needed
    return mark_price


def calculate_option_fair_value(
    underlying_price: float,
    strike_price: float,
    time_to_expiry: float,
    volatility: float,
    risk_free_rate: float = 0.0,
    option_type: str = "call"
) -> float:
    """
    Calculate Black-Scholes option fair value (simplified)
    
    Args:
        underlying_price: Current underlying price
        strike_price: Option strike price
        time_to_expiry: Time to expiry in years
        volatility: Implied volatility (as decimal, e.g., 0.2 for 20%)
        risk_free_rate: Risk-free rate (as decimal)
        option_type: "call" or "put"
        
    Returns:
        Theoretical option value
    """
    if time_to_expiry <= 0:
        # At expiry, option value is intrinsic value
        if option_type.lower() == "call":
            return max(0, underlying_price - strike_price)
        else:
            return max(0, strike_price - underlying_price)
    
    # Simplified Black-Scholes approximation
    # This is a basic implementation - in production, use a proper BS library
    try:
        from math import log, sqrt, exp
        from scipy.stats import norm
        
        d1 = (log(underlying_price / strike_price) + 
              (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * sqrt(time_to_expiry))
        d2 = d1 - volatility * sqrt(time_to_expiry)
        
        if option_type.lower() == "call":
            value = (underlying_price * norm.cdf(d1) - 
                    strike_price * exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2))
        else:
            value = (strike_price * exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - 
                    underlying_price * norm.cdf(-d1))
        
        return max(0, value)
        
    except ImportError:
        # Fallback to intrinsic value if scipy not available
        if option_type.lower() == "call":
            return max(0, underlying_price - strike_price)
        else:
            return max(0, strike_price - underlying_price)


def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """
    Format amount as currency
    
    Args:
        amount: Amount to format
        currency: Currency code
        decimals: Number of decimal places
        
    Returns:
        Formatted currency string
    """
    if currency.upper() == "BTC":
        return f"{amount:.8f} BTC"
    elif currency.upper() == "ETH":
        return f"{amount:.6f} ETH"
    else:
        return f"${amount:,.{decimals}f}"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    
    return ((new_value - old_value) / old_value) * 100


def correct_order_amount(amount: float, min_amount: float = 1.0) -> float:
    """
    Correct order amount to valid minimum

    Args:
        amount: Original amount
        min_amount: Minimum order amount (default: 1.0)

    Returns:
        Corrected amount
    """
    if amount <= 0:
        return 0.0

    # Ensure minimum amount
    if amount < min_amount:
        return min_amount

    # Round to integer for option contracts
    return float(int(amount))


def correct_smart_price(price: float, market_price: float, tick_size: float = 0.0005, max_deviation: float = 0.1) -> float:
    """
    Smart price correction with market price validation

    Args:
        price: Original price
        market_price: Current market price
        tick_size: Minimum price increment
        max_deviation: Maximum allowed deviation from market price (10%)

    Returns:
        Corrected and validated price
    """
    if price <= 0 or market_price <= 0:
        return correct_price(market_price, tick_size)

    # Check if price is within reasonable range of market price
    deviation = abs(price - market_price) / market_price

    if deviation > max_deviation:
        # If price deviates too much, use market price
        corrected_price = market_price
    else:
        corrected_price = price

    return correct_price(corrected_price, tick_size)
