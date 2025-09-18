"""
Calculation utilities for options and portfolio management
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta


def calculate_option_delta(
    position_size: float,
    option_delta: float
) -> float:
    """
    Calculate position delta
    
    Args:
        position_size: Size of the position
        option_delta: Delta of the option
        
    Returns:
        Position delta
    """
    return position_size * option_delta


def calculate_portfolio_delta(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate portfolio Greeks from positions
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        Dictionary with portfolio Greeks
    """
    total_delta = 0.0
    total_gamma = 0.0
    total_theta = 0.0
    total_vega = 0.0
    option_count = 0
    
    for position in positions:
        if position.get("kind") == "option":
            size = position.get("size", 0.0)
            delta = position.get("delta", 0.0)
            gamma = position.get("gamma", 0.0)
            theta = position.get("theta", 0.0)
            vega = position.get("vega", 0.0)
            
            total_delta += size * delta
            total_gamma += size * gamma
            total_theta += size * theta
            total_vega += size * vega
            option_count += 1
    
    return {
        "delta": round(total_delta, 4),
        "gamma": round(total_gamma, 4),
        "theta": round(total_theta, 4),
        "vega": round(total_vega, 4),
        "option_count": option_count
    }


def calculate_position_value(
    position_size: float,
    mark_price: float,
    multiplier: float = 1.0
) -> float:
    """
    Calculate position value
    
    Args:
        position_size: Size of the position
        mark_price: Current mark price
        multiplier: Contract multiplier
        
    Returns:
        Position value
    """
    return position_size * mark_price * multiplier


def calculate_pnl(
    position_size: float,
    entry_price: float,
    current_price: float,
    multiplier: float = 1.0
) -> Dict[str, float]:
    """
    Calculate profit and loss
    
    Args:
        position_size: Size of the position
        entry_price: Entry price
        current_price: Current price
        multiplier: Contract multiplier
        
    Returns:
        Dictionary with PnL information
    """
    if entry_price <= 0:
        return {
            "unrealized_pnl": 0.0,
            "pnl_percentage": 0.0,
            "valid": False
        }
    
    price_diff = current_price - entry_price
    unrealized_pnl = position_size * price_diff * multiplier
    pnl_percentage = (price_diff / entry_price) * 100
    
    return {
        "unrealized_pnl": round(unrealized_pnl, 4),
        "pnl_percentage": round(pnl_percentage, 2),
        "valid": True
    }


def calculate_greeks_summary(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate comprehensive Greeks summary
    
    Args:
        positions: List of position dictionaries
        
    Returns:
        Comprehensive Greeks summary
    """
    portfolio_greeks = calculate_portfolio_delta(positions)
    
    # Calculate additional metrics
    total_notional = 0.0
    total_premium = 0.0
    long_positions = 0
    short_positions = 0
    
    for position in positions:
        if position.get("kind") == "option":
            size = position.get("size", 0.0)
            mark_price = position.get("mark_price", 0.0)
            
            notional = abs(size) * mark_price
            total_notional += notional
            total_premium += size * mark_price
            
            if size > 0:
                long_positions += 1
            elif size < 0:
                short_positions += 1
    
    return {
        "greeks": portfolio_greeks,
        "summary": {
            "total_notional": round(total_notional, 4),
            "total_premium": round(total_premium, 4),
            "long_positions": long_positions,
            "short_positions": short_positions,
            "net_positions": long_positions - short_positions
        }
    }


def calculate_implied_volatility_change_impact(
    vega: float,
    iv_change: float
) -> float:
    """
    Calculate impact of implied volatility change
    
    Args:
        vega: Position vega
        iv_change: Change in implied volatility (in percentage points)
        
    Returns:
        Impact on position value
    """
    return vega * (iv_change / 100)


def calculate_time_decay_impact(
    theta: float,
    days: float = 1.0
) -> float:
    """
    Calculate time decay impact
    
    Args:
        theta: Position theta
        days: Number of days
        
    Returns:
        Time decay impact
    """
    return theta * days


def calculate_delta_hedge_ratio(
    portfolio_delta: float,
    underlying_delta: float = 1.0
) -> float:
    """
    Calculate hedge ratio for delta neutrality
    
    Args:
        portfolio_delta: Current portfolio delta
        underlying_delta: Delta of underlying (usually 1.0)
        
    Returns:
        Hedge ratio (negative of portfolio delta / underlying delta)
    """
    if underlying_delta == 0:
        return 0.0
    
    return -portfolio_delta / underlying_delta


def calculate_option_moneyness(
    underlying_price: float,
    strike_price: float,
    option_type: str = "call"
) -> Dict[str, Any]:
    """
    Calculate option moneyness
    
    Args:
        underlying_price: Current underlying price
        strike_price: Option strike price
        option_type: "call" or "put"
        
    Returns:
        Moneyness information
    """
    if strike_price <= 0:
        return {"valid": False}
    
    moneyness_ratio = underlying_price / strike_price
    
    if option_type.lower() == "call":
        intrinsic_value = max(0, underlying_price - strike_price)
        if moneyness_ratio > 1.0:
            moneyness = "ITM"  # In the money
        elif moneyness_ratio == 1.0:
            moneyness = "ATM"  # At the money
        else:
            moneyness = "OTM"  # Out of the money
    else:  # put
        intrinsic_value = max(0, strike_price - underlying_price)
        if moneyness_ratio < 1.0:
            moneyness = "ITM"
        elif moneyness_ratio == 1.0:
            moneyness = "ATM"
        else:
            moneyness = "OTM"
    
    return {
        "moneyness": moneyness,
        "moneyness_ratio": round(moneyness_ratio, 4),
        "intrinsic_value": round(intrinsic_value, 4),
        "valid": True
    }


def calculate_time_to_expiry(expiry_timestamp: int) -> Dict[str, float]:
    """
    Calculate time to expiry
    
    Args:
        expiry_timestamp: Expiry timestamp in milliseconds
        
    Returns:
        Time to expiry information
    """
    try:
        expiry_date = datetime.fromtimestamp(expiry_timestamp / 1000)
        current_date = datetime.now()
        
        if expiry_date <= current_date:
            return {
                "days": 0.0,
                "hours": 0.0,
                "years": 0.0,
                "expired": True
            }
        
        time_diff = expiry_date - current_date
        days = time_diff.total_seconds() / (24 * 3600)
        hours = time_diff.total_seconds() / 3600
        years = days / 365.25
        
        return {
            "days": round(days, 2),
            "hours": round(hours, 2),
            "years": round(years, 4),
            "expired": False
        }
        
    except (ValueError, OSError):
        return {
            "days": 0.0,
            "hours": 0.0,
            "years": 0.0,
            "expired": True
        }


def calculate_break_even_points(
    strike_price: float,
    premium: float,
    option_type: str = "call"
) -> Dict[str, Any]:
    """
    Calculate break-even points for options
    
    Args:
        strike_price: Option strike price
        premium: Option premium paid
        option_type: "call" or "put"
        
    Returns:
        Break-even information
    """
    if option_type.lower() == "call":
        break_even = strike_price + premium
    else:  # put
        break_even = strike_price - premium
    
    return {
        "break_even_price": round(break_even, 4),
        "option_type": option_type.lower(),
        "strike_price": strike_price,
        "premium": premium
    }


def calculate_max_profit_loss(
    position_size: float,
    strike_price: float,
    premium: float,
    option_type: str = "call",
    position_type: str = "long"
) -> Dict[str, Any]:
    """
    Calculate maximum profit and loss for option position
    
    Args:
        position_size: Size of position
        strike_price: Option strike price
        premium: Option premium
        option_type: "call" or "put"
        position_type: "long" or "short"
        
    Returns:
        Max profit/loss information
    """
    premium_total = abs(position_size) * premium
    
    if position_type.lower() == "long":
        if option_type.lower() == "call":
            max_loss = premium_total
            max_profit = float('inf')  # Unlimited
        else:  # put
            max_loss = premium_total
            max_profit = (strike_price * abs(position_size)) - premium_total
    else:  # short
        if option_type.lower() == "call":
            max_profit = premium_total
            max_loss = float('inf')  # Unlimited
        else:  # put
            max_profit = premium_total
            max_loss = (strike_price * abs(position_size)) - premium_total
    
    return {
        "max_profit": max_profit if max_profit != float('inf') else "Unlimited",
        "max_loss": max_loss if max_loss != float('inf') else "Unlimited",
        "premium_total": round(premium_total, 4)
    }
