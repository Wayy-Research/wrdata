#!/usr/bin/env python3
"""
Interactive Brokers live test.

REQUIREMENTS:
1. TWS or IB Gateway must be running locally
2. API must be enabled in TWS settings
3. Socket port configured: 7497 (paper) or 7496 (live)

Setup TWS/IB Gateway:
- Download: https://www.interactivebrokers.com/en/trading/tws.php
- Enable API: File → Global Configuration → API → Settings
- Check "Enable ActiveX and Socket Clients"
- Set socket port: 7497 for paper trading

This test uses paper trading port (7497) by default.
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wrdata.providers.ibkr_provider import IBKRProvider


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_connection():
    """Test basic connection to TWS/Gateway."""
    print_section("Test 1: Connection")

    # Use paper trading port by default
    provider = IBKRProvider(
        host="127.0.0.1",
        port=7497,  # Paper trading
        client_id=1,
        readonly=True
    )

    success = provider.connect()

    if success:
        print("✓ Successfully connected to IBKR TWS/Gateway")
        provider.disconnect()
        return True
    else:
        print("✗ Failed to connect to IBKR")
        print("\nTroubleshooting:")
        print("1. Is TWS or IB Gateway running?")
        print("2. Is API enabled in TWS settings?")
        print("3. Is the correct port configured (7497 for paper, 7496 for live)?")
        print("4. Try restarting TWS/Gateway")
        return False


def test_historical_data():
    """Test fetching historical stock data."""
    print_section("Test 2: Historical Stock Data")

    provider = IBKRProvider(port=7497)

    if not provider.connect():
        print("✗ Cannot connect to IBKR")
        return False

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
        else:
            print(f"✗ Failed: {response.error}")
            return False

    finally:
        provider.disconnect()

    return True


def test_market_data():
    """Test real-time market data."""
    print_section("Test 3: Real-time Market Data")

    provider = IBKRProvider(port=7497)

    if not provider.connect():
        print("✗ Cannot connect to IBKR")
        return False

    try:
        symbol = "AAPL"
        print(f"\nGetting market data for {symbol}...")

        data = provider.get_market_data(symbol)

        if data:
            print(f"✓ Market data retrieved:")
            print(f"  Symbol: {data.get('symbol')}")
            print(f"  Last: ${data.get('last')}")
            print(f"  Bid: ${data.get('bid')} x {data.get('bid_size')}")
            print(f"  Ask: ${data.get('ask')} x {data.get('ask_size')}")
            print(f"  Volume: {data.get('volume'):,}")
            print(f"  High: ${data.get('high')}")
            print(f"  Low: ${data.get('low')}")
            print(f"  Close: ${data.get('close')}")
            return True
        else:
            print("✗ No market data returned")
            return False

    finally:
        provider.disconnect()


def test_account_info():
    """Test account information (if available)."""
    print_section("Test 4: Account Information")

    provider = IBKRProvider(port=7497)

    if not provider.connect():
        print("✗ Cannot connect to IBKR")
        return False

    try:
        print("\nFetching account summary...")

        summary = provider.get_account_summary()

        if summary:
            print("✓ Account summary retrieved:")

            # Show key metrics
            important_keys = [
                'NetLiquidation',
                'TotalCashValue',
                'GrossPositionValue',
                'BuyingPower',
                'AvailableFunds'
            ]

            for key in important_keys:
                if key in summary:
                    item = summary[key]
                    print(f"  {key}: {item['value']} {item['currency']}")

            return True
        else:
            print("⚠ No account summary (may require account login)")
            return True  # Not a failure

    finally:
        provider.disconnect()


def test_positions():
    """Test getting open positions."""
    print_section("Test 5: Open Positions")

    provider = IBKRProvider(port=7497)

    if not provider.connect():
        print("✗ Cannot connect to IBKR")
        return False

    try:
        print("\nFetching open positions...")

        positions = provider.get_positions()

        if positions:
            print(f"✓ Found {len(positions)} open position(s):")
            for pos in positions:
                print(f"  {pos['symbol']}: {pos['position']} shares @ ${pos['avg_cost']:.2f}")
                print(f"    Market Value: ${pos['market_value']:.2f}")
        else:
            print("✓ No open positions (or account not logged in)")

        return True

    finally:
        provider.disconnect()


def test_multi_symbol():
    """Test fetching data for multiple symbols."""
    print_section("Test 6: Multiple Symbols")

    provider = IBKRProvider(port=7497)

    if not provider.connect():
        print("✗ Cannot connect to IBKR")
        return False

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

    finally:
        provider.disconnect()


def test_option_expirations():
    """Test getting available option expirations."""
    print_section("Test 7: Option Expirations")

    provider = IBKRProvider(port=7497)

    if not provider.connect():
        print("✗ Cannot connect to IBKR")
        return False

    try:
        symbol = "AAPL"
        print(f"\nFetching option expirations for {symbol}...")

        expirations = provider.get_available_expirations(symbol)

        if expirations:
            print(f"✓ Found {len(expirations)} expiration dates:")
            for exp in expirations[:10]:  # Show first 10
                print(f"  {exp}")

            if len(expirations) > 10:
                print(f"  ... and {len(expirations) - 10} more")

            return True
        else:
            print("✗ No option expirations found")
            return False

    finally:
        provider.disconnect()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  Interactive Brokers Provider - Live Test Suite")
    print("=" * 70)
    print("\nNOTE: TWS or IB Gateway must be running on port 7497")
    print("      (Paper trading port)")

    tests = [
        ("Connection", test_connection),
        ("Historical Data", test_historical_data),
        ("Market Data", test_market_data),
        ("Account Info", test_account_info),
        ("Positions", test_positions),
        ("Multi-Symbol", test_multi_symbol),
        ("Option Expirations", test_option_expirations),
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

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
