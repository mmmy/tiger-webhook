"""
Configuration-related type definitions
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


class WeChatBotSettings(BaseModel):
    """WeChat bot settings within account configuration"""
    webhook_url: str = Field(..., description="WeChat bot webhook URL")
    timeout: Optional[int] = Field(default=10000, description="Request timeout in milliseconds")
    retry_count: Optional[int] = Field(default=3, description="Number of retry attempts")
    retry_delay: Optional[int] = Field(default=1000, description="Delay between retries in milliseconds")
    enabled: Optional[bool] = Field(default=True, description="Whether WeChat bot is enabled")


class ApiKeyConfig(BaseModel):
    """Tiger Brokers API configuration"""
    name: str = Field(..., description="Account name")
    description: str = Field(..., description="Account description")
    enabled: bool = Field(default=True, description="Whether account is enabled")

    # Tiger Brokers fields
    tiger_id: str = Field(..., description="Tiger Brokers ID")
    private_key_path: str = Field(..., description="Path to Tiger private key file")
    account: str = Field(..., description="Tiger trading account number")
    market: str = Field(default="US", description="Market type (US, HK, etc.)")
    user_token: Optional[str] = Field(default=None, alias="userToken", description="Tiger user token for OpenAPI requests")

    @model_validator(mode='after')
    def validate_tiger_config(self):
        """Validate Tiger configuration"""
        if not self.tiger_id or not self.private_key_path or not self.account:
            raise ValueError("Tiger configuration incomplete: tiger_id, private_key_path, and account are required")

        return self
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


class TigerEnvironmentConfig(BaseModel):
    """Tiger Brokers环境配置"""
    base_url: str = Field(..., description="API base URL")
    socket_url: str = Field(..., description="WebSocket URL")


class TigerGlobalConfig(BaseModel):
    """Tiger Brokers全局配置"""
    sandbox: TigerEnvironmentConfig = Field(..., description="沙盒环境配置")
    production: TigerEnvironmentConfig = Field(..., description="生产环境配置")


class AppGlobalConfig(BaseModel):
    """应用全局配置"""
    use_test_environment: bool = Field(default=True, description="是否使用测试环境")
    use_mock_mode: bool = Field(default=False, description="是否使用模拟模式")


class TigerConfig(BaseModel):
    """完整的Tiger Brokers交易配置"""
    accounts: List[ApiKeyConfig] = Field(..., description="List of account configurations")
    settings: Optional[GlobalSettings] = Field(default_factory=GlobalSettings, description="Global settings")

    # Tiger配置字段
    global_config: Optional[AppGlobalConfig] = Field(None, alias="global", description="全局应用配置")
    tiger_config: Optional[TigerGlobalConfig] = Field(None, description="Tiger Brokers配置")

    @property
    def use_test_environment(self) -> bool:
        """是否使用测试环境"""
        if self.global_config:
            return self.global_config.use_test_environment
        return True


# 为了向后兼容，保留DeribitConfig别名
DeribitConfig = TigerConfig


class WeChatBotConfig(BaseModel):
    """WeChat bot configuration for runtime use"""
    webhook_url: str = Field(..., description="WeChat bot webhook URL")
    timeout: int = Field(default=10000, description="Request timeout in milliseconds")
    retry_count: int = Field(default=3, description="Number of retry attempts")
    retry_delay: int = Field(default=1000, description="Delay between retries in milliseconds")
