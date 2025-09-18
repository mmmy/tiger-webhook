"""
Account validation middleware and dependencies
"""

from typing import Any, List
from datetime import datetime
from fastapi import HTTPException, Request, Depends

from ..config import ConfigLoader
from ..models.config_types import ApiKeyConfig


class AccountValidationError(Exception):
    """Account validation error base class"""

    def __init__(self, message: str, status_code: int, error_code: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class AccountNotFoundError(AccountValidationError):
    """Account not found error"""

    def __init__(self, message: str):
        super().__init__(message, 404, "ACCOUNT_NOT_FOUND")


class AccountDisabledError(AccountValidationError):
    """Account disabled error"""

    def __init__(self, message: str):
        super().__init__(message, 403, "ACCOUNT_DISABLED")


class AccountValidationService:
    """Account validation service class"""

    def __init__(self):
        self._config_loader = None

    def _get_config_loader(self) -> ConfigLoader:
        """Lazy initialization of ConfigLoader (avoid circular dependencies)"""
        if self._config_loader is None:
            self._config_loader = ConfigLoader.get_instance()
        return self._config_loader

    def validate_account(self, account_name: str) -> ApiKeyConfig:
        """
        Validate account existence and enabled status

        Args:
            account_name: Account name

        Returns:
            Validated account object

        Raises:
            AccountValidationError: Account not found or disabled
        """
        account = self._get_config_loader().get_account_by_name(account_name)

        if not account:
            raise AccountNotFoundError(f"Account not found: {account_name}")

        if not account.enabled:
            raise AccountDisabledError(f"Account is disabled: {account_name}")

        return account

    async def validate_account_async(self, account_name: str) -> ApiKeyConfig:
        """
        Async version of account validation (for API consistency)

        Args:
            account_name: Account name

        Returns:
            Validated account object
        """
        return self.validate_account(account_name)

    def validate_multiple_accounts(self, account_names: List[str]) -> List[ApiKeyConfig]:
        """
        Validate multiple accounts in batch

        Args:
            account_names: List of account names

        Returns:
            List of validated account objects
        """
        validated_accounts = []

        for account_name in account_names:
            validated_accounts.append(self.validate_account(account_name))

        return validated_accounts

    def check_account(self, account_name: str) -> dict:
        """
        Check account existence without throwing exceptions

        Args:
            account_name: Account name

        Returns:
            Account validation result
        """
        account = self._get_config_loader().get_account_by_name(account_name)

        if not account:
            return {"exists": False, "enabled": False}

        return {
            "exists": True,
            "enabled": account.enabled,
            "account": account
        }


# Global singleton instance
account_validation_service = AccountValidationService()


def validate_account_from_body(request: Request) -> ApiKeyConfig:
    """
    Validate account from request body
    
    Args:
        request: FastAPI request object
        
    Returns:
        Validated account configuration
        
    Raises:
        HTTPException: If account validation fails
    """
    async def _validate():
        try:
            # Get request body
            body = await request.json()
            account_name = body.get("account_name") or body.get("accountName")
            
            if not account_name:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "message": "Account name is required in request body",
                        "field": "account_name or accountName"
                    }
                )
            
            # Validate account
            config_loader = ConfigLoader.get_instance()
            account = config_loader.get_account_by_name(account_name)
            
            if not account:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "success": False,
                        "message": f"Account not found: {account_name}",
                        "account_name": account_name
                    }
                )
            
            if not account.enabled:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "success": False,
                        "message": f"Account is disabled: {account_name}",
                        "account_name": account_name
                    }
                )
            
            return account
            
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail={
                    "success": False,
                    "message": f"Account validation error: {str(error)}"
                }
            )
    
    return _validate


def validate_account_from_params(account_name: str) -> ApiKeyConfig:
    """
    Validate account from path parameters
    
    Args:
        account_name: Account name from path parameters
        
    Returns:
        Validated account configuration
        
    Raises:
        HTTPException: If account validation fails
    """
    try:
        if not account_name:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "Account name is required",
                    "field": "account_name"
                }
            )
        
        # Validate account
        config_loader = ConfigLoader.get_instance()
        account = config_loader.get_account_by_name(account_name)
        
        if not account:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "message": f"Account not found: {account_name}",
                    "account_name": account_name
                }
            )
        
        if not account.enabled:
            raise HTTPException(
                status_code=403,
                detail={
                    "success": False,
                    "message": f"Account is disabled: {account_name}",
                    "account_name": account_name
                }
            )
        
        return account
        
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Account validation error: {str(error)}",
                "account_name": account_name
            }
        )
