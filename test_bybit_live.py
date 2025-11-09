"""
Live test for Bybit provider.

FREE API - No key required for market data!

API Docs: https://bybit-exchange.github.io/docs/
"""

import os
from datetime import datetime, timedelta
from wrdata.providers.bybit_provider import BybitProvider


def test_connection():
    """Test if we can connect to Bybit API."""
    provider = BybitProvider()  # No API key needed!

    if provider.validate_connection():
        print("✅ Bybit connection successful!")
        print("   Using FREE public API (no key required)")
        return True
    else:
        print("❌ Bybit connection failed")
        return False


def test_crypto_data():
    """Test fetching crypto data."""
    provider = BybitProvider()

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        print(f"\n📊 Testing Bybit data for {symbol}...")
        response = provider.fetch_timeseries(
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1d"
        )

        if response.success:
            print(f"✅ Got {len(response.data)} records")
            print(f"Latest: O=${response.data[-1]['open']:.2f} C=${response.data[-1]['close']:.2f}")
        else:
            print(f"❌ Error: {response.error}")


if __name__ == "__main__":
    print("=" * 60)
    print("BYBIT LIVE TEST")
    print("=" * 60)

    if test_connection():
        test_crypto_data()

    print("\n" + "=" * 60)
    print("FREE features (NO API KEY!):")
    print("- Spot & derivatives data")
    print("- Historical klines")
    print("- Real-time tickers")
    print("- Order book data")
    print("- Unlimited public endpoints")
    print("=" * 60)
