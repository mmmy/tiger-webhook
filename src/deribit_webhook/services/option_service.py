"""
Option service class - provides option-related functionality
"""

from typing import Optional, List
from datetime import datetime

from deribit_webhook.config import ConfigLoader, settings
from deribit_webhook.models.deribit_types import DeribitOptionInstrument, OptionListResult
from deribit_webhook.models.trading_types import OptionListParams
from .auth_service import AuthenticationService
from .deribit_client import DeribitClient
from .mock_deribit_client import MockDeribitClient


class OptionService:
    """Option service class - provides option-related functionality"""
    
    def __init__(
        self,
        config_loader: Optional[ConfigLoader] = None,
        auth_service: Optional[AuthenticationService] = None,
        deribit_client: Optional[DeribitClient] = None,
        mock_client: Optional[MockDeribitClient] = None
    ):
        # Support dependency injection while maintaining backward compatibility
        self.config_loader = config_loader or ConfigLoader.get_instance()
        self.auth_service = auth_service or AuthenticationService.get_instance()
        self.deribit_client = deribit_client or DeribitClient()
        self.mock_client = mock_client or MockDeribitClient()
        self.use_mock_mode = settings.use_mock_mode
    
    async def close(self):
        """Close service and cleanup resources"""
        await self.deribit_client.close()
        await self.mock_client.close()
    
    async def get_options_list(
        self,
        params: OptionListParams,
        account_name: Optional[str] = None
    ) -> OptionListResult:
        """
        Get options list
        
        Args:
            params: Option list query parameters
            account_name: Optional account name for authentication
            
        Returns:
            Option list query result
        """
        try:
            print(f"🔍 Getting options list for {params.underlying}, direction: {params.direction}")
            
            # 1. Get raw options list
            instruments: List[DeribitOptionInstrument] = []
            
            if self.use_mock_mode:
                # Use mock data
                mock_data = await self.mock_client.get_instruments(params.underlying, "option")
                instruments = mock_data
            else:
                # Use real API data
                real_data = await self.deribit_client.get_instruments(params.underlying, "option")
                instruments = real_data
            
            if not instruments:
                return OptionListResult(
                    success=False,
                    message=f"No options found for {params.underlying}",
                    error="Empty instruments list"
                )
            
            # 2. Filter by direction (long -> call, short -> put)
            # Note: This is simplified logic, in actual trading long/short can apply to both calls and puts
            option_type = "call" if params.direction == "long" else "put"
            filtered_instruments = [
                instrument for instrument in instruments
                if instrument.option_type == option_type
            ]
            
            # 3. Apply additional filtering conditions
            if params.min_strike is not None:
                filtered_instruments = [
                    instrument for instrument in filtered_instruments
                    if instrument.strike >= params.min_strike
                ]
            
            if params.max_strike is not None:
                filtered_instruments = [
                    instrument for instrument in filtered_instruments
                    if instrument.strike <= params.max_strike
                ]
            
            if params.min_expiry is not None:
                min_timestamp = int(datetime.fromisoformat(params.min_expiry).timestamp() * 1000)
                filtered_instruments = [
                    instrument for instrument in filtered_instruments
                    if instrument.expiration_timestamp >= min_timestamp
                ]
            
            if params.max_expiry is not None:
                max_timestamp = int(datetime.fromisoformat(params.max_expiry).timestamp() * 1000)
                filtered_instruments = [
                    instrument for instrument in filtered_instruments
                    if instrument.expiration_timestamp <= max_timestamp
                ]
            
            # 4. Filter out expired options if not requested
            if not params.expired:
                current_timestamp = int(datetime.now().timestamp() * 1000)
                filtered_instruments = [
                    instrument for instrument in filtered_instruments
                    if instrument.expiration_timestamp > current_timestamp
                ]
            
            # 5. Sort by expiration date and strike price
            filtered_instruments.sort(key=lambda x: (x.expiration_timestamp, x.strike))
            
            print(f"✅ Found {len(filtered_instruments)} {option_type} options for {params.underlying}")
            
            return OptionListResult(
                success=True,
                message=f"Found {len(filtered_instruments)} options",
                data={
                    "instruments": filtered_instruments,
                    "total": len(instruments),
                    "filtered": len(filtered_instruments),
                    "underlying": params.underlying,
                    "direction": params.direction
                }
            )
            
        except Exception as error:
            print(f"❌ Failed to get options list: {error}")
            return OptionListResult(
                success=False,
                message="Failed to get options list",
                error=str(error)
            )
    
    async def get_option_by_delta(
        self,
        underlying: str,
        option_type: str,
        target_delta: float,
        min_expiry_days: Optional[int] = None,
        account_name: Optional[str] = None
    ) -> Optional[DeribitOptionInstrument]:
        """
        Find option by target delta value
        
        Args:
            underlying: Underlying asset (e.g., 'BTC', 'ETH')
            option_type: Option type ('call' or 'put')
            target_delta: Target delta value
            min_expiry_days: Minimum days to expiry
            account_name: Optional account name for authentication
            
        Returns:
            Best matching option or None
        """
        try:
            print(f"🎯 Finding {option_type} option with delta ~{target_delta} for {underlying}")
            
            # Get all options of the specified type
            direction = "long" if option_type == "call" else "short"
            params = OptionListParams(
                underlying=underlying,
                direction=direction,
                expired=False
            )
            
            # Add minimum expiry filter if specified
            if min_expiry_days:
                min_expiry_date = datetime.now().timestamp() + (min_expiry_days * 24 * 3600)
                params.min_expiry = datetime.fromtimestamp(min_expiry_date).isoformat()
            
            result = await self.get_options_list(params, account_name)
            
            if not result.success or not result.data:
                return None
            
            instruments = result.data.get("instruments", [])
            if not instruments:
                return None
            
            # For now, return the first instrument as a placeholder
            # In a real implementation, you would:
            # 1. Get option details with Greeks for each instrument
            # 2. Calculate delta distance from target
            # 3. Return the closest match
            
            print(f"📊 Mock: Returning first {option_type} option as delta match")
            return instruments[0]
            
        except Exception as error:
            print(f"❌ Failed to find option by delta: {error}")
            return None
    
    async def calculate_option_price(
        self,
        instrument_name: str,
        account_name: Optional[str] = None
    ) -> Optional[float]:
        """
        Calculate smart option price
        
        Args:
            instrument_name: Option instrument name
            account_name: Optional account name for authentication
            
        Returns:
            Calculated price or None
        """
        try:
            if self.use_mock_mode:
                # Return mock price
                return 0.05
            
            # Get option details
            option_details = await self.deribit_client.get_option_details(instrument_name)
            
            if not option_details:
                return None
            
            # Use mark price as smart price
            return option_details.mark_price
            
        except Exception as error:
            print(f"❌ Failed to calculate option price: {error}")
            return None
