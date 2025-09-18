"""
Deribit Options Trading Microservice - Python Implementation

A comprehensive Python port of the Node.js/TypeScript Deribit webhook service,
maintaining 100% functionality while leveraging Python's ecosystem.
"""

__version__ = "1.1.1"
__author__ = "Deribit Webhook Team"
__email__ = "support@example.com"

# Core exports
from config import ConfigLoader
from types import *
from services import *

__all__ = [
    "__version__",
    "__author__", 
    "__email__",
    "ConfigLoader",
]
