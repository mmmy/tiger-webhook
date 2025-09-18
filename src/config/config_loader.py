"""
Configuration loader for YAML-based API key configuration

Provides singleton access to account configurations and WeChat bot settings.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

from models.config_types import DeribitConfig, ApiKeyConfig, WeChatBotConfig
from .settings import settings


class ConfigLoader:
    """Singleton configuration loader for API keys and account settings"""
    
    _instance: Optional['ConfigLoader'] = None
    _config: Optional[DeribitConfig] = None
    
    def __init__(self):
        if ConfigLoader._instance is not None:
            raise RuntimeError("ConfigLoader is a singleton. Use get_instance() instead.")
        ConfigLoader._instance = self
    
    @classmethod
    def get_instance(cls) -> 'ConfigLoader':
        """Get the singleton instance of ConfigLoader"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_config(self) -> DeribitConfig:
        """Load configuration from YAML file"""
        if self._config is not None:
            return self._config
        
        try:
            config_path = Path(settings.api_key_file).resolve()
            
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
            
            if not config_data or 'accounts' not in config_data:
                raise ValueError("Invalid configuration: No accounts found")
            
            # Convert to DeribitConfig object
            self._config = DeribitConfig.model_validate(config_data)
            
            if not self._config.accounts:
                raise ValueError("Invalid configuration: No accounts found")
            
            return self._config
            
        except Exception as error:
            raise RuntimeError(f"Failed to load configuration: {error}")
    
    def get_enabled_accounts(self) -> List[ApiKeyConfig]:
        """Get all enabled accounts"""
        config = self.load_config()
        return [account for account in config.accounts if account.enabled]
    
    def get_account_by_name(self, name: str) -> Optional[ApiKeyConfig]:
        """Get account configuration by name"""
        config = self.load_config()
        for account in config.accounts:
            if account.name == name:
                return account
        return None
    
    def get_api_base_url(self) -> str:
        """Get the appropriate Deribit API base URL based on environment"""
        return settings.get_api_base_url()
    
    def get_websocket_url(self) -> str:
        """Get the appropriate Deribit WebSocket URL based on environment"""
        return settings.get_websocket_url()
    
    def _get_wechat_bot_config(self, account_name: str) -> Optional[WeChatBotConfig]:
        """Get WeChat bot configuration for a specific account"""
        account = self.get_account_by_name(account_name)
        
        if not account or not account.wechat_bot or not account.wechat_bot.webhook_url:
            return None
        
        wechat_config = account.wechat_bot
        if wechat_config.enabled is False:
            return None
        
        return WeChatBotConfig(
            webhook_url=wechat_config.webhook_url,
            timeout=wechat_config.timeout or settings.wechat_timeout,
            retry_count=wechat_config.retry_count or settings.wechat_retry_count,
            retry_delay=wechat_config.retry_delay or settings.wechat_retry_delay
        )
    
    def get_all_wechat_bot_configs(self) -> List[Dict[str, Any]]:
        """Get all enabled WeChat bot configurations"""
        enabled_accounts = self.get_enabled_accounts()
        configs = []
        
        for account in enabled_accounts:
            config = self._get_wechat_bot_config(account.name)
            if config:
                configs.append({
                    "account_name": account.name,
                    "config": config
                })
        
        return configs
    
    def get_account_wechat_bot_config(self, account_name: str) -> Optional[WeChatBotConfig]:
        """Get WeChat bot configuration for a specific account"""
        return self._get_wechat_bot_config(account_name)
    
    def reload_config(self) -> None:
        """Force reload configuration from file"""
        self._config = None
        self.load_config()
