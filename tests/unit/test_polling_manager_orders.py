"""Unit tests for enhanced order polling in PollingManager."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Ensure src directory is on import path for direct module imports during tests
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from deribit_webhook.config import settings  # type: ignore
from deribit_webhook.services.polling_manager import PollingManager  # type: ignore
from deribit_webhook.services.mock_deribit_client import MockDeribitClient  # type: ignore


@pytest.mark.asyncio
async def test_start_polling_initializes_order_components(monkeypatch):
    """start_polling should spin up order polling and initial burst tasks."""
    manager = PollingManager()

    async def fake_position_loop():
        await asyncio.sleep(0)

    async def fake_order_loop():
        await asyncio.sleep(0)

    async def fake_initial_polling():
        pass

    # Replace long-running loops with short coroutines
    monkeypatch.setattr(manager, "_position_polling_loop", fake_position_loop)
    monkeypatch.setattr(manager, "_order_polling_loop", fake_order_loop)
    monkeypatch.setattr(manager, "_execute_initial_polling", fake_initial_polling)
    monkeypatch.setattr(manager, "_on_initial_polling_complete", lambda task: None)

    await manager.start_polling()
    await asyncio.sleep(0)  # give scheduled tasks a chance to finish

    assert manager.order_polling_enabled is True
    assert manager.position_polling_task is not None
    assert manager.order_polling_task is not None
    assert manager.initial_polling_task is not None
    assert manager.initial_polling_task.done()

    await manager.stop_polling()


@pytest.mark.asyncio
async def test_process_pending_orders_matches_open_orders(monkeypatch):
    """Pending order records should be matched against open orders by ID."""
    manager = PollingManager()

    # Force mock mode so we use the mock client branch
    monkeypatch.setattr(settings, "use_mock_mode", True, raising=False)

    async def fake_query_records(_query):
        return [SimpleNamespace(order_id="order-1", id=1)]

    monkeypatch.setattr(manager, "_get_delta_manager", lambda: SimpleNamespace(query_records=fake_query_records))

    async def fake_get_open_orders(self, account_name, currency="BTC", kind="option", order_type="limit"):
        return [
            {
                "order_id": "order-1",
                "instrument_name": "BTC-TEST",
                "direction": "buy",
                "amount": 1.0,
                "price": 0.1,
            }
        ]

    async def fake_close(self):
        return None

    monkeypatch.setattr(MockDeribitClient, "get_open_orders", fake_get_open_orders)
    monkeypatch.setattr(MockDeribitClient, "close", fake_close)

    matched = await manager._process_pending_orders_for_account("test_account")

    assert len(matched) == 1
    assert matched[0]["order_id"] == "order-1"
    assert matched[0]["instrument_name"] == "BTC-TEST"
