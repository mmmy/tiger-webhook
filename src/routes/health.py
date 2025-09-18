"""
Health and status routes
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import ConfigLoader, settings


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    version: str


class StatusResponse(BaseModel):
    """Detailed status response"""
    service: str
    version: str
    environment: str
    mock_mode: bool
    enabled_accounts: int
    accounts: list
    test_environment: bool
    timestamp: str


health_router = APIRouter()

# Cache version information at module initialization
_cached_version: str = "1.0.0"

try:
    # Try to read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Simple parsing for version line
            for line in content.split('\n'):
                if line.strip().startswith('version = '):
                    _cached_version = line.split('=')[1].strip().strip('"').strip("'")
                    break
    print(f"📦 Service version loaded: v{_cached_version}")
except Exception as error:
    print(f"Failed to read version during initialization: {error}")
    _cached_version = "1.0.0"  # Fallback version


def get_package_version() -> str:
    """Get cached version information"""
    return _cached_version


@health_router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat(),
        version=get_package_version()
    )


@health_router.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Status endpoint with more details"""
    try:
        config_loader = ConfigLoader.get_instance()
        accounts = config_loader.get_enabled_accounts()
        
        return StatusResponse(
            service="Deribit Options Trading Microservice",
            version=get_package_version(),
            environment=settings.environment,
            mock_mode=settings.use_mock_mode,
            enabled_accounts=len(accounts),
            accounts=[{"name": acc.name, "enabled": True} for acc in accounts],
            test_environment=settings.use_test_environment,
            timestamp=datetime.now().isoformat()
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "Failed to get status",
                "error": str(error),
                "timestamp": datetime.now().isoformat()
            }
        )
