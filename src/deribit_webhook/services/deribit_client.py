"""
Deribit client service

Main client for interacting with Deribit API, combining public and private endpoints.
"""

from typing import Optional, List, Dict, Any, NamedTuple
import time
import math
from datetime import datetime

from ..config import ConfigLoader, settings
from ..api import (
    DeribitPublicAPI,
    DeribitPrivateAPI,
    DeribitConfig,
    AuthInfo,
    get_config_by_environment,
    create_auth_info
)
from ..models.deribit_types import DeribitOptionInstrument, OptionDetails
from .auth_service import AuthenticationService


class DeltaFilterResult(NamedTuple):
    """Delta filter result containing instrument and details"""
    instrument: DeribitOptionInstrument
    details: OptionDetails
    delta_distance: float
    spread_ratio: float


class DeribitOrderResponse:
    """Deribit order response wrapper"""
    
    def __init__(self, data: Dict[str, Any]):
        self.order = data.get("order", {})
        self.trades = data.get("trades", [])


class DeribitClient:
    """Main Deribit client combining public and private API functionality"""
    
    def __init__(self):
        self.config_loader = ConfigLoader.get_instance()
        self.auth_service = AuthenticationService.get_instance()
        
        # Create public API instance
        api_config = get_config_by_environment(settings.use_test_environment)
        self.public_api = DeribitPublicAPI(api_config)
        self.private_api: Optional[DeribitPrivateAPI] = None
        self._current_account: Optional[str] = None
    
    async def close(self):
        """Close all API clients"""
        await self.public_api.close()
        if self.private_api:
            await self.private_api.close()
    
    def _init_private_api(self, access_token: str):
        """Initialize private API with access token"""
        api_config = get_config_by_environment(settings.use_test_environment)
        auth_info = create_auth_info(access_token)
        self.private_api = DeribitPrivateAPI(api_config, auth_info)
    
    async def _ensure_private_api(self, account_name: str):
        """Ensure private API is initialized with valid token"""
        if self.private_api is None or self._current_account != account_name:
            # Get valid token for the account
            token = await self.auth_service.ensure_authenticated(account_name)
            self._init_private_api(token.access_token)
            self._current_account = account_name
    
    async def test_connectivity(self) -> bool:
        """Test basic connectivity to Deribit API"""
        try:
            print(f"Testing connectivity to: {self.public_api.config.base_url}")
            result = await self.public_api.get_time()
            print("Connectivity test successful:", result)
            return True
        except Exception as error:
            print(f"Connectivity test failed: {error}")
            return False
    
    async def get_instruments(
        self, 
        currency: str = "BTC", 
        kind: str = "option"
    ) -> List[DeribitOptionInstrument]:
        """
        Get option/future instruments list
        
        Args:
            currency: Currency type
            kind: Instrument type like 'option', 'future'
            
        Returns:
            List of instruments
        """
        try:
            result = await self.public_api.get_instruments({
                "currency": currency,
                "kind": kind,
                "expired": False
            })
            
            # Convert to DeribitOptionInstrument objects
            instruments = []
            for item in result:
                try:
                    instrument = DeribitOptionInstrument.model_validate(item)
                    instruments.append(instrument)
                except Exception as e:
                    print(f"Warning: Failed to parse instrument {item.get('instrument_name', 'unknown')}: {e}")
                    continue
            
            return instruments
            
        except Exception as error:
            print(f"Failed to get instruments: {error}")
            return []
    
    async def get_instrument(self, instrument_name: str) -> Optional[Dict[str, Any]]:
        """
        Get single instrument details
        
        Args:
            instrument_name: Instrument name like BTC-PERPETUAL, BTC-25MAR23-50000-C
            
        Returns:
            Instrument details or None
        """
        try:
            result = await self.public_api.get_instrument({
                "instrument_name": instrument_name
            })
            return result
        except Exception as error:
            print(f"Failed to get instrument {instrument_name}: {error}")
            return None
    
    async def get_option_details(self, instrument_name: str) -> Optional[OptionDetails]:
        """
        Get option detailed information
        
        Args:
            instrument_name: Option contract name
            
        Returns:
            Option details or None
        """
        try:
            result = await self.public_api.get_ticker({
                "instrument_name": instrument_name
            })
            
            if result:
                return OptionDetails.model_validate(result)
            return None
            
        except Exception as error:
            print(f"Failed to get option details for {instrument_name}: {error}")
            return None

    async def get_positions(self, account_name: str, currency: str = "BTC") -> List[Dict[str, Any]]:
        """
        Get positions for account
        
        Args:
            account_name: Account name
            currency: Currency (default BTC)
            
        Returns:
            List of positions
        """
        try:
            await self._ensure_private_api(account_name)
            
            if not self.private_api:
                raise Exception("Private API not initialized")
            
            result = await self.private_api.get_positions({
                "currency": currency
            })
            return result
            
        except Exception as error:
            print(f"Failed to get positions for {account_name}: {error}")
            return []
    

    async def get_all_positions(self, account_name: str, kind: str = "option") -> List[Dict[str, Any]]:
        """Get all positions for an account, optionally filtered by kind."""
        try:
            await self._ensure_private_api(account_name)
            if not self.private_api:
                raise Exception("Private API not initialized")

            params: Dict[str, Any] = {}
            if kind:
                params["kind"] = kind

            positions = await self.private_api.get_positions(params or None)
            if not positions:
                return []

            if kind:
                positions = [pos for pos in positions if pos.get("kind") == kind]

            for position in positions:
                position.setdefault("account_name", account_name)

            return positions

        except Exception as error:
            print(f"Failed to get all positions for {account_name}: {error}")
            return []

    async def get_account_summary(self, account_name: str, currency: str = "BTC") -> Optional[Dict[str, Any]]:
        """
        Get account summary
        
        Args:
            account_name: Account name
            currency: Currency (default BTC)
            
        Returns:
            Account summary or None
        """
        try:
            await self._ensure_private_api(account_name)
            
            if not self.private_api:
                raise Exception("Private API not initialized")
            
            result = await self.private_api.get_account_summary({
                "currency": currency,
                "extended": True
            })
            return result
            
        except Exception as error:
            print(f"Failed to get account summary for {account_name}: {error}")
            return None
    
    async def place_buy_order(
        self, 
        account_name: str, 
        instrument_name: str, 
        amount: float, 
        **kwargs
    ) -> Optional[DeribitOrderResponse]:
        """
        Place buy order
        
        Args:
            account_name: Account name
            instrument_name: Instrument name
            amount: Order amount
            **kwargs: Additional order parameters
            
        Returns:
            Order response or None
        """
        try:
            await self._ensure_private_api(account_name)
            
            if not self.private_api:
                raise Exception("Private API not initialized")
            
            params = {
                "instrument_name": instrument_name,
                "amount": amount,
                **kwargs
            }
            
            result = await self.private_api.buy(params)
            return DeribitOrderResponse(result)
            
        except Exception as error:
            print(f"Failed to place buy order: {error}")
            return None
    
    async def place_sell_order(
        self, 
        account_name: str, 
        instrument_name: str, 
        amount: float, 
        **kwargs
    ) -> Optional[DeribitOrderResponse]:
        """
        Place sell order
        
        Args:
            account_name: Account name
            instrument_name: Instrument name
            amount: Order amount
            **kwargs: Additional order parameters
            
        Returns:
            Order response or None
        """
        try:
            await self._ensure_private_api(account_name)
            
            if not self.private_api:
                raise Exception("Private API not initialized")
            
            params = {
                "instrument_name": instrument_name,
                "amount": amount,
                **kwargs
            }
            
            result = await self.private_api.sell(params)
            return DeribitOrderResponse(result)
            
        except Exception as error:
            print(f"Failed to place sell order: {error}")
            return None

    async def edit_order(
        self,
        account_name: str,
        order_id: str,
        amount: float,
        price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Edit existing order parameters"""
        try:
            await self._ensure_private_api(account_name)
            if not self.private_api:
                raise Exception("Private API not initialized")

            params = {
                "order_id": order_id,
                "amount": amount
            }
            if price is not None:
                params["price"] = price

            return await self.private_api.edit(params)

        except Exception as error:
            print(f"Failed to edit order {order_id}: {error}")
            return None

    async def get_open_orders(
        self,
        account_name: str,
        currency: Optional[str] = None,
        kind: Optional[str] = None,
        order_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get open orders for an account"""
        try:
            await self._ensure_private_api(account_name)
            if not self.private_api:
                raise Exception("Private API not initialized")

            params: Dict[str, Any] = {}
            if currency:
                params["currency"] = currency
            if kind:
                params["kind"] = kind
            if order_type:
                params["type"] = order_type

            return await self.private_api.get_open_orders(params or None)

        except Exception as error:
            print(f"Failed to get open orders for {account_name}: {error}")
            return []

    async def get_order_state(
        self,
        account_name: str,
        order_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get order state for specific order"""
        try:
            await self._ensure_private_api(account_name)
            if not self.private_api:
                raise Exception("Private API not initialized")

            return await self.private_api.get_order_state({"order_id": order_id})

        except Exception as error:
            print(f"Failed to get order state for {order_id}: {error}")
            return None

    async def get_open_orders_by_instrument(
        self,
        account_name: str,
        instrument_name: str
    ) -> List[Dict[str, Any]]:
        """Get open orders for a specific instrument"""
        try:
            await self._ensure_private_api(account_name)
            if not self.private_api:
                raise Exception("Private API not initialized")

            return await self.private_api.get_open_orders_by_instrument({"instrument_name": instrument_name})

        except Exception as error:
            print(f"Failed to get open orders for instrument {instrument_name}: {error}")
            return []

    async def get_instrument_by_delta(
        self,
        currency: str,
        min_expired_days: int,
        delta: float,
        long_side: bool,
        underlying_asset: str = ""
    ) -> Optional[DeltaFilterResult]:
        """
        Find the best option instrument by target delta value

        Args:
            currency: Currency (e.g., 'BTC', 'ETH', 'USDC')
            min_expired_days: Minimum expiry days
            delta: Target delta value
            long_side: True for call options, False for put options
            underlying_asset: Underlying asset for USDC options

        Returns:
            DeltaFilterResult or None if no suitable option found
        """
        try:
            print(f"🔍 Finding option by delta: {currency}, minExpiredDays: {min_expired_days}, "
                  f"delta: {delta}, longSide: {long_side}"
                  f"{f', underlying: {underlying_asset}' if underlying_asset else ''}")

            # 1. Get all option instruments
            instruments = await self.get_instruments(currency, "option")
            if not instruments:
                print("❌ No instruments found")
                return None

            # 1.5. Filter by underlying asset for USDC options
            filtered_by_underlying = instruments
            if underlying_asset and currency == 'USDC':
                filtered_by_underlying = [
                    inst for inst in instruments
                    if inst.instrument_name.startswith(f"{underlying_asset}_USDC-")
                ]
                print(f"📊 Filtered by underlying asset ({underlying_asset}): {len(filtered_by_underlying)} instruments")

                if not filtered_by_underlying:
                    print(f"❌ No {underlying_asset}_USDC instruments found")
                    return None

            # 2. Filter by option type
            option_type = "call" if long_side else "put"
            filtered_instruments = [
                inst for inst in filtered_by_underlying
                if inst.option_type == option_type
            ]
            print(f"📊 Filtered by option type ({option_type}): {len(filtered_instruments)} instruments")

            if not filtered_instruments:
                print(f"❌ No {option_type} options found")
                return None

            # 3. Group by expiry and find nearest two expiry dates
            now = datetime.now()
            min_expiry_time = datetime.fromtimestamp(
                now.timestamp() + (min_expired_days - 1) * 24 * 60 * 60
            )

            # Group all instruments by expiry
            all_expiry_groups: Dict[int, List[DeribitOptionInstrument]] = {}
            for instrument in filtered_instruments:
                expiry_timestamp = instrument.expiration_timestamp
                if expiry_timestamp not in all_expiry_groups:
                    all_expiry_groups[expiry_timestamp] = []
                all_expiry_groups[expiry_timestamp].append(instrument)

            if not all_expiry_groups:
                print("❌ No instruments found for expiry grouping")
                return None

            # Calculate distances and sort by distance to min expiry
            expiry_distances = [
                {
                    'expiry_timestamp': expiry_timestamp,
                    'distance': abs(expiry_timestamp - min_expiry_time.timestamp() * 1000)
                }
                for expiry_timestamp in all_expiry_groups.keys()
            ]
            expiry_distances.sort(key=lambda x: x['distance'])

            # Select nearest two expiry dates
            nearest_two_expiries = [item['expiry_timestamp'] for item in expiry_distances[:2]]

            print(f"📅 Found {len(nearest_two_expiries)} nearest expiry dates to minimum expiry time")
            print(f"📅 Minimum expiry time: {min_expiry_time.strftime('%Y-%m-%d')}")

            for i, expiry in enumerate(nearest_two_expiries):
                expiry_date = datetime.fromtimestamp(expiry / 1000)
                distance = abs(expiry - min_expiry_time.timestamp() * 1000)
                days_difference = round(distance / (24 * 60 * 60 * 1000))
                print(f"📅 Expiry {i + 1}: {expiry_date.strftime('%Y-%m-%d')} ({days_difference} days from min expiry)")

            # 4. Process each expiry date and find best options
            candidate_options: List[DeltaFilterResult] = []

            for expiry_timestamp in nearest_two_expiries:
                instruments_for_expiry = all_expiry_groups[expiry_timestamp]
                expiry_date = datetime.fromtimestamp(expiry_timestamp / 1000)
                print(f"📊 Processing {len(instruments_for_expiry)} instruments for expiry {expiry_date.strftime('%Y-%m-%d')}")

                options_with_delta: List[DeltaFilterResult] = []

                # Get detailed information for each instrument
                for instrument in instruments_for_expiry:
                    try:
                        details = await self.get_option_details(instrument.instrument_name)
                        if (details and details.greeks and
                            details.greeks.delta is not None):

                            instrument_delta = details.greeks.delta
                            delta_distance = abs(instrument_delta - delta)

                            # Calculate spread ratio
                            spread_ratio = self._calculate_spread_ratio(
                                details.best_bid_price,
                                details.best_ask_price
                            )

                            options_with_delta.append(DeltaFilterResult(
                                instrument=instrument,
                                details=details,
                                delta_distance=delta_distance,
                                spread_ratio=spread_ratio
                            ))

                    except Exception as error:
                        print(f"⚠️ Failed to get details for {instrument.instrument_name}: {error}")

                # Print delta information
                for i, option in enumerate(options_with_delta):
                    delta_val = option.details.greeks.delta
                    print(f"  {i + 1}. {option.instrument.instrument_name}: "
                          f"Delta: {delta_val:.4f}, "
                          f"Best Bid: {option.details.best_bid_price}, "
                          f"Best Ask: {option.details.best_ask_price}")

                # Sort by delta distance and select top 2
                options_with_delta.sort(key=lambda x: x.delta_distance)
                top_2_for_expiry = options_with_delta[:2]

                print(f"🎯 Selected {len(top_2_for_expiry)} options for expiry {expiry_date.strftime('%Y-%m-%d')}")
                for option in top_2_for_expiry:
                    delta_val = option.details.greeks.delta
                    print(f"   - {option.instrument.instrument_name} "
                          f"(Delta: {delta_val:.3f}, Distance: {option.delta_distance:.3f}), "
                          f"盘口价差比例: {option.spread_ratio * 100:.2f}%")

                candidate_options.extend(top_2_for_expiry)

            # Filter out options with invalid spread ratios
            candidate_options = [
                op for op in candidate_options
                if 0 < op.spread_ratio < 1
            ]

            if not candidate_options:
                print("❌ No candidate options found with valid delta data")
                return None

            # 5. Select the best option
            best_option = min(candidate_options, key=lambda x: (x.delta_distance, x.spread_ratio))

            print(f"✅ Selected option: {best_option.instrument.instrument_name}")
            delta_val = best_option.details.greeks.delta
            print(f"📊 Delta: {delta_val} (target: {delta}, distance: {best_option.delta_distance})")
            print(f"💰 Spread ratio: {best_option.spread_ratio * 100:.2f}%")

            return best_option

        except Exception as error:
            print(f"❌ Error in get_instrument_by_delta: {error}")
            return None

    def _calculate_spread_ratio(self, best_bid: float, best_ask: float) -> float:
        """Calculate spread ratio between bid and ask prices"""
        if best_bid <= 0 or best_ask <= 0 or best_ask <= best_bid:
            return 1.0  # Invalid spread

        mid_price = (best_bid + best_ask) / 2
        if mid_price <= 0:
            return 1.0

        return (best_ask - best_bid) / mid_price
