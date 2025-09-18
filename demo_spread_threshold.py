#!/usr/bin/env python3
"""
Demo script for SPREAD_RATIO_THRESHOLD and SPREAD_TICK_MULTIPLE_THRESHOLD functionality.
Shows how to use the spread calculation utilities with configurable thresholds.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import settings
from utils.spread_calculation import (
    get_spread_info,
    is_spread_reasonable,
    format_spread_ratio_as_percentage,
    calculate_spread_ratio,
    calculate_spread_tick_multiple
)


def demo_spread_threshold():
    """Demonstrate the SPREAD_RATIO_THRESHOLD and SPREAD_TICK_MULTIPLE_THRESHOLD functionality"""
    
    print("🚀 SPREAD_RATIO_THRESHOLD & SPREAD_TICK_MULTIPLE_THRESHOLD Demo")
    print("=" * 70)
    print()
    
    # Show current configuration
    print("📋 Current Trading Configuration:")
    print(f"   Spread Ratio Threshold: {settings.spread_ratio_threshold} ({settings.spread_ratio_threshold*100:.1f}%)")
    print(f"   Spread Tick Multiple Threshold: {settings.spread_tick_multiple_threshold}")
    print()
    
    # Demo different spread scenarios
    print("📊 Spread Analysis Demo:")
    print()
    
    # Define test scenarios
    scenarios = [
        {
            "name": "Excellent Liquidity",
            "bid": 0.0500,
            "ask": 0.0502,
            "tick_size": 0.0001,
            "description": "Very tight spread, excellent for trading"
        },
        {
            "name": "Good Liquidity", 
            "bid": 0.0500,
            "ask": 0.0510,
            "tick_size": 0.0001,
            "description": "Reasonable spread, good for trading"
        },
        {
            "name": "Moderate Liquidity",
            "bid": 0.0500,
            "ask": 0.0525,
            "tick_size": 0.0001,
            "description": "Medium spread, acceptable for trading"
        },
        {
            "name": "Poor Liquidity",
            "bid": 0.0500,
            "ask": 0.0600,
            "tick_size": 0.0001,
            "description": "Wide spread, challenging for trading"
        },
        {
            "name": "Very Poor Liquidity",
            "bid": 0.0500,
            "ask": 0.0750,
            "tick_size": 0.0001,
            "description": "Very wide spread, avoid trading"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"🔍 Scenario {i}: {scenario['name']}")
        print(f"   Description: {scenario['description']}")
        print(f"   Bid: {scenario['bid']:.4f}, Ask: {scenario['ask']:.4f}")
        
        # Get comprehensive spread info
        spread_info = get_spread_info(
            bid_price=scenario['bid'],
            ask_price=scenario['ask'],
            tick_size=scenario['tick_size'],
            ratio_threshold=settings.spread_ratio_threshold,
            tick_threshold=settings.spread_tick_multiple_threshold
        )
        
        # Display analysis
        print(f"   📈 Spread Analysis:")
        print(f"     Absolute Spread: {spread_info.absolute_spread:.4f}")
        print(f"     Spread Ratio: {spread_info.formatted_ratio}")
        print(f"     Mid Price: {spread_info.mid_price:.4f}")
        print(f"     Tick Multiple: {spread_info.tick_multiple:.1f}")
        print(f"     Quality: {spread_info.quality_description}")
        
        print(f"   🎯 Trading Decision:")
        print(f"     Reasonable by Ratio: {spread_info.is_reasonable_by_ratio}")
        print(f"     Reasonable by Ticks: {spread_info.is_reasonable_by_ticks}")
        print(f"     Overall Reasonable: {spread_info.is_reasonable_overall}")
        
        # Trading recommendation
        if spread_info.is_reasonable_overall:
            print(f"   ✅ Recommendation: Use progressive pricing strategy")
        else:
            print(f"   ⚠️ Recommendation: Use direct order (market/limit)")
        
        print()
    
    # Demo threshold sensitivity
    print("🔧 Threshold Sensitivity Analysis:")
    print()
    
    # Use a medium spread example
    test_bid = 0.0500
    test_ask = 0.0530
    test_tick = 0.0001
    
    print(f"Test Case: Bid={test_bid:.4f}, Ask={test_ask:.4f}, Tick={test_tick:.4f}")
    print()
    
    threshold_tests = [
        {"ratio": 0.05, "tick": 1, "desc": "Very Strict"},
        {"ratio": 0.10, "tick": 2, "desc": "Strict"},
        {"ratio": 0.15, "tick": 2, "desc": "Default"},
        {"ratio": 0.20, "tick": 3, "desc": "Lenient"},
        {"ratio": 0.30, "tick": 5, "desc": "Very Lenient"}
    ]
    
    for test in threshold_tests:
        is_reasonable = is_spread_reasonable(
            test_bid, test_ask, test_tick,
            test["ratio"], test["tick"]
        )
        
        print(f"   {test['desc']} Thresholds:")
        print(f"     Ratio: {test['ratio']*100:.0f}%, Tick: {test['tick']}")
        print(f"     Result: {'✅ Reasonable' if is_reasonable else '❌ Too Wide'}")
        print()
    
    # Demo environment variable override
    print("🌍 Environment Variable Override Demo:")
    print()
    
    # Show current values
    print(f"Current values:")
    print(f"   SPREAD_RATIO_THRESHOLD: {settings.spread_ratio_threshold}")
    print(f"   SPREAD_TICK_MULTIPLE_THRESHOLD: {settings.spread_tick_multiple_threshold}")
    print()
    
    # Set custom values
    os.environ["SPREAD_RATIO_THRESHOLD"] = "0.25"
    os.environ["SPREAD_TICK_MULTIPLE_THRESHOLD"] = "5"
    
    # Create new settings instance
    from config.settings import Settings
    custom_settings = Settings()
    
    print(f"After override:")
    print(f"   SPREAD_RATIO_THRESHOLD: {custom_settings.spread_ratio_threshold}")
    print(f"   SPREAD_TICK_MULTIPLE_THRESHOLD: {custom_settings.spread_tick_multiple_threshold}")
    print()
    
    # Test with new thresholds
    test_reasonable = is_spread_reasonable(
        test_bid, test_ask, test_tick,
        custom_settings.spread_ratio_threshold,
        custom_settings.spread_tick_multiple_threshold
    )
    
    print(f"Same test case with new thresholds: {'✅ Reasonable' if test_reasonable else '❌ Too Wide'}")
    print()
    
    # Show practical usage
    print("💡 Practical Usage Examples:")
    print()
    print("1. In trading services:")
    print("   ```python")
    print("   from config.settings import settings")
    print("   from utils.spread_calculation import is_spread_reasonable")
    print("   ")
    print("   # Check if spread is reasonable for trading")
    print("   reasonable = is_spread_reasonable(")
    print("       bid_price, ask_price, tick_size,")
    print("       settings.spread_ratio_threshold,")
    print("       settings.spread_tick_multiple_threshold")
    print("   )")
    print("   ```")
    print()
    print("2. In configuration files:")
    print("   ```bash")
    print("   # .env file")
    print("   SPREAD_RATIO_THRESHOLD=0.15      # 15% ratio threshold")
    print("   SPREAD_TICK_MULTIPLE_THRESHOLD=2 # 2x tick threshold")
    print("   ```")
    print()
    
    print("✨ Demo completed successfully!")
    print()
    print("📚 Key Takeaways:")
    print("   - SPREAD_RATIO_THRESHOLD controls ratio-based spread filtering")
    print("   - SPREAD_TICK_MULTIPLE_THRESHOLD controls tick-based spread filtering")
    print("   - Both thresholds work together (OR logic) for comprehensive analysis")
    print("   - Configurable via environment variables for different environments")
    print("   - Used in trading services for optimal order placement strategy")
    
    # Clean up
    for key in ["SPREAD_RATIO_THRESHOLD", "SPREAD_TICK_MULTIPLE_THRESHOLD"]:
        if key in os.environ:
            del os.environ[key]


if __name__ == "__main__":
    demo_spread_threshold()
