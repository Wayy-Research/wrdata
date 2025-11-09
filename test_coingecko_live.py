"""
Live test for CoinGecko provider.

NO API KEY REQUIRED for demo tier!
Optional API key for higher limits.

API Docs: https://www.coingecko.com/en/api/documentation
"""

import os
from datetime import datetime, timedelta
from wrdata.providers.coingecko_provider import CoinGeckoProvider


def test_connection():
    """Test if we can connect to CoinGecko API."""
    api_key = os.getenv("COINGECKO_API_KEY")  # Optional!

    provider = CoinGeckoProvider(api_key=api_key)

    if provider.validate_connection():
        print("✅ CoinGecko connection successful!")
        if api_key:
            print("   Using Pro API")
        else:
            print("   Using FREE demo tier (no API key)")
        return True
    else:
        print("❌ CoinGecko connection failed")
        return False


def test_crypto_data():
    """Test fetching crypto data."""
    api_key = os.getenv("COINGECKO_API_KEY")  # Optional!
    provider = CoinGeckoProvider(api_key=api_key)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    for symbol in ["BTC", "ETH", "SOL"]:
        print(f"\n📊 Testing CoinGecko data for {symbol}...")
        response = provider.fetch_timeseries(
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            interval="1d"
        )

        if response.success:
            print(f"✅ Got {len(response.data)} records")
            print(f"Latest price: ${response.data[-1]['close']:.2f}")
        else:
            print(f"❌ Error: {response.error}")


if __name__ == "__main__":
    print("=" * 60)
    print("COINGECKO LIVE TEST")
    print("=" * 60)

    if test_connection():
        test_crypto_data()

    print("\n" + "=" * 60)
    print("FREE tier features (NO API KEY!):")
    print("- 10-50 calls/minute")
    print("- 10,000+ cryptocurrencies")
    print("- Market data & rankings")
    print("- Historical prices")
    print("- No registration required!")
    print("=" * 60)
