"""
Live test of Coinbase provider.

No API key required for public market data!
Tests both historical REST API and real-time WebSocket streaming.
"""

import asyncio
from wrdata import DataStream
from wrdata.providers.coinbase_provider import CoinbaseProvider, POPULAR_PAIRS


def test_coinbase_provider():
    """Test Coinbase provider directly."""
    print("=" * 60)
    print("Testing Coinbase Provider")
    print("=" * 60)

    # Create provider (no API key needed!)
    print("\n✓ Creating Coinbase provider (no API key required)")
    provider = CoinbaseProvider()

    # Test connection
    print("✓ Testing connection...")
    if provider.validate_connection():
        print("  ✓ Connection successful!")
    else:
        print("  ❌ Connection failed!")
        return

    # Get available products
    print("\n✓ Fetching available trading pairs...")
    products = provider.get_products()
    if products:
        print(f"  ✓ Found {len(products)} trading pairs")
        print("  First 5 pairs:")
        for product in products[:5]:
            print(f"    {product['id']}: {product.get('display_name', 'N/A')}")
    else:
        print("  ❌ Failed to get products")

    # Test BTC-USD historical data
    print("\n✓ Fetching BTC-USD historical data...")
    response = provider.fetch_timeseries(
        symbol="BTC-USD",
        start_date="2024-11-01",
        end_date="2024-11-07",
        interval="1d"
    )

    if response.success:
        print(f"  ✓ Got {len(response.data)} data points")
        if response.data:
            print(f"  First point: {response.data[0]}")
            print(f"  Last point: {response.data[-1]}")
    else:
        print(f"  ❌ Failed: {response.error}")

    # Test ETH-USD data
    print("\n✓ Fetching ETH-USD historical data...")
    response = provider.fetch_timeseries(
        symbol="ETH-USD",
        start_date="2024-11-01",
        end_date="2024-11-07",
        interval="1d"
    )

    if response.success:
        print(f"  ✓ Got {len(response.data)} data points")
        if response.data:
            print(f"  Last point: {response.data[-1]}")
    else:
        print(f"  ❌ Failed: {response.error}")

    print("\n" + "=" * 60)
    print("Coinbase Provider Test Complete!")
    print("=" * 60)


def test_datastream_with_coinbase():
    """Test Coinbase via DataStream API."""
    print("\n" + "=" * 60)
    print("Testing Coinbase via DataStream")
    print("=" * 60)

    # Create DataStream
    stream = DataStream()

    # Check provider status
    status = stream.status()
    print(f"\n✓ Available providers: {list(stream.providers.keys())}")
    if 'coinbase' in status:
        print(f"  Coinbase connected: {status['coinbase'].get('connected', False)}")

    # Fetch Bitcoin data
    print("\n✓ Fetching Bitcoin (BTC-USD) via DataStream...")
    df = stream.get(
        "BTC-USD",
        start="2024-11-01",
        end="2024-11-07",
        asset_type="crypto"
    )

    print(f"  ✓ Got {len(df)} rows of BTC data")
    if len(df) > 0:
        print("\n  Latest BTC prices:")
        print(df.tail(5))

    # Fetch Ethereum data
    print("\n✓ Fetching Ethereum (ETH-USD)...")
    df = stream.get(
        "ETH-USD",
        start="2024-11-01",
        end="2024-11-07",
        asset_type="crypto"
    )

    print(f"  ✓ Got {len(df)} rows")
    if len(df) > 0:
        print("\n  Latest ETH prices:")
        print(df.tail(5))

    # Test symbol normalization
    print("\n✓ Testing symbol normalization (BTCUSD → BTC-USD)...")
    df = stream.get(
        "BTCUSD",  # Without dash
        start="2024-11-06",
        end="2024-11-07",
        asset_type="crypto",
        provider="coinbase"
    )

    print(f"  ✓ Got {len(df)} rows (symbol auto-normalized)")

    print("\n" + "=" * 60)
    print("DataStream Coinbase Test Complete!")
    print("=" * 60)


async def test_coinbase_streaming():
    """Test Coinbase real-time streaming."""
    print("\n" + "=" * 60)
    print("Testing Coinbase Real-Time Streaming")
    print("=" * 60)

    stream = DataStream()

    # Test 1: Stream BTC ticker
    print("\n✓ Streaming BTC-USD ticker (10 ticks)...")
    count = 0
    async for tick in stream.stream("BTC-USD", stream_type="ticker", provider="coinbase_stream"):
        print(f"  BTC: ${tick.price:.2f} | Bid: ${tick.bid:.2f} | Ask: ${tick.ask:.2f}")
        count += 1
        if count >= 10:
            break

    # Test 2: Stream ETH ticker
    print("\n✓ Streaming ETH-USD ticker (5 ticks)...")
    count = 0
    async for tick in stream.stream("ETH-USD", stream_type="ticker", provider="coinbase_stream"):
        print(f"  ETH: ${tick.price:.2f}")
        count += 1
        if count >= 5:
            break

    await stream.disconnect_streams()

    print("\n" + "=" * 60)
    print("Coinbase Streaming Test Complete!")
    print("=" * 60)


def show_popular_pairs():
    """Show popular Coinbase trading pairs."""
    print("\n" + "=" * 60)
    print("Popular Coinbase Trading Pairs")
    print("=" * 60)

    print("\nTop 20 pairs:")
    for i, pair in enumerate(POPULAR_PAIRS, 1):
        print(f"  {i:2d}. {pair}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Show popular pairs
    show_popular_pairs()

    # Test Coinbase provider
    test_coinbase_provider()

    # Test via DataStream
    test_datastream_with_coinbase()

    # Test real-time streaming
    print("\n✓ Testing real-time streaming...")
    asyncio.run(test_coinbase_streaming())

    print("\n✅ All Coinbase tests completed!")
    print("\nNote: Coinbase provides FREE public market data - no API key required!")
