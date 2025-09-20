"""
Routes module for Deribit Webhook Python

Provides FastAPI routers for all REST endpoints.
"""

from .health import health_router
from .webhook import webhook_router
from .trading import trading_router
from .auth import auth_router
from .delta import delta_router
from .positions import positions_router
from .wechat import wechat_router
from .logs import logs_router
from .accounts import accounts_router

__all__ = [
    "health_router",
    "webhook_router",
    "trading_router",
    "auth_router",
    "delta_router",
    "positions_router",
    "wechat_router",
    "logs_router",
    "accounts_router",
]
