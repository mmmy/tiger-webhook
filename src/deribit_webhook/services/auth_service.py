"""
Deribit authentication service

Handles OAuth 2.0 authentication, token management, and refresh logic.
"""

import time
from typing import Dict, Optional
import httpx
import asyncio
from datetime import datetime, timedelta

from deribit_webhook.config import ConfigLoader, settings
from deribit_webhook.models.auth_types import (
    AuthToken, 
    AuthResponse, 
    DeribitAuthRequestParams,
    DeribitError
)
from deribit_webhook.models.config_types import ApiKeyConfig
from .authentication_errors import (
    AuthenticationError,
    TokenExpiredError,
    TokenNotFoundError,
    AuthenticationResult
)


class DeribitAuth:
    """Deribit OAuth 2.0 authentication service"""
    
    def __init__(self):
        self.config_loader = ConfigLoader.get_instance()
        self.tokens: Dict[str, AuthToken] = {}
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Content-Type": "application/json"}
            )
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_auth_url(self) -> str:
        """Get authentication URL based on environment"""
        base_url = self.config_loader.get_api_base_url()
        return f"{base_url}/public/auth"
    
    async def _make_auth_request(self, params: dict) -> AuthResponse:
        """Make HTTP request to Deribit auth endpoint"""
        url = self._get_auth_url()
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return AuthResponse.model_validate(data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 400:
                try:
                    error_data = e.response.json()
                    deribit_error = DeribitError.model_validate(error_data)
                    raise AuthenticationError(
                        f"Deribit API Error [{deribit_error.error.code}]: {deribit_error.error.message}",
                        "unknown"
                    )
                except Exception:
                    pass
            raise AuthenticationError(f"HTTP Error: {e}", "unknown")
        except Exception as e:
            raise AuthenticationError(f"Request failed: {e}", "unknown")
    
    def _is_token_valid(self, token: AuthToken) -> bool:
        """Check if a token is valid (not expired)"""
        # Add 5 seconds buffer before expiration
        current_time = int(time.time() * 1000)  # milliseconds
        return current_time < (token.expires_at - 5000)
    
    async def _request_new_token(self, account: ApiKeyConfig) -> AuthToken:
        """Request a new access token from Deribit"""
        params = {
            "grant_type": account.grant_type,
            "client_id": account.client_id,
            "client_secret": account.client_secret,
        }
        
        # Add scope if specified
        if account.scope and account.scope.strip():
            params["scope"] = account.scope
        
        try:
            response = await self._make_auth_request(params)
            
            if not response.result or not response.result.access_token:
                raise AuthenticationError("Invalid response: No access token received", account.name)
            
            result = response.result
            expires_at = int(time.time() * 1000) + (result.expires_in * 1000)
            
            return AuthToken(
                access_token=result.access_token,
                refresh_token=result.refresh_token,
                expires_at=expires_at,
                scope=result.scope
            )
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Token request failed: {e}", account.name)
    
    async def authenticate(self, account_name: str) -> AuthToken:
        """Authenticate with Deribit API using OAuth 2.0 client credentials flow"""
        # Validate account exists
        account = self.config_loader.get_account_by_name(account_name)
        if not account:
            raise AuthenticationError(f"Account not found: {account_name}", account_name)
        
        if not account.enabled:
            raise AuthenticationError(f"Account disabled: {account_name}", account_name)
        
        # Check if we have a valid cached token
        cached_token = self.tokens.get(account_name)
        if cached_token and self._is_token_valid(cached_token):
            return cached_token
        
        # Get new token from Deribit
        token = await self._request_new_token(account)
        self.tokens[account_name] = token
        
        return token
    
    async def refresh_token(self, account_name: str) -> AuthToken:
        """Refresh an access token using refresh token"""
        # Validate account exists
        account = self.config_loader.get_account_by_name(account_name)
        if not account:
            raise AuthenticationError(f"Account not found: {account_name}", account_name)
        
        cached_token = self.tokens.get(account_name)
        if not cached_token or not cached_token.refresh_token:
            raise TokenNotFoundError(account_name)
        
        params = {
            "grant_type": "refresh_token",
            "refresh_token": cached_token.refresh_token,
        }
        
        try:
            response = await self._make_auth_request(params)
            result = response.result
            expires_at = int(time.time() * 1000) + (result.expires_in * 1000)
            
            new_token = AuthToken(
                access_token=result.access_token,
                refresh_token=result.refresh_token,
                expires_at=expires_at,
                scope=result.scope
            )
            
            self.tokens[account_name] = new_token
            return new_token
            
        except Exception:
            # If refresh fails, clear the cached token and re-authenticate
            self.tokens.pop(account_name, None)
            return await self.authenticate(account_name)
    
    async def get_valid_token(self, account_name: str) -> str:
        """Get a valid access token for an account"""
        token = await self.authenticate(account_name)
        
        # If token is about to expire, refresh it
        if not self._is_token_valid(token):
            refreshed_token = await self.refresh_token(account_name)
            return refreshed_token.access_token
        
        return token.access_token
    
    def clear_token(self, account_name: str) -> None:
        """Clear cached token for an account"""
        self.tokens.pop(account_name, None)
    
    def clear_all_tokens(self) -> None:
        """Clear all cached tokens"""
        self.tokens.clear()
    
    def get_token_info(self, account_name: str) -> Optional[AuthToken]:
        """Get token info for an account"""
        return self.tokens.get(account_name)
    
    async def test_connection(self, account_name: Optional[str] = None) -> bool:
        """Test connection with Deribit API"""
        try:
            if account_name:
                accounts = [self.config_loader.get_account_by_name(account_name)]
                accounts = [acc for acc in accounts if acc is not None]
            else:
                accounts = self.config_loader.get_enabled_accounts()
            
            if not accounts:
                raise AuthenticationError("No enabled accounts found", "unknown")
            
            # Test first enabled account
            account = accounts[0]
            
            # Test authentication
            await self.authenticate(account.name)
            
            return True

        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


class AuthenticationService:
    """Unified authentication service class"""

    _instance: Optional['AuthenticationService'] = None

    def __init__(self):
        if AuthenticationService._instance is not None:
            raise RuntimeError("AuthenticationService is a singleton. Use get_instance() instead.")
        self.deribit_auth = DeribitAuth()
        AuthenticationService._instance = self

    @classmethod
    def get_instance(cls) -> 'AuthenticationService':
        """Get authentication service singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _create_mock_token(self, account_name: str) -> AuthToken:
        """Create a mock token for testing"""
        expires_at = int(time.time() * 1000) + (3600 * 1000)  # 1 hour from now
        return AuthToken(
            access_token=f"mock_token_{account_name}_{int(time.time())}",
            refresh_token=f"mock_refresh_{account_name}_{int(time.time())}",
            expires_at=expires_at,
            scope="mainaccount"
        )

    async def authenticate(self, account_name: str, skip_validation: bool = False) -> AuthenticationResult:
        """
        Unified authentication method - includes account validation and authentication flow

        Args:
            account_name: Account name
            skip_validation: Whether to skip account validation (default False)

        Returns:
            Authentication result
        """
        try:
            # 1. Account validation (unless skipped)
            account = None
            if not skip_validation:
                config_loader = ConfigLoader.get_instance()
                account = config_loader.get_account_by_name(account_name)
                if not account:
                    raise AuthenticationError(f"Account not found: {account_name}", account_name)
                if not account.enabled:
                    raise AuthenticationError(f"Account disabled: {account_name}", account_name)

            # 2. Mock mode check
            if settings.use_mock_mode:
                print(f"✅ Mock mode - skipping real authentication for account: {account_name}")
                return AuthenticationResult(
                    success=True,
                    account=account,
                    is_mock=True,
                    token=self._create_mock_token(account_name)
                )

            # 3. Real mode authentication
            print(f"🔐 Authenticating account: {account_name}")
            token = await self.deribit_auth.authenticate(account_name)

            print(f"✅ Authentication successful for account: {account_name}")
            return AuthenticationResult(
                success=True,
                token=token,
                account=account,
                is_mock=False
            )

        except Exception as error:
            print(f"❌ Authentication failed for account {account_name}: {error}")

            if isinstance(error, AuthenticationError):
                auth_error = error
            else:
                auth_error = AuthenticationError(
                    str(error) if error else "Unknown authentication error",
                    account_name
                )

            return AuthenticationResult(
                success=False,
                account=account,
                is_mock=settings.use_mock_mode,
                error=auth_error.args[0],
                error_code=auth_error.error_code
            )

    def get_token_info(self, account_name: str) -> Optional[AuthToken]:
        """Get cached token information"""
        if settings.use_mock_mode:
            return self._create_mock_token(account_name)
        return self.deribit_auth.get_token_info(account_name)

    async def ensure_authenticated(self, account_name: str, force_refresh: bool = False) -> AuthToken:
        """
        Ensure authentication state is valid (get or refresh token)

        Args:
            account_name: Account name
            force_refresh: Whether to force token refresh

        Returns:
            Valid token information
        """
        if settings.use_mock_mode:
            return self._create_mock_token(account_name)

        # Check existing token
        token_info = self.deribit_auth.get_token_info(account_name)

        if not token_info or force_refresh:
            # Token doesn't exist or force refresh, re-authenticate
            result = await self.authenticate(account_name, skip_validation=True)
            if not result.success or not result.token:
                raise AuthenticationError(
                    result.error or "Failed to authenticate",
                    account_name
                )
            return result.token

        # Check if token is about to expire (refresh 5 minutes early)
        expires_at = token_info.expires_at
        five_minutes_from_now = int(time.time() * 1000) + (5 * 60 * 1000)

        if expires_at <= five_minutes_from_now:
            try:
                print(f"🔄 Token expiring soon for account {account_name}, refreshing...")
                token_info = await self.deribit_auth.refresh_token(account_name)
            except Exception as error:
                print(f"⚠️ Token refresh failed for {account_name}, re-authenticating...")
                result = await self.authenticate(account_name, skip_validation=True)
                if not result.success or not result.token:
                    raise TokenExpiredError(account_name)
                return result.token

        return token_info

    async def test_connection(self, account_name: Optional[str] = None) -> bool:
        """Test account connection status"""
        if settings.use_mock_mode:
            print(f"✅ Mock mode - connection test passed for account: {account_name or 'all'}")
            return True

        return await self.deribit_auth.test_connection(account_name)

    async def close(self):
        """Close authentication service and cleanup resources"""
        await self.deribit_auth.close()
