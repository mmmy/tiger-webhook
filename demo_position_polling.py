#!/usr/bin/env python3
"""
Demo script for POSITION_POLLING_INTERVAL_MINUTES functionality.
Shows how to use the enhanced polling manager with minute-based intervals.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from deribit_webhook.config.settings import settings
from deribit_webhook.services.polling_manager import polling_manager


async def demo_position_polling():
    """Demonstrate the POSITION_POLLING_INTERVAL_MINUTES functionality"""
    
    print("🚀 POSITION_POLLING_INTERVAL_MINUTES Demo")
    print("=" * 50)
    print()
    
    # Show current configuration
    print("📋 Current Configuration:")
    print(f"   Position Polling Interval: {settings.position_polling_interval_minutes} minutes")
    print(f"   Order Polling Interval: {settings.order_polling_interval_minutes} minutes")
    print(f"   Auto Start Polling: {settings.auto_start_polling}")
    print(f"   Mock Mode: {settings.use_mock_mode}")
    print(f"   Max Polling Errors: {settings.max_polling_errors}")
    print()
    
    # Show initial status
    print("📊 Initial Polling Status:")
    status = polling_manager.get_status()
    print(f"   Running: {status['is_running']}")
    print(f"   Enabled Accounts: {status['enabled_accounts']}")
    print(f"   Account Names: {', '.join(status['account_names'])}")
    print()
    
    # Demonstrate manual polling
    print("🔄 Manual Polling Demo:")
    print("   Triggering manual poll...")
    
    result = await polling_manager.poll_once()
    if result['success']:
        print(f"   ✅ Success: {result['message']}")
        print(f"   Duration: {result.get('duration_seconds', 0):.2f} seconds")
    else:
        print(f"   ❌ Failed: {result['message']}")
    print()
    
    # Demonstrate polling start/stop
    print("⚡ Polling Control Demo:")
    
    # Start polling
    print("   Starting polling...")
    await polling_manager.start_polling()
    
    # Show status while running
    running_status = polling_manager.get_status()
    print(f"   Status: Running = {running_status['is_running']}")
    print(f"   Next poll in: {running_status['interval_minutes']} minutes")
    
    # Wait a few seconds to see polling in action
    print("   Waiting 5 seconds to observe polling...")
    await asyncio.sleep(5)
    
    # Stop polling
    print("   Stopping polling...")
    await polling_manager.stop_polling()
    
    # Show final status
    final_status = polling_manager.get_status()
    print(f"   Final Status: Running = {final_status['is_running']}")
    print()
    
    # Show detailed status information
    print("📈 Detailed Status Information:")
    status = polling_manager.get_status()
    
    print("   Position Polling:")
    pos_status = status['position_polling']
    print(f"     Interval: {pos_status['interval_minutes']} minutes")
    print(f"     Poll Count: {pos_status['poll_count']}")
    print(f"     Error Count: {pos_status['error_count']}")
    print(f"     Last Poll: {pos_status['last_poll_time'] or 'Never'}")
    
    print("   Order Polling (Future Feature):")
    order_status = status['order_polling']
    print(f"     Enabled: {order_status['enabled']}")
    print(f"     Interval: {order_status['interval_minutes']} minutes")
    print(f"     Poll Count: {order_status['poll_count']}")
    print()
    
    # Demonstrate environment variable override
    print("🔧 Environment Variable Override Demo:")
    
    # Set custom values
    os.environ["POSITION_POLLING_INTERVAL_MINUTES"] = "30"
    os.environ["ORDER_POLLING_INTERVAL_MINUTES"] = "10"
    
    # Create new settings instance
    from deribit_webhook.config.settings import Settings
    custom_settings = Settings()
    
    print(f"   Custom Position Interval: {custom_settings.position_polling_interval_minutes} minutes")
    print(f"   Custom Order Interval: {custom_settings.order_polling_interval_minutes} minutes")
    print(f"   Converted to seconds: {custom_settings.position_polling_interval_minutes * 60} seconds")
    print()
    
    # Show API endpoints
    print("🌐 Available API Endpoints:")
    print("   GET  /api/positions/polling/status  - Get polling status")
    print("   POST /api/positions/polling/start   - Start polling")
    print("   POST /api/positions/polling/stop    - Stop polling")
    print("   POST /api/positions/poll            - Manual poll")
    print()
    
    print("✨ Demo completed successfully!")
    print()
    print("💡 Tips:")
    print("   - Set POSITION_POLLING_INTERVAL_MINUTES in .env file")
    print("   - Use AUTO_START_POLLING=true for automatic startup")
    print("   - Monitor polling status via API endpoints")
    print("   - Check logs for detailed polling information")
    
    # Clean up
    for key in ["POSITION_POLLING_INTERVAL_MINUTES", "ORDER_POLLING_INTERVAL_MINUTES"]:
        if key in os.environ:
            del os.environ[key]


if __name__ == "__main__":
    asyncio.run(demo_position_polling())
