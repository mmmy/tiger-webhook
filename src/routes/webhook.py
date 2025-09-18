"""
Webhook routes for TradingView signals
"""

import time
import random
import string
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel

from config import ConfigLoader
from models.webhook_types import WebhookSignalPayload
from services import OptionTradingService
from middleware.account_validation import validate_account_from_body


class WebhookResponse(BaseModel):
    """Webhook response model"""
    success: bool
    message: str
    order_id: str = None
    instrument_name: str = None
    executed_quantity: float = None
    executed_price: float = None
    meta: Dict[str, Any] = None


webhook_router = APIRouter()


def generate_request_id() -> str:
    """Generate unique request ID"""
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
    return f"req_{timestamp}_{random_suffix}"


@webhook_router.post("/webhook/signal", response_model=WebhookResponse)
async def webhook_signal(
    payload: WebhookSignalPayload,
    request: Request,
    validated_account=Depends(validate_account_from_body)
):
    """TradingView Webhook Signal endpoint"""
    request_id = generate_request_id()
    
    try:
        print(f"📡 [{request_id}] Received webhook signal:", payload.model_dump())
        
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        # Process trading signal
        print(f"🔄 [{request_id}] Processing signal for account: {payload.account_name}")
        
        # Create option trading service instance
        option_trading_service = OptionTradingService()
        
        try:
            result = await option_trading_service.process_webhook_signal(payload)
            
            if not result.success:
                print(f"❌ [{request_id}] Trading failed: {result.error or result.message}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "message": result.error or "Trading operation failed",
                        "meta": {
                            "request_id": request_id,
                            "order_id": result.order_id,
                            "instrument_name": result.instrument_name,
                            "executed_quantity": result.executed_quantity,
                            "executed_price": result.executed_price
                        }
                    }
                )
            
            print(f"✅ [{request_id}] Trading successful:", result.model_dump())
            
            return WebhookResponse(
                success=True,
                message=result.message,
                order_id=result.order_id,
                instrument_name=result.instrument_name,
                executed_quantity=result.executed_quantity,
                executed_price=result.executed_price,
                meta={"request_id": request_id}
            )
            
        finally:
            # Cleanup service resources
            await option_trading_service.close()
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as error:
        print(f"💥 [{request_id}] Webhook processing error: {error}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error),
                "meta": {"request_id": request_id}
            }
        )
