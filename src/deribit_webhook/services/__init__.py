"""
Services module for Tiger Brokers Trading System

Provides core business logic services including authentication, trading, and API clients.
"""

from .auth_service import AuthenticationService
from .authentication_errors import (
    AuthenticationError,
    TokenExpiredError,
    TokenNotFoundError,
    AuthenticationResult
)
from .tiger_client import TigerClient
from .trading_client_factory import TradingClientFactory, get_trading_client
from .option_service import OptionService
from .option_trading_service import OptionTradingService
from .wechat_notification import wechat_notification_service
from .progressive_limit_strategy import ProgressiveLimitParams, execute_progressive_limit_strategy
from .polling_manager import polling_manager
from .background_tasks import background_task_manager

__all__ = [
    "AuthenticationService",
    "AuthenticationError",
    "TokenExpiredError",
    "TokenNotFoundError",
    "AuthenticationResult",
    "TigerClient",
    "TradingClientFactory",
    "get_trading_client",
    "OptionService",
    "OptionTradingService",
    "ProgressiveLimitParams",
    "execute_progressive_limit_strategy",
    "wechat_notification_service",
    "polling_manager",
    "background_task_manager",
]
