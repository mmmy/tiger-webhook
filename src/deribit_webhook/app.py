"""
FastAPI application factory

Creates and configures the FastAPI application with all routes and middleware.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .utils.logging_config import get_logger

from .config import settings
from .routes import (
    health_router,
    webhook_router,
    trading_router,
    auth_router,
    delta_router,
    positions_router,
    wechat_router,
    logs_router,
    accounts_router
)

PUBLIC_DIR = Path(__file__).resolve().parents[2] / "public"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("?? Starting Deribit Webhook Python service...")
    
    # TODO: Add startup tasks here
    # - Initialize database connections
    # - Start background tasks (position polling)
    # - Validate configuration
    
    yield
    
    # Shutdown
    print("?? Shutting down Deribit Webhook Python service...")
    
    # TODO: Add cleanup tasks here
    # - Close database connections
    # - Stop background tasks
    # - Cleanup resources


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI application
    """
    # Create FastAPI application
    app = FastAPI(
        title="Deribit Webhook Python",
        description="Python port of Deribit Options Trading Microservice",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files (support new tiger_static directory while keeping legacy fallback)
    tiger_static_dir = PUBLIC_DIR / "tiger_static"
    if tiger_static_dir.exists():
        app.mount("/tiger_static", StaticFiles(directory=str(tiger_static_dir)), name="tiger_static")

    legacy_static_dir = PUBLIC_DIR / "static"
    if legacy_static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(legacy_static_dir)), name="static")
    
    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(webhook_router, tags=["Webhook"])
    app.include_router(trading_router, tags=["Trading"])
    app.include_router(auth_router, tags=["Authentication"])
    app.include_router(delta_router, tags=["Delta Management"])
    app.include_router(positions_router, tags=["Positions"])
    app.include_router(wechat_router, tags=["WeChat Bot"])
    app.include_router(logs_router, tags=["Logs"])
    app.include_router(accounts_router, tags=["Accounts"])
    
    validation_logger = get_logger("deribit_webhook.webhook.validation")

    @app.exception_handler(RequestValidationError)
    async def webhook_validation_exception_handler(request: Request, exc: RequestValidationError):
        if request.url.path == "/webhook/signal":
            log_context = {
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors(),
            }
            if exc.body is not None:
                log_context["body"] = exc.body
            validation_logger.warning(
                "Webhook payload validation failed",
                **log_context,
            )
        return await request_validation_exception_handler(request, exc)

    @app.get("/")
    async def root():
        """Root endpoint - serve dashboard"""
        return FileResponse(PUBLIC_DIR / "index.html")

    @app.get("/delta")
    async def delta_manager():
        """Delta manager page"""
        return FileResponse(PUBLIC_DIR / "delta-manager.html")

    @app.get("/logs")
    async def logs_page():
        """Logs query page"""
        return FileResponse(PUBLIC_DIR / "logs.html")

    @app.get("/tiger/options")
    async def tiger_options_page():
        """Tiger options explorer page"""
        return FileResponse(PUBLIC_DIR / "tiger-options.html")

    @app.get("/accounts/{account_name}")
    async def account_detail_page(account_name: str):
        """Account detail dashboard"""
        return FileResponse(PUBLIC_DIR / "account-detail.html")

    @app.get("/api")
    async def api_info():
        """API information endpoint"""
        return {
            "service": "Deribit Webhook Python",
            "version": "1.0.0",
            "status": "running",
            "environment": settings.environment,
            "docs_url": "/docs",
            "redoc_url": "/redoc"
        }
    
    return app


# Create default app instance for uvicorn
app = create_app()

