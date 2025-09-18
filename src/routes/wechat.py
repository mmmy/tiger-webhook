"""
WeChat bot management routes
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Depends
from pydantic import BaseModel

from config import ConfigLoader
from services.wechat_notification import wechat_notification_service
from middleware.account_validation import validate_account_from_params


class WeChatTestResponse(BaseModel):
    """WeChat test response"""
    success: bool
    message: str
    account_name: str


class WeChatConfigResponse(BaseModel):
    """WeChat configuration response"""
    success: bool
    message: str
    account_name: str
    has_config: bool
    config_details: Optional[dict] = None


class WeChatBroadcastRequest(BaseModel):
    """WeChat broadcast request"""
    message: str
    notification_type: str = "system"
    account_names: Optional[List[str]] = None


class WeChatBroadcastResponse(BaseModel):
    """WeChat broadcast response"""
    success: bool
    message: str
    results: dict
    total_accounts: int
    successful_sends: int


wechat_router = APIRouter()


@wechat_router.post("/api/wechat/test/{account_name}", response_model=WeChatTestResponse)
async def test_wechat_notification(
    account_name: str = Path(..., description="Account name"),
    validated_account=Depends(validate_account_from_params)
):
    """Test WeChat notification for account"""
    try:
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        success = await wechat_notification_service.test_notification(account_name)
        
        return WeChatTestResponse(
            success=success,
            message="WeChat test notification sent successfully" if success else "WeChat test notification failed",
            account_name=account_name
        )
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error),
                "account_name": account_name
            }
        )


@wechat_router.get("/api/wechat/config/{account_name}", response_model=WeChatConfigResponse)
async def get_wechat_config(
    account_name: str = Path(..., description="Account name"),
    validated_account=Depends(validate_account_from_params)
):
    """Get WeChat configuration for account"""
    try:
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        config_loader = ConfigLoader.get_instance()
        wechat_config = config_loader.get_account_wechat_bot_config(account_name)
        
        if wechat_config:
            # Return config without sensitive information
            config_details = {
                "webhook_url_configured": bool(wechat_config.webhook_url),
                "timeout": wechat_config.timeout,
                "retry_count": wechat_config.retry_count,
                "retry_delay": wechat_config.retry_delay
            }
            
            return WeChatConfigResponse(
                success=True,
                message="WeChat configuration found",
                account_name=account_name,
                has_config=True,
                config_details=config_details
            )
        else:
            return WeChatConfigResponse(
                success=True,
                message="No WeChat configuration found",
                account_name=account_name,
                has_config=False
            )
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error),
                "account_name": account_name
            }
        )


@wechat_router.get("/api/wechat/configs")
async def get_all_wechat_configs():
    """Get all WeChat configurations"""
    try:
        config_loader = ConfigLoader.get_instance()
        wechat_configs = config_loader.get_all_wechat_bot_configs()
        
        # Return configs without sensitive information
        safe_configs = []
        for config_info in wechat_configs:
            account_name = config_info["account_name"]
            config = config_info["config"]
            
            safe_configs.append({
                "account_name": account_name,
                "webhook_url_configured": bool(config.webhook_url),
                "timeout": config.timeout,
                "retry_count": config.retry_count,
                "retry_delay": config.retry_delay
            })
        
        return {
            "success": True,
            "message": f"Found {len(safe_configs)} WeChat configurations",
            "total_configs": len(safe_configs),
            "configs": safe_configs
        }
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@wechat_router.post("/api/wechat/broadcast", response_model=WeChatBroadcastResponse)
async def broadcast_wechat_message(request: WeChatBroadcastRequest):
    """Broadcast message to WeChat groups"""
    try:
        results = await wechat_notification_service.send_system_notification(
            message=request.message,
            account_names=request.account_names,
            notification_type=request.notification_type
        )
        
        successful_sends = sum(1 for success in results.values() if success)
        total_accounts = len(results)
        
        return WeChatBroadcastResponse(
            success=successful_sends > 0,
            message=f"Broadcast sent to {successful_sends}/{total_accounts} accounts",
            results=results,
            total_accounts=total_accounts,
            successful_sends=successful_sends
        )
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )


@wechat_router.post("/api/wechat/test-all")
async def test_all_wechat_notifications():
    """Test WeChat notifications for all configured accounts"""
    try:
        config_loader = ConfigLoader.get_instance()
        wechat_configs = config_loader.get_all_wechat_bot_configs()
        
        if not wechat_configs:
            return {
                "success": False,
                "message": "No WeChat configurations found",
                "results": {}
            }
        
        results = {}
        
        # Test each account
        for config_info in wechat_configs:
            account_name = config_info["account_name"]
            try:
                success = await wechat_notification_service.test_notification(account_name)
                results[account_name] = success
            except Exception as error:
                print(f"❌ Error testing WeChat for {account_name}: {error}")
                results[account_name] = False
        
        successful_tests = sum(1 for success in results.values() if success)
        total_accounts = len(results)
        
        return {
            "success": successful_tests > 0,
            "message": f"WeChat test completed: {successful_tests}/{total_accounts} successful",
            "results": results,
            "total_accounts": total_accounts,
            "successful_tests": successful_tests
        }
        
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error)
            }
        )
