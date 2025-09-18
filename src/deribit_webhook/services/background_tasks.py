"""
Background task management

Manages various background tasks like database cleanup, health checks, etc.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from deribit_webhook.config import settings
from deribit_webhook.database import get_delta_manager


class BackgroundTaskManager:
    """Background task manager"""
    
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self._delta_manager = None
    
    def _get_delta_manager(self):
        """Get delta manager instance"""
        if self._delta_manager is None:
            self._delta_manager = get_delta_manager()
        return self._delta_manager
    
    async def start_all_tasks(self):
        """Start all background tasks"""
        if self.is_running:
            print("⚠️ Background tasks are already running")
            return
        
        print("🟢 Starting background tasks...")
        self.is_running = True
        
        # Start database cleanup task
        if settings.enable_database_cleanup:
            self.tasks["database_cleanup"] = asyncio.create_task(
                self._database_cleanup_loop()
            )
            print("✅ Database cleanup task started")
        
        # Start health check task
        if settings.enable_health_checks:
            self.tasks["health_check"] = asyncio.create_task(
                self._health_check_loop()
            )
            print("✅ Health check task started")
        
        print(f"✅ Started {len(self.tasks)} background tasks")
    
    async def stop_all_tasks(self):
        """Stop all background tasks"""
        if not self.is_running:
            print("⚠️ Background tasks are not running")
            return
        
        print("🛑 Stopping background tasks...")
        self.is_running = False
        
        # Cancel all tasks
        for task_name, task in self.tasks.items():
            print(f"🛑 Stopping {task_name}...")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks.clear()
        print("✅ All background tasks stopped")
    
    async def _database_cleanup_loop(self):
        """Database cleanup loop"""
        try:
            while self.is_running:
                try:
                    await self._cleanup_old_records()
                    
                    # Wait for next cleanup (daily)
                    await asyncio.sleep(24 * 3600)  # 24 hours
                    
                except Exception as error:
                    print(f"❌ Database cleanup error: {error}")
                    # Wait before retry
                    await asyncio.sleep(3600)  # 1 hour
                    
        except asyncio.CancelledError:
            print("📡 Database cleanup loop cancelled")
            raise
    
    async def _health_check_loop(self):
        """Health check loop"""
        try:
            while self.is_running:
                try:
                    await self._perform_health_checks()
                    
                    # Wait for next health check
                    await asyncio.sleep(settings.health_check_interval)
                    
                except Exception as error:
                    print(f"❌ Health check error: {error}")
                    # Wait before retry
                    await asyncio.sleep(60)  # 1 minute
                    
        except asyncio.CancelledError:
            print("📡 Health check loop cancelled")
            raise
    
    async def _cleanup_old_records(self):
        """Clean up old database records"""
        try:
            delta_manager = self._get_delta_manager()
            
            # Clean up records older than configured days
            deleted_count = await delta_manager.cleanup_old_records(
                settings.database_cleanup_days
            )
            
            if deleted_count > 0:
                print(f"🧹 Cleaned up {deleted_count} old delta records")
            
        except Exception as error:
            print(f"❌ Failed to cleanup old records: {error}")
            raise
    
    async def _perform_health_checks(self):
        """Perform system health checks"""
        try:
            # Check database connectivity
            delta_manager = self._get_delta_manager()
            stats = await delta_manager.get_stats()
            
            # Log health status
            print(f"💓 Health check: {stats.total_records} total records, "
                  f"{stats.position_records} positions, {stats.order_records} orders")
            
            # Here you could add more health checks:
            # - API connectivity
            # - Memory usage
            # - Disk space
            # - Error rates
            
        except Exception as error:
            print(f"❌ Health check failed: {error}")
            # Don't raise - health checks should be non-critical
    
    def get_status(self) -> Dict[str, Any]:
        """Get background task status"""
        task_status = {}
        
        for task_name, task in self.tasks.items():
            task_status[task_name] = {
                "running": not task.done(),
                "cancelled": task.cancelled(),
                "done": task.done()
            }
            
            if task.done() and not task.cancelled():
                try:
                    task.result()
                    task_status[task_name]["status"] = "completed"
                except Exception as e:
                    task_status[task_name]["status"] = "failed"
                    task_status[task_name]["error"] = str(e)
        
        return {
            "is_running": self.is_running,
            "task_count": len(self.tasks),
            "tasks": task_status
        }


# Add settings for background tasks
class BackgroundTaskSettings:
    """Background task settings"""
    enable_database_cleanup: bool = True
    database_cleanup_days: int = 30
    enable_health_checks: bool = True
    health_check_interval: int = 300  # 5 minutes


# Background task settings are accessed directly when needed
# No automatic extension to avoid Pydantic field conflicts

# Global instance
background_task_manager = BackgroundTaskManager()
