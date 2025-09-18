#!/usr/bin/env python3
"""
Test script to demonstrate text format logging with millisecond precision
"""

import os
import sys
import time
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set environment variables for text format
os.environ['LOG_FORMAT'] = 'text'
os.environ['LOG_FILE'] = './logs/text_format.log'
os.environ['LOG_LEVEL'] = 'DEBUG'

from utils.logging_config import init_logging, get_global_logger


def test_text_format_logging():
    """Test text format logging with millisecond precision"""
    
    # Initialize logging with text format
    logger = init_logging()
    
    print("=" * 60)
    print("Testing Text Format Logging with Millisecond Precision")
    print("=" * 60)
    
    # Test rapid logging to show millisecond differences
    logger.info("🚀 Application starting in text format")
    
    for i in range(3):
        logger.debug("Debug message", iteration=i, timestamp=datetime.now().isoformat())
        time.sleep(0.002)  # 2ms delay
    
    logger.info("📊 Trading data", 
               symbol="BTC-25DEC24-100000-C",
               price=45678.123,
               volume=1.5)
    
    logger.warning("⚠️ High spread detected", 
                  spread_ratio=0.25,
                  threshold=0.15)
    
    logger.error("❌ Connection failed", 
                endpoint="/api/v2/private/get_positions",
                retry_count=3)
    
    print("\nText format logging completed!")
    print("Check ./logs/text_format.log for the output")


if __name__ == "__main__":
    test_text_format_logging()
