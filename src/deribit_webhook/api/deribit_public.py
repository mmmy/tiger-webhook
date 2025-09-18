"""
Deribit Public API client - no authentication required

Based on Deribit API v2.1.1 official documentation.
"""

from typing import Optional, Dict, Any, List, Literal
import httpx

from .config import DeribitConfig


class DeribitPublicAPI:
    """Deribit public API client class"""
    
    def __init__(self, config: DeribitConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Deribit-Options-Microservice-Python/1.1.1"
                }
            )
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_time(self) -> Dict[str, Any]:
        """
        Get server time
        GET /public/get_time
        """
        response = await self.client.get("/public/get_time")
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_instruments(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get list of options/futures instruments
        GET /public/get_instruments
        
        Args:
            params: Dictionary containing:
                - currency: str (BTC, ETH, etc.)
                - kind: str (option, future, spot) - optional
                - expired: bool (include expired) - optional
        """
        response = await self.client.get("/public/get_instruments", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_ticker(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get ticker information for option/future
        GET /public/ticker
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (option contract name)
        """
        response = await self.client.get("/public/ticker", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_order_book(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get order book
        GET /public/get_order_book
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (option contract name)
                - depth: int (depth, default 5) - optional
        """
        response = await self.client.get("/public/get_order_book", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_index_price(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get index price
        GET /public/get_index_price
        
        Args:
            params: Dictionary containing:
                - index_name: str (btc_usd, eth_usd)
        """
        response = await self.client.get("/public/get_index_price", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_last_trades_by_instrument(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get latest trades
        GET /public/get_last_trades_by_instrument
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (option contract name)
                - start_seq: int (start sequence number) - optional
                - end_seq: int (end sequence number) - optional
                - count: int (return count, default 10) - optional
                - include_old: bool (include old data) - optional
                - sorting: str ('asc' or 'desc') - optional
        """
        response = await self.client.get("/public/get_last_trades_by_instrument", params=params)
        response.raise_for_status()
        return response.json()["result"]["trades"]
    
    async def get_instrument(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get single instrument details
        GET /public/get_instrument
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (instrument name like BTC-PERPETUAL, BTC-25MAR23-50000-C)
        """
        response = await self.client.get("/public/get_instrument", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_currencies(self) -> List[Dict[str, Any]]:
        """
        Get available currencies
        GET /public/get_currencies
        """
        response = await self.client.get("/public/get_currencies")
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_book_summary_by_currency(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get book summary by currency
        GET /public/get_book_summary_by_currency
        
        Args:
            params: Dictionary containing:
                - currency: str (BTC, ETH, etc.)
                - kind: str (option, future, spot) - optional
        """
        response = await self.client.get("/public/get_book_summary_by_currency", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def get_book_summary_by_instrument(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get book summary by instrument
        GET /public/get_book_summary_by_instrument
        
        Args:
            params: Dictionary containing:
                - instrument_name: str (instrument name)
        """
        response = await self.client.get("/public/get_book_summary_by_instrument", params=params)
        response.raise_for_status()
        return response.json()["result"]
    
    async def test_connection(self) -> bool:
        """Test connection to Deribit API"""
        try:
            await self.get_time()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


def create_deribit_public_api(config: DeribitConfig) -> DeribitPublicAPI:
    """Factory function to create DeribitPublicAPI instance"""
    return DeribitPublicAPI(config)
