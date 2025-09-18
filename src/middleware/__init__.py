"""
Middleware module for Deribit Webhook Python

Provides FastAPI middleware and dependencies for request processing.
"""

from .account_validation import (
    validate_account_from_body,
    validate_account_from_params,
    AccountValidationService,
    AccountValidationError,
    AccountNotFoundError,
    AccountDisabledError,
    account_validation_service
)
from .error_handler import (
    ErrorHandler,
    ErrorResponse,
    CustomHTTPException,
    ValidationError,
    UnauthorizedError,
    NotFoundError,
    InternalServerError,
    bad_request,
    unauthorized,
    not_found,
    internal_error
)
from .security import (
    RateLimiter,
    WebhookSecurity,
    APIKeyAuth,
    rate_limit_dependency,
    webhook_security_dependency,
    require_api_key,
    get_client_ip
)

__all__ = [
    # Account validation
    "validate_account_from_body",
    "validate_account_from_params",
    "AccountValidationService",
    "AccountValidationError",
    "AccountNotFoundError",
    "AccountDisabledError",
    "account_validation_service",

    # Error handling
    "ErrorHandler",
    "ErrorResponse",
    "CustomHTTPException",
    "ValidationError",
    "UnauthorizedError",
    "NotFoundError",
    "InternalServerError",
    "bad_request",
    "unauthorized",
    "not_found",
    "internal_error",

    # Security
    "RateLimiter",
    "WebhookSecurity",
    "APIKeyAuth",
    "rate_limit_dependency",
    "webhook_security_dependency",
    "require_api_key",
    "get_client_ip",
]
