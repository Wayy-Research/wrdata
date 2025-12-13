"""
Simple example using the unified get_many() function.

get_many() now automatically:
- Returns a single combined DataFrame (not a dict)
- Filters out symbols with <70% data coverage
- Forward-fills gaps
- Returns clean data ready for correlation analysis
"""

from wrdata import DataStream
from datetime import datetime, timedelta
import polars as pl

# RESTART YOUR KERNEL FIRST!

stream = DataStream()

symbols = [
    'ALCX-USD', 'BARD-USD', 'ATOM-USD', 'CVX-USD', 'SKY-USD',
    'EDGE-USD', 'AVAX-USD', 'ZORA-USD', 'KSM-USD', 'COOKIE-USD',
    'CRV-USD', 'AERGO-USD', 'ACX-USD', 'ALLO-USD', 'YFI-USD',
    'FARM-USD', 'LOKA-USD', 'AST-USD', 'T-USD', 'CAKE-USD',
    'PENGU-USD'
]

end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

print("Fetching data with automatic filtering and gap-filling...")
print(f"Symbols: {len(symbols)}")
print(f"Date range: {start_date} to {end_date}")
print()

# Simple one-line call - automatic filtering enabled by default!
df = stream.get_many(
    symbols=symbols,
    start=start_date,
    end=end_date,
    interval="1m",
    asset_type="crypto"
    # min_coverage=0.70 (default)
    # forward_fill=True (default)
    # drop_low_coverage=True (default)
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
    pl.col('close').mean().alias('avg_price')
]).sort('symbol')
print(summary)

print("\n" + "=" * 80)
print("✅ Ready for correlation analysis!")
print("=" * 80)
print(f"Symbols included: {df['symbol'].n_unique()}")
print(f"Total rows: {len(df):,}")
print("\nLow-coverage symbols (BARD, ZORA, PENGU, COOKIE, ACX) automatically excluded!")
