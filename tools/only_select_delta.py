import asyncio
from datetime import datetime

import sys, os
sys.path.insert(0, os.path.abspath('.'))
from src.deribit_webhook.services.tiger_client import TigerClient

async def run_combo(client: TigerClient, target_delta: float, min_days: int):
    print(f"\n=== Test: target_delta={target_delta}, min_days={min_days} ===")
    result = await client.get_instrument_by_delta(
        currency='USD',
        min_expired_days=min_days,
        delta=target_delta,
        long_side=True,
        underlying_asset='QQQ'
    )
    if not result:
        print('[SELECT] No instrument found')
        return
    name = result.instrument.instrument_name
    bid = result.details.best_bid_price
    ask = result.details.best_ask_price
    spread = result.spread_ratio
    idx = result.details.index_price
    # Fetch detailed greeks for the chosen instrument
    ticker = await client.get_ticker(name)
    greeks = ticker.get('greeks', {}) if ticker else {}
    delta_val = greeks.get('delta') if greeks else None

    print('[SELECT] Instrument:', name)
    print('[SELECT] Bid/Ask:', bid, '/', ask)
    print('[SELECT] Spread Ratio:', f'{spread*100:.2f}%')
    print('[SELECT] Underlying(Index) Price:', idx)
    print('[SELECT] Greeks.delta:', delta_val)

async def main():
    client = TigerClient()
    try:
        for d in (0.35, 0.5):
            for n in (7, 14):
                await run_combo(client, d, n)
    finally:
        await client.close()

if __name__ == '__main__':
    asyncio.run(main())

