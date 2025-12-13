"""
Fetch crypto data as a single multi-indexed DataFrame.

Perfect for correlation analysis and regime detection.
"""

from wrdata import DataStream
from datetime import datetime, timedelta
import polars as pl

# Restart your kernel first, then run this!

stream = DataStream()

# Major liquid crypto pairs
symbols = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'AVAX-USD',
    'MATIC-USD', 'LINK-USD', 'XRP-USD', 'ADA-USD'
]

# Use 7 days for 1-minute data
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

print("Fetching data...")
print(f"Symbols: {symbols}")
print(f"Range: {start_date} to {end_date}")
print(f"Interval: 1 minute\n")

# NEW METHOD: Get as single combined DataFrame
df = stream.get_many_combined(
    symbols=symbols,
    start=start_date,
    end=end_date,
    interval="1m",
    asset_type="crypto"
)

print("=" * 80)
print("Combined DataFrame Structure:")
print("=" * 80)
print(df)

print("\n" + "=" * 80)
print("Data Summary by Symbol:")
print("=" * 80)
summary = df.group_by('symbol').agg([
    pl.count().alias('rows'),
    pl.col('timestamp').min().alias('start'),
    pl.col('timestamp').max().alias('end'),
    pl.col('close').mean().alias('avg_price')
])
print(summary)

print("\n" + "=" * 80)
print("Ready for Analysis!")
print("=" * 80)

if not df.is_empty():
    print(f"\nTotal rows: {len(df):,}")
    print(f"Symbols with data: {df['symbol'].n_unique()}")

    print("\nExample 1 - Pivot for correlation matrix:")
    print("-" * 80)
    print("pivot_df = df.pivot(")
    print("    values='close',")
    print("    index='timestamp',")
    print("    columns='symbol'")
    print(")")

    print("\nExample 2 - Calculate returns:")
    print("-" * 80)
    print("returns_df = df.sort(['symbol', 'timestamp']).with_columns([")
    print("    pl.col('close').log().diff().over('symbol').alias('log_return')")
    print("])")

    print("\nExample 3 - Filter to single symbol:")
    print("-" * 80)
    print("btc_df = df.filter(pl.col('symbol') == 'BTC-USD')")

    # Actually create the pivot for demonstration
    print("\n" + "=" * 80)
    print("Creating pivot table (this is what you want for correlations):")
    print("=" * 80)

    try:
        pivot_df = df.pivot(
            values='close',
            index='timestamp',
            columns='symbol'
        )
        print(pivot_df.head(10))
        print(f"\nPivot shape: {pivot_df.shape}")
        print("\n✅ This pivot table is ready for correlation analysis!")
        print("   Each column is a crypto symbol, each row is a timestamp")

    except Exception as e:
        print(f"Note: Pivot requires aligned timestamps. Error: {e}")
        print("For non-aligned data, resample or use group_by operations instead.")

else:
    print("❌ No data retrieved. Try:")
    print("  1. Restart your Python kernel")
    print("  2. Check internet connection")
    print("  3. Try interval='1h' or '1d' for more reliable data")
