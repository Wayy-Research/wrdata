"""
Live test of Alpha Vantage provider.

Get your free API key at: https://www.alphavantage.co/support/#api-key
Then set it as an environment variable: export ALPHAVANTAGE_API_KEY="your_key_here"

Free tier limits: 5 calls/min, 500 calls/day
"""

import os
from wrdata import DataStream
from wrdata.providers.alphavantage_provider import AlphaVantageProvider


def test_alphavantage_provider():
    """Test Alpha Vantage provider directly."""
    print("=" * 60)
    print("Testing Alpha Vantage Provider")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv('ALPHAVANTAGE_API_KEY')
    if not api_key:
        print("\n❌ ALPHAVANTAGE_API_KEY not set!")
        print("Get a free API key at: https://www.alphavantage.co/support/#api-key")
        print("Then set it: export ALPHAVANTAGE_API_KEY='your_key_here'")
        return

    # Create provider
    print(f"\n✓ Alpha Vantage API key found")
    provider = AlphaVantageProvider(api_key=api_key)

    # Test connection
    print("✓ Testing connection...")
    if provider.validate_connection():
        print("  ✓ Connection successful!")
    else:
        print("  ❌ Connection failed!")
        return

    # Test stock data fetch - AAPL
    print("\n✓ Fetching Apple (AAPL) stock data...")
    print("  (Rate limited: 12 seconds between calls)")
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

    # Test forex data - EUR/USD
    print("\n✓ Fetching EUR/USD forex data...")
    print("  (Rate limited: 12 seconds between calls)")
    response = provider.fetch_timeseries(
        symbol="EUR/USD",
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

    print("\n" + "=" * 60)
    print("Alpha Vantage Provider Test Complete!")
    print("=" * 60)


def test_datastream_with_alphavantage():
    """Test Alpha Vantage via DataStream API."""
    print("\n" + "=" * 60)
    print("Testing Alpha Vantage via DataStream")
    print("=" * 60)

    # Get API key
    api_key = os.getenv('ALPHAVANTAGE_API_KEY')
    if not api_key:
        print("\n❌ Skipping DataStream test - no API key")
        return

    # Create DataStream with Alpha Vantage
    stream = DataStream(alphavantage_key=api_key)

    # Check provider status
    status = stream.status()
    print(f"\n✓ Available providers: {list(stream.providers.keys())}")
    if 'alphavantage' in status:
        print(f"  Alpha Vantage connected: {status['alphavantage'].get('connected', False)}")

    # Fetch Microsoft stock data
    print("\n✓ Fetching Microsoft (MSFT) stock data...")
    df = stream.get(
        "MSFT",
        start="2024-10-01",
        end="2024-11-07",
        asset_type="stock"
    )

    print(f"  ✓ Got {len(df)} rows of MSFT data")
    if len(df) > 0:
        print("\n  Latest MSFT prices:")
        print(df.tail(5))

    # Fetch forex data
    print("\n✓ Fetching GBP/USD forex data...")
    print("  (Rate limited: 12 seconds between calls)")
    df = stream.get(
        "GBP/USD",
        start="2024-11-01",
        end="2024-11-07",
        asset_type="forex"
    )

    print(f"  ✓ Got {len(df)} rows")
    if len(df) > 0:
        print("\n  Recent GBP/USD rates:")
        print(df.tail(5))

    print("\n" + "=" * 60)
    print("DataStream Alpha Vantage Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Test Alpha Vantage provider
    test_alphavantage_provider()

    # Test via DataStream
    test_datastream_with_alphavantage()

    print("\n✅ All Alpha Vantage tests completed!")
    print("\nNote: Alpha Vantage free tier is rate-limited to 5 calls/minute.")
    print("Tests include automatic 12-second delays between calls.")
