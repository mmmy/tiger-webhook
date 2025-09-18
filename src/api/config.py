"""
Deribit API configuration and utilities
"""

from typing import Optional
from pydantic import BaseModel, Field


class DeribitConfig(BaseModel):
    """Deribit API configuration"""
    base_url: str = Field(..., description="API base URL")
    timeout: float = Field(default=15.0, description="Request timeout in seconds")


class AuthInfo(BaseModel):
    """Authentication information for private API"""
    access_token: str = Field(..., description="Access token")
    token_type: str = Field(default="Bearer", description="Token type")


# Common configuration presets
DERIBIT_CONFIGS = {
    "PRODUCTION": DeribitConfig(
        base_url="https://www.deribit.com/api/v2",
        timeout=15.0
    ),
    "TEST": DeribitConfig(
        base_url="https://test.deribit.com/api/v2",
        timeout=15.0
    )
}


def create_auth_info(access_token: str, token_type: str = "Bearer") -> AuthInfo:
    """Create authentication info"""
    return AuthInfo(access_token=access_token, token_type=token_type)


def get_config_by_environment(is_test: bool = False) -> DeribitConfig:
    """Get configuration based on environment"""
    return DERIBIT_CONFIGS["TEST"] if is_test else DERIBIT_CONFIGS["PRODUCTION"]
