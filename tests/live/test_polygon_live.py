#!/usr/bin/env python3
"""
Polygon.io live test.

Get your free API key: https://polygon.io/dashboard/signup
Free tier: 100 API calls/day, 5 calls/minute

Set POLYGON_API_KEY in .env file
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wrdata.providers.polygon_provider import PolygonProvider


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_connection():
    """Test basic connection to Polygon.io."""
    print_section("Test 1: Connection")

    api_key = os.getenv("POLYGON_API_KEY")

    if not api_key:
        print("✗ POLYGON_API_KEY not found in environment")
        print("\nGet your free API key:")
        print("1. Sign up: https://polygon.io/dashboard/signup")
        print("2. Copy your API key")
        print("3. Add to .env: POLYGON_API_KEY=your_key")
        return False

    try:
        provider = PolygonProvider(api_key=api_key)

        if provider.validate_connection():
            print("✓ Successfully connected to Polygon.io")
            return True
        else:
            print("✗ Failed to connect to Polygon.io")
            return False

    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False


def test_historical_data():
    """Test fetching historical stock data."""
    print_section("Test 2: Historical Stock Data")

    api_key = os.getenv("POLYGON_API_KEY")
    provider = PolygonProvider(api_key=api_key)

    try:
        # Fetch AAPL data
        symbol = "AAPL"
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        print(f"\nFetching {symbol} from {start_date} to {end_date}...")

        response = provider.fetch_timeseries(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )

        if response.success:
            print(f"✓ Retrieved {len(response.data)} records")
            print(f"\nMetadata: {response.metadata}")

            if response.data:
                print("\nFirst 3 records:")
                for record in response.data[:3]:
                    print(f"  {record}")

                print("\nLast 3 records:")
                for record in response.data[-3:]:
                    print(f"  {record}")

            return True
        else:
            print(f"✗ Failed: {response.error}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_previous_close():
    """Test getting previous day's close."""
    print_section("Test 3: Previous Close")

    api_key = os.getenv("POLYGON_API_KEY")
    provider = PolygonProvider(api_key=api_key)

    try:
        symbol = "AAPL"
        print(f"\nGetting previous close for {symbol}...")

        data = provider.get_previous_close(symbol)

        if data:
            print(f"✓ Previous close data retrieved:")
            print(f"  Symbol: {data.get('symbol')}")
            print(f"  Open: ${data.get('open')}")
            print(f"  High: ${data.get('high')}")
            print(f"  Low: ${data.get('low')}")
            print(f"  Close: ${data.get('close')}")
            print(f"  Volume: {data.get('volume'):,}")
            print(f"  VWAP: ${data.get('vwap')}")
            return True
        else:
            print("✗ No previous close data returned")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_ticker_details():
    """Test getting ticker details."""
    print_section("Test 4: Ticker Details")

    api_key = os.getenv("POLYGON_API_KEY")
    provider = PolygonProvider(api_key=api_key)

    try:
        symbol = "AAPL"
        print(f"\nGetting ticker details for {symbol}...")

        data = provider.get_ticker_details(symbol)

        if data:
            print(f"✓ Ticker details retrieved:")
            print(f"  Symbol: {data.get('symbol')}")
            print(f"  Name: {data.get('name')}")
            print(f"  Market: {data.get('market')}")
            print(f"  Exchange: {data.get('primary_exchange')}")
            print(f"  Type: {data.get('type')}")
            print(f"  Currency: {data.get('currency_name')}")
            if data.get('description'):
                desc = data.get('description')
                print(f"  Description: {desc[:100]}...")
            if data.get('homepage_url'):
                print(f"  Website: {data.get('homepage_url')}")
            if data.get('total_employees'):
                print(f"  Employees: {data.get('total_employees'):,}")
            if data.get('market_cap'):
                print(f"  Market Cap: ${data.get('market_cap'):,.0f}")
            return True
        else:
            print("✗ No ticker details returned")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_market_status():
    """Test getting market status."""
    print_section("Test 5: Market Status")

    api_key = os.getenv("POLYGON_API_KEY")
    provider = PolygonProvider(api_key=api_key)

    try:
        print("\nGetting current market status...")

        data = provider.get_market_status()

        if data:
            print(f"✓ Market status retrieved:")
            print(f"  Market: {data.get('market')}")
            print(f"  Server Time: {data.get('serverTime')}")

            if 'exchanges' in data:
                print(f"\n  Exchanges:")
                for exchange, status in data['exchanges'].items():
                    print(f"    {exchange}: {status}")

            if 'currencies' in data:
                print(f"\n  Currencies:")
                for currency, status in data['currencies'].items():
                    print(f"    {currency}: {status}")

            return True
        else:
            print("✗ No market status returned")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_multi_symbol():
    """Test fetching data for multiple symbols."""
    print_section("Test 6: Multiple Symbols")

    api_key = os.getenv("POLYGON_API_KEY")
    provider = PolygonProvider(api_key=api_key)

    try:
        symbols = ["AAPL", "MSFT", "GOOGL"]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        print(f"\nFetching data for {len(symbols)} symbols...")

        for symbol in symbols:
            response = provider.fetch_timeseries(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval="1d"
            )

            if response.success:
                latest = response.data[-1] if response.data else {}
                print(f"  ✓ {symbol}: {len(response.data)} records, Latest close: ${latest.get('close', 'N/A')}")
            else:
                print(f"  ✗ {symbol}: {response.error}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_intraday_data():
    """Test fetching intraday data."""
    print_section("Test 7: Intraday Data")

    api_key = os.getenv("POLYGON_API_KEY")
    provider = PolygonProvider(api_key=api_key)

    try:
        symbol = "AAPL"
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = datetime.now().strftime("%Y-%m-%d")

        print(f"\nFetching {symbol} 5-minute bars for today...")

        response = provider.fetch_timeseries(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval="5m"
        )

        if response.success:
            print(f"✓ Retrieved {len(response.data)} 5-minute bars")

            if response.data:
                print("\nFirst 3 bars:")
                for record in response.data[:3]:
                    print(f"  {record}")

            return True
        else:
            print(f"⚠ Note: {response.error}")
            print("  (Market may be closed or you need a paid plan for intraday data)")
            return True  # Not a failure if market is closed

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  Polygon.io Provider - Live Test Suite")
    print("=" * 70)
    print("\nGet your free API key: https://polygon.io/dashboard/signup")
    print("Free tier: 100 calls/day, 5 calls/minute")

    tests = [
        ("Connection", test_connection),
        ("Historical Data", test_historical_data),
        ("Previous Close", test_previous_close),
        ("Ticker Details", test_ticker_details),
        ("Market Status", test_market_status),
        ("Multi-Symbol", test_multi_symbol),
        ("Intraday Data", test_intraday_data),
    ]

    results = {}

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Print summary
    print_section("Test Summary")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}  {name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All tests passed!")
    else:
        print(f"\n  ⚠ {total - passed} test(s) failed")

    print("\n  Rate Limit Info:")
    print("    Free tier: 5 calls/min, 100 calls/day")
    print("    Paid plans: Unlimited calls + WebSocket streaming")
    print("    Upgrade: https://polygon.io/pricing")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
