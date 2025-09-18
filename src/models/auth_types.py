"""
Authentication-related type definitions
"""

from typing import List, Optional, Union, Literal, Any
from pydantic import BaseModel, Field


# Deribit grant types
DeribitGrantType = Literal["client_credentials", "client_signature", "refresh_token"]

# Deribit scopes
DeribitScope = Union[
    Literal["mainaccount"],
    Literal["connection"],
    Literal["account:read"],
    Literal["account:read_write"],
    Literal["trade:read"],
    Literal["trade:read_write"],
    Literal["wallet:read"],
    Literal["wallet:read_write"],
    Literal["wallet:none"],
    Literal["account:none"],
    Literal["trade:none"],
    Literal["block_trade:read"],
    Literal["block_trade:read_write"],
    Literal["block_rfq:read"],
    Literal["block_rfq:read_write"],
    str  # For session:name, expires:NUMBER, ip:ADDR patterns
]


class DeribitAuthResult(BaseModel):
    """Deribit authentication response data"""
    access_token: str = Field(..., description="Access token")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: str = Field(..., description="Refresh token")
    scope: str = Field(..., description="Granted scope")
    token_type: str = Field(..., description="Token type (usually 'bearer')")
    enabled_features: List[str] = Field(..., description="List of enabled features")
    sid: Optional[str] = Field(default=None, description="Session ID")


class AuthResponse(BaseModel):
    """Deribit API standard response format for authentication"""
    jsonrpc: str = Field(..., description="JSON-RPC version")
    result: DeribitAuthResult = Field(..., description="Authentication result")
    testnet: bool = Field(..., description="Whether this is testnet")
    us_in: int = Field(..., alias="usIn", description="Request timestamp (microseconds)")
    us_out: int = Field(..., alias="usOut", description="Response timestamp (microseconds)")
    us_diff: int = Field(..., alias="usDiff", description="Processing time (microseconds)")
    
    class Config:
        allow_population_by_field_name = True


class DeribitErrorDetail(BaseModel):
    """Deribit error detail"""
    message: str = Field(..., description="Error message")
    code: int = Field(..., description="Error code")
    data: Optional[Any] = Field(default=None, description="Additional error data")


class DeribitError(BaseModel):
    """Deribit error response"""
    error: DeribitErrorDetail = Field(..., description="Error details")


class AuthToken(BaseModel):
    """Authentication token information"""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    expires_at: int = Field(..., description="Expiration timestamp")
    scope: str = Field(..., description="Token scope")


class DeribitBaseAuthParams(BaseModel):
    """Base authentication parameters"""
    grant_type: DeribitGrantType = Field(..., description="Grant type")
    scope: Optional[str] = Field(default=None, description="Access scope")


class DeribitClientCredentialsParams(DeribitBaseAuthParams):
    """Client credentials authentication parameters"""
    grant_type: Literal["client_credentials"] = Field(default="client_credentials")
    client_id: str = Field(..., description="Client ID")
    client_secret: str = Field(..., description="Client secret")


class DeribitClientSignatureParams(DeribitBaseAuthParams):
    """Client signature authentication parameters"""
    grant_type: Literal["client_signature"] = Field(default="client_signature")
    client_id: str = Field(..., description="Client ID")
    timestamp: int = Field(..., description="Timestamp in milliseconds")
    signature: str = Field(..., description="HMAC-SHA256 signature")
    nonce: str = Field(..., description="Random nonce string")
    data: Optional[str] = Field(default=None, description="Optional user data")


class DeribitRefreshTokenParams(DeribitBaseAuthParams):
    """Refresh token authentication parameters"""
    grant_type: Literal["refresh_token"] = Field(default="refresh_token")
    refresh_token: str = Field(..., description="Refresh token")


# Union type for all authentication parameters
DeribitAuthParams = Union[
    DeribitClientCredentialsParams,
    DeribitClientSignatureParams,
    DeribitRefreshTokenParams
]


class DeribitAuthRequestParams(BaseModel):
    """Complete authentication request parameters"""
    # Base parameters
    grant_type: DeribitGrantType = Field(..., description="Grant type")
    scope: Optional[str] = Field(default=None, description="Access scope")
    
    # Client credentials parameters
    client_id: str = Field(..., description="Client ID")
    client_secret: str = Field(..., description="Client secret")
    
    # Client signature parameters (optional)
    timestamp: Optional[int] = Field(default=None, description="Timestamp in milliseconds")
    signature: Optional[str] = Field(default=None, description="HMAC-SHA256 signature")
    nonce: Optional[str] = Field(default=None, description="Random nonce string")
    data: Optional[str] = Field(default=None, description="Optional user data")
    
    # Refresh token parameters (optional)
    refresh_token: Optional[str] = Field(default=None, description="Refresh token")
    
    # Security key authorization parameters (optional)
    authorization_data: Optional[str] = Field(default=None, description="TFA code or other authorization data")
    challenge: Optional[str] = Field(default=None, description="Server challenge string")
