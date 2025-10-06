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

from ..config import ConfigLoader
from ..models.webhook_types import WebhookSignalPayload
from ..services import OptionTradingService
from ..middleware.account_validation import validate_account_from_body
from ..utils.logging_config import get_logger


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

# Get logger instance
logger = get_logger(__name__)


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
        logger.info(
            "Received webhook signal", 
            request_id=request_id,
            payload=payload.model_dump(),
            account_name=payload.account_name
        )
        
        # Account validation is handled by dependency
        # validated_account contains the validated account
        
        # Process trading signal
        logger.info(
            "Processing trading signal", 
            request_id=request_id,
            account_name=payload.account_name
        )
        
        # Create option trading service instance
        logger.debug("Creating option trading service instance", request_id=request_id)
        option_trading_service = OptionTradingService()
        
        try:
            result = await option_trading_service.process_webhook_signal(payload)
            
            if not result.success:
                logger.error(
                    "Trading operation failed",
                    request_id=request_id,
                    error=result.error or result.message,
                    order_id=result.order_id,
                    instrument_name=result.instrument_name,
                    executed_quantity=result.executed_quantity,
                    executed_price=result.executed_price
                )
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
            
            logger.info(
                "Trading operation successful",
                request_id=request_id,
                result=result.model_dump(),
                order_id=result.order_id,
                instrument_name=result.instrument_name,
                executed_quantity=result.executed_quantity,
                executed_price=result.executed_price
            )
            
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
            logger.debug("Cleaning up option trading service resources", request_id=request_id)
            await option_trading_service.close()
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as error:
        logger.error(
            "Webhook processing error",
            request_id=request_id,
            error=str(error),
            error_type=type(error).__name__,
            account_name=payload.account_name
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": str(error),
                "meta": {"request_id": request_id}
            }
        )
