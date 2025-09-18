"""
Configuration-related type definitions
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class WeChatBotSettings(BaseModel):
    """WeChat bot settings within account configuration"""
    webhook_url: str = Field(..., description="WeChat bot webhook URL")
    timeout: Optional[int] = Field(default=10000, description="Request timeout in milliseconds")
    retry_count: Optional[int] = Field(default=3, description="Number of retry attempts")
    retry_delay: Optional[int] = Field(default=1000, description="Delay between retries in milliseconds")
    enabled: Optional[bool] = Field(default=True, description="Whether WeChat bot is enabled")


class ApiKeyConfig(BaseModel):
    """API key configuration for a Deribit account"""
    name: str = Field(..., description="Account name")
    description: str = Field(..., description="Account description")
    client_id: str = Field(..., alias="clientId", description="Deribit client ID")
    client_secret: str = Field(..., alias="clientSecret", description="Deribit client secret")
    enabled: bool = Field(default=True, description="Whether account is enabled")
    grant_type: Literal["client_credentials", "client_signature", "refresh_token"] = Field(
        default="client_credentials", 
        alias="grantType",
        description="OAuth grant type"
    )
    scope: Optional[str] = Field(default=None, description="OAuth scope")
    wechat_bot: Optional[WeChatBotSettings] = Field(default=None, description="WeChat bot configuration")
    
    class Config:
        allow_population_by_field_name = True


class GlobalSettings(BaseModel):
    """Global application settings"""
    connection_timeout: int = Field(default=30, alias="connectionTimeout", description="Connection timeout in seconds")
    max_reconnect_attempts: int = Field(default=5, alias="maxReconnectAttempts", description="Maximum reconnect attempts")
    rate_limit_per_minute: int = Field(default=60, alias="rateLimitPerMinute", description="Rate limit per minute")
    
    class Config:
        allow_population_by_field_name = True


class DeribitConfig(BaseModel):
    """Complete Deribit configuration"""
    accounts: List[ApiKeyConfig] = Field(..., description="List of account configurations")
    settings: Optional[GlobalSettings] = Field(default_factory=GlobalSettings, description="Global settings")


class WeChatBotConfig(BaseModel):
    """WeChat bot configuration for runtime use"""
    webhook_url: str = Field(..., description="WeChat bot webhook URL")
    timeout: int = Field(default=10000, description="Request timeout in milliseconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=1000, description="Delay between retries in milliseconds")
