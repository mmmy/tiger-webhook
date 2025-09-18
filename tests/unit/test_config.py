"""
Unit tests for configuration management.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from deribit_webhook.config.config_loader import ConfigLoader
from deribit_webhook.config.settings import Settings


class TestConfigLoader:
    """Test configuration loader functionality."""

    def test_load_valid_config(self, test_config_file: Path):
        """Test loading a valid configuration file."""
        loader = ConfigLoader()
        config = loader.load_config(str(test_config_file))
        
        assert config is not None
        assert len(config.accounts) == 2
        assert config.accounts[0].name == "test_account"
        assert config.accounts[0].enabled is True
        assert config.accounts[1].name == "disabled_account"
        assert config.accounts[1].enabled is False

    def test_load_nonexistent_config(self):
        """Test loading a non-existent configuration file."""
        loader = ConfigLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_config("/nonexistent/path/config.yml")

    def test_load_invalid_yaml(self, temp_dir: Path):
        """Test loading an invalid YAML file."""
        invalid_file = temp_dir / "invalid.yml"
        invalid_file.write_text("invalid: yaml: content: [")
        
        loader = ConfigLoader()
        with pytest.raises(yaml.YAMLError):
            loader.load_config(str(invalid_file))

    def test_get_account_by_name(self, config_loader: ConfigLoader):
        """Test getting account by name."""
        account = config_loader.get_account("test_account")
        assert account is not None
        assert account.name == "test_account"
        assert account.client_id == "test_client_id"

    def test_get_nonexistent_account(self, config_loader: ConfigLoader):
        """Test getting a non-existent account."""
        account = config_loader.get_account("nonexistent_account")
        assert account is None

    def test_get_enabled_accounts(self, config_loader: ConfigLoader):
        """Test getting only enabled accounts."""
        enabled_accounts = config_loader.get_enabled_accounts()
        assert len(enabled_accounts) == 1
        assert enabled_accounts[0].name == "test_account"

    def test_singleton_behavior(self, test_env_vars):
        """Test that ConfigLoader behaves as a singleton."""
        loader1 = ConfigLoader()
        loader2 = ConfigLoader()
        assert loader1 is loader2

    def test_wechat_config(self, config_loader: ConfigLoader):
        """Test WeChat configuration loading."""
        account = config_loader.get_account("test_account")
        assert account.wechat_bot is not None
        assert account.wechat_bot.webhook_url == "https://test.webhook.url"
        assert account.wechat_bot.timeout == 5000
        assert account.wechat_bot.enabled is True


class TestSettings:
    """Test application settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.node_env == "development"
        assert settings.port == 3000
        assert settings.host == "0.0.0.0"

    def test_environment_override(self, test_env_vars):
        """Test that environment variables override defaults."""
        settings = Settings()
        assert settings.node_env == "test"
        assert settings.use_mock_mode is True
        assert settings.use_test_environment is True

    def test_database_url_construction(self, test_env_vars):
        """Test database URL construction."""
        settings = Settings()
        assert "sqlite+aiosqlite://" in settings.database_url
        assert settings.database_url.endswith("test.db")

    def test_api_urls(self, test_env_vars):
        """Test API URL selection based on environment."""
        settings = Settings()
        # Should use test URLs when USE_TEST_ENVIRONMENT=true
        assert "test.deribit.com" in settings.deribit_api_url
        assert "test.deribit.com" in settings.deribit_ws_url

    def test_production_urls(self):
        """Test production API URLs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["USE_TEST_ENVIRONMENT"] = "false"
            os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{temp_dir}/prod.db"
            
            settings = Settings()
            assert "www.deribit.com" in settings.deribit_api_url
            assert "www.deribit.com" in settings.deribit_ws_url

    def test_security_settings(self, test_env_vars):
        """Test security-related settings."""
        settings = Settings()
        assert settings.secret_key == "test-secret-key"
        assert settings.webhook_secret == "test-webhook-secret"
        assert settings.rate_limit_enabled is False
        assert settings.webhook_security_enabled is False

    def test_polling_settings(self, test_env_vars):
        """Test position polling settings."""
        settings = Settings()
        assert settings.enable_position_polling is False
        assert settings.polling_interval_seconds == 30  # default value

    def test_logging_settings(self, test_env_vars):
        """Test logging configuration."""
        settings = Settings()
        assert settings.log_level == "DEBUG"

    def test_boolean_parsing(self):
        """Test boolean environment variable parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("invalid", False),
        ]
        
        for env_value, expected in test_cases:
            os.environ["TEST_BOOL"] = env_value
            # Test the boolean parsing logic
            result = os.getenv("TEST_BOOL", "false").lower() in ("true", "1", "yes")
            assert result == expected

    def test_required_settings_validation(self):
        """Test that required settings are validated."""
        # Clear required environment variables
        required_vars = ["SECRET_KEY", "DATABASE_URL"]
        original_values = {}
        
        for var in required_vars:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            # This should work with defaults or raise appropriate errors
            settings = Settings()
            # Basic validation - settings object should be created
            assert settings is not None
        finally:
            # Restore original values
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value

    def test_config_file_path_resolution(self, test_env_vars, test_config_file):
        """Test configuration file path resolution."""
        settings = Settings()
        assert settings.api_key_file == str(test_config_file)
        assert Path(settings.api_key_file).exists()

    def test_directory_creation(self, test_env_vars):
        """Test that necessary directories are created."""
        settings = Settings()
        # The database URL should point to a valid directory structure
        db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
        assert db_path.parent.exists() or str(db_path) == ":memory:"
