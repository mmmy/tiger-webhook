"""
Enhanced polling manager

Manages background polling of account positions and orders.
Supports both position polling (every 15 minutes) and order polling (every 5 minutes).
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from config import ConfigLoader, settings
from services.deribit_client import DeribitClient
from services.mock_deribit_client import MockDeribitClient
from database import get_delta_manager


class PollingManager:
    """Enhanced polling manager for positions and orders"""

    def __init__(self):
        # Position polling state
        self.is_running = False
        self.position_polling_task: Optional[asyncio.Task] = None
        self.position_error_count = 0
        self.last_position_poll_time: Optional[datetime] = None
        self.position_poll_count = 0

        # Order polling state (future enhancement)
        self.order_polling_enabled = False
        self.order_polling_task: Optional[asyncio.Task] = None
        self.order_error_count = 0
        self.last_order_poll_time: Optional[datetime] = None
        self.order_poll_count = 0

        # Shared resources
        self._config_loader: Optional[ConfigLoader] = None
        self._delta_manager = None

        # Backward compatibility aliases
        self.polling_task = None  # Will point to position_polling_task
        self.error_count = 0      # Will point to position_error_count
        self.last_poll_time = None # Will point to last_position_poll_time
        self.poll_count = 0       # Will point to position_poll_count

    def _get_config_loader(self) -> ConfigLoader:
        """Get config loader instance"""
        if self._config_loader is None:
            self._config_loader = ConfigLoader.get_instance()
        return self._config_loader

    def _get_delta_manager(self):
        """Get delta manager instance"""
        if self._delta_manager is None:
            self._delta_manager = get_delta_manager()
        return self._delta_manager

    async def start_polling(self):
        """Start position polling (and optionally order polling)"""
        if self.is_running:
            print("⚠️ Position polling is already running")
            return

        if not settings.enable_position_polling:
            print("⚠️ Position polling is disabled in settings")
            return

        print("🟢 Starting position polling...")
        self.is_running = True
        self.position_error_count = 0

        # Start the position polling task
        self.position_polling_task = asyncio.create_task(self._position_polling_loop())

        # Update backward compatibility aliases
        self.polling_task = self.position_polling_task
        self.error_count = self.position_error_count

        # Use minute-based interval for display (following reference project pattern)
        position_interval = settings.position_polling_interval_minutes
        print(f"✅ Position polling started with {position_interval} minute interval")

        # Future: Start order polling if enabled
        # if settings.enable_order_polling:
        #     await self.start_order_polling()

    async def stop_polling(self):
        """Stop all polling (position and order)"""
        if not self.is_running:
            print("⚠️ Polling is not running")
            return

        print("🛑 Stopping position polling...")
        self.is_running = False

        # Stop position polling
        if self.position_polling_task:
            self.position_polling_task.cancel()
            try:
                await self.position_polling_task
            except asyncio.CancelledError:
                pass
            self.position_polling_task = None

        # Stop order polling (future enhancement)
        if self.order_polling_task:
            self.order_polling_task.cancel()
            try:
                await self.order_polling_task
            except asyncio.CancelledError:
                pass
            self.order_polling_task = None
            self.order_polling_enabled = False

        # Update backward compatibility aliases
        self.polling_task = None

        print("✅ All polling stopped")

    async def _position_polling_loop(self):
        """Main position polling loop"""
        try:
            while self.is_running:
                try:
                    await self._poll_all_accounts()
                    self.position_error_count = 0  # Reset error count on success
                    self.last_position_poll_time = datetime.now()
                    self.position_poll_count += 1

                    # Update backward compatibility aliases
                    self.error_count = self.position_error_count
                    self.last_poll_time = self.last_position_poll_time
                    self.poll_count = self.position_poll_count

                    # Wait for next poll (convert minutes to seconds)
                    interval_seconds = settings.position_polling_interval_minutes * 60
                    await asyncio.sleep(interval_seconds)

                except Exception as error:
                    self.position_error_count += 1
                    self.error_count = self.position_error_count  # Update alias
                    print(f"❌ Position polling error #{self.position_error_count}: {error}")

                    # Stop polling if too many errors
                    if self.position_error_count >= settings.max_polling_errors:
                        print(f"🛑 Too many position polling errors ({self.position_error_count}), stopping polling")
                        self.is_running = False
                        break

                    # Wait before retry (use shorter interval for retries)
                    retry_interval = min(30, settings.position_polling_interval_minutes * 60)
                    await asyncio.sleep(retry_interval)

        except asyncio.CancelledError:
            print("📡 Position polling loop cancelled")
            raise
        except Exception as error:
            print(f"💥 Fatal position polling error: {error}")
            self.is_running = False

    async def _poll_all_accounts(self):
        """Poll positions for all enabled accounts"""
        config_loader = self._get_config_loader()
        accounts = config_loader.get_enabled_accounts()

        if not accounts:
            print("⚠️ No enabled accounts found for polling")
            return

        print(f"📊 Polling {len(accounts)} accounts...")

        # Poll each account
        for account in accounts:
            try:
                await self._poll_account(account.name)
            except Exception as error:
                print(f"❌ Failed to poll account {account.name}: {error}")
                # Continue with other accounts
                continue

    async def _poll_account(self, account_name: str):
        """Poll positions for a single account"""
        try:
            # Get client (mock or real)
            if settings.use_mock_mode:
                client = MockDeribitClient()
            else:
                client = DeribitClient()

            try:
                # Get positions
                positions = await client.get_positions(account_name, "BTC")
                summary = await client.get_account_summary(account_name, "BTC")

                # Process positions
                await self._process_positions(account_name, positions, summary)

            finally:
                await client.close()

        except Exception as error:
            print(f"❌ Error polling account {account_name}: {error}")
            raise

    async def _process_positions(
        self,
        account_name: str,
        positions: List[Dict[str, Any]],
        summary: Optional[Dict[str, Any]]
    ):
        """Process polled positions"""
        try:
            # Calculate total delta
            total_delta = 0.0
            option_positions = []

            for position in positions:
                if position.get("kind") == "option":
                    delta = position.get("delta", 0.0)
                    size = position.get("size", 0.0)
                    position_delta = delta * size
                    total_delta += position_delta
                    option_positions.append(position)

            # Log position summary
            if option_positions:
                print(f"📈 {account_name}: {len(option_positions)} option positions, total delta: {total_delta:.4f}")

            # Here you could:
            # 1. Update delta records in database
            # 2. Check for position adjustments needed
            # 3. Send notifications if thresholds exceeded
            # 4. Log position changes

        except Exception as error:
            print(f"❌ Error processing positions for {account_name}: {error}")

    async def poll_once(self) -> Dict[str, Any]:
        """Perform a single poll of all accounts"""
        try:
            start_time = datetime.now()
            await self._poll_all_accounts()
            end_time = datetime.now()

            return {
                "success": True,
                "message": "Manual poll completed successfully",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": (end_time - start_time).total_seconds()
            }

        except Exception as error:
            return {
                "success": False,
                "message": f"Manual poll failed: {str(error)}",
                "error": str(error)
            }

    def get_status(self) -> dict:
        """Get polling status"""
        config_loader = self._get_config_loader()
        accounts = config_loader.get_enabled_accounts()

        return {
            # Main status
            "is_running": self.is_running,
            "auto_start": settings.auto_start_polling,
            "enabled_accounts": len(accounts),
            "account_names": [acc.name for acc in accounts],
            "mock_mode": settings.use_mock_mode,

            # Position polling status
            "position_polling": {
                "interval_minutes": settings.position_polling_interval_minutes,
                "error_count": self.position_error_count,
                "last_poll_time": self.last_position_poll_time.isoformat() if self.last_position_poll_time else None,
                "poll_count": self.position_poll_count,
            },

            # Order polling status (future enhancement)
            "order_polling": {
                "enabled": self.order_polling_enabled,
                "interval_minutes": settings.order_polling_interval_minutes,
                "error_count": self.order_error_count,
                "last_poll_time": self.last_order_poll_time.isoformat() if self.last_order_poll_time else None,
                "poll_count": self.order_poll_count,
            },

            # Backward compatibility fields
            "interval_seconds": settings.position_polling_interval_minutes * 60,
            "interval_minutes": settings.position_polling_interval_minutes,
            "position_polling_interval_minutes": settings.position_polling_interval_minutes,
            "order_polling_interval_minutes": settings.order_polling_interval_minutes,
            "error_count": self.position_error_count,  # Alias for position errors
            "max_errors": settings.max_polling_errors,
            "last_poll_time": self.last_position_poll_time.isoformat() if self.last_position_poll_time else None,
            "poll_count": self.position_poll_count,  # Alias for position poll count
        }


# Global instance
polling_manager = PollingManager()
