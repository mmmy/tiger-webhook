#!/usr/bin/env python3
"""
Deribit Options Trading Microservice - Main Entry Point
Python port of the original TypeScript implementation
"""

import asyncio
import signal
import sys
from typing import Optional

import uvicorn
from fastapi import FastAPI

from app import create_app
from config import settings
from services.polling_manager import polling_manager
from utils.logging_config import init_logging, get_global_logger


class GracefulShutdown:
    """Handle graceful shutdown of the application"""
    
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        if sys.platform != "win32":
            # Unix-like systems
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
        else:
            # Windows
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger = get_global_logger()
        logger.info("🛑 Received shutdown signal", signal=signum)
        self.shutdown_event.set()
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self.shutdown_event.wait()


async def startup_tasks():
    """Perform startup tasks"""
    logger = get_global_logger()
    try:
        # Auto-start polling if configured
        if settings.auto_start_polling:
            logger.info("🟢 Starting automatic position polling")
            await polling_manager.start_polling()
        else:
            logger.info("⏸️ Polling not started automatically - use POST /api/positions/start-polling to start manually")
    except Exception as error:
        logger.warning("⚠️ Warning during startup", error=str(error))


async def shutdown_tasks():
    """Perform cleanup tasks during shutdown"""
    logger = get_global_logger()
    try:
        logger.info("⏹️ Stopping position polling")
        await polling_manager.stop_polling()
        logger.info("✅ Server shutdown completed")
    except Exception as error:
        logger.error("❌ Error during shutdown", error=str(error))


async def main():
    """Main application entry point"""
    try:
        # Initialize logging system first
        logger = init_logging()

        # Create FastAPI app
        app = create_app()

        # Set up graceful shutdown
        shutdown_handler = GracefulShutdown()

        # Log startup information
        logger.info("🚀 Deribit Options Trading Microservice starting",
                   port=settings.port,
                   environment=settings.environment,
                   test_environment=settings.use_test_environment,
                   mock_mode=settings.use_mock_mode,
                   config_file=settings.api_key_file)
        
        # Log service endpoints
        logger.info("📡 Service endpoints available",
                   health_check=f"http://localhost:{settings.port}/health",
                   webhook=f"http://localhost:{settings.port}/webhook/signal",
                   delta_manager=f"http://localhost:{settings.port}/delta",
                   manual_polling=f"http://localhost:{settings.port}/api/positions/poll",
                   polling_status=f"http://localhost:{settings.port}/api/positions/polling-status",
                   start_polling=f"http://localhost:{settings.port}/api/positions/start-polling",
                   stop_polling=f"http://localhost:{settings.port}/api/positions/stop-polling",
                   logs=f"http://localhost:{settings.port}/logs")
        
        # Show configured accounts
        try:
            from config import ConfigLoader
            config_loader = ConfigLoader.get_instance()
            accounts = config_loader.get_enabled_accounts()
            account_names = [account.name for account in accounts]
            logger.info("👥 Account configuration loaded",
                       enabled_accounts=account_names,
                       account_count=len(account_names))
        except Exception as error:
            logger.warning("⚠️ Could not load account configuration", error=str(error))

        logger.info("🔄 Polling configuration", auto_start_polling=settings.auto_start_polling)
        
        # Perform startup tasks
        await startup_tasks()
        
        # Configure uvicorn
        config = uvicorn.Config(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            access_log=True,
            loop="asyncio"
        )
        
        server = uvicorn.Server(config)
        
        # Start server in background
        server_task = asyncio.create_task(server.serve())
        
        # Wait for shutdown signal
        await shutdown_handler.wait_for_shutdown()
        
        # Perform shutdown tasks
        await shutdown_tasks()
        
        # Stop the server
        server.should_exit = True
        await server_task
        
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt, shutting down")
    except Exception as error:
        logger.critical("❌ Failed to start application", error=str(error))
        sys.exit(1)


def cli_main():
    """CLI entry point for setuptools"""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
