"""
Mock Deribit client for testing and development

Provides simulated responses without making real API calls.
"""

import time
import random
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from deribit_webhook.models.deribit_types import DeribitOptionInstrument, OptionDetails, OptionGreeks
from .deribit_client import DeribitOrderResponse


class MockDeribitClient:
    """Mock Deribit client for testing purposes"""
    
    def __init__(self):
        self._mock_positions: Dict[str, List[Dict[str, Any]]] = {}
        self._mock_orders: Dict[str, Dict[str, Any]] = {}
        self._order_counter = 1000
    
    async def close(self):
        """Mock close method"""
        pass
    
    async def test_connectivity(self) -> bool:
        """Mock connectivity test - always returns True"""
        print("✅ Mock mode - connectivity test passed")
        return True
    
    def _generate_mock_instrument(self, currency: str = "BTC", option_type: str = "call") -> DeribitOptionInstrument:
        """Generate a mock option instrument"""
        strike_prices = [30000, 35000, 40000, 45000, 50000, 55000, 60000, 65000, 70000]
        strike = random.choice(strike_prices)
        
        # Generate expiry date (1-90 days from now)
        days_to_expiry = random.randint(1, 90)
        expiry_date = datetime.now() + timedelta(days=days_to_expiry)
        expiry_str = expiry_date.strftime("%d%b%y").upper()
        
        option_suffix = "C" if option_type == "call" else "P"
        instrument_name = f"{currency}-{expiry_str}-{strike}-{option_suffix}"
        
        return DeribitOptionInstrument(
            instrument_name=instrument_name,
            currency=currency,
            kind="option",
            option_type=option_type,
            strike=float(strike),
            expiration_timestamp=int(expiry_date.timestamp() * 1000),
            tick_size=0.0005,
            min_trade_amount=0.1,
            contract_size=1.0,
            is_active=True,
            settlement_period="month",
            creation_timestamp=int(time.time() * 1000),
            base_currency=currency,
            quote_currency="USD"
        )
    
    async def get_instruments(
        self, 
        currency: str = "BTC", 
        kind: str = "option"
    ) -> List[DeribitOptionInstrument]:
        """Mock get instruments - returns sample instruments"""
        print(f"🎭 Mock mode - generating sample {kind} instruments for {currency}")
        
        instruments = []
        
        if kind == "option":
            # Generate some call and put options
            for _ in range(10):
                instruments.append(self._generate_mock_instrument(currency, "call"))
            for _ in range(10):
                instruments.append(self._generate_mock_instrument(currency, "put"))
        
        return instruments
    
    async def get_instrument(self, instrument_name: str) -> Optional[Dict[str, Any]]:
        """Mock get single instrument"""
        print(f"🎭 Mock mode - returning mock instrument details for {instrument_name}")
        
        return {
            "instrument_name": instrument_name,
            "currency": "BTC",
            "kind": "option",
            "option_type": "call",
            "strike": 50000.0,
            "expiration_timestamp": int((datetime.now() + timedelta(days=30)).timestamp() * 1000),
            "tick_size": 0.0005,
            "min_trade_amount": 0.1,
            "contract_size": 1.0,
            "is_active": True,
            "settlement_period": "month",
            "creation_timestamp": int(time.time() * 1000),
            "base_currency": "BTC",
            "quote_currency": "USD"
        }
    
    async def get_option_details(self, instrument_name: str) -> Optional[OptionDetails]:
        """Mock get option details"""
        print(f"🎭 Mock mode - returning mock option details for {instrument_name}")
        
        # Generate realistic mock Greeks
        mock_greeks = OptionGreeks(
            delta=random.uniform(0.1, 0.9),
            gamma=random.uniform(0.001, 0.01),
            theta=random.uniform(-0.1, -0.01),
            vega=random.uniform(0.1, 1.0),
            rho=random.uniform(0.01, 0.1)
        )
        
        return OptionDetails(
            instrument_name=instrument_name,
            underlying_index="btc_usd",
            underlying_price=45000.0,
            timestamp=int(time.time() * 1000),
            state="open",
            settlement_price=0.0,
            open_interest=100.0,
            min_price=0.0001,
            max_price=1.0,
            mark_price=0.05,
            mark_iv=0.8,
            last_price=0.048,
            interest_rate=0.05,
            instrument_type="option",
            index_price=45000.0,
            greeks=mock_greeks,
            bid_iv=0.78,
            best_bid_price=0.047,
            best_bid_amount=10.0,
            best_ask_price=0.053,
            best_ask_amount=15.0,
            ask_iv=0.82
        )
    
    async def get_positions(self, account_name: str, currency: str = "BTC") -> List[Dict[str, Any]]:
        """Mock get positions"""
        print(f"🎭 Mock mode - returning mock positions for {account_name}")
        
        # Return cached positions or generate new ones
        if account_name not in self._mock_positions:
            self._mock_positions[account_name] = [
                {
                    "instrument_name": "BTC-29MAR24-50000-C",
                    "size": 2.0,
                    "direction": "buy",
                    "average_price": 0.05,
                    "mark_price": 0.048,
                    "unrealized_pnl": -0.004,
                    "total_profit_loss": -0.004,
                    "maintenance_margin": 0.1,
                    "initial_margin": 0.15,
                    "delta": 0.6,
                    "gamma": 0.005,
                    "theta": -0.02,
                    "vega": 0.3,
                    "kind": "option"
                }
            ]
        
        return self._mock_positions[account_name]
    
    async def get_account_summary(self, account_name: str, currency: str = "BTC") -> Optional[Dict[str, Any]]:
        """Mock get account summary"""
        print(f"🎭 Mock mode - returning mock account summary for {account_name}")
        
        return {
            "currency": currency,
            "balance": 1.5,
            "equity": 1.48,
            "available_funds": 1.3,
            "maintenance_margin": 0.18,
            "initial_margin": 0.2,
            "margin_balance": 1.48,
            "total_pl": -0.02,
            "session_rpl": 0.0,
            "session_upl": -0.02,
            "options_value": 0.096,
            "options_pl": -0.008,
            "options_session_rpl": 0.0,
            "options_session_upl": -0.008,
            "options_delta": 1.2,
            "options_gamma": 0.01,
            "options_theta": -0.04,
            "options_vega": 0.6
        }
    
    async def get_open_orders(
        self,
        account_name: str,
        currency: Optional[str] = None,
        kind: Optional[str] = None,
        order_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Mock get open orders for account"""
        print(f"?? Mock mode - returning open orders for {account_name}")
        return list(self._mock_orders.values())

    def _generate_order_id(self) -> str:
        """Generate mock order ID"""
        order_id = f"mock_order_{self._order_counter}"
        self._order_counter += 1
        return order_id
    
    async def place_buy_order(
        self, 
        account_name: str, 
        instrument_name: str, 
        amount: float, 
        **kwargs
    ) -> Optional[DeribitOrderResponse]:
        """Mock place buy order"""
        print(f"🎭 Mock mode - placing mock buy order for {account_name}: {amount} {instrument_name}")
        
        order_id = self._generate_order_id()
        price = kwargs.get("price", 0.05)  # Default mock price
        
        mock_order = {
            "order_id": order_id,
            "instrument_name": instrument_name,
            "direction": "buy",
            "amount": amount,
            "price": price,
            "order_type": kwargs.get("type", "limit"),
            "order_state": "filled",  # Mock as immediately filled
            "filled_amount": amount,
            "average_price": price,
            "creation_timestamp": int(time.time() * 1000),
            "last_update_timestamp": int(time.time() * 1000),
            "label": kwargs.get("label", "mock_order")
        }
        
        mock_trade = {
            "trade_id": f"mock_trade_{int(time.time())}",
            "instrument_name": instrument_name,
            "order_id": order_id,
            "direction": "buy",
            "amount": amount,
            "price": price,
            "timestamp": int(time.time() * 1000),
            "role": "taker",
            "fee": amount * price * 0.0003,  # Mock 0.03% fee
            "fee_currency": "BTC"
        }
        
        self._mock_orders[order_id] = mock_order
        
        return DeribitOrderResponse({
            "order": mock_order,
            "trades": [mock_trade]
        })
    
    async def place_sell_order(
        self, 
        account_name: str, 
        instrument_name: str, 
        amount: float, 
        **kwargs
    ) -> Optional[DeribitOrderResponse]:
        """Mock place sell order"""
        print(f"🎭 Mock mode - placing mock sell order for {account_name}: {amount} {instrument_name}")
        
        order_id = self._generate_order_id()
        price = kwargs.get("price", 0.05)  # Default mock price
        
        mock_order = {
            "order_id": order_id,
            "instrument_name": instrument_name,
            "direction": "sell",
            "amount": amount,
            "price": price,
            "order_type": kwargs.get("type", "limit"),
            "order_state": "filled",  # Mock as immediately filled
            "filled_amount": amount,
            "average_price": price,
            "creation_timestamp": int(time.time() * 1000),
            "last_update_timestamp": int(time.time() * 1000),
            "label": kwargs.get("label", "mock_order")
        }
        
        mock_trade = {
            "trade_id": f"mock_trade_{int(time.time())}",
            "instrument_name": instrument_name,
            "order_id": order_id,
            "direction": "sell",
            "amount": amount,
            "price": price,
            "timestamp": int(time.time() * 1000),
            "role": "taker",
            "fee": amount * price * 0.0003,  # Mock 0.03% fee
            "fee_currency": "BTC"
        }
        
        self._mock_orders[order_id] = mock_order
        
        return DeribitOrderResponse({
            "order": mock_order,
            "trades": [mock_trade]
        })
