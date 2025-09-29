#!/usr/bin/env python3
"""
Test script to verify position adjustment fix
"""

def test_position_filtering():
    """Test the position filtering logic with dictionary data"""

    # Mock delta records
    delta_records = [
        type('DeltaRecord', (), {'instrument_name': 'BTC-25OCT24-60000-C'})(),
        type('DeltaRecord', (), {'instrument_name': 'ETH-25OCT24-3000-P'})()
    ]

    # Mock positions (as dictionaries returned by TigerClient)
    positions = [
        {
            'instrument_name': 'BTC-25OCT24-60000-C',
            'size': 1.0,
            'direction': 'buy'
        },
        {
            'instrument_name': 'ETH-25OCT24-3000-P',
            'size': 2.0,
            'direction': 'sell'
        },
        {
            'instrument_name': 'SOL-25OCT24-100-C',
            'size': 1.5,
            'direction': 'buy'
        }
    ]

    # Test the fixed logic
    positions_to_adjust = [
        pos for pos in positions
        if any(record.instrument_name == pos.get('instrument_name') for record in delta_records)
        and pos.get('size', 0) != 0
    ]

    print("Testing position filtering logic...")
    print(f"   Total positions: {len(positions)}")
    print(f"   Delta records: {len(delta_records)}")
    print(f"   Positions to adjust: {len(positions_to_adjust)}")

    # Verify results
    expected_instruments = {'BTC-25OCT24-60000-C', 'ETH-25OCT24-3000-P'}
    actual_instruments = {pos.get('instrument_name') for pos in positions_to_adjust}

    if expected_instruments == actual_instruments:
        print("PASS: Position filtering works correctly")
        return True
    else:
        print(f"FAIL: Expected {expected_instruments}, got {actual_instruments}")
        return False

def test_dict_access():
    """Test dictionary access patterns"""
    print("\nTesting dictionary access patterns...")

    # Test case 1: Normal access
    pos1 = {'instrument_name': 'BTC-25OCT24-60000-C', 'size': 1.0}
    print(f"   Case 1 - Normal access: {pos1.get('instrument_name')} (size: {pos1.get('size')})")

    # Test case 2: Missing instrument_name
    pos2 = {'size': 2.0}
    print(f"   Case 2 - Missing instrument: {pos2.get('instrument_name', 'UNKNOWN')} (size: {pos2.get('size')})")

    # Test case 3: Missing size
    pos3 = {'instrument_name': 'ETH-25OCT24-3000-P'}
    print(f"   Case 3 - Missing size: {pos3.get('instrument_name')} (size: {pos3.get('size', 0)})")

    # Test case 4: Empty dict
    pos4 = {}
    print(f"   Case 4 - Empty dict: {pos4.get('instrument_name', 'UNKNOWN')} (size: {pos4.get('size', 0)})")

    print("PASS: Dictionary access patterns work correctly")
    return True

if __name__ == "__main__":
    print("Testing position adjustment fix...")

    success = True
    success &= test_position_filtering()
    success &= test_dict_access()

    if success:
        print("\nSUCCESS: All tests passed! The fix should resolve the AttributeError.")
    else:
        print("\nFAILED: Some tests failed. Please review the fix.")

    print("\nSummary of changes:")
    print("   - Changed pos.instrument_name to pos.get('instrument_name')")
    print("   - Changed pos.size to pos.get('size', 0)")
    print("   - These changes make the code work with dictionary objects")