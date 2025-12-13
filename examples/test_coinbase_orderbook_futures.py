"""
Coinbase Perp-Style Futures - Complete Capability Test

This script tests all available high-frequency data capabilities for
Coinbase perp-style futures contracts:

Contracts:
- BIP-20DEC30-CDE: Bitcoin nano perp (0.01 BTC per contract)
- ETP-20DEC30-CDE: Ethereum nano perp
- SLP-20DEC30-CDE: Solana nano perp
- XPP-20DEC30-CDE: XRP nano perp

Capabilities:
1. REST API - Recent trades (tick-level data, last 100 trades)
2. REST API - Historical OHLCV (1-minute granularity)
3. REST API - Orderbook snapshots
4. WebSocket - Real-time orderbook streaming (level2)
5. WebSocket - Real-time trade streaming (market_trades)
"""

import asyncio
from datetime import datetime
from pathlib import Path


def load_env_file(filepath: str) -> dict:
    """Load environment variables from a file."""
    env_vars = {}
    path = Path(filepath).expanduser()
    if path.exists():
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


PERP_CONTRACTS = {
    'BTC': 'BIP-20DEC30-CDE',
    'ETH': 'ETP-20DEC30-CDE',
    'SOL': 'SLP-20DEC30-CDE',
    'XRP': 'XPP-20DEC30-CDE',
}


async def test_rest_api():
    """Test REST API capabilities."""
    print("=" * 70)
    print("REST API TESTS")
    print("=" * 70)

    env = load_env_file("~/.env.fin")
    api_key = env.get("COINBASE_KEY")
    api_secret = env.get("COINBASE_PRIVATE_KEY")

    from wrdata.providers.coinbase_advanced_provider import CoinbaseAdvancedProvider
    provider = CoinbaseAdvancedProvider(api_key=api_key, api_secret=api_secret)

    print(f"\nAuthenticated: {provider.is_authenticated}")

    # Test 1: Recent trades (tick data)
    print("\n--- Recent Trades (Tick Data) ---")
    for asset, contract in PERP_CONTRACTS.items():
        result = provider.get_recent_trades(contract)
        if result['success']:
            trades = result['data'].get('trades', [])
            print(f"{asset}: {len(trades)} trades")
            if trades:
                t = trades[0]
                print(f"  Latest: ${float(t['price']):,.0f} | Size: {t['size']} | {t['side']}")
        else:
            print(f"{asset}: FAILED - {result['error']}")

    # Test 2: Historical 1-minute data
    print("\n--- Historical 1-Minute OHLCV ---")
    for asset, contract in list(PERP_CONTRACTS.items())[:2]:
        result = provider.fetch_timeseries(contract, '2025-12-11', '2025-12-11', interval='1m')
        if result.success:
            print(f"{asset}: {len(result.data)} candles")
        else:
            print(f"{asset}: FAILED - {result.error}")

    # Test 3: Orderbook snapshot
    print("\n--- Orderbook Snapshot ---")
    for asset, contract in list(PERP_CONTRACTS.items())[:2]:
        result = provider.get_product_book(contract, limit=5)
        if result['success']:
            pb = result['data'].get('pricebook', {})
            bids, asks = pb.get('bids', []), pb.get('asks', [])
            if bids and asks:
                spread = float(asks[0]['price']) - float(bids[0]['price'])
                print(f"{asset}: Bid ${float(bids[0]['price']):,.0f} | Ask ${float(asks[0]['price']):,.0f} | Spread ${spread:.0f}")
        else:
            print(f"{asset}: FAILED - {result['error']}")


async def test_websocket_orderbook(duration_seconds: int = 10):
    """Test WebSocket orderbook streaming."""
    print("\n" + "=" * 70)
    print("WEBSOCKET ORDERBOOK STREAMING")
    print("=" * 70)

    from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider

    for asset, contract in list(PERP_CONTRACTS.items())[:2]:
        provider = CoinbaseStreamProvider()
        await provider.connect()

        count = 0
        start = datetime.utcnow()
        try:
            async for msg in provider.subscribe_depth(contract):
                count += 1
                if count == 1:
                    print(f"\n{asset} ({contract}):")
                    print(f"  Bid: ${msg.bid:,.0f} | Ask: ${msg.ask:,.0f}")
                if (datetime.utcnow() - start).total_seconds() > duration_seconds:
                    break
        finally:
            await provider.disconnect()
        print(f"  {count} updates in {duration_seconds}s ({count/duration_seconds:.1f}/sec)")


async def test_websocket_trades(duration_seconds: int = 15):
    """Test WebSocket trade streaming."""
    print("\n" + "=" * 70)
    print("WEBSOCKET TRADE STREAMING")
    print("=" * 70)

    from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider

    contract = PERP_CONTRACTS['BTC']
    provider = CoinbaseStreamProvider()
    await provider.connect()

    print(f"\nBTC Perp ({contract}) - {duration_seconds} seconds:")
    print()

    count = 0
    start = datetime.utcnow()
    try:
        async for msg in provider.subscribe_market_trades(contract):
            count += 1
            if count <= 20:
                side = msg.raw_data.get('side', 'N/A')
                print(f"  #{count:3d} {msg.timestamp.strftime('%H:%M:%S')} | ${msg.price:>10,.0f} | Size: {msg.volume:>6} | {side:>4}")
            if (datetime.utcnow() - start).total_seconds() > duration_seconds:
                break
    finally:
        await provider.disconnect()

    print()
    print(f"  Total: {count} trades ({count/duration_seconds:.1f}/sec)")


async def test_multi_asset_streaming(duration_seconds: int = 10):
    """Test concurrent multi-asset streaming."""
    print("\n" + "=" * 70)
    print("MULTI-ASSET CONCURRENT STREAMING")
    print("=" * 70)

    from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider

    results = {}

    async def stream_trades(name, symbol):
        provider = CoinbaseStreamProvider()
        await provider.connect()
        count = 0
        start = datetime.utcnow()
        try:
            async for msg in provider.subscribe_market_trades(symbol):
                count += 1
                if (datetime.utcnow() - start).total_seconds() > duration_seconds:
                    break
        finally:
            await provider.disconnect()
        results[f'{name}_trades'] = count

    async def stream_orderbook(name, symbol):
        provider = CoinbaseStreamProvider()
        await provider.connect()
        count = 0
        start = datetime.utcnow()
        try:
            async for msg in provider.subscribe_depth(symbol):
                count += 1
                if (datetime.utcnow() - start).total_seconds() > duration_seconds:
                    break
        finally:
            await provider.disconnect()
        results[f'{name}_orderbook'] = count

    # Stream all 4 assets
    tasks = []
    for name, symbol in PERP_CONTRACTS.items():
        tasks.append(stream_trades(name, symbol))
        tasks.append(stream_orderbook(name, symbol))

    print(f"\nStreaming all 4 perps ({duration_seconds} seconds)...")
    await asyncio.gather(*tasks)

    print("\nResults:")
    for key, count in sorted(results.items()):
        print(f"  {key}: {count} updates ({count/duration_seconds:.1f}/sec)")


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("COINBASE PERP-STYLE FUTURES - COMPLETE CAPABILITY TEST")
    print(f"Started: {datetime.now()}")
    print("=" * 70)

    await test_rest_api()
    await test_websocket_orderbook(duration_seconds=5)
    await test_websocket_trades(duration_seconds=10)
    await test_multi_asset_streaming(duration_seconds=8)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
Available Data:

  REST API:
    - get_recent_trades(symbol)     : Last 100 trades (tick-level)
    - fetch_timeseries(symbol, ...) : Historical OHLCV (1m finest)
    - get_product_book(symbol)      : Current orderbook snapshot
    - get_futures_products()        : List all futures contracts

  WebSocket Streaming:
    - subscribe_depth(symbol)         : Real-time orderbook (level2)
    - subscribe_market_trades(symbol) : Real-time tick trades

Perp-Style Futures Contracts:
    - BIP-20DEC30-CDE : BTC (0.01 BTC per contract)
    - ETP-20DEC30-CDE : ETH
    - SLP-20DEC30-CDE : SOL
    - XPP-20DEC30-CDE : XRP

Note: Historical tick data is NOT available via REST API.
      For historical ticks, you need to stream and store data yourself.
""")


if __name__ == "__main__":
    asyncio.run(main())
