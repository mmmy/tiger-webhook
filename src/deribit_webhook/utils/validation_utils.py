"""
Validation utilities
"""

import re
from typing import Optional, List
from decimal import Decimal, InvalidOperation


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol
    
    Args:
        symbol: Symbol to validate
        
    Returns:
        True if valid symbol
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Valid symbols: BTC, ETH, etc.
    valid_symbols = ['BTC', 'ETH', 'SOL', 'MATIC', 'ADA', 'DOT', 'AVAX', 'LINK']
    return symbol.upper() in valid_symbols


def validate_quantity(quantity: float, min_quantity: float = 0.0001, max_quantity: float = 1000000) -> bool:
    """
    Validate trading quantity
    
    Args:
        quantity: Quantity to validate
        min_quantity: Minimum allowed quantity
        max_quantity: Maximum allowed quantity
        
    Returns:
        True if valid quantity
    """
    if not isinstance(quantity, (int, float)):
        return False
    
    return min_quantity <= quantity <= max_quantity


def validate_price(price: float, min_price: float = 0.0001, max_price: float = 1000000) -> bool:
    """
    Validate price
    
    Args:
        price: Price to validate
        min_price: Minimum allowed price
        max_price: Maximum allowed price
        
    Returns:
        True if valid price
    """
    if not isinstance(price, (int, float)):
        return False
    
    return min_price <= price <= max_price


def validate_account_name(account_name: str) -> bool:
    """
    Validate account name format
    
    Args:
        account_name: Account name to validate
        
    Returns:
        True if valid account name
    """
    if not account_name or not isinstance(account_name, str):
        return False
    
    # Account name should be alphanumeric with underscores, 3-50 characters
    pattern = r'^[a-zA-Z0-9_]{3,50}$'
    return bool(re.match(pattern, account_name))


def is_valid_instrument_name(instrument_name: str) -> bool:
    """
    Validate Deribit instrument name format
    
    Args:
        instrument_name: Instrument name to validate
        
    Returns:
        True if valid instrument name
    """
    if not instrument_name or not isinstance(instrument_name, str):
        return False
    
    # Examples:
    # BTC-PERPETUAL
    # BTC-25DEC21
    # BTC-25DEC21-50000-C
    # BTC-25DEC21-50000-P
    
    parts = instrument_name.split('-')
    
    if len(parts) < 2:
        return False
    
    # First part should be a valid symbol
    if not validate_symbol(parts[0]):
        return False
    
    # Second part should be date or PERPETUAL
    if parts[1] == "PERPETUAL":
        return len(parts) == 2
    
    # For options, should have 4 parts: SYMBOL-DATE-STRIKE-TYPE
    if len(parts) == 4:
        # Validate strike price (should be numeric)
        try:
            float(parts[2])
        except ValueError:
            return False
        
        # Validate option type
        if parts[3] not in ['C', 'P']:
            return False
        
        return True
    
    # For futures, should have 2 parts: SYMBOL-DATE
    if len(parts) == 2:
        # Basic date format validation (not comprehensive)
        date_pattern = r'^\d{1,2}[A-Z]{3}\d{2}$'
        return bool(re.match(date_pattern, parts[1]))
    
    return False


def sanitize_string(input_string: str, max_length: int = 255) -> str:
    """
    Sanitize string input
    
    Args:
        input_string: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(input_string, str):
        return ""
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\';\\]', '', input_string)
    
    # Trim whitespace and limit length
    sanitized = sanitized.strip()[:max_length]
    
    return sanitized


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email to validate
        
    Returns:
        True if valid email format
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL format
    """
    if not url or not isinstance(url, str):
        return False
    
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_webhook_url(webhook_url: str) -> bool:
    """
    Validate WeChat webhook URL format
    
    Args:
        webhook_url: Webhook URL to validate
        
    Returns:
        True if valid webhook URL
    """
    if not validate_url(webhook_url):
        return False
    
    # Should be HTTPS and contain WeChat domain
    return (webhook_url.startswith('https://') and 
            'qyapi.weixin.qq.com' in webhook_url and 
            'webhook/send' in webhook_url)


def validate_decimal_precision(value: float, max_decimals: int = 8) -> bool:
    """
    Validate decimal precision
    
    Args:
        value: Value to validate
        max_decimals: Maximum allowed decimal places
        
    Returns:
        True if within precision limits
    """
    try:
        decimal_value = Decimal(str(value))
        _, digits, exponent = decimal_value.as_tuple()
        
        if exponent >= 0:
            return True  # No decimal places
        
        decimal_places = -exponent
        return decimal_places <= max_decimals
        
    except (InvalidOperation, ValueError):
        return False


def validate_trading_side(side: str) -> bool:
    """
    Validate trading side
    
    Args:
        side: Trading side to validate
        
    Returns:
        True if valid trading side
    """
    if not side or not isinstance(side, str):
        return False
    
    valid_sides = ['buy', 'sell', 'long', 'short']
    return side.lower() in valid_sides


def validate_order_type(order_type: str) -> bool:
    """
    Validate order type
    
    Args:
        order_type: Order type to validate
        
    Returns:
        True if valid order type
    """
    if not order_type or not isinstance(order_type, str):
        return False
    
    valid_types = ['market', 'limit', 'stop', 'stop_limit']
    return order_type.lower() in valid_types


def validate_time_in_force(tif: str) -> bool:
    """
    Validate time in force
    
    Args:
        tif: Time in force to validate
        
    Returns:
        True if valid time in force
    """
    if not tif or not isinstance(tif, str):
        return False
    
    valid_tifs = ['GTC', 'IOC', 'FOK']
    return tif.upper() in valid_tifs


def validate_positive_number(value: float) -> bool:
    """
    Validate that a number is positive
    
    Args:
        value: Value to validate
        
    Returns:
        True if positive number
    """
    return isinstance(value, (int, float)) and value > 0


def validate_non_negative_number(value: float) -> bool:
    """
    Validate that a number is non-negative
    
    Args:
        value: Value to validate
        
    Returns:
        True if non-negative number
    """
    return isinstance(value, (int, float)) and value >= 0


def validate_percentage(value: float) -> bool:
    """
    Validate percentage value (0-100)
    
    Args:
        value: Percentage value to validate
        
    Returns:
        True if valid percentage
    """
    return isinstance(value, (int, float)) and 0 <= value <= 100


def validate_list_not_empty(items: List) -> bool:
    """
    Validate that a list is not empty
    
    Args:
        items: List to validate
        
    Returns:
        True if list is not empty
    """
    return isinstance(items, list) and len(items) > 0
