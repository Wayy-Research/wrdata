"""
Live test of FRED (Federal Reserve Economic Data) provider.

Get your free API key at: https://fred.stlouisfed.org/docs/api/api_key.html
Then set it as an environment variable: export FRED_API_KEY="your_key_here"
"""

import os
from wrdata import DataStream
from wrdata.providers.fred_provider import FREDProvider, POPULAR_SERIES


def test_fred_provider():
    """Test FRED provider directly."""
    print("=" * 60)
    print("Testing FRED Provider")
    print("=" * 60)

    # Get API key from environment
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("\n❌ FRED_API_KEY not set!")
        print("Get a free API key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        print("Then set it: export FRED_API_KEY='your_key_here'")
        return

    # Create provider
    print(f"\n✓ FRED API key found")
    provider = FREDProvider(api_key=api_key)

    # Test connection
    print("✓ Testing connection...")
    if provider.validate_connection():
        print("  ✓ Connection successful!")
    else:
        print("  ❌ Connection failed!")
        return

    # Test series search
    print("\n✓ Testing series search...")
    results = provider.search_series("unemployment", limit=5)
    if results:
        print(f"  Found {len(results)} series:")
        for series in results[:3]:
            print(f"    {series['id']}: {series['title']}")
    else:
        print("  ❌ Search failed!")

    # Test data fetch - Unemployment Rate
    print("\n✓ Fetching Unemployment Rate (UNRATE)...")
    response = provider.fetch_timeseries(
        symbol="UNRATE",
        start_date="2020-01-01",
        end_date="2024-01-01"
    )

    if response.success:
        print(f"  ✓ Got {len(response.data)} data points")
        print(f"  First point: {response.data[0]}")
        print(f"  Last point: {response.data[-1]}")
    else:
        print(f"  ❌ Failed: {response.error}")

    print("\n" + "=" * 60)
    print("FRED Provider Test Complete!")
    print("=" * 60)


def test_datastream_with_fred():
    """Test FRED via DataStream API."""
    print("\n" + "=" * 60)
    print("Testing FRED via DataStream")
    print("=" * 60)

    # Get API key
    api_key = os.getenv('FRED_API_KEY')
    if not api_key:
        print("\n❌ Skipping DataStream test - no API key")
        return

    # Create DataStream with FRED
    stream = DataStream(fred_key=api_key)

    # Check provider status
    status = stream.status()
    print(f"\n✓ Available providers: {list(stream.providers.keys())}")
    if 'fred' in status:
        print(f"  FRED connected: {status['fred'].get('connected', False)}")

    # Fetch GDP data
    print("\n✓ Fetching GDP data...")
    df = stream.get(
        "GDP",
        start="2020-01-01",
        end="2024-01-01",
        asset_type="economic"
    )

    print(f"  ✓ Got {len(df)} rows of GDP data")
    print("\n  Latest GDP values:")
    print(df.tail(5))

    # Fetch Unemployment Rate
    print("\n✓ Fetching Unemployment Rate...")
    df = stream.get(
        "UNRATE",
        start="2023-01-01",
        end="2024-01-01",
        asset_type="economic"
    )

    print(f"  ✓ Got {len(df)} rows")
    print("\n  Recent unemployment rates:")
    print(df.tail(5))

    # Fetch 10-Year Treasury Rate
    print("\n✓ Fetching 10-Year Treasury Rate...")
    df = stream.get(
        "DGS10",
        start="2023-01-01",
        end="2024-01-01",
        asset_type="economic"
    )

    print(f"  ✓ Got {len(df)} rows")
    print("\n  Recent 10Y rates:")
    print(df.tail(5))

    print("\n" + "=" * 60)
    print("DataStream FRED Test Complete!")
    print("=" * 60)


def show_popular_series():
    """Show popular FRED series IDs."""
    print("\n" + "=" * 60)
    print("Popular FRED Series")
    print("=" * 60)

    categories = {
        'GDP & Growth': ['GDP', 'GDPC1', 'A191RL1Q225SBEA'],
        'Unemployment': ['UNRATE', 'PAYEMS', 'U6RATE'],
        'Inflation': ['CPIAUCSL', 'PCEPI'],
        'Interest Rates': ['DGS10', 'DGS2', 'DFF', 'MORTGAGE30US'],
        'Housing': ['CSUSHPISA', 'HOUST'],
        'Commodities': ['DCOILWTICO', 'GOLDAMGBD228NLBM'],
    }

    for category, series_list in categories.items():
        print(f"\n{category}:")
        for series_id in series_list:
            desc = POPULAR_SERIES.get(series_id, series_id)
            print(f"  {series_id:20s} - {desc}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Show popular series
    show_popular_series()

    # Test FRED provider
    test_fred_provider()

    # Test via DataStream
    test_datastream_with_fred()

    print("\n✅ All FRED tests completed!")
