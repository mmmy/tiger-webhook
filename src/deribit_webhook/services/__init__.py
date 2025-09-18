"""
Services module for Deribit Webhook Python

Provides core business logic services including authentication, trading, and API clients.
"""

from .auth_service import DeribitAuth, AuthenticationService
from .authentication_errors import (
    AuthenticationError,
    TokenExpiredError,
    TokenNotFoundError,
    AuthenticationResult
)
from .deribit_client import DeribitClient
from .mock_deribit_client import MockDeribitClient
from .option_service import OptionService
from .option_trading_service import OptionTradingService
from .wechat_notification import wechat_notification_service
from .progressive_limit_strategy import ProgressiveLimitParams, execute_progressive_limit_strategy
from .polling_manager import polling_manager
from .background_tasks import background_task_manager

__all__ = [
    "DeribitAuth",
    "AuthenticationService",
    "AuthenticationError",
    "TokenExpiredError",
    "TokenNotFoundError",
    "AuthenticationResult",
    "DeribitClient",
    "MockDeribitClient",
    "OptionService",
    "OptionTradingService",
    "ProgressiveLimitParams",
    "execute_progressive_limit_strategy",
    "wechat_notification_service",
    "polling_manager",
    "background_task_manager",
]
