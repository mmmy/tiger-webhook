"""
FastAPI application factory

Creates and configures the FastAPI application with all routes and middleware.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from routes import (
    health_router,
    webhook_router,
    trading_router,
    auth_router,
    delta_router,
    positions_router,
    wechat_router,
    logs_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting Deribit Webhook Python service...")
    
    # TODO: Add startup tasks here
    # - Initialize database connections
    # - Start background tasks (position polling)
    # - Validate configuration
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Deribit Webhook Python service...")
    
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

    # Mount static files
    app.mount("/static", StaticFiles(directory="../public/static"), name="static")
    
    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(webhook_router, tags=["Webhook"])
    app.include_router(trading_router, tags=["Trading"])
    app.include_router(auth_router, tags=["Authentication"])
    app.include_router(delta_router, tags=["Delta Management"])
    app.include_router(positions_router, tags=["Positions"])
    app.include_router(wechat_router, tags=["WeChat Bot"])
    app.include_router(logs_router, tags=["Logs"])
    
    @app.get("/")
    async def root():
        """Root endpoint - serve dashboard"""
        return FileResponse("../public/index.html")

    @app.get("/delta")
    async def delta_manager():
        """Delta manager page"""
        return FileResponse("../public/delta-manager.html")

    @app.get("/logs")
    async def logs_page():
        """Logs query page"""
        return FileResponse("../public/logs.html")

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
