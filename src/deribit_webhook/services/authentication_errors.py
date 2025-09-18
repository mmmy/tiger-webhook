"""
Authentication error classes and result types
"""

from typing import Optional
from pydantic import BaseModel, Field

from ..models.auth_types import AuthToken
from ..models.config_types import ApiKeyConfig


class AuthenticationError(Exception):
    """Base authentication error class"""
    
    def __init__(
        self, 
        message: str, 
        account_name: str, 
        status_code: int = 401, 
        error_code: str = "AUTHENTICATION_FAILED"
    ):
        super().__init__(message)
        self.account_name = account_name
        self.status_code = status_code
        self.error_code = error_code


class TokenExpiredError(AuthenticationError):
    """Token expired error"""
    
    def __init__(self, account_name: str):
        super().__init__(
            f"Authentication token expired for account: {account_name}",
            account_name,
            401,
            "TOKEN_EXPIRED"
        )


class TokenNotFoundError(AuthenticationError):
    """Token not found error"""
    
    def __init__(self, account_name: str):
        super().__init__(
            f"No authentication token found for account: {account_name}",
            account_name,
            401,
            "TOKEN_NOT_FOUND"
        )


class AuthenticationResult(BaseModel):
    """Authentication result interface"""
    success: bool = Field(..., description="Whether authentication was successful")
    token: Optional[AuthToken] = Field(default=None, description="Authentication token")
    account: Optional[ApiKeyConfig] = Field(default=None, description="Account configuration")
    is_mock: bool = Field(..., description="Whether this is mock mode")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
