"""
Test which symbols have data available, then fetch only working symbols.

This script:
1. Quietly tests each symbol to see if data is available
2. Shows which symbols work and which don't
3. Fetches data only for working symbols
4. Returns a clean combined DataFrame
"""

from wrdata import DataStream
from datetime import datetime, timedelta
import polars as pl
import sys
from io import StringIO

def test_symbol_quietly(stream, symbol, start_date, end_date, interval="1m", asset_type="crypto"):
    """
    Test if a symbol has data available, suppressing all output.

    Returns:
        tuple: (success: bool, row_count: int, error_msg: str)
    """
    # Suppress print statements
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()

    try:
        df = stream.get(
            symbol=symbol,
            start=start_date,
            end=end_date,
            interval=interval,
            asset_type=asset_type
        )

        # Restore output
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        if df.is_empty():
            return (False, 0, "No data returned")
        else:
            return (True, len(df), None)

    except Exception as e:
        # Restore output
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        return (False, 0, str(e))


def test_and_fetch_symbols(
    symbols,
    interval="1m",
    days_back=7,
    asset_type="crypto"
):
    """
    Test symbols and fetch data for working ones.

    Args:
        symbols: List of symbol strings
        interval: Time interval (1m, 5m, 1h, 1d, etc.)
        days_back: How many days of history to fetch
        asset_type: Asset type

    Returns:
        tuple: (combined_df, working_symbols, failed_symbols)
    """
    stream = DataStream()

    # Calculate date range
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"Testing {len(symbols)} symbols for data availability")
    print("=" * 80)
    print(f"Date range: {start_date} to {end_date} ({days_back} days)")
    print(f"Interval: {interval}")
    print(f"Asset type: {asset_type}")
    print("\nTesting symbols (this may take a minute)...\n")

    working = {}
    failed = {}

    for i, symbol in enumerate(symbols, 1):
        print(f"\r[{i}/{len(symbols)}] Testing {symbol:20}", end="", flush=True)

        success, rows, error = test_symbol_quietly(
            stream, symbol, start_date, end_date, interval, asset_type
        )

        if success:
            working[symbol] = rows
        else:
            failed[symbol] = error

    print("\n\n" + "=" * 80)
    print(f"Results: {len(working)} working, {len(failed)} failed")
    print("=" * 80)

    if working:
        print("\n✅ Symbols WITH data:")
        print("-" * 80)
        for symbol, rows in working.items():
            print(f"  {symbol:20} - {rows:,} rows")

    if failed:
        print(f"\n❌ Symbols WITHOUT data ({len(failed)}):")
        print("-" * 80)
        failed_list = list(failed.keys())
        # Show first 10, then summarize
        for symbol in failed_list[:10]:
            print(f"  {symbol}")
        if len(failed_list) > 10:
            print(f"  ... and {len(failed_list) - 10} more")

    if not working:
        print("\n⚠️  No working symbols found. Try:")
        print("  1. Different time range (e.g., days_back=30)")
        print("  2. Different interval (e.g., interval='1h' or '1d')")
        print("  3. Major symbols like BTC-USD, ETH-USD")
        return pl.DataFrame(), [], list(failed.keys())

    # Fetch data for working symbols
    print("\n" + "=" * 80)
    print(f"Fetching data for {len(working)} working symbols...")
    print("=" * 80)

    working_symbols = list(working.keys())

    # Use get_many_combined for clean multi-indexed DataFrame
    combined_df = stream.get_many_combined(
        symbols=working_symbols,
        start=start_date,
        end=end_date,
        interval=interval,
        asset_type=asset_type
    )

    print("\n✅ Data fetch complete!")
    print(f"   Total rows: {len(combined_df):,}")
    print(f"   Symbols: {combined_df['symbol'].n_unique()}")
    print(f"   Columns: {', '.join(combined_df.columns)}")

    return combined_df, working_symbols, list(failed.keys())


def main():
    # Your specific list of symbols
    symbols = [
        'ALCX-USD', 'BARD-USD', 'ATOM-USD', 'CVX-USD', 'SKY-USD',
        'EDGE-USD', 'AVAX-USD', 'ZORA-USD', 'KSM-USD', 'COOKIE-USD',
        'CRV-USD', 'AERGO-USD', 'ACX-USD', 'ALLO-USD', 'YFI-USD',
        'FARM-USD', 'LOKA-USD', 'AST-USD', 'T-USD', 'CAKE-USD',
        'PENGU-USD'
    ]

    # Test and fetch
    df, working, failed = test_and_fetch_symbols(
        symbols=symbols,
        interval="1m",
        days_back=7,
        asset_type="crypto"
    )

    if not df.is_empty():
        print("\n" + "=" * 80)
        print("Data Preview:")
        print("=" * 80)
        print(df.head(20))

        print("\n" + "=" * 80)
        print("Summary by Symbol:")
        print("=" * 80)
        summary = df.group_by('symbol').agg([
            pl.count().alias('rows'),
            pl.col('close').mean().alias('avg_price'),
            pl.col('timestamp').min().alias('start'),
            pl.col('timestamp').max().alias('end')
        ]).sort('symbol')
        print(summary)

        print("\n" + "=" * 80)
        print("Next Steps - Correlation Analysis:")
        print("=" * 80)
        print("\n1. Calculate returns:")
        print("   returns_df = df.sort(['symbol', 'timestamp']).with_columns([")
        print("       pl.col('close').log().diff().over('symbol').alias('log_return')")
        print("   ])")

        print("\n2. Pivot for correlation matrix:")
        print("   pivot_df = df.pivot(")
        print("       values='close',")
        print("       index='timestamp',")
        print("       columns='symbol'")
        print("   )")

        print("\n3. Calculate correlation:")
        print("   # Convert to numpy for correlation")
        print("   import numpy as np")
        print("   corr_matrix = np.corrcoef(pivot_df.select(working).to_numpy().T)")

        return df, working, failed
    else:
        return None, working, failed


if __name__ == "__main__":
    df, working_symbols, failed_symbols = main()

    # Make data available for interactive use
    if df is not None and not df.is_empty():
        print("\n" + "=" * 80)
        print("✅ Data stored in variables:")
        print("   df             - Combined DataFrame")
        print("   working_symbols - List of symbols with data")
        print("   failed_symbols  - List of symbols without data")
        print("=" * 80)
