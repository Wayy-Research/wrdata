"""
Live test for Tiingo provider.

Get your FREE API key at: https://www.tiingo.com/account/api/token
Free tier: 500/hour, 1000/day
"""

import os
from datetime import datetime, timedelta
from wrdata.providers.tiingo_provider import TiingoProvider


def test_connection():
    """Test if we can connect to Tiingo API."""
    api_key = os.getenv("TIINGO_API_KEY")
    if not api_key:
        print("Set TIINGO_API_KEY in .env file")
        print("Get FREE key at: https://www.tiingo.com/account/api/token")
        return False

    provider = TiingoProvider(api_key=api_key)

    if provider.validate_connection():
        print("✅ Tiingo connection successful!")
        return True
    else:
        print("❌ Tiingo connection failed")
        return False


def test_stock_data():
    """Test fetching stock data."""
    api_key = os.getenv("TIINGO_API_KEY")
    if not api_key:
        print("Set TIINGO_API_KEY in .env file")
        return

    provider = TiingoProvider(api_key=api_key)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    print(f"\n📊 Testing Tiingo stock data for AAPL...")
    response = provider.fetch_timeseries(
        symbol="AAPL",
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        interval="1d"
    )

    if response.success:
        print(f"✅ Got {len(response.data)} records")
        print(f"Latest data: {response.data[-1]}")
        print(f"Metadata: {response.metadata}")
    else:
        print(f"❌ Error: {response.error}")


if __name__ == "__main__":
    print("=" * 60)
    print("TIINGO LIVE TEST")
    print("=" * 60)

    if test_connection():
        test_stock_data()

    print("\n" + "=" * 60)
    print("Free tier limits:")
    print("- 500 API calls per hour")
    print("- 1,000 API calls per day")
    print("- US & International stocks")
    print("- News with sentiment analysis")
    print("=" * 60)
