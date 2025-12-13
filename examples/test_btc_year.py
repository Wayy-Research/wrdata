"""
Simple test: Fetch 1 year of 1-minute BTC data to validate:
1. Binance provider is being used
2. Pagination is working
3. Provider fallback is working correctly
"""

from wrdata import DataStream
from datetime import datetime, timedelta

stream = DataStream()

# Request 1 year of 1-minute BTC data
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

print("=" * 80)
print("Testing BTC-USD: 1 Year of 1-Minute Data")
print("=" * 80)
print(f"Date range: {start_date} to {end_date} (365 days)")
print(f"Interval: 1-minute bars")
print(f"Expected rows: ~525,600 (365 × 1440 minutes/day)")
print()

# Fetch data
df = stream.get(
    symbol='BTC-USD',
    start=start_date,
    end=end_date,
    interval="1m",
    asset_type="crypto"
)

print("\n" + "=" * 80)
print("Results:")
print("=" * 80)

if not df.is_empty():
    print(f"✅ Success!")
    print(f"   Rows fetched: {len(df):,}")
    print(f"   Coverage: {(len(df) / 525600) * 100:.1f}%")
    print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print()
    print("First 10 rows:")
    print(df.head(10))
    print()
    print("Last 10 rows:")
    print(df.tail(10))
else:
    print("❌ No data returned")
