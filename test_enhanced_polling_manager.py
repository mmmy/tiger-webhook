#!/usr/bin/env python3
"""
Test script to verify the enhanced polling manager with POSITION_POLLING_INTERVAL_MINUTES support.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import settings
from services.polling_manager import polling_manager


async def test_enhanced_polling_manager():
    """Test the enhanced polling manager functionality"""
    
    print("🧪 Testing Enhanced Polling Manager with POSITION_POLLING_INTERVAL_MINUTES...")
    print()
    
    # Test 1: Check configuration loading
    print("📋 Test 1: Configuration Loading")
    print(f"   position_polling_interval_minutes: {settings.position_polling_interval_minutes}")
    print(f"   order_polling_interval_minutes: {settings.order_polling_interval_minutes}")
    print(f"   auto_start_polling: {settings.auto_start_polling}")
    print(f"   enable_position_polling: {settings.enable_position_polling}")
    print(f"   max_polling_errors: {settings.max_polling_errors}")
    print()
    
    # Test 2: Check initial status
    print("📋 Test 2: Initial Polling Status")
    status = polling_manager.get_status()
    
    print(f"   is_running: {status['is_running']}")
    print(f"   interval_minutes: {status['interval_minutes']}")
    print(f"   position_polling_interval_minutes: {status['position_polling_interval_minutes']}")
    print(f"   order_polling_interval_minutes: {status['order_polling_interval_minutes']}")
    print(f"   enabled_accounts: {status['enabled_accounts']}")
    print(f"   mock_mode: {status['mock_mode']}")
    print()
    
    print("   Position Polling Details:")
    pos_status = status['position_polling']
    print(f"     interval_minutes: {pos_status['interval_minutes']}")
    print(f"     error_count: {pos_status['error_count']}")
    print(f"     poll_count: {pos_status['poll_count']}")
    print(f"     last_poll_time: {pos_status['last_poll_time']}")
    print()
    
    print("   Order Polling Details:")
    order_status = status['order_polling']
    print(f"     enabled: {order_status['enabled']}")
    print(f"     interval_minutes: {order_status['interval_minutes']}")
    print(f"     error_count: {order_status['error_count']}")
    print(f"     poll_count: {order_status['poll_count']}")
    print(f"     last_poll_time: {order_status['last_poll_time']}")
    print()
    
    # Test 3: Test manual polling
    print("📋 Test 3: Manual Polling Test")
    try:
        result = await polling_manager.poll_once()
        print(f"   Manual poll success: {result['success']}")
        print(f"   Message: {result['message']}")
        if 'duration_seconds' in result:
            print(f"   Duration: {result['duration_seconds']:.2f} seconds")
    except Exception as error:
        print(f"   Manual poll error: {error}")
    print()
    
    # Test 4: Test polling start/stop (brief test)
    print("📋 Test 4: Polling Start/Stop Test")
    
    # Start polling
    print("   Starting polling...")
    await polling_manager.start_polling()
    
    # Check status after start
    status_after_start = polling_manager.get_status()
    print(f"   After start - is_running: {status_after_start['is_running']}")
    
    # Wait a short time
    print("   Waiting 3 seconds...")
    await asyncio.sleep(3)
    
    # Stop polling
    print("   Stopping polling...")
    await polling_manager.stop_polling()
    
    # Check status after stop
    status_after_stop = polling_manager.get_status()
    print(f"   After stop - is_running: {status_after_stop['is_running']}")
    print()
    
    # Test 5: Test environment variable override
    print("📋 Test 5: Environment Variable Override Test")
    
    # Set custom environment variables
    os.environ["POSITION_POLLING_INTERVAL_MINUTES"] = "25"
    os.environ["ORDER_POLLING_INTERVAL_MINUTES"] = "8"
    
    # Create new settings instance to test override
    from config.settings import Settings
    test_settings = Settings()
    
    print(f"   POSITION_POLLING_INTERVAL_MINUTES=25 -> {test_settings.position_polling_interval_minutes}")
    print(f"   ORDER_POLLING_INTERVAL_MINUTES=8 -> {test_settings.order_polling_interval_minutes}")
    
    # Verify conversion to seconds
    expected_seconds = test_settings.position_polling_interval_minutes * 60
    print(f"   {test_settings.position_polling_interval_minutes} minutes = {expected_seconds} seconds")
    print()
    
    # Test 6: Backward compatibility check
    print("📋 Test 6: Backward Compatibility Check")
    status = polling_manager.get_status()
    
    # Check that old field names still exist
    backward_compat_fields = [
        'interval_seconds', 'interval_minutes', 'error_count', 
        'last_poll_time', 'poll_count'
    ]
    
    for field in backward_compat_fields:
        if field in status:
            print(f"   ✅ {field}: {status[field]}")
        else:
            print(f"   ❌ {field}: MISSING")
    print()
    
    print("🎉 Enhanced Polling Manager test completed!")
    
    # Clean up environment variables
    for key in ["POSITION_POLLING_INTERVAL_MINUTES", "ORDER_POLLING_INTERVAL_MINUTES"]:
        if key in os.environ:
            del os.environ[key]


if __name__ == "__main__":
    asyncio.run(test_enhanced_polling_manager())
