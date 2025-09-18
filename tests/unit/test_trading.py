"""
Unit tests for trading services.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deribit_webhook.services.option_service import OptionService
from deribit_webhook.services.option_trading_service import OptionTradingService
from deribit_webhook.types.trading_types import TradeRequest, TradeResponse


class TestOptionService:
    """Test option service functionality."""

    @pytest.fixture
    def option_service(self, config_loader):
        """Create an option service instance."""
        return OptionService(config_loader)

    @pytest.mark.asyncio
    async def test_get_options_success(self, option_service, mock_options_data):
        """Test successful options retrieval."""
        with patch.object(option_service.deribit_client, 'get_instruments', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_options_data
            
            result = await option_service.get_options("test_account", "BTC", "long")
            
            assert result["success"] is True
            assert len(result["data"]["instruments"]) == 2
            assert result["data"]["instruments"][0]["instrument_name"] == "BTC-25DEC21-50000-C"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_options_account_not_found(self, option_service):
        """Test options retrieval with non-existent account."""
        result = await option_service.get_options("nonexistent_account", "BTC", "long")
        
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_get_options_api_error(self, option_service):
        """Test options retrieval with API error."""
        with patch.object(option_service.deribit_client, 'get_instruments', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("API Error")
            
            result = await option_service.get_options("test_account", "BTC", "long")
            
            assert result["success"] is False
            assert "error" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_filter_options_by_direction(self, option_service, mock_options_data):
        """Test option filtering by direction."""
        with patch.object(option_service.deribit_client, 'get_instruments', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_options_data
            
            # Test long direction (should include calls)
            result = await option_service.get_options("test_account", "BTC", "long")
            instruments = result["data"]["instruments"]
            call_options = [opt for opt in instruments if opt["option_type"] == "call"]
            assert len(call_options) > 0

    @pytest.mark.asyncio
    async def test_mock_mode_behavior(self, option_service):
        """Test behavior in mock mode."""
        option_service.use_mock_mode = True
        
        result = await option_service.get_options("test_account", "BTC", "long")
        
        assert result["success"] is True
        assert "mock" in result["message"].lower()
        assert len(result["data"]["instruments"]) > 0


class TestOptionTradingService:
    """Test option trading service functionality."""

    @pytest.fixture
    def trading_service(self, config_loader):
        """Create a trading service instance."""
        return OptionTradingService(config_loader)

    @pytest.mark.asyncio
    async def test_execute_trade_success(self, trading_service, mock_order_response):
        """Test successful trade execution."""
        trade_request = TradeRequest(
            account_name="test_account",
            side="buy",
            size=1.0,
            market_position="long",
            prev_market_position="flat",
            comment="Test trade",
            tv_id="test_123"
        )
        
        with patch.object(trading_service.deribit_client, 'buy', new_callable=AsyncMock) as mock_buy:
            mock_buy.return_value = mock_order_response
            
            with patch.object(trading_service, '_select_best_option', new_callable=AsyncMock) as mock_select:
                mock_select.return_value = "BTC-25DEC21-50000-C"
                
                result = await trading_service.execute_trade(trade_request)
                
                assert result.success is True
                assert result.order_id == "test_order_12345"
                assert result.instrument_name == "BTC-25DEC21-50000-C"
                mock_buy.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_trade_account_not_found(self, trading_service):
        """Test trade execution with non-existent account."""
        trade_request = TradeRequest(
            account_name="nonexistent_account",
            side="buy",
            size=1.0,
            market_position="long",
            prev_market_position="flat",
            comment="Test trade",
            tv_id="test_123"
        )
        
        result = await trading_service.execute_trade(trade_request)
        
        assert result.success is False
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_no_suitable_option(self, trading_service):
        """Test trade execution when no suitable option is found."""
        trade_request = TradeRequest(
            account_name="test_account",
            side="buy",
            size=1.0,
            market_position="long",
            prev_market_position="flat",
            comment="Test trade",
            tv_id="test_123"
        )
        
        with patch.object(trading_service, '_select_best_option', new_callable=AsyncMock) as mock_select:
            mock_select.return_value = None
            
            result = await trading_service.execute_trade(trade_request)
            
            assert result.success is False
            assert "no suitable option" in result.message.lower()

    @pytest.mark.asyncio
    async def test_execute_trade_api_error(self, trading_service, mock_order_response):
        """Test trade execution with API error."""
        trade_request = TradeRequest(
            account_name="test_account",
            side="buy",
            size=1.0,
            market_position="long",
            prev_market_position="flat",
            comment="Test trade",
            tv_id="test_123"
        )
        
        with patch.object(trading_service.deribit_client, 'buy', new_callable=AsyncMock) as mock_buy:
            mock_buy.side_effect = Exception("API Error")
            
            with patch.object(trading_service, '_select_best_option', new_callable=AsyncMock) as mock_select:
                mock_select.return_value = "BTC-25DEC21-50000-C"
                
                result = await trading_service.execute_trade(trade_request)
                
                assert result.success is False
                assert "error" in result.message.lower()

    @pytest.mark.asyncio
    async def test_select_best_option_call(self, trading_service, mock_options_data):
        """Test option selection for call options."""
        with patch.object(trading_service.option_service, 'get_options', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "success": True,
                "data": {"instruments": mock_options_data["result"]}
            }
            
            result = await trading_service._select_best_option("test_account", "long", "BTC")
            
            # Should select the call option for long direction
            assert result == "BTC-25DEC21-50000-C"

    @pytest.mark.asyncio
    async def test_select_best_option_put(self, trading_service, mock_options_data):
        """Test option selection for put options."""
        with patch.object(trading_service.option_service, 'get_options', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "success": True,
                "data": {"instruments": mock_options_data["result"]}
            }
            
            result = await trading_service._select_best_option("test_account", "short", "BTC")
            
            # Should select the put option for short direction
            assert result == "BTC-25DEC21-45000-P"

    @pytest.mark.asyncio
    async def test_select_best_option_no_options(self, trading_service):
        """Test option selection when no options are available."""
        with patch.object(trading_service.option_service, 'get_options', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "success": True,
                "data": {"instruments": []}
            }
            
            result = await trading_service._select_best_option("test_account", "long", "BTC")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_mock_mode_behavior(self, trading_service):
        """Test behavior in mock mode."""
        trading_service.use_mock_mode = True
        
        trade_request = TradeRequest(
            account_name="test_account",
            side="buy",
            size=1.0,
            market_position="long",
            prev_market_position="flat",
            comment="Test trade",
            tv_id="test_123"
        )
        
        result = await trading_service.execute_trade(trade_request)
        
        assert result.success is True
        assert "mock" in result.message.lower()
        assert result.order_id.startswith("mock_order_")

    def test_determine_option_type_long(self, trading_service):
        """Test option type determination for long positions."""
        option_type = trading_service._determine_option_type("long")
        assert option_type == "call"

    def test_determine_option_type_short(self, trading_service):
        """Test option type determination for short positions."""
        option_type = trading_service._determine_option_type("short")
        assert option_type == "put"

    def test_determine_option_type_flat(self, trading_service):
        """Test option type determination for flat positions."""
        option_type = trading_service._determine_option_type("flat")
        assert option_type == "call"  # default

    def test_calculate_trade_size(self, trading_service):
        """Test trade size calculation."""
        # Test normal size
        size = trading_service._calculate_trade_size(1.5)
        assert size == 1.5
        
        # Test minimum size
        size = trading_service._calculate_trade_size(0.05)
        assert size == 0.1  # minimum trade size
        
        # Test maximum size
        size = trading_service._calculate_trade_size(100.0)
        assert size == 10.0  # maximum trade size

    @pytest.mark.asyncio
    async def test_position_change_detection(self, trading_service):
        """Test position change detection logic."""
        # Test entry signal (flat -> long)
        trade_request = TradeRequest(
            account_name="test_account",
            side="buy",
            size=1.0,
            market_position="long",
            prev_market_position="flat",
            comment="Entry signal",
            tv_id="test_123"
        )
        
        is_entry = trading_service._is_entry_signal(trade_request)
        assert is_entry is True
        
        # Test exit signal (long -> flat)
        trade_request.market_position = "flat"
        trade_request.prev_market_position = "long"
        trade_request.comment = "Exit signal"
        
        is_entry = trading_service._is_entry_signal(trade_request)
        assert is_entry is False
