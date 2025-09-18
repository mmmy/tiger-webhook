"""
Response formatting utilities
"""

import time
import random
import string
from typing import Dict, Any, Optional, List
from datetime import datetime

from deribit_webhook.models.trading_types import OptionTradingResult


def create_request_id() -> str:
    """
    Generate unique request ID
    
    Returns:
        Unique request ID string
    """
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
    return f"req_{timestamp}_{random_suffix}"


def get_timestamp() -> str:
    """
    Get current timestamp in ISO format
    
    Returns:
        ISO formatted timestamp
    """
    return datetime.now().isoformat()


def format_success_response(
    message: str,
    data: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format standard success response
    
    Args:
        message: Success message
        data: Optional data payload
        request_id: Optional request ID
        
    Returns:
        Formatted success response
    """
    response = {
        "success": True,
        "message": message,
        "timestamp": get_timestamp()
    }
    
    if data is not None:
        response["data"] = data
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def format_error_response(
    message: str,
    error: Optional[str] = None,
    code: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format standard error response
    
    Args:
        message: Error message
        error: Optional detailed error
        code: Optional error code
        request_id: Optional request ID
        
    Returns:
        Formatted error response
    """
    response = {
        "success": False,
        "message": message,
        "timestamp": get_timestamp()
    }
    
    if error:
        response["error"] = error
    
    if code:
        response["code"] = code
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def format_trading_response(
    trading_result: OptionTradingResult,
    request_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format trading response from OptionTradingResult
    
    Args:
        trading_result: Trading result object
        request_id: Optional request ID
        additional_data: Optional additional data
        
    Returns:
        Formatted trading response
    """
    response = {
        "success": trading_result.success,
        "message": trading_result.message,
        "timestamp": get_timestamp()
    }
    
    if trading_result.success:
        # Success response with trading details
        if trading_result.order_id:
            response["order_id"] = trading_result.order_id
        
        if trading_result.instrument_name:
            response["instrument_name"] = trading_result.instrument_name
        
        if trading_result.executed_quantity is not None:
            response["executed_quantity"] = trading_result.executed_quantity
        
        if trading_result.executed_price is not None:
            response["executed_price"] = trading_result.executed_price
        
        if trading_result.order_label:
            response["order_label"] = trading_result.order_label
        
        if trading_result.final_order_state:
            response["final_order_state"] = trading_result.final_order_state
    else:
        # Error response
        if trading_result.error:
            response["error"] = trading_result.error
    
    if request_id:
        response["request_id"] = request_id
    
    if additional_data:
        response.update(additional_data)
    
    return response


def format_position_response(
    account_name: str,
    currency: str,
    positions: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
    mock_mode: bool = False,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format position response
    
    Args:
        account_name: Account name
        currency: Currency
        positions: List of positions
        summary: Optional account summary
        mock_mode: Whether in mock mode
        request_id: Optional request ID
        
    Returns:
        Formatted position response
    """
    response = {
        "success": True,
        "message": f"Retrieved {len(positions)} positions for {account_name}",
        "account_name": account_name,
        "currency": currency,
        "mock_mode": mock_mode,
        "positions": positions,
        "timestamp": get_timestamp()
    }
    
    if summary:
        response["summary"] = summary
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def format_delta_response(
    account_name: str,
    currency: str,
    total_delta: float,
    total_gamma: float = 0.0,
    total_theta: float = 0.0,
    total_vega: float = 0.0,
    position_count: int = 0,
    mock_mode: bool = False,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format delta calculation response
    
    Args:
        account_name: Account name
        currency: Currency
        total_delta: Total portfolio delta
        total_gamma: Total portfolio gamma
        total_theta: Total portfolio theta
        total_vega: Total portfolio vega
        position_count: Number of positions
        mock_mode: Whether in mock mode
        request_id: Optional request ID
        
    Returns:
        Formatted delta response
    """
    response = {
        "success": True,
        "message": f"Calculated delta for {account_name}",
        "account_name": account_name,
        "currency": currency,
        "mock_mode": mock_mode,
        "greeks": {
            "delta": round(total_delta, 4),
            "gamma": round(total_gamma, 4),
            "theta": round(total_theta, 4),
            "vega": round(total_vega, 4)
        },
        "position_count": position_count,
        "timestamp": get_timestamp()
    }
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def format_health_response(
    service_name: str,
    version: str,
    status: str = "healthy",
    additional_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format health check response
    
    Args:
        service_name: Service name
        version: Service version
        status: Health status
        additional_info: Optional additional information
        
    Returns:
        Formatted health response
    """
    response = {
        "service": service_name,
        "version": version,
        "status": status,
        "timestamp": get_timestamp()
    }
    
    if additional_info:
        response.update(additional_info)
    
    return response


def format_pagination_response(
    data: List[Any],
    page: int,
    page_size: int,
    total_count: int,
    message: str = "Data retrieved successfully"
) -> Dict[str, Any]:
    """
    Format paginated response
    
    Args:
        data: Data items for current page
        page: Current page number (1-based)
        page_size: Items per page
        total_count: Total number of items
        message: Response message
        
    Returns:
        Formatted paginated response
    """
    total_pages = (total_count + page_size - 1) // page_size
    
    return {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        },
        "timestamp": get_timestamp()
    }


def sanitize_response_data(data: Any) -> Any:
    """
    Sanitize response data by removing sensitive information
    
    Args:
        data: Data to sanitize
        
    Returns:
        Sanitized data
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Remove sensitive keys
            if key.lower() in ['password', 'secret', 'token', 'key', 'client_secret']:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = sanitize_response_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_response_data(item) for item in data]
    else:
        return data
