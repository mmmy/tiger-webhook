#!/usr/bin/env python3
"""
Test webhook signal to create data for testing edit and delete functionality
"""

import requests
import json

def test_webhook_signal():
    """Send a webhook signal to create test data"""
    
    # Webhook URL
    url = "http://localhost:3001/webhook/signal"
    
    # Test data - complete TradingView webhook payload
    payload = {
        "accountName": "yq2024",
        "side": "buy",
        "exchange": "deribit",
        "period": "1h",
        "marketPosition": "long",
        "prevMarketPosition": "flat",
        "symbol": "btcusdt",
        "price": "50000.0",
        "timestamp": "2024-01-01T12:00:00Z",
        "size": "1000",
        "positionSize": "0",
        "id": "test_signal_001",
        "tv_id": 12345,
        "alertMessage": "Test signal for edit/delete functionality",
        "comment": "Test entry signal",
        "qtyType": "cash",
        "delta1": 0.5,
        "delta2": 0.7,
        "n": 2
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("🚀 Sending webhook signal...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            result = response.json()
            print(f"📊 Response Body: {json.dumps(result, indent=2)}")
        else:
            print(f"📊 Response Body: {response.text}")
            
        if response.status_code == 200:
            print("✅ Webhook signal sent successfully!")
            return True
        else:
            print(f"❌ Webhook signal failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending webhook signal: {e}")
        return False

if __name__ == "__main__":
    test_webhook_signal()
