#!/usr/bin/env python3
"""
Test script to verify POSITION_POLLING_INTERVAL_MINUTES configuration is working correctly.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from deribit_webhook.config.settings import settings
from deribit_webhook.services.polling_manager import polling_manager


def test_position_polling_config():
    """Test that POSITION_POLLING_INTERVAL_MINUTES configuration is properly loaded"""
    
    print("🧪 Testing POSITION_POLLING_INTERVAL_MINUTES configuration...")
    print()
    
    # Test 1: Check default values
    print("📋 Test 1: Default configuration values")
    print(f"   position_polling_interval_minutes: {settings.position_polling_interval_minutes}")
    print(f"   order_polling_interval_minutes: {settings.order_polling_interval_minutes}")
    print(f"   auto_start_polling: {settings.auto_start_polling}")
    print(f"   use_mock_mode: {settings.use_mock_mode}")
    print()
    
    # Test 2: Check environment variable loading
    print("📋 Test 2: Environment variable loading")
    
    # Set environment variables
    os.environ["POSITION_POLLING_INTERVAL_MINUTES"] = "20"
    os.environ["ORDER_POLLING_INTERVAL_MINUTES"] = "10"
    os.environ["AUTO_START_POLLING"] = "false"
    
    # Reload settings
    from deribit_webhook.config.settings import Settings
    test_settings = Settings()
    
    print(f"   POSITION_POLLING_INTERVAL_MINUTES=20 -> {test_settings.position_polling_interval_minutes}")
    print(f"   ORDER_POLLING_INTERVAL_MINUTES=10 -> {test_settings.order_polling_interval_minutes}")
    print(f"   AUTO_START_POLLING=false -> {test_settings.auto_start_polling}")
    print()
    
    # Test 3: Check polling manager status
    print("📋 Test 3: Polling manager status")
    status = polling_manager.get_status()
    
    print(f"   is_running: {status['is_running']}")
    print(f"   interval_minutes: {status['interval_minutes']}")
    print(f"   position_polling_interval_minutes: {status['position_polling_interval_minutes']}")
    print(f"   order_polling_interval_minutes: {status['order_polling_interval_minutes']}")
    print(f"   enabled_accounts: {status['enabled_accounts']}")
    print(f"   mock_mode: {status['mock_mode']}")
    print()
    
    # Test 4: Verify conversion to seconds
    print("📋 Test 4: Minutes to seconds conversion")
    expected_seconds = settings.position_polling_interval_minutes * 60
    actual_seconds = status['interval_seconds']
    print(f"   {settings.position_polling_interval_minutes} minutes = {expected_seconds} seconds")
    print(f"   Status reports: {actual_seconds} seconds")
    print(f"   Conversion correct: {expected_seconds == actual_seconds}")
    print()
    
    # Test 5: Check all environment variable aliases
    print("📋 Test 5: Environment variable aliases")
    env_tests = [
        ("HOST", "0.0.0.0", settings.host),
        ("PORT", "3001", str(settings.port)),
        ("LOG_LEVEL", "INFO", settings.log_level),
        ("NODE_ENV", "development", settings.environment),
        ("USE_MOCK_MODE", "true", str(settings.use_mock_mode).lower()),
        ("USE_TEST_ENVIRONMENT", "true", str(settings.use_test_environment).lower()),
        ("AUTO_START_POLLING", "true", str(settings.auto_start_polling).lower()),
        ("API_KEY_FILE", "./config/apikeys.yml", settings.api_key_file),
        ("DATABASE_URL", "sqlite+aiosqlite:///./data/delta_records.db", settings.database_url),
        ("SECRET_KEY", "your-secret-key-here-change-in-production", settings.secret_key),
        ("POLLING_INTERVAL_SECONDS", "30", str(settings.polling_interval_seconds)),
        ("POSITION_POLLING_INTERVAL_MINUTES", "15", str(settings.position_polling_interval_minutes)),
        ("ORDER_POLLING_INTERVAL_MINUTES", "5", str(settings.order_polling_interval_minutes)),
        ("MAX_POLLING_ERRORS", "5", str(settings.max_polling_errors)),
        ("LOG_FORMAT", "json", settings.log_format),
        ("LOG_FILE", "./logs/combined.log", settings.log_file or ""),
        ("SPREAD_RATIO_THRESHOLD", "0.15", str(settings.spread_ratio_threshold)),
        ("SPREAD_TICK_MULTIPLE_THRESHOLD", "2", str(settings.spread_tick_multiple_threshold)),
        ("WECHAT_TIMEOUT", "10000", str(settings.wechat_timeout)),
        ("WECHAT_RETRY_COUNT", "3", str(settings.wechat_retry_count)),
        ("WECHAT_RETRY_DELAY", "1000", str(settings.wechat_retry_delay)),
    ]
    
    for env_var, expected, actual in env_tests:
        status_icon = "✅" if expected == actual else "❌"
        print(f"   {status_icon} {env_var}: expected='{expected}', actual='{actual}'")
    
    print()
    print("🎉 Configuration test completed!")
    
    # Clean up environment variables
    for key in ["POSITION_POLLING_INTERVAL_MINUTES", "ORDER_POLLING_INTERVAL_MINUTES", "AUTO_START_POLLING"]:
        if key in os.environ:
            del os.environ[key]


if __name__ == "__main__":
    test_position_polling_config()
