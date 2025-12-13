"""
Simple example using get_many_combined with automatic filtering.

The function now automatically:
1. Filters out symbols with <70% data coverage
2. Forward-fills gaps in the data
3. Returns a clean, aligned DataFrame
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

print("Fetching data with automatic coverage filtering...")
print(f"Symbols: {len(symbols)}")
print(f"Date range: {start_date} to {end_date}")
print()

# ONE LINE - automatic filtering and gap filling!
df = stream.get_many_combined(
    symbols=symbols,
    start=start_date,
    end=end_date,
    interval="1m",
    asset_type="crypto",
    min_coverage=0.70,      # Exclude symbols with <70% data
    forward_fill=True,      # Fill gaps
    drop_low_coverage=True  # Auto-remove low coverage symbols
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
