"""
Trading and instruments routes
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel

from ..config import ConfigLoader, settings
from ..services import TigerClient, get_trading_client
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


class TigerExpiration(BaseModel):
    """Tiger option expiration entry"""
    timestamp: int
    date: str
    days_to_expiry: int


class TigerUnderlying(BaseModel):
    """Tiger option underlying entry"""
    symbol: str
    name: Optional[str] = None
    market: Optional[str] = None
    currency: Optional[str] = None


class TigerUnderlyingsResponse(BaseModel):
    """Tiger option underlyings response"""
    success: bool
    message: str
    account_name: str
    mock_mode: bool
    count: int
    underlyings: List[TigerUnderlying]


class TigerExpirationsResponse(BaseModel):
    """Tiger option expirations response"""
    success: bool
    message: str
    account_name: str
    underlying: str
    mock_mode: bool
    count: int
    expirations: List[TigerExpiration]


class TigerOptionsResponse(BaseModel):
    """Tiger options list response"""
    success: bool
    message: str
    account_name: str
    underlying: str
    expiry_timestamp: int
    mock_mode: bool
    count: int
    options: List[Dict[str, Any]]


trading_router = APIRouter()


def _normalize_underlying(symbol: Optional[str]) -> str:
    """Normalize user-supplied underlying (strip suffix like .US)."""
    if not symbol:
        return ""

    trimmed = symbol.strip().upper()
    if not trimmed:
        return ""

    if '.' in trimmed:
        base, _, _ = trimmed.partition('.')
        if base:
            trimmed = base

    return trimmed


def get_unified_client():
    """Get unified client"""
    return get_trading_client(), settings.use_mock_mode


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


@trading_router.get("/api/tiger/underlyings", response_model=TigerUnderlyingsResponse)
async def get_tiger_underlyings(
    account_name: Optional[str] = Query(None, alias="accountName", description="Account name defined in configuration"),
    market: Optional[str] = Query(None, description="Tiger market identifier, e.g. 'US'")
) -> TigerUnderlyingsResponse:
    """List available option underlyings from Tiger"""
    config_loader = ConfigLoader.get_instance()

    if account_name:
        target_account = config_loader.get_account_by_name(account_name)
        if not target_account:
            raise HTTPException(status_code=404, detail=f"Account not found: {account_name}")
        if not target_account.enabled:
            raise HTTPException(status_code=400, detail=f"Account is disabled: {account_name}")
    else:
        enabled_accounts = config_loader.get_enabled_accounts()
        if not enabled_accounts:
            raise HTTPException(status_code=400, detail="No enabled accounts available")
        target_account = enabled_accounts[0]

    client, is_mock = get_unified_client()

    try:
        await client.ensure_quote_client(target_account.name)
        underlyings = await client.get_option_underlyings(target_account.name, market)
    finally:
        await client.close()

    return TigerUnderlyingsResponse(
        success=True,
        message=f"Retrieved {len(underlyings)} option underlyings",
        account_name=target_account.name,
        mock_mode=is_mock,
        count=len(underlyings),
        underlyings=underlyings
    )


@trading_router.get("/api/tiger/options/expirations", response_model=TigerExpirationsResponse)
async def get_tiger_option_expirations(
    underlying: str = Query(..., description="Underlying symbol, e.g. QQQ"),
    account_name: Optional[str] = Query(None, alias="accountName", description="Account name defined in configuration")
) -> TigerExpirationsResponse:
    """List available Tiger option expirations for a given underlying"""
    normalized_symbol = _normalize_underlying(underlying)
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Underlying symbol is required")

    config_loader = ConfigLoader.get_instance()

    if account_name:
        target_account = config_loader.get_account_by_name(account_name)
        if not target_account:
            raise HTTPException(status_code=404, detail=f"Account not found: {account_name}")
        if not target_account.enabled:
            raise HTTPException(status_code=400, detail=f"Account is disabled: {account_name}")
    else:
        enabled_accounts = config_loader.get_enabled_accounts()
        if not enabled_accounts:
            raise HTTPException(status_code=400, detail="No enabled accounts available")
        target_account = enabled_accounts[0]

    client, is_mock = get_unified_client()

    try:
        await client.ensure_quote_client(target_account.name)
        expirations = await client.get_option_expirations(normalized_symbol)
    finally:
        await client.close()

    return TigerExpirationsResponse(
        success=True,
        message=f"Retrieved {len(expirations)} expirations for {normalized_symbol}",
        account_name=target_account.name,
        underlying=normalized_symbol,
        mock_mode=is_mock,
        count=len(expirations),
        expirations=expirations
    )


@trading_router.get("/api/tiger/options", response_model=TigerOptionsResponse)
async def get_tiger_options(
    underlying: str = Query(..., description="Underlying symbol, e.g. QQQ"),
    account_name: Optional[str] = Query(None, alias="accountName", description="Account name defined in configuration"),
    option_type: Optional[str] = Query(None, alias="optionType", description="Filter by option type: call or put"),
    min_days: Optional[int] = Query(None, alias="minDays", ge=0, description="Minimum days to expiry"),
    max_days: Optional[int] = Query(None, alias="maxDays", ge=0, description="Maximum days to expiry"),
    min_strike: Optional[float] = Query(None, alias="minStrike", description="Minimum strike price"),
    max_strike: Optional[float] = Query(None, alias="maxStrike", description="Maximum strike price"),
    expiry_timestamp: int = Query(..., alias="expiryTs", description="Target expiration timestamp (milliseconds or seconds)")
) -> TigerOptionsResponse:
    """List Tiger Brokers options for a given underlying"""
    normalized_symbol = _normalize_underlying(underlying)
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Underlying symbol is required")

    config_loader = ConfigLoader.get_instance()

    target_account = None
    if account_name:
        target_account = config_loader.get_account_by_name(account_name)
        if not target_account:
            raise HTTPException(
                status_code=404,
                detail=f"Account not found: {account_name}"
            )
        if not target_account.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Account is disabled: {account_name}"
            )
    else:
        enabled_accounts = config_loader.get_enabled_accounts()
        if not enabled_accounts:
            raise HTTPException(
                status_code=400,
                detail="No enabled accounts available"
            )
        target_account = enabled_accounts[0]

    option_type_filter = None
    if option_type:
        option_type_normalized = option_type.lower()
        if option_type_normalized not in {"call", "put"}:
            raise HTTPException(status_code=400, detail="optionType must be 'call' or 'put'")
        option_type_filter = option_type_normalized

    client, is_mock = get_unified_client()

    try:
        await client.ensure_quote_client(target_account.name)
        options = await client.get_instruments(normalized_symbol, "option", expiry_timestamp=expiry_timestamp)
    finally:
        await client.close()

    if not options:
        return TigerOptionsResponse(
            success=True,
            message=f"No options found for {normalized_symbol} at {expiry_timestamp}",
            account_name=target_account.name,
            underlying=normalized_symbol,
            expiry_timestamp=int(expiry_timestamp),
            mock_mode=is_mock,
            count=0,
            options=[]
        )

    filtered_options = []

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    min_expiry_ts = now_ms + int(min_days * 24 * 3600 * 1000) if min_days is not None else None
    max_expiry_ts = now_ms + int(max_days * 24 * 3600 * 1000) if max_days is not None else None

    for option in options:
        opt_type = (option.get("option_type") or "").lower()
        if option_type_filter and opt_type != option_type_filter:
            continue

        strike_value = option.get("strike")
        if min_strike is not None and strike_value is not None and strike_value < min_strike:
            continue
        if max_strike is not None and strike_value is not None and strike_value > max_strike:
            continue

        expiry_ts = option.get("expiration_timestamp")
        if min_expiry_ts is not None and expiry_ts is not None and expiry_ts < min_expiry_ts:
            continue
        if max_expiry_ts is not None and expiry_ts is not None and expiry_ts > max_expiry_ts:
            continue

        filtered_options.append(option)

    filtered_options.sort(
        key=lambda item: (
            item.get("expiration_timestamp") or 0,
            item.get("strike") or 0.0,
            (item.get("option_type") or "")
        )
    )

    return TigerOptionsResponse(
        success=True,
        message=f"Retrieved {len(filtered_options)} options for {normalized_symbol}",
        account_name=target_account.name,
        underlying=normalized_symbol,
        expiry_timestamp=int(expiry_timestamp),
        mock_mode=is_mock,
        count=len(filtered_options),
        options=filtered_options
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
