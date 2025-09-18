"""
Trading and instruments routes
"""

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel

from ..config import ConfigLoader, settings
from ..services import DeribitClient, MockDeribitClient
from ..middleware.account_validation import validate_account_from_params
from ..models.deribit_types import DeribitOptionInstrument


class InstrumentsResponse(BaseModel):
    """Instruments list response"""
    mock_mode: bool
    currency: str
    kind: str
    count: int
    instruments: List[DeribitOptionInstrument]


class InstrumentResponse(BaseModel):
    """Single instrument response"""
    mock_mode: bool
    instrument_name: str
    instrument: Optional[Dict[str, Any]]


class AccountSummaryResponse(BaseModel):
    """Account summary response"""
    mock_mode: bool
    account_name: str
    currency: str
    summary: Optional[Dict[str, Any]]
    positions: Optional[List[Dict[str, Any]]]


trading_router = APIRouter()


def get_unified_client():
    """Get unified client (mock or real based on settings)"""
    if settings.use_mock_mode:
        return MockDeribitClient(), True
    else:
        return DeribitClient(), False


@trading_router.get("/api/instruments", response_model=InstrumentsResponse)
async def get_instruments(
    currency: str = Query(default="BTC", description="Currency type"),
    kind: str = Query(default="option", description="Instrument kind")
):
    """Get instruments endpoint"""
    try:
        # Use unified client, automatically handles Mock/Real mode
        client, is_mock = get_unified_client()
        
        try:
            instruments = await client.get_instruments(currency, kind)
            
            return InstrumentsResponse(
                mock_mode=is_mock,
                currency=currency,
                kind=kind,
                count=len(instruments),
                instruments=instruments
            )
        finally:
            await client.close()
            
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@trading_router.get("/api/instrument/{instrument_name}", response_model=InstrumentResponse)
async def get_instrument(
    instrument_name: str = Path(..., description="Instrument name")
):
    """Get single instrument endpoint"""
    try:
        if not instrument_name:
            raise HTTPException(
                status_code=400,
                detail="Instrument name is required"
            )
        
        # Use unified client, automatically handles Mock/Real mode
        client, is_mock = get_unified_client()
        
        try:
            instrument = await client.get_instrument(instrument_name)
            
            return InstrumentResponse(
                mock_mode=is_mock,
                instrument_name=instrument_name,
                instrument=instrument
            )
        finally:
            await client.close()
            
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@trading_router.get("/api/account/{account_name}/{currency}", response_model=AccountSummaryResponse)
async def get_account_positions(
    account_name: str = Path(..., description="Account name"),
    currency: str = Path(..., description="Currency"),
    validated_account=Depends(validate_account_from_params)
):
    """Get account positions endpoint"""
    try:
        currency_upper = currency.upper()
        
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        # Use unified client, automatically handles Mock/Real mode
        client, is_mock = get_unified_client()
        
        try:
            if is_mock:
                # Mock mode: return simulated data
                summary = await client.get_account_summary(account_name, currency_upper)
                positions = await client.get_positions(account_name, currency_upper)
                
                return AccountSummaryResponse(
                    mock_mode=True,
                    account_name=account_name,
                    currency=currency_upper,
                    summary=summary,
                    positions=positions
                )
            else:
                # Real mode: get actual data
                summary = await client.get_account_summary(account_name, currency_upper)
                positions = await client.get_positions(account_name, currency_upper)
                
                return AccountSummaryResponse(
                    mock_mode=False,
                    account_name=account_name,
                    currency=currency_upper,
                    summary=summary,
                    positions=positions
                )
        finally:
            await client.close()
            
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@trading_router.get("/api/connectivity")
async def test_connectivity():
    """Test API connectivity"""
    try:
        client, is_mock = get_unified_client()
        
        try:
            success = await client.test_connectivity()
            
            return {
                "success": success,
                "mock_mode": is_mock,
                "message": "Connectivity test successful" if success else "Connectivity test failed"
            }
        finally:
            await client.close()
            
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
