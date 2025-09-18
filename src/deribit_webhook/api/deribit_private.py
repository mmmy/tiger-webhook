"""
Deribit Private API client - requires authentication

Based on Deribit API v2.1.1 official documentation.
"""

from typing import Optional, Dict, Any, List, Literal
import httpx

from .config import DeribitConfig, AuthInfo


class DeribitPrivateAPI:
    """Deribit private API client class"""
    
    def __init__(self, config: DeribitConfig, auth: AuthInfo):
        self.config = config
        self.auth = auth
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Deribit-Options-Microservice-Python/1.1.1",
                    "Authorization": f"{self.auth.token_type} {self.auth.access_token}"
                }
            )
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_account_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get account summary
        GET /private/get_account_summary
        
        Args:
            params: Dictionary containing:
                - currency: str (BTC, ETH, etc.)
                - extended: bool (extended info) - optional
        """
        response = await self.client.get("/private/get_account_summary", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_positions(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get positions
        GET /private/get_positions
        
        Args:
            params: Dictionary containing:
                - currency: str (BTC, ETH, etc.)
                - kind: str (option, future, spot) - optional
        """
        response = await self.client.get("/private/get_positions", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_position(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get single position
        GET /private/get_position
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (instrument name)
        """
        response = await self.client.get("/private/get_position", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def buy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place buy order
        GET /private/buy
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (instrument name)
                - amount: float (order amount)
                - type: str (order type: limit, market, stop_limit, stop_market) - optional
                - price: float (limit price) - optional for market orders
                - time_in_force: str (good_til_cancelled, fill_or_kill, immediate_or_cancel) - optional
                - max_show: float (max visible amount) - optional
                - post_only: bool (post only flag) - optional
                - reduce_only: bool (reduce only flag) - optional
                - stop_price: float (stop price for stop orders) - optional
                - trigger: str (index_price, mark_price, last_price) - optional
                - advanced: str (usd, implv) - optional
                - label: str (order label) - optional
        """
        response = await self.client.get("/private/buy", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def sell(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place sell order
        GET /private/sell
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (instrument name)
                - amount: float (order amount)
                - type: str (order type: limit, market, stop_limit, stop_market) - optional
                - price: float (limit price) - optional for market orders
                - time_in_force: str (good_til_cancelled, fill_or_kill, immediate_or_cancel) - optional
                - max_show: float (max visible amount) - optional
                - post_only: bool (post only flag) - optional
                - reduce_only: bool (reduce only flag) - optional
                - stop_price: float (stop price for stop orders) - optional
                - trigger: str (index_price, mark_price, last_price) - optional
                - advanced: str (usd, implv) - optional
                - label: str (order label) - optional
        """
        response = await self.client.get("/private/sell", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def edit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Edit existing order"""
        response = await self.client.get("/private/edit", params=params)
        response.raise_for_status()
        return response.json()["result"]

    async def cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cancel order
        GET /private/cancel
        
        Args:
            params: Dictionary containing:
                - order_id: str (order ID)
        """
        response = await self.client.get("/private/cancel", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def cancel_all(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Cancel all orders
        GET /private/cancel_all
        
        Args:
            params: Dictionary containing (optional):
                - currency: str (BTC, ETH, etc.) - optional
                - kind: str (option, future, spot) - optional
                - type: str (all, limit, stop_all, stop_limit, stop_market) - optional
        """
        response = await self.client.get("/private/cancel_all", params=params or {})
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_open_orders(self, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get open orders
        GET /private/get_open_orders
        
        Args:
            params: Dictionary containing (optional):
                - currency: str (BTC, ETH, etc.) - optional
                - kind: str (option, future, spot) - optional
                - type: str (all, limit, stop_all, stop_limit, stop_market) - optional
        """
        response = await self.client.get("/private/get_open_orders", params=params or {})
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_open_orders_by_instrument(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get open orders for specific instrument"""
        response = await self.client.get("/private/get_open_orders_by_instrument", params=params)
        response.raise_for_status()
        return response.json().get("result", [])

    async def get_order_history(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get order history
        GET /private/get_order_history
        
        Args:
            params: Dictionary containing:
                - currency: str (BTC, ETH, etc.)
                - kind: str (option, future, spot) - optional
                - count: int (number of orders to return) - optional
                - offset: int (offset) - optional
                - include_old: bool (include old orders) - optional
                - include_unfilled: bool (include unfilled orders) - optional
        """
        response = await self.client.get("/private/get_order_history", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_user_trades(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get user trades
        GET /private/get_user_trades
        
        Args:
            params: Dictionary containing:
                - currency: str (BTC, ETH, etc.)
                - kind: str (option, future, spot) - optional
                - start_timestamp: int (start timestamp) - optional
                - end_timestamp: int (end timestamp) - optional
                - count: int (number of trades to return) - optional
                - include_old: bool (include old trades) - optional
                - sorting: str (asc, desc, default) - optional
        """
        response = await self.client.get("/private/get_user_trades", params=params)
        response.raise_for_status()
        return response.json()["result"]["trades"]
    
    async def get_order_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get order state
        GET /private/get_order_state
        
        Args:
            params: Dictionary containing:
                - order_id: str (order ID)
        """
        response = await self.client.get("/private/get_order_state", params=params)
        response.raise_for_status()
        return response.json()["result"]


def create_deribit_private_api(config: DeribitConfig, auth: AuthInfo) -> DeribitPrivateAPI:
    """Factory function to create DeribitPrivateAPI instance"""
    return DeribitPrivateAPI(config, auth)
