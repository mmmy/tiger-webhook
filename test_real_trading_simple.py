#!/usr/bin/env python3
"""
简化的真实期权交易测试
使用指定参数：yq2024账户, btcusdt, delta1=0.5, delta2=0.7, n=2, size=1000
"""

import requests
import json
from datetime import datetime

def test_real_trading():
    """测试真实期权交易"""
    
    print("🚀 测试真实期权交易功能")
    print("🎯 参数: yq2024, btcusdt, delta1=0.5, delta2=0.7, n=2, size=100 (cash mode)")
    print("=" * 60)
    
    # 构造 webhook 信号
    webhook_payload = {
        "accountName": "yq2024",
        "side": "buy",
        "exchange": "deribit", 
        "period": "1h",
        "marketPosition": "long",
        "prevMarketPosition": "flat",
        "symbol": "btcusdt",
        "price": "65000.0",
        "timestamp": datetime.now().isoformat(),
        "size": "100",
        "positionSize": "0",
        "id": "test_real_001",
        "tv_id": 12345,
        "alertMessage": "BTC期权开仓信号",
        "comment": "开仓测试",
        "qtyType": "cash",
        "delta1": 0.5,
        "n": 2,
        "delta2": 0.7
    }
    
    print("📡 发送 Webhook 信号...")
    
    try:
        response = requests.post(
            "http://localhost:3001/webhook/signal",
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        print(f"📊 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 成功!")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print("❌ 失败!")
            print(f"错误: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

if __name__ == "__main__":
    test_real_trading()
