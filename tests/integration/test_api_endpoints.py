"""
Integration tests for API endpoints.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health and status endpoints."""

    def test_health_endpoint(self, client: TestClient):
        """Test basic health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_status_endpoint(self, client: TestClient):
        """Test detailed status endpoint."""
        response = client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Deribit Options Trading Microservice"
        assert "version" in data
        assert "environment" in data
        assert "mock_mode" in data
        assert "accounts" in data


class TestWebhookEndpoints:
    """Test webhook endpoints."""

    def test_webhook_signal_success(self, client: TestClient, mock_webhook_payload):
        """Test successful webhook signal processing."""
        with patch('deribit_webhook.services.option_trading_service.OptionTradingService.execute_trade', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = type('TradeResponse', (), {
                'success': True,
                'message': 'Trade executed successfully',
                'order_id': 'test_order_123',
                'instrument_name': 'BTC-25DEC21-50000-C',
                'executed_quantity': 1.0,
                'executed_price': 0.05,
                'final_order_state': 'filled'
            })()
            
            response = client.post("/webhook/signal", json=mock_webhook_payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["order_id"] == "test_order_123"

    def test_webhook_signal_invalid_payload(self, client: TestClient):
        """Test webhook with invalid payload."""
        invalid_payload = {"invalid": "data"}
        
        response = client.post("/webhook/signal", json=invalid_payload)
        
        assert response.status_code == 422  # Validation error

    def test_webhook_signal_missing_account(self, client: TestClient):
        """Test webhook with non-existent account."""
        payload = {
            "account_name": "nonexistent_account",
            "side": "buy",
            "size": "1.0",
            "market_position": "long",
            "prev_market_position": "flat",
            "comment": "Test signal",
            "tv_id": "test_123"
        }
        
        response = client.post("/webhook/signal", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["message"].lower()


class TestTradingEndpoints:
    """Test trading-related endpoints."""

    def test_get_options_success(self, client: TestClient, mock_options_data):
        """Test successful options retrieval."""
        with patch('deribit_webhook.services.option_service.OptionService.get_options', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "success": True,
                "message": "Found 2 options",
                "data": {"instruments": mock_options_data["result"]}
            }
            
            response = client.get("/api/trading/options/test_account")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["instruments"]) == 2

    def test_get_options_with_parameters(self, client: TestClient, mock_options_data):
        """Test options retrieval with query parameters."""
        with patch('deribit_webhook.services.option_service.OptionService.get_options', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "success": True,
                "message": "Found options",
                "data": {"instruments": mock_options_data["result"]}
            }
            
            response = client.get("/api/trading/options/test_account?underlying=BTC&direction=long")
            
            assert response.status_code == 200
            mock_get.assert_called_with("test_account", "BTC", "long")

    def test_get_options_account_not_found(self, client: TestClient):
        """Test options retrieval with non-existent account."""
        response = client.get("/api/trading/options/nonexistent_account")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False


class TestPositionEndpoints:
    """Test position management endpoints."""

    def test_get_positions_success(self, client: TestClient):
        """Test successful position retrieval."""
        response = client.get("/api/positions/test_account/USD")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data.get("positions"), list)

    def test_get_positions_with_currency(self, client: TestClient):
        """Test position retrieval with currency parameter."""
        response = client.get("/api/positions/test_account/BTC")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data.get("currency") == "BTC"

    def test_calculate_delta_success(self, client: TestClient):
        """Test successful delta calculation."""
        response = client.get("/api/positions/delta/test_account?currency=USD")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data.get("currency") == "USD"
        assert "total_delta" in data

    def test_polling_status(self, client: TestClient):
        """Test polling status endpoint."""
        response = client.get("/api/positions/polling/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "polling_enabled" in data

    def test_start_polling(self, client: TestClient):
        """Test start polling endpoint."""
        with patch('deribit_webhook.services.polling_manager.PollingManager.start_polling', new_callable=AsyncMock) as mock_start:
            mock_start.return_value = None
            
            response = client.post("/api/positions/polling/start")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_stop_polling(self, client: TestClient):
        """Test stop polling endpoint."""
        with patch('deribit_webhook.services.polling_manager.PollingManager.stop_polling', new_callable=AsyncMock) as mock_stop:
            mock_stop.return_value = None
            
            response = client.post("/api/positions/polling/stop")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestWeChatEndpoints:
    """Test WeChat bot endpoints."""

    def test_wechat_test_success(self, client: TestClient):
        """Test successful WeChat notification test."""
        with patch('deribit_webhook.services.wechat_notification.WeChatNotificationService.send_test_notification', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            response = client.post("/api/wechat/test/test_account")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_wechat_test_account_not_found(self, client: TestClient):
        """Test WeChat test with non-existent account."""
        response = client.post("/api/wechat/test/nonexistent_account")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_get_wechat_config(self, client: TestClient):
        """Test WeChat configuration retrieval."""
        response = client.get("/api/wechat/config/test_account")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["account_name"] == "test_account"

    def test_get_all_wechat_configs(self, client: TestClient):
        """Test all WeChat configurations retrieval."""
        response = client.get("/api/wechat/configs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "configs" in data

    def test_wechat_broadcast(self, client: TestClient):
        """Test WeChat broadcast functionality."""
        payload = {
            "message": "Test broadcast message",
            "notification_type": "system",
            "account_names": ["test_account"]
        }
        
        with patch('deribit_webhook.services.wechat_notification.WeChatNotificationService.send_system_notification', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            response = client.post("/api/wechat/broadcast", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_get_token_success(self, client: TestClient, mock_auth_response):
        """Test successful token retrieval."""
        with patch('deribit_webhook.services.auth_service.AuthService.authenticate', new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = mock_auth_response["result"]
            
            response = client.post("/api/auth/token/test_account")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "expires_in" in data

    def test_get_token_account_not_found(self, client: TestClient):
        """Test token retrieval with non-existent account."""
        response = client.post("/api/auth/token/nonexistent_account")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_refresh_token_success(self, client: TestClient, mock_auth_response):
        """Test successful token refresh."""
        with patch('deribit_webhook.services.auth_service.AuthService.refresh_token', new_callable=AsyncMock) as mock_refresh:
            mock_refresh.return_value = mock_auth_response["result"]
            
            response = client.post("/api/auth/refresh/test_account")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test endpoints using async client."""

    async def test_concurrent_requests(self, async_client: AsyncClient):
        """Test handling of concurrent requests."""
        import asyncio
        
        # Make multiple concurrent requests
        tasks = [
            async_client.get("/health"),
            async_client.get("/api/status"),
            async_client.get("/health"),
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

    async def test_request_timeout_handling(self, async_client: AsyncClient):
        """Test request timeout handling."""
        # This test would require mocking slow responses
        # For now, just test that the endpoint responds
        response = await async_client.get("/health")
        assert response.status_code == 200

    async def test_error_handling(self, async_client: AsyncClient):
        """Test error handling in async endpoints."""
        # Test non-existent endpoint
        response = await async_client.get("/api/nonexistent")
        assert response.status_code == 404

    async def test_large_payload_handling(self, async_client: AsyncClient):
        """Test handling of large payloads."""
        large_payload = {
            "account_name": "test_account",
            "side": "buy",
            "size": "1.0",
            "market_position": "long",
            "prev_market_position": "flat",
            "comment": "x" * 1000,  # Large comment
            "tv_id": "test_123"
        }
        
        response = await async_client.post("/webhook/signal", json=large_payload)
        # Should handle large payload (might fail validation but not crash)
        assert response.status_code in [200, 400, 422]
