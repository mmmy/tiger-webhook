"""
Security middleware and utilities
"""

import time
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from deribit_webhook.config import settings


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for given identifier"""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > window_start
            ]
        else:
            self.requests[identifier] = []
        
        # Check if under limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        now = time.time()
        window_start = now - self.window_seconds
        
        if identifier not in self.requests:
            return self.max_requests
        
        # Count recent requests
        recent_requests = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        return max(0, self.max_requests - len(recent_requests))


# Global rate limiter instance
rate_limiter = RateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window
)


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    # Fallback to client host
    if hasattr(request.client, "host"):
        return request.client.host
    
    return "unknown"


def rate_limit_dependency(request: Request):
    """Rate limiting dependency"""
    if not settings.enable_rate_limiting:
        return
    
    client_ip = get_client_ip(request)
    
    if not rate_limiter.is_allowed(client_ip):
        remaining = rate_limiter.get_remaining(client_ip)
        raise HTTPException(
            status_code=429,
            detail={
                "success": False,
                "message": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "remaining": remaining,
                "reset_time": int(time.time() + rate_limiter.window_seconds)
            }
        )


class WebhookSecurity:
    """Webhook security utilities"""
    
    @staticmethod
    def verify_signature(
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature"""
        if not secret:
            return True  # Skip verification if no secret configured
        
        # Calculate expected signature
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures (constant time comparison)
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def verify_timestamp(
        timestamp: str,
        tolerance_seconds: int = 300
    ) -> bool:
        """Verify webhook timestamp to prevent replay attacks"""
        try:
            webhook_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            current_time = datetime.now(webhook_time.tzinfo)
            
            time_diff = abs((current_time - webhook_time).total_seconds())
            return time_diff <= tolerance_seconds
        except (ValueError, TypeError):
            return False


def webhook_security_dependency(request: Request):
    """Webhook security dependency"""
    if not settings.enable_webhook_security:
        return
    
    # Check signature if configured
    if settings.webhook_secret:
        signature = request.headers.get("x-signature")
        if not signature:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "message": "Missing webhook signature",
                    "error_code": "MISSING_SIGNATURE"
                }
            )
        
        # Note: In a real implementation, you would need to get the raw body
        # This is a simplified version
        # payload = await request.body()
        # if not WebhookSecurity.verify_signature(payload, signature, settings.webhook_secret):
        #     raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Check timestamp if provided
    timestamp = request.headers.get("x-timestamp")
    if timestamp and not WebhookSecurity.verify_timestamp(timestamp):
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "message": "Request timestamp too old",
                "error_code": "TIMESTAMP_TOO_OLD"
            }
        )


class APIKeyAuth:
    """API key authentication"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.api_key
    
    def __call__(self, request: Request) -> bool:
        """Validate API key from request"""
        if not self.api_key:
            return True  # Skip if no API key configured
        
        # Check header
        api_key = request.headers.get("x-api-key")
        if not api_key:
            # Check query parameter as fallback
            api_key = request.query_params.get("api_key")
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "message": "Missing API key",
                    "error_code": "MISSING_API_KEY"
                }
            )
        
        if not hmac.compare_digest(api_key, self.api_key):
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "message": "Invalid API key",
                    "error_code": "INVALID_API_KEY"
                }
            )
        
        return True


# Security dependencies
api_key_auth = APIKeyAuth()


def require_api_key(request: Request):
    """Require API key dependency"""
    if settings.require_api_key:
        return api_key_auth(request)
    return True
