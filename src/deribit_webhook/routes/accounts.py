"""Account configuration and status routes"""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import ConfigLoader, settings
from ..models.config_types import ApiKeyConfig, WeChatBotSettings
from ..services import get_trading_client, polling_manager


class AccountMetadata(BaseModel):
    """Serializable representation of account configuration"""
    name: str
    description: str
    enabled: bool
    market: str
    tiger_id: str
    account_number: str
    private_key_path: str
    has_user_token: bool


class AccountListResponse(BaseModel):
    """List response for account configurations"""
    success: bool
    message: str
    total: int
    accounts: List[AccountMetadata]


class AccountDetailResponse(BaseModel):
    """Detailed account response"""
    success: bool
    message: str
    account: AccountMetadata
    environment: Dict[str, Any]
    polling: Dict[str, Any]
    wechat_bot: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None
    positions: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    managed_accounts: Optional[List[Dict[str, Any]]] = None
    errors: Optional[Dict[str, str]] = None


accounts_router = APIRouter()


def _to_metadata(account: ApiKeyConfig) -> AccountMetadata:
    """Convert configuration object to serializable metadata"""
    return AccountMetadata(
        name=account.name,
        description=account.description,
        enabled=account.enabled,
        market=account.market,
        tiger_id=account.tiger_id,
        account_number=account.account,
        private_key_path=account.private_key_path,
        has_user_token=bool(account.user_token)
    )


def _serialize_wechat_bot(bot: Optional[WeChatBotSettings]) -> Optional[Dict[str, Any]]:
    """Serialize WeChat bot configuration if available"""
    if not bot or not bot.webhook_url:
        return None

    return {
        "webhook_url": bot.webhook_url,
        "enabled": bot.enabled if bot.enabled is not None else True,
        "timeout": bot.timeout,
        "retry_count": bot.retry_count,
        "retry_delay": bot.retry_delay,
    }


@accounts_router.get("/api/accounts", response_model=AccountListResponse)
async def list_accounts(
    enabled_only: bool = Query(True, description="Return only enabled accounts when true")
) -> AccountListResponse:
    """List configured trading accounts"""
    config_loader = ConfigLoader.get_instance()
    config = config_loader.load_config()

    accounts = config.accounts
    if enabled_only:
        accounts = [account for account in accounts if account.enabled]

    metadata = [_to_metadata(account) for account in accounts]

    return AccountListResponse(
        success=True,
        message="Accounts retrieved successfully",
        total=len(metadata),
        accounts=metadata
    )


@accounts_router.get("/api/accounts/{account_name}", response_model=AccountDetailResponse)
async def get_account_detail(
    account_name: str,
    include_positions: bool = Query(True, description="Include open positions in response"),
    include_summary: bool = Query(True, description="Include account summary in response"),
    include_assets: bool = Query(True, description="Include account asset information in response"),
    include_managed: bool = Query(True, description="Include managed account profiles in response"),
    currency: str = Query("USD", description="Currency to request from upstream broker")
) -> AccountDetailResponse:
    """Fetch detailed account information with optional live data"""
    config_loader = ConfigLoader.get_instance()
    config = config_loader.load_config()

    account = config_loader.get_account_by_name(account_name)
    if not account:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "message": f"Account not found: {account_name}",
                "account_name": account_name,
            }
        )

    metadata = _to_metadata(account)

    polling_status = polling_manager.get_status()
    polling_response = {
        "is_running": polling_status.get("is_running", False),
        "interval_seconds": polling_status.get("interval_seconds", 0),
        "accounts": polling_status.get("account_names", []),
        "tracking_account": account_name in polling_status.get("account_names", []),
    }

    environment_info = {
        "environment": settings.environment,
        "mock_mode": settings.use_mock_mode,
        "test_environment": getattr(config, "use_test_environment", settings.use_test_environment),
    }

    wechat_config = _serialize_wechat_bot(account.wechat_bot)

    summary: Optional[Dict[str, Any]] = None
    positions: Optional[List[Dict[str, Any]]] = None
    assets: Optional[List[Dict[str, Any]]] = None
    managed_accounts: Optional[List[Dict[str, Any]]] = None
    errors: Dict[str, str] = {}

    if include_positions or include_summary or include_assets or include_managed:
        client = get_trading_client()
        currency_code = currency.upper()
        try:
            if include_positions:
                try:
                    positions = await client.get_positions(account_name, currency_code)
                except Exception as position_error:  # pragma: no cover - depends on external API
                    errors["positions"] = str(position_error)
                    positions = None
            if include_summary:
                try:
                    summary = await client.get_account_summary(account_name, currency_code)
                except NotImplementedError:
                    errors["summary"] = "Account summary not supported for this broker"
                    summary = None
                except Exception as summary_error:  # pragma: no cover - depends on external API
                    errors["summary"] = str(summary_error)
                    summary = None
            if include_assets:
                try:
                    assets = await client.get_account_assets(account_name)
                except NotImplementedError:
                    errors["assets"] = "Account assets not supported for this broker"
                    assets = None
                except Exception as asset_error:  # pragma: no cover - depends on external API
                    errors["assets"] = str(asset_error)
                    assets = None
            if include_managed:
                try:
                    managed_accounts = await client.get_managed_accounts_info(account_name)
                except NotImplementedError:
                    errors["managed_accounts"] = "Managed accounts not supported for this broker"
                    managed_accounts = None
                except Exception as managed_error:  # pragma: no cover - depends on external API
                    errors["managed_accounts"] = str(managed_error)
                    managed_accounts = None
        finally:
            await client.close()

    return AccountDetailResponse(
        success=True,
        message=f"Account detail retrieved for {account_name}",
        account=metadata,
        environment=environment_info,
        polling=polling_response,
        wechat_bot=wechat_config,
        summary=summary,
        positions=positions,
        assets=assets,
        managed_accounts=managed_accounts,
        errors=errors or None,
    )
