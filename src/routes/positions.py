"""
Position polling and management routes
"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Depends
from pydantic import BaseModel

from config import ConfigLoader, settings
from services import DeribitClient, MockDeribitClient
from services.polling_manager import polling_manager
from middleware.account_validation import validate_account_from_params


class PositionsResponse(BaseModel):
    """Positions response"""
    success: bool
    message: str
    account_name: str
    currency: str
    mock_mode: bool
    positions: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None


class PollingStatusResponse(BaseModel):
    """Polling status response"""
    success: bool
    message: str
    polling_enabled: bool
    accounts: List[str]
    interval_seconds: int


positions_router = APIRouter()


def get_unified_client():
    """Get unified client (mock or real based on settings)"""
    if settings.use_mock_mode:
        return MockDeribitClient(), True
    else:
        return DeribitClient(), False


@positions_router.get("/api/positions/{account_name}/{currency}", response_model=PositionsResponse)
async def get_positions(
    account_name: str = Path(..., description="Account name"),
    currency: str = Path(..., description="Currency"),
    validated_account=Depends(validate_account_from_params)
):
    """Get account positions"""
    try:
        currency_upper = currency.upper()
        
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        # Use unified client, automatically handles Mock/Real mode
        client, is_mock = get_unified_client()
        
        try:
            positions = await client.get_positions(account_name, currency_upper)
            summary = await client.get_account_summary(account_name, currency_upper)
            
            return PositionsResponse(
                success=True,
                message=f"Retrieved {len(positions)} positions for {account_name}",
                account_name=account_name,
                currency=currency_upper,
                mock_mode=is_mock,
                positions=positions,
                summary=summary
            )
        finally:
            await client.close()
            
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error),
                "account_name": account_name,
                "currency": currency
            }
        )


@positions_router.get("/api/positions/polling/status", response_model=PollingStatusResponse)
async def get_polling_status():
    """Get position polling status"""
    try:
        status = polling_manager.get_status()

        return PollingStatusResponse(
            success=True,
            message="Polling status retrieved successfully",
            polling_enabled=status["is_running"],
            accounts=status["account_names"],
            interval_seconds=status["interval_seconds"]
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@positions_router.post("/api/positions/polling/start")
async def start_polling():
    """Start position polling"""
    try:
        await polling_manager.start_polling()
        status = polling_manager.get_status()

        return {
            "success": True,
            "message": "Position polling started successfully",
            "is_running": status["is_running"],
            "interval_seconds": status["interval_seconds"],
            "mock_mode": settings.use_mock_mode
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@positions_router.post("/api/positions/polling/stop")
async def stop_polling():
    """Stop position polling"""
    try:
        await polling_manager.stop_polling()
        status = polling_manager.get_status()

        return {
            "success": True,
            "message": "Position polling stopped successfully",
            "is_running": status["is_running"],
            "mock_mode": settings.use_mock_mode
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@positions_router.post("/api/positions/poll")
async def manual_poll():
    """Perform manual position poll"""
    try:
        result = await polling_manager.poll_once()

        return {
            "success": result["success"],
            "message": result["message"],
            "mock_mode": settings.use_mock_mode,
            **result
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@positions_router.get("/api/positions/delta/{account_name}")
async def get_position_delta(
    account_name: str = Path(..., description="Account name"),
    currency: str = Query(default="BTC", description="Currency"),
    validated_account=Depends(validate_account_from_params)
):
    """Get position delta summary"""
    try:
        currency_upper = currency.upper()
        
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        # Use unified client, automatically handles Mock/Real mode
        client, is_mock = get_unified_client()
        
        try:
            positions = await client.get_positions(account_name, currency_upper)
            
            # Calculate total delta from positions
            total_delta = 0.0
            total_gamma = 0.0
            total_theta = 0.0
            total_vega = 0.0
            
            for position in positions:
                if position.get("kind") == "option":
                    total_delta += position.get("delta", 0.0) * position.get("size", 0.0)
                    total_gamma += position.get("gamma", 0.0) * position.get("size", 0.0)
                    total_theta += position.get("theta", 0.0) * position.get("size", 0.0)
                    total_vega += position.get("vega", 0.0) * position.get("size", 0.0)
            
            return {
                "success": True,
                "message": f"Position delta calculated for {account_name}",
                "account_name": account_name,
                "currency": currency_upper,
                "mock_mode": is_mock,
                "total_delta": total_delta,
                "total_gamma": total_gamma,
                "total_theta": total_theta,
                "total_vega": total_vega,
                "position_count": len(positions)
            }
        finally:
            await client.close()
            
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error),
                "account_name": account_name
            }
        )
