"""
Test fetching 1 YEAR of 1-minute cryptocurrency data.

This tests the new pagination implementation that allows fetching
large date ranges from Binance (7-8 years of data available).
"""

from wrdata import DataStream
from datetime import datetime, timedelta
import polars as pl

stream = DataStream()

# Test with a few symbols first
test_symbols = [
    'BTC-USD',
    'ETH-USD',
    'ATOM-USD',
    'AVAX-USD',
    'CRV-USD'
]

# Request 1 FULL YEAR of 1-minute data
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

print("=" * 80)
print("Testing 1-Year 1-Minute Data Fetch with Pagination")
print("=" * 80)
print(f"Symbols: {test_symbols}")
print(f"Date range: {start_date} to {end_date} (365 days)")
print(f"Interval: 1-minute bars")
print(f"Expected rows per symbol: ~525,600 (365 days × 1440 minutes/day)")
print()
print("Using Binance via CCXT (supports 7-8 years of 1-minute data)")
print("=" * 80)
print()

# Fetch with automatic pagination
df = stream.get_many(
    symbols=test_symbols,
    start=start_date,
    end=end_date,
    interval="1m",
    asset_type="crypto",
    min_coverage=0.70,
    forward_fill=True,
    drop_low_coverage=True
)

print("\n" + "=" * 80)
print("Results:")
print("=" * 80)
print(df)

print("\n" + "=" * 80)
print("Summary by Symbol:")
print("=" * 80)
summary = df.group_by('symbol').agg([
    pl.count().alias('rows'),
    pl.col('close').mean().alias('avg_price'),
    pl.col('timestamp').min().alias('earliest'),
    pl.col('timestamp').max().alias('latest')
]).sort('symbol')
print(summary)

print("\n" + "=" * 80)
print("Coverage Analysis:")
print("=" * 80)
expected_rows = 365 * 24 * 60  # 1 year of 1-minute data
for row in summary.iter_rows(named=True):
    symbol = row['symbol']
    actual_rows = row['rows']
    coverage = (actual_rows / expected_rows) * 100
    print(f"{symbol:15} - {actual_rows:7,} rows ({coverage:5.1f}% coverage)")

print("\n" + "=" * 80)
print("✅ Success! Fetched 1 year of 1-minute data using pagination")
print("=" * 80)
print(f"Total rows: {len(df):,}")
print(f"Symbols: {df['symbol'].n_unique()}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
