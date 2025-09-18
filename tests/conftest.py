"""
Test configuration and fixtures for the Deribit Webhook Python service.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / 'src'
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from deribit_webhook.app import create_app
from deribit_webhook.config.config_loader import ConfigLoader
from deribit_webhook.database.delta_manager import DeltaManager


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def test_config_file(temp_dir: Path) -> Path:
    """Create a test configuration file."""
    config_content = """
accounts:
  - name: test_account
    description: "Test account"
    clientId: "test_client_id"
    clientSecret: "test_client_secret"
    enabled: true
    grantType: "client_credentials"
    scope: ""
    
    wechat_bot:
      webhook_url: "https://test.webhook.url"
      timeout: 5000
      retry_count: 2
      retry_delay: 500
      enabled: true

  - name: disabled_account
    description: "Disabled test account"
    clientId: "disabled_client_id"
    clientSecret: "disabled_client_secret"
    enabled: false

settings:
  connectionTimeout: 30
  maxReconnectAttempts: 3
  rateLimitPerMinute: 100
"""
    config_file = temp_dir / "test_apikeys.yml"
    config_file.write_text(config_content.strip())
    return config_file


@pytest.fixture
def test_env_vars(temp_dir: Path, test_config_file: Path) -> Generator[None, None, None]:
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    test_env = {
        "NODE_ENV": "test",
        "USE_MOCK_MODE": "true",
        "USE_TEST_ENVIRONMENT": "true",
        "DATABASE_URL": f"sqlite+aiosqlite:///{temp_dir}/test.db",
        "API_KEY_FILE": str(test_config_file),
        "SECRET_KEY": "test-secret-key",
        "WEBHOOK_SECRET": "test-webhook-secret",
        "RATE_LIMIT_ENABLED": "false",
        "WEBHOOK_SECURITY_ENABLED": "false",
        "ENABLE_POSITION_POLLING": "false",
        "LOG_LEVEL": "DEBUG",
    }
    
    os.environ.update(test_env)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def config_loader(test_env_vars: None, test_config_file: Path) -> ConfigLoader:
    """Create a test configuration loader."""
    return ConfigLoader()


@pytest_asyncio.fixture
async def delta_manager(temp_dir: Path) -> AsyncGenerator[DeltaManager, None]:
    """Create a test delta manager with in-memory database."""
    db_path = temp_dir / "test_delta.db"
    manager = DeltaManager(f"sqlite+aiosqlite:///{db_path}")
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture
def app(test_env_vars: None):
    """Create a test FastAPI application."""
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_webhook_payload() -> dict:
    """Create a mock TradingView webhook payload."""
    return {
        "account_name": "test_account",
        "side": "buy",
        "size": "1.0",
        "market_position": "long",
        "prev_market_position": "flat",
        "comment": "Test entry signal",
        "tv_id": "test_12345",
        "timestamp": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
def mock_position_data() -> dict:
    """Create mock position data."""
    return {
        "result": [
            {
                "instrument_name": "BTC-25DEC21-50000-C",
                "size": 1.0,
                "mark_price": 0.05,
                "delta": 0.5,
                "gamma": 0.001,
                "theta": -0.01,
                "vega": 0.1,
                "average_price": 0.048,
                "floating_profit_loss": 20.0,
                "realized_profit_loss": 0.0,
                "total_profit_loss": 20.0,
                "index_price": 50000.0,
                "settlement_price": 0.049,
                "direction": "buy",
                "kind": "option",
                "option_type": "call",
                "strike": 50000
            }
        ]
    }


@pytest.fixture
def mock_options_data() -> dict:
    """Create mock options data."""
    return {
        "result": [
            {
                "instrument_name": "BTC-25DEC21-50000-C",
                "kind": "option",
                "option_type": "call",
                "strike": 50000,
                "expiration_timestamp": 1640419200000,
                "underlying": "BTC",
                "is_active": True,
                "settlement_period": "day",
                "creation_timestamp": 1640332800000,
                "tick_size": 0.0005,
                "min_trade_amount": 0.1,
                "contract_size": 1.0
            },
            {
                "instrument_name": "BTC-25DEC21-45000-P",
                "kind": "option",
                "option_type": "put",
                "strike": 45000,
                "expiration_timestamp": 1640419200000,
                "underlying": "BTC",
                "is_active": True,
                "settlement_period": "day",
                "creation_timestamp": 1640332800000,
                "tick_size": 0.0005,
                "min_trade_amount": 0.1,
                "contract_size": 1.0
            }
        ]
    }


@pytest.fixture
def mock_auth_response() -> dict:
    """Create mock authentication response."""
    return {
        "result": {
            "access_token": "test_access_token_12345",
            "expires_in": 3600,
            "refresh_token": "test_refresh_token_12345",
            "scope": "read write",
            "token_type": "Bearer"
        }
    }


@pytest.fixture
def mock_order_response() -> dict:
    """Create mock order response."""
    return {
        "result": {
            "order": {
                "order_id": "test_order_12345",
                "instrument_name": "BTC-25DEC21-50000-C",
                "direction": "buy",
                "amount": 1.0,
                "price": 0.05,
                "order_type": "market",
                "order_state": "filled",
                "filled_amount": 1.0,
                "average_price": 0.05,
                "creation_timestamp": 1640332800000,
                "last_update_timestamp": 1640332805000
            },
            "trades": [
                {
                    "trade_id": "test_trade_12345",
                    "instrument_name": "BTC-25DEC21-50000-C",
                    "order_id": "test_order_12345",
                    "direction": "buy",
                    "amount": 1.0,
                    "price": 0.05,
                    "timestamp": 1640332805000,
                    "fee": 0.0005,
                    "fee_currency": "BTC"
                }
            ]
        }
    }


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add unit marker to tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in integration/ directory
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker to tests that might be slow
        if any(keyword in item.name.lower() for keyword in ["polling", "background", "timeout"]):
            item.add_marker(pytest.mark.slow)

