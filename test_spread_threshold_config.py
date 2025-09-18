#!/usr/bin/env python3
"""
Test script to verify SPREAD_RATIO_THRESHOLD and SPREAD_TICK_MULTIPLE_THRESHOLD configuration.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import settings
from utils.spread_calculation import (
    calculate_spread_ratio,
    calculate_spread_tick_multiple,
    is_spread_reasonable,
    get_spread_info,
    format_spread_ratio_as_percentage
)


def test_spread_threshold_config():
    """Test SPREAD_RATIO_THRESHOLD and SPREAD_TICK_MULTIPLE_THRESHOLD configuration"""
    
    print("🧪 Testing SPREAD_RATIO_THRESHOLD and SPREAD_TICK_MULTIPLE_THRESHOLD...")
    print()
    
    # Test 1: Check default configuration values
    print("📋 Test 1: Default Configuration Values")
    print(f"   spread_ratio_threshold: {settings.spread_ratio_threshold}")
    print(f"   spread_tick_multiple_threshold: {settings.spread_tick_multiple_threshold}")
    print()
    
    # Test 2: Test environment variable loading
    print("📋 Test 2: Environment Variable Loading")
    
    # Set custom environment variables
    os.environ["SPREAD_RATIO_THRESHOLD"] = "0.20"
    os.environ["SPREAD_TICK_MULTIPLE_THRESHOLD"] = "3"
    
    # Create new settings instance to test override
    from config.settings import Settings
    test_settings = Settings()
    
    print(f"   SPREAD_RATIO_THRESHOLD=0.20 -> {test_settings.spread_ratio_threshold}")
    print(f"   SPREAD_TICK_MULTIPLE_THRESHOLD=3 -> {test_settings.spread_tick_multiple_threshold}")
    print()
    
    # Test 3: Test spread calculation functions
    print("📋 Test 3: Spread Calculation Functions")
    
    # Test case 1: Narrow spread (good liquidity)
    bid_price = 0.0500
    ask_price = 0.0505
    tick_size = 0.0001
    
    spread_ratio = calculate_spread_ratio(bid_price, ask_price)
    tick_multiple = calculate_spread_tick_multiple(bid_price, ask_price, tick_size)
    is_reasonable = is_spread_reasonable(bid_price, ask_price, tick_size, 
                                       settings.spread_ratio_threshold, 
                                       settings.spread_tick_multiple_threshold)
    
    print(f"   Test Case 1 - Narrow Spread:")
    print(f"     Bid: {bid_price}, Ask: {ask_price}, Tick: {tick_size}")
    print(f"     Spread Ratio: {format_spread_ratio_as_percentage(spread_ratio)}")
    print(f"     Tick Multiple: {tick_multiple:.1f}")
    print(f"     Is Reasonable: {is_reasonable}")
    print()
    
    # Test case 2: Wide spread (poor liquidity)
    bid_price = 0.0500
    ask_price = 0.0600
    tick_size = 0.0001
    
    spread_ratio = calculate_spread_ratio(bid_price, ask_price)
    tick_multiple = calculate_spread_tick_multiple(bid_price, ask_price, tick_size)
    is_reasonable = is_spread_reasonable(bid_price, ask_price, tick_size, 
                                       settings.spread_ratio_threshold, 
                                       settings.spread_tick_multiple_threshold)
    
    print(f"   Test Case 2 - Wide Spread:")
    print(f"     Bid: {bid_price}, Ask: {ask_price}, Tick: {tick_size}")
    print(f"     Spread Ratio: {format_spread_ratio_as_percentage(spread_ratio)}")
    print(f"     Tick Multiple: {tick_multiple:.1f}")
    print(f"     Is Reasonable: {is_reasonable}")
    print()
    
    # Test 4: Test comprehensive spread info
    print("📋 Test 4: Comprehensive Spread Info")
    
    spread_info = get_spread_info(
        bid_price=0.0500,
        ask_price=0.0520,
        tick_size=0.0001,
        ratio_threshold=settings.spread_ratio_threshold,
        tick_threshold=settings.spread_tick_multiple_threshold
    )
    
    print(f"   Spread Info:")
    print(f"     Bid Price: {spread_info.bid_price}")
    print(f"     Ask Price: {spread_info.ask_price}")
    print(f"     Absolute Spread: {spread_info.absolute_spread}")
    print(f"     Spread Ratio: {spread_info.formatted_ratio}")
    print(f"     Mid Price: {spread_info.mid_price}")
    print(f"     Quality: {spread_info.quality_description}")
    print(f"     Tick Multiple: {spread_info.tick_multiple:.1f}")
    print(f"     Reasonable by Ratio: {spread_info.is_reasonable_by_ratio}")
    print(f"     Reasonable by Ticks: {spread_info.is_reasonable_by_ticks}")
    print(f"     Reasonable Overall: {spread_info.is_reasonable_overall}")
    print()
    
    # Test 5: Test different threshold scenarios
    print("📋 Test 5: Different Threshold Scenarios")
    
    test_cases = [
        {"bid": 0.0500, "ask": 0.0505, "description": "Very narrow spread"},
        {"bid": 0.0500, "ask": 0.0510, "description": "Narrow spread"},
        {"bid": 0.0500, "ask": 0.0520, "description": "Medium spread"},
        {"bid": 0.0500, "ask": 0.0550, "description": "Wide spread"},
        {"bid": 0.0500, "ask": 0.0600, "description": "Very wide spread"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        bid = case["bid"]
        ask = case["ask"]
        desc = case["description"]
        
        ratio = calculate_spread_ratio(bid, ask)
        tick_mult = calculate_spread_tick_multiple(bid, ask, 0.0001)
        reasonable = is_spread_reasonable(bid, ask, 0.0001, 
                                        settings.spread_ratio_threshold,
                                        settings.spread_tick_multiple_threshold)
        
        print(f"   Case {i} - {desc}:")
        print(f"     Prices: {bid} / {ask}")
        print(f"     Ratio: {format_spread_ratio_as_percentage(ratio)}")
        print(f"     Tick Multiple: {tick_mult:.1f}")
        print(f"     Reasonable: {reasonable}")
        print()
    
    # Test 6: Test with different thresholds
    print("📋 Test 6: Custom Threshold Testing")
    
    bid_price = 0.0500
    ask_price = 0.0520
    tick_size = 0.0001
    
    thresholds = [
        {"ratio": 0.10, "tick": 1, "desc": "Strict thresholds"},
        {"ratio": 0.15, "tick": 2, "desc": "Default thresholds"},
        {"ratio": 0.25, "tick": 5, "desc": "Lenient thresholds"},
    ]
    
    for threshold in thresholds:
        reasonable = is_spread_reasonable(bid_price, ask_price, tick_size,
                                        threshold["ratio"], threshold["tick"])
        print(f"   {threshold['desc']} (ratio={threshold['ratio']*100:.0f}%, tick={threshold['tick']}): {reasonable}")
    
    print()
    print("🎉 SPREAD_RATIO_THRESHOLD configuration test completed!")
    
    # Clean up environment variables
    for key in ["SPREAD_RATIO_THRESHOLD", "SPREAD_TICK_MULTIPLE_THRESHOLD"]:
        if key in os.environ:
            del os.environ[key]


if __name__ == "__main__":
    test_spread_threshold_config()
