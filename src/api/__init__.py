"""
Deribit API module

Provides unified access to Deribit public and private API endpoints.
"""

from .deribit_public import DeribitPublicAPI, create_deribit_public_api
from .deribit_private import DeribitPrivateAPI, create_deribit_private_api, AuthInfo
from .config import DeribitConfig, DERIBIT_CONFIGS, get_config_by_environment, create_auth_info

__all__ = [
    "DeribitPublicAPI",
    "DeribitPrivateAPI", 
    "create_deribit_public_api",
    "create_deribit_private_api",
    "AuthInfo",
    "DeribitConfig",
    "DERIBIT_CONFIGS",
    "get_config_by_environment",
    "create_auth_info",
]
