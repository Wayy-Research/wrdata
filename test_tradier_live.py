#!/usr/bin/env python3
"""
Tradier live test.

Get your FREE API key: https://developer.tradier.com/getting_started
NO CREDIT CARD REQUIRED!

Sandbox (paper trading): FREE, unlimited
Production: FREE with brokerage account

Set TRADIER_API_KEY in .env file
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wrdata.providers.tradier_provider import TradierProvider


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_connection():
    """Test basic connection to Tradier."""
    print_section("Test 1: Connection")

    api_key = os.getenv("TRADIER_API_KEY")

    if not api_key:
        print("✗ TRADIER_API_KEY not found in environment")
        print("\nGet your FREE API key (no credit card!):")
        print("1. Sign up: https://developer.tradier.com/getting_started")
        print("2. Click 'Create Application'")
        print("3. Copy your Sandbox API Key")
        print("4. Add to .env: TRADIER_API_KEY=your_key")
        print("\n💡 Tip: Use sandbox for testing (it's free and unlimited!)")
        return False

    try:
        provider = TradierProvider(api_key=api_key, sandbox=True)

        if provider.validate_connection():
            print("✓ Successfully connected to Tradier (Sandbox)")
            return True
        else:
            print("✗ Failed to connect to Tradier")
            return False

    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False


def test_market_clock():
    """Test market clock/status."""
    print_section("Test 2: Market Clock")

    api_key = os.getenv("TRADIER_API_KEY")
    provider = TradierProvider(api_key=api_key, sandbox=True)

    try:
        print("\nGetting market status...")

        clock = provider.get_market_clock()

        if clock:
            print(f"✓ Market clock retrieved:")
            print(f"  Date: {clock.get('date')}")
            print(f"  State: {clock.get('state')}")
            print(f"  Description: {clock.get('description')}")
            print(f"  Next Change: {clock.get('next_change')}")
            print(f"  Next State: {clock.get('next_state')}")
            return True
        else:
            print("✗ No clock data returned")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_real_time_quote():
    """Test real-time quote."""
    print_section("Test 3: Real-time Quote")

    api_key = os.getenv("TRADIER_API_KEY")
    provider = TradierProvider(api_key=api_key, sandbox=True)

    try:
        symbol = "AAPL"
        print(f"\nGetting real-time quote for {symbol}...")

        quote = provider.get_quote(symbol)

        if quote:
            print(f"✓ Quote retrieved:")
            print(f"  Symbol: {quote.get('symbol')}")
            print(f"  Description: {quote.get('description')}")
            print(f"  Last: ${quote.get('last')}")
            print(f"  Bid: ${quote.get('bid')} x {quote.get('bid_size')}")
            print(f"  Ask: ${quote.get('ask')} x {quote.get('ask_size')}")
            print(f"  Change: ${quote.get('change')} ({quote.get('change_percentage')}%)")
            print(f"  Volume: {quote.get('volume'):,}")
            print(f"  Prev Close: ${quote.get('prev_close')}")
            return True
        else:
            print("✗ No quote data returned")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_historical_data():
    """Test historical data."""
    print_section("Test 4: Historical Data")

    api_key = os.getenv("TRADIER_API_KEY")
    provider = TradierProvider(api_key=api_key, sandbox=True)

    try:
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
        return False


def test_options_expirations():
    """Test getting options expirations (FREE!)."""
    print_section("Test 5: Options Expirations (FREE!)")

    api_key = os.getenv("TRADIER_API_KEY")
    provider = TradierProvider(api_key=api_key, sandbox=True)

    try:
        symbol = "AAPL"
        print(f"\nGetting options expirations for {symbol}...")

        expirations = provider.get_available_expirations(symbol)

        if expirations:
            print(f"✓ Found {len(expirations)} expiration dates:")
            for exp in expirations[:10]:
                print(f"  {exp}")

            if len(expirations) > 10:
                print(f"  ... and {len(expirations) - 10} more")

            return True
        else:
            print("✗ No expirations found")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_options_strikes():
    """Test getting strike prices."""
    print_section("Test 6: Options Strike Prices")

    api_key = os.getenv("TRADIER_API_KEY")
    provider = TradierProvider(api_key=api_key, sandbox=True)

    try:
        symbol = "AAPL"

        # Get first available expiration
        expirations = provider.get_available_expirations(symbol)

        if not expirations:
            print("⚠ No expirations available, skipping strike test")
            return True

        expiry = expirations[0].strftime('%Y-%m-%d')
        print(f"\nGetting strike prices for {symbol} expiring {expiry}...")

        strikes = provider.get_option_strikes(symbol, expiry)

        if strikes:
            print(f"✓ Found {len(strikes)} strike prices:")
            print(f"  Range: ${min(strikes)} - ${max(strikes)}")
            print(f"  Sample strikes: {strikes[:10]}")
            return True
        else:
            print("✗ No strikes found")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_options_chain():
    """Test fetching full options chain (FREE!)."""
    print_section("Test 7: Options Chain (FREE!)")

    api_key = os.getenv("TRADIER_API_KEY")
    provider = TradierProvider(api_key=api_key, sandbox=True)

    try:
        symbol = "AAPL"

        # Get first available expiration
        expirations = provider.get_available_expirations(symbol)

        if not expirations:
            print("⚠ No expirations available, skipping chain test")
            return True

        from wrdata.models.schemas import OptionsChainRequest

        request = OptionsChainRequest(
            symbol=symbol,
            expiry=expirations[0]
        )

        print(f"\nFetching options chain for {symbol} expiring {expirations[0]}...")

        response = provider.fetch_options_chain(request)

        if response.success:
            print(f"✓ Options chain retrieved!")
            print(f"\nMetadata: {response.metadata}")
            print(f"\n💡 This is FREE data! Most providers charge for this.")
            return True
        else:
            print(f"✗ Failed: {response.error}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_market_calendar():
    """Test market calendar."""
    print_section("Test 8: Market Calendar")

    api_key = os.getenv("TRADIER_API_KEY")
    provider = TradierProvider(api_key=api_key, sandbox=True)

    try:
        print("\nGetting market calendar...")

        calendar = provider.get_market_calendar()

        if calendar and 'calendar' in calendar:
            cal_data = calendar['calendar']

            if 'days' in cal_data and 'day' in cal_data['days']:
                days = cal_data['days']['day']
                print(f"✓ Market calendar retrieved:")
                print(f"  Total days: {len(days) if isinstance(days, list) else 1}")

                # Show first few days
                sample_days = days[:5] if isinstance(days, list) else [days]
                for day in sample_days:
                    print(f"  {day.get('date')}: {day.get('status')}")

                return True
            else:
                print("✓ Calendar data retrieved (structure varies)")
                return True
        else:
            print("⚠ Calendar data not available")
            return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  Tradier Provider - Live Test Suite")
    print("=" * 70)
    print("\nGet your FREE API key: https://developer.tradier.com/getting_started")
    print("NO CREDIT CARD REQUIRED!")
    print("\n🎁 FREE Features:")
    print("  ✅ Real-time quotes")
    print("  ✅ Options chains (full data!)")
    print("  ✅ Historical data")
    print("  ✅ Market calendar")
    print("  ✅ 120 requests/minute")

    tests = [
        ("Connection", test_connection),
        ("Market Clock", test_market_clock),
        ("Real-time Quote", test_real_time_quote),
        ("Historical Data", test_historical_data),
        ("Options Expirations", test_options_expirations),
        ("Options Strikes", test_options_strikes),
        ("Options Chain", test_options_chain),
        ("Market Calendar", test_market_calendar),
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

    print("\n  💡 Tradier Tips:")
    print("    - Sandbox is FREE and unlimited")
    print("    - Options data is FREE (rare!)")
    print("    - Production requires account (no minimum)")
    print("    - Rate limit: 120 requests/minute")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
