#!/usr/bin/env python3
"""
Test script to demonstrate millisecond precision logging

This script shows how the new logging system works with millisecond timestamps.
"""

import asyncio
import time
from datetime import datetime

# Add src to path for imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from deribit_webhook.utils.logging_config import init_logging, get_global_logger, debug, info, warning, error, critical


async def test_logging_precision():
    """Test logging with millisecond precision"""
    
    # Initialize logging
    logger = init_logging()
    
    print("=" * 60)
    print("Testing Millisecond Precision Logging")
    print("=" * 60)
    
    # Test different log levels with context
    logger.info("🚀 Application starting", 
               version="1.0.0",
               environment="test",
               timestamp_precision="milliseconds")
    
    # Test rapid logging to show millisecond differences
    for i in range(5):
        logger.debug("Rapid log entry", 
                    iteration=i,
                    current_time=datetime.now().isoformat())
        await asyncio.sleep(0.001)  # 1ms delay
    
    # Test with different data types
    logger.info("📊 Trading data received",
               symbol="BTC-25DEC24-100000-C",
               price=45678.123,
               volume=1.5,
               bid=45677.5,
               ask=45678.7,
               spread=1.2,
               timestamp=time.time())
    
    # Test warning with context
    logger.warning("⚠️ High spread detected",
                  symbol="ETH-25DEC24-3500-P",
                  spread_ratio=0.25,
                  threshold=0.15,
                  action="skipping_trade")
    
    # Test error logging
    try:
        # Simulate an error
        raise ValueError("Simulated trading error for testing")
    except Exception as e:
        logger.error("❌ Trading operation failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    operation="place_order",
                    symbol="BTC-25DEC24-100000-C")
    
    # Test critical logging
    logger.critical("🚨 System critical alert",
                   component="position_manager",
                   issue="connection_lost",
                   retry_count=3,
                   max_retries=3)
    
    # Test convenience functions
    info("📈 Position update", account="test_account", delta=0.25)
    warning("⏰ Polling timeout", timeout_seconds=30)
    error("🔌 API connection failed", endpoint="/api/v2/private/get_positions")
    
    # Test with nested data
    logger.info("📋 Account summary",
               account_data={
                   "name": "test_account",
                   "balance": 10000.50,
                   "positions": [
                       {"symbol": "BTC-25DEC24-100000-C", "size": 1.0, "delta": 0.5},
                       {"symbol": "ETH-25DEC24-3500-P", "size": -2.0, "delta": -0.3}
                   ],
                   "total_delta": 0.2
               })
    
    print("\n" + "=" * 60)
    print("Logging test completed!")
    print("Check the log file for millisecond timestamps.")
    print("=" * 60)


def test_timestamp_formats():
    """Test different timestamp formats"""
    print("\nTesting timestamp formats:")
    print("-" * 40)
    
    # Current time with different precisions
    now = datetime.now()
    
    print(f"Standard format:     {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"With milliseconds:   {now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
    print(f"With microseconds:   {now.strftime('%Y-%m-%d %H:%M:%S.%f')}")
    print(f"ISO format:          {now.isoformat()}")
    print(f"Timestamp:           {now.timestamp()}")


if __name__ == "__main__":
    # Test timestamp formats first
    test_timestamp_formats()
    
    # Run async logging test
    asyncio.run(test_logging_precision())
