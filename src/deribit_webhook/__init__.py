"""
Deribit Options Trading Microservice - Python Implementation

A comprehensive Python port of the Node.js/TypeScript Deribit webhook service,
maintaining 100% functionality while leveraging Python's ecosystem.
"""

from .config.config_loader import ConfigLoader  # noqa: F401
from .config.settings import settings  # noqa: F401

__version__ = "1.1.1"
__author__ = "Deribit Webhook Team"
__email__ = "support@example.com"

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "ConfigLoader",
    "settings",
]
