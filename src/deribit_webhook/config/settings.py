"""
Application settings using Pydantic Settings

Handles environment variables and application configuration.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", alias="HOST", description="Server host")
    port: int = Field(default=3001, alias="PORT", description="Server port")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL", description="Logging level")
    
    # Environment Settings
    environment: str = Field(default="development", alias="NODE_ENV")
    use_mock_mode: bool = Field(default=True, alias="USE_MOCK_MODE", description="Enable mock mode for development")
    use_test_environment: bool = Field(default=True, alias="USE_TEST_ENVIRONMENT", description="Use Deribit test environment")
    auto_start_polling: bool = Field(default=True, alias="AUTO_START_POLLING", description="Auto-start position polling")
    
    # API Configuration
    api_key_file: str = Field(default="./config/apikeys.yml", alias="API_KEY_FILE", description="Path to API keys configuration file")
    
    # Deribit API URLs
    deribit_api_url: str = Field(default="https://www.deribit.com/api/v2", alias="DERIBIT_API_URL", description="Deribit production API URL")
    deribit_test_api_url: str = Field(default="https://test.deribit.com/api/v2", alias="DERIBIT_TEST_API_URL", description="Deribit test API URL")
    deribit_ws_url: str = Field(default="wss://www.deribit.com/ws/api/v2", alias="DERIBIT_WS_URL", description="Deribit production WebSocket URL")
    deribit_test_ws_url: str = Field(default="wss://test.deribit.com/ws/api/v2", alias="DERIBIT_TEST_WS_URL", description="Deribit test WebSocket URL")
    
    # Database Configuration
    database_url: str = Field(default="sqlite+aiosqlite:///./data/delta_records.db", alias="DATABASE_URL", description="Database connection URL")

    # Security Settings
    secret_key: str = Field(default="your-secret-key-here-change-in-production", alias="SECRET_KEY", description="Secret key for security")
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Max requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    enable_webhook_security: bool = Field(default=False, description="Enable webhook signature verification")
    webhook_secret: Optional[str] = Field(default=None, description="Webhook signature secret")
    require_api_key: bool = Field(default=False, description="Require API key for requests")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    
    # Polling Configuration
    enable_position_polling: bool = Field(default=True, alias="ENABLE_POSITION_POLLING", description="Enable automatic position polling")
    position_polling_interval: int = Field(default=30, description="Position polling interval in seconds")
    polling_interval_seconds: int = Field(default=30, alias="POLLING_INTERVAL_SECONDS", description="Position polling interval in seconds")
    # New minute-based polling intervals (following reference project pattern)
    position_polling_interval_minutes: int = Field(default=15, alias="POSITION_POLLING_INTERVAL_MINUTES", description="Position polling interval in minutes")
    order_polling_interval_minutes: int = Field(default=5, alias="ORDER_POLLING_INTERVAL_MINUTES", description="Order polling interval in minutes")
    max_polling_errors: int = Field(default=5, alias="MAX_POLLING_ERRORS", description="Maximum consecutive polling errors before stopping")
    
    # Logging Configuration
    log_format: str = Field(default="json", alias="LOG_FORMAT", description="Log format (json or text)")
    log_file: Optional[str] = Field(default="./logs/combined.log", alias="LOG_FILE", description="Log file path")
    log_max_size: str = Field(default="10MB", alias="LOG_MAX_SIZE", description="Maximum log file size")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT", description="Number of backup log files to keep")

    # Trading Configuration
    spread_ratio_threshold: float = Field(default=0.15, alias="SPREAD_RATIO_THRESHOLD", description="Spread ratio threshold for trading decisions")
    spread_tick_multiple_threshold: int = Field(default=2, alias="SPREAD_TICK_MULTIPLE_THRESHOLD", description="Spread tick multiple threshold for trading decisions")

    # WeChat Bot Configuration (Global defaults)
    wechat_timeout: int = Field(default=10000, alias="WECHAT_TIMEOUT", description="WeChat bot request timeout in milliseconds")
    wechat_retry_count: int = Field(default=3, alias="WECHAT_RETRY_COUNT", description="WeChat bot retry count")
    wechat_retry_delay: int = Field(default=1000, alias="WECHAT_RETRY_DELAY", description="WeChat bot retry delay in milliseconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    def get_api_base_url(self) -> str:
        """Get the appropriate Deribit API base URL based on environment"""
        if self.use_test_environment:
            return self.deribit_test_api_url
        return self.deribit_api_url
    
    def get_websocket_url(self) -> str:
        """Get the appropriate Deribit WebSocket URL based on environment"""
        if self.use_test_environment:
            return self.deribit_test_ws_url
        return self.deribit_ws_url


# Global settings instance
settings = Settings()
