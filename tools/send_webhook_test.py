import json
from datetime import datetime
import sys
import requests

PORT = 3002
URL = f"http://localhost:{PORT}/webhook/signal"

payload = {
    "accountName": "tiger_main",
    "side": "buy",
    "exchange": "deribit",
    "period": "1h",
    "marketPosition": "long",
    "prevMarketPosition": "flat",
    "symbol": "QQQ",
    "price": "",  # empty -> treated as market
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "size": "100",
    "positionSize": "0",
    "id": "test_qqq_long_s100_d040_060_n3",
    "tv_id": 987654321,
    "alertMessage": "Test QQQ open long",
    "comment": "delta-open",
    "qtyType": "cash",
    "delta1": 0.4,
    "delta2": 0.6,
    "n": 3,
}

try:
    print("POST", URL)
    print(json.dumps(payload))
    r = requests.post(URL, json=payload, timeout=60)
    print("Status:", r.status_code)
    ct = r.headers.get("content-type", "")
    if ct.startswith("application/json"):
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    else:
        print(r.text[:1000])
    sys.exit(0 if r.ok else 1)
except Exception as e:
    print("ERROR:", e)
    sys.exit(2)

