"""
Authentication routes
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Path, Depends
from pydantic import BaseModel

from deribit_webhook.config import ConfigLoader
from deribit_webhook.services import AuthenticationService
from deribit_webhook.middleware.account_validation import validate_account_from_params


class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    message: str
    account_name: str
    is_mock: bool
    token_expires_at: str = None


auth_router = APIRouter()


@auth_router.post("/api/auth/{account_name}", response_model=AuthResponse)
async def authenticate_account(
    account_name: str = Path(..., description="Account name"),
    validated_account=Depends(validate_account_from_params)
):
    """Authenticate account endpoint"""
    try:
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        auth_service = AuthenticationService.get_instance()
        result = await auth_service.authenticate(account_name)
        
        if not result.success:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "message": result.error or "Authentication failed",
                    "account_name": account_name
                }
            )
        
        return AuthResponse(
            success=True,
            message=result.message,
            account_name=account_name,
            is_mock=result.is_mock,
            token_expires_at=result.token.expires_at.isoformat() if result.token and result.token.expires_at else None
        )
        
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


@auth_router.get("/api/auth/{account_name}/status")
async def get_auth_status(
    account_name: str = Path(..., description="Account name"),
    validated_account=Depends(validate_account_from_params)
):
    """Get authentication status"""
    try:
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        auth_service = AuthenticationService.get_instance()
        
        # Check if we have a valid token
        try:
            token = await auth_service.ensure_authenticated(account_name)
            
            return {
                "success": True,
                "authenticated": True,
                "account_name": account_name,
                "token_expires_at": token.expires_at.isoformat() if token.expires_at else None,
                "is_mock": auth_service.is_mock_mode()
            }
        except Exception:
            return {
                "success": True,
                "authenticated": False,
                "account_name": account_name,
                "is_mock": auth_service.is_mock_mode()
            }
            
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
