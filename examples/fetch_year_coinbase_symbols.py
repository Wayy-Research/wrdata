"""
Fetch 1 YEAR of 1-minute data for Coinbase symbols.

This uses the updated wrdata with:
- Binance via CCXT for 1-year historical data
- Automatic pagination to fetch 525K+ candles
- Priority-based provider fallback
- Automatic coverage filtering (70%)
- Forward-fill for gaps
"""

from wrdata import DataStream
from datetime import datetime, timedelta
import polars as pl

stream = DataStream()

# Your Coinbase symbols
symbols = [
    'ALCX-USD', 'BARD-USD', 'ATOM-USD', 'CVX-USD', 'SKY-USD',
    'EDGE-USD', 'AVAX-USD', 'ZORA-USD', 'KSM-USD', 'COOKIE-USD',
    'CRV-USD', 'AERGO-USD', 'ACX-USD', 'ALLO-USD', 'YFI-USD',
    'FARM-USD', 'LOKA-USD', 'AST-USD', 'T-USD', 'CAKE-USD',
    'PENGU-USD'
]

# Request 1 FULL YEAR of 1-minute data
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

print("=" * 80)
print("Fetching 1-Year 1-Minute Data for Coinbase Symbols")
print("=" * 80)
print(f"Symbols: {len(symbols)}")
print(f"Date range: {start_date} to {end_date} (365 days)")
print(f"Interval: 1-minute bars")
print(f"Expected rows per symbol: ~525,600")
print()
print("Provider fallback: Coinbase → Binance → Kraken → other CCXT exchanges")
print("Automatic features:")
print("  - Coverage filtering: Excludes symbols with <70% data")
print("  - Forward-fill: Fills gaps in data")
print("  - Pagination: Automatically fetches full year from Binance")
print("=" * 80)
print()

# Fetch with automatic filtering and gap-filling
df = stream.get_many(
    symbols=symbols,
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
expected_rows = 365 * 24 * 60  # 525,600 rows for 1 year of 1-minute data
print(f"Expected rows per symbol: {expected_rows:,}")
print()
for row in summary.iter_rows(named=True):
    symbol = row['symbol']
    actual_rows = row['rows']
    coverage = (actual_rows / expected_rows) * 100
    print(f"{symbol:15} - {actual_rows:7,} rows ({coverage:5.1f}% coverage)")

print("\n" + "=" * 80)
print("✅ Data ready for regime detection and correlation analysis!")
print("=" * 80)
print(f"Symbols included: {df['symbol'].n_unique()}/{len(symbols)}")
print(f"Total rows: {len(df):,}")
print()
print("Example - Calculate correlation matrix:")
print("  pivot_df = df.pivot(values='close', index='timestamp', columns='symbol')")
print("  corr = pivot_df.select(pl.all().exclude('timestamp')).corr()")
