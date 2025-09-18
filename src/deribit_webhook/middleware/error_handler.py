"""
Error handling middleware and utilities
"""

import time
import random
import string
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..config import settings


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    message: str
    error: Optional[str] = None
    timestamp: str
    request_id: Optional[str] = None
    code: Optional[str] = None


class ErrorHandler:
    """Error handling utilities"""
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate unique request ID"""
        timestamp = int(time.time())
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
        return f"req_{timestamp}_{random_suffix}"
    
    @staticmethod
    def get_request_id(request: Request) -> str:
        """Get or generate request ID"""
        request_id = request.headers.get("x-request-id")
        if not request_id:
            request_id = ErrorHandler.generate_request_id()
        return request_id
    
    @staticmethod
    def create_error_response(
        message: str,
        error: Optional[str] = None,
        request_id: Optional[str] = None,
        code: Optional[str] = None
    ) -> ErrorResponse:
        """Create standardized error response"""
        return ErrorResponse(
            success=False,
            message=message,
            error=error,
            timestamp=datetime.now().isoformat(),
            request_id=request_id,
            code=code
        )
    
    @staticmethod
    def handle_exception(
        request: Request,
        exc: Exception,
        status_code: int = 500
    ) -> JSONResponse:
        """Handle exception and return JSON response"""
        request_id = ErrorHandler.get_request_id(request)
        
        print(f"[{request_id}] Error: {exc}")
        
        # Create error response
        error_response = ErrorHandler.create_error_response(
            message=str(exc),
            request_id=request_id
        )
        
        # Add error details in development
        if settings.environment == "development":
            error_response.error = traceback.format_exc()
        
        # Determine status code based on exception type
        if isinstance(exc, HTTPException):
            status_code = exc.status_code
        elif exc.__class__.__name__ == "ValidationError":
            status_code = 400
        elif exc.__class__.__name__ == "UnauthorizedError":
            status_code = 401
        elif exc.__class__.__name__ == "NotFoundError":
            status_code = 404
        
        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump()
        )


class CustomHTTPException(HTTPException):
    """Custom HTTP exception with additional fields"""
    
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(status_code, detail, headers)
        self.error_code = error_code


class ValidationError(CustomHTTPException):
    """Validation error"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        detail = {"message": message}
        if field:
            detail["field"] = field
        super().__init__(400, detail, error_code="VALIDATION_ERROR")


class UnauthorizedError(CustomHTTPException):
    """Unauthorized error"""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(401, {"message": message}, error_code="UNAUTHORIZED")


class NotFoundError(CustomHTTPException):
    """Not found error"""
    
    def __init__(self, message: str, resource: Optional[str] = None):
        detail = {"message": message}
        if resource:
            detail["resource"] = resource
        super().__init__(404, detail, error_code="NOT_FOUND")


class InternalServerError(CustomHTTPException):
    """Internal server error"""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(500, {"message": message}, error_code="INTERNAL_ERROR")


# Utility functions for common error responses
def bad_request(message: str, field: Optional[str] = None) -> ValidationError:
    """Create bad request error"""
    return ValidationError(message, field)


def unauthorized(message: str = "Unauthorized") -> UnauthorizedError:
    """Create unauthorized error"""
    return UnauthorizedError(message)


def not_found(message: str, resource: Optional[str] = None) -> NotFoundError:
    """Create not found error"""
    return NotFoundError(message, resource)


def internal_error(message: str = "Internal server error") -> InternalServerError:
    """Create internal server error"""
    return InternalServerError(message)
