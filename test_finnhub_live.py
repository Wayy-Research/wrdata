"""
Live test of Finnhub provider.

Get your free API key: https://finnhub.io/register
Free tier: 60 calls/minute + FREE WebSocket streaming!

Set it as: export FINNHUB_API_KEY="your_key_here"
"""

import os
import asyncio
from wrdata import DataStream
from wrdata.providers.finnhub_provider import FinnhubProvider, FINNHUB_ENDPOINTS


def test_finnhub_provider():
    """Test Finnhub provider directly."""
    print("=" * 60)
    print("Testing Finnhub Provider")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key:
        print("\n❌ FINNHUB_API_KEY not set!")
        print("Get a free API key at: https://finnhub.io/register")
        print("Then set it: export FINNHUB_API_KEY='your_key_here'")
        return

    # Create provider
    print(f"\n✓ Finnhub API key found")
    provider = FinnhubProvider(api_key=api_key)

    # Test connection
    print("✓ Testing connection...")
    if provider.validate_connection():
        print("  ✓ Connection successful!")
    else:
        print("  ❌ Connection failed!")
        return

    # Test real-time quote
    print("\n✓ Fetching real-time quote for AAPL...")
    quote = provider.get_quote("AAPL")
    if quote:
        print(f"  ✓ AAPL: ${quote.get('c', 'N/A')}")  # current price
        print(f"    Open: ${quote.get('o', 'N/A')}")
        print(f"    High: ${quote.get('h', 'N/A')}")
        print(f"    Low: ${quote.get('l', 'N/A')}")
        print(f"    Previous Close: ${quote.get('pc', 'N/A')}")
    else:
        print("  ❌ Failed to get quote")

    # Test historical data
    print("\n✓ Fetching historical data for AAPL...")
    response = provider.fetch_timeseries(
        symbol="AAPL",
        start_date="2024-10-01",
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

    # Test company profile
    print("\n✓ Fetching company profile for AAPL...")
    profile = provider.get_company_profile("AAPL")
    if profile:
        print(f"  Company: {profile.get('name', 'N/A')}")
        print(f"  Industry: {profile.get('finnhubIndustry', 'N/A')}")
        print(f"  Country: {profile.get('country', 'N/A')}")
        print(f"  Market Cap: ${profile.get('marketCapitalization', 'N/A')}B")
        print(f"  IPO: {profile.get('ipo', 'N/A')}")
    else:
        print("  ⚠️ Could not get company profile")

    # Test symbol search
    print("\n✓ Testing symbol search for 'Apple'...")
    results = provider.search_symbols("Apple")
    if results:
        print(f"  ✓ Found {len(results)} results")
        for i, result in enumerate(results[:3]):
            print(f"    {i+1}. {result.get('description', 'N/A')} ({result.get('symbol', 'N/A')})")
    else:
        print("  ⚠️ No results found")

    # Test company news
    print("\n✓ Fetching recent news for AAPL...")
    news = provider.get_company_news("AAPL", "2024-11-01", "2024-11-07")
    if news:
        print(f"  ✓ Found {len(news)} news articles")
        if news:
            print(f"  Latest: {news[0].get('headline', 'N/A')}")
    else:
        print("  ⚠️ No news found")

    print("\n" + "=" * 60)
    print("Finnhub Provider Test Complete!")
    print("=" * 60)


def test_datastream_with_finnhub():
    """Test Finnhub via DataStream API."""
    print("\n" + "=" * 60)
    print("Testing Finnhub via DataStream")
    print("=" * 60)

    # Get API key
    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key:
        print("\n❌ Skipping DataStream test - no API key")
        return

    # Create DataStream with Finnhub
    stream = DataStream(finnhub_key=api_key)

    # Check provider status
    status = stream.status()
    print(f"\n✓ Available providers: {list(stream.providers.keys())}")
    if 'finnhub' in status:
        print(f"  Finnhub connected: {status['finnhub'].get('connected', False)}")

    # Fetch Apple stock data
    print("\n✓ Fetching Apple (AAPL) stock data...")
    df = stream.get(
        "AAPL",
        start="2024-10-01",
        end="2024-11-07",
        asset_type="stock"
    )

    print(f"  ✓ Got {len(df)} rows of AAPL data")
    if len(df) > 0:
        print("\n  Latest AAPL prices:")
        print(df.tail(5))

    # Fetch Microsoft data
    print("\n✓ Fetching Microsoft (MSFT)...")
    df = stream.get(
        "MSFT",
        start="2024-11-01",
        end="2024-11-07",
        asset_type="stock"
    )

    print(f"  ✓ Got {len(df)} rows")
    if len(df) > 0:
        print("\n  Recent MSFT prices:")
        print(df.tail(5))

    # Test provider priority (Finnhub should be first for stocks)
    print("\n✓ Testing provider auto-selection...")
    print("  For stocks, priority is: finnhub → alphavantage → yfinance")

    print("\n" + "=" * 60)
    print("DataStream Finnhub Test Complete!")
    print("=" * 60)


async def test_finnhub_streaming():
    """Test Finnhub WebSocket streaming."""
    print("\n" + "=" * 60)
    print("Testing Finnhub WebSocket Streaming")
    print("=" * 60)

    # Get API key
    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key:
        print("\n❌ Skipping streaming test - no API key")
        return

    print("\n✓ Starting Finnhub WebSocket stream...")
    print("  Streaming live trades for AAPL and MSFT")
    print("  Press Ctrl+C to stop\n")

    from wrdata.streaming.finnhub_stream import FinnhubStreamProvider

    stream = FinnhubStreamProvider(api_key=api_key)

    try:
        await stream.connect()

        # Stream multiple symbols
        count = 0
        max_messages = 20  # Just show first 20 messages

        async for msg in stream.subscribe_multiple(['AAPL', 'MSFT']):
            print(f"  {msg.symbol}: ${msg.price:.2f} @ {msg.timestamp.strftime('%H:%M:%S')} (vol: {msg.volume:.0f})")

            count += 1
            if count >= max_messages:
                print(f"\n  ✓ Received {count} real-time trade messages!")
                break

    except KeyboardInterrupt:
        print("\n  Stream stopped by user")
    finally:
        await stream.disconnect()

    print("\n" + "=" * 60)
    print("Finnhub Streaming Test Complete!")
    print("=" * 60)


def show_finnhub_endpoints():
    """Show available Finnhub endpoints."""
    print("\n" + "=" * 60)
    print("Finnhub Available Endpoints")
    print("=" * 60)

    for endpoint, description in FINNHUB_ENDPOINTS.items():
        print(f"  {endpoint:15s} - {description}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Show endpoints
    show_finnhub_endpoints()

    # Test Finnhub provider
    test_finnhub_provider()

    # Test via DataStream
    test_datastream_with_finnhub()

    # Test WebSocket streaming
    print("\n✅ REST API tests completed!")
    print("\nReady to test WebSocket streaming? (y/n): ", end='')
    try:
        response = input()
        if response.lower() == 'y':
            asyncio.run(test_finnhub_streaming())
    except:
        print("\nSkipping streaming test")

    print("\n✅ All Finnhub tests completed!")
    print("\nNote: Finnhub free tier includes:")
    print("  - 60 API calls per minute")
    print("  - FREE WebSocket streaming (real-time trades!)")
    print("  - Global coverage: 60+ exchanges")
    print("  - Company data, news, fundamentals")
