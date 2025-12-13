"""
Robust Coinbase data fetching with validation.

This script:
1. Tests which symbols actually have historical data
2. Uses a reasonable time range for 1-minute data (7-30 days)
3. Provides clear feedback on what works and what doesn't
"""

from wrdata import DataStream
from wrdata.providers.coinbase_provider import CoinbaseProvider
from datetime import datetime, timedelta
import polars as pl

def test_symbol(stream, symbol, start_date, end_date, interval="1m"):
    """
    Test if a symbol has available data.

    Returns:
        tuple: (symbol, success, df, error_msg)
    """
    try:
        df = stream.get(
            symbol=symbol,
            start=start_date,
            end=end_date,
            interval=interval,
            asset_type="crypto",
            provider="coinbase"
        )

        if df.is_empty():
            return (symbol, False, df, "No data returned")
        else:
            return (symbol, True, df, None)

    except Exception as e:
        return (symbol, False, pl.DataFrame(), str(e))


def main():
    # Initialize
    stream = DataStream()
    coinbase = CoinbaseProvider()

    print("=" * 80)
    print("Coinbase 1-Minute Data Fetcher")
    print("=" * 80)

    # Get all products
    products = coinbase.get_products()

    # Filter for USDC pairs (more stable/liquid than some USD pairs)
    usdc_pairs = [
        p['id'] for p in products
        if p['id'].endswith('-USDC')
        and p.get('status') == 'online'
        and p.get('trading_disabled') == False
    ]

    # Also get major USD pairs
    usd_pairs = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'USDC-USD',
        'AVAX-USD', 'MATIC-USD', 'LINK-USD', 'DOGE-USD',
        'XRP-USD', 'ADA-USD', 'DOT-USD', 'ATOM-USD'
    ]

    # Combine and deduplicate
    all_pairs = list(set(usdc_pairs + usd_pairs))

    print(f"\nFound {len(all_pairs)} candidate trading pairs")
    print(f"USDC pairs: {len(usdc_pairs)}")
    print(f"Major USD pairs: {len(usd_pairs)}")

    # Use a shorter, more realistic time range for 1-minute data
    # Coinbase typically limits 1-minute data to recent history
    days_back = 7  # Start with 7 days

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print(f"\nDate range: {start_date} to {end_date} ({days_back} days)")
    print(f"Interval: 1-minute bars")
    print("\n" + "=" * 80)
    print("Testing symbols (this may take a few minutes)...")
    print("=" * 80)

    # Test a small sample first to validate approach
    sample_pairs = all_pairs[:20]  # Test first 20

    successful = {}
    failed = {}

    for i, symbol in enumerate(sample_pairs, 1):
        print(f"\r[{i}/{len(sample_pairs)}] Testing {symbol:20}", end="", flush=True)

        sym, success, df, error = test_symbol(
            stream, symbol, start_date, end_date, interval="1m"
        )

        if success:
            successful[sym] = df
        else:
            failed[sym] = error

    print("\n" + "=" * 80)
    print(f"Results: {len(successful)} successful, {len(failed)} failed")
    print("=" * 80)

    if successful:
        print("\n✅ Successfully fetched data for:")
        print("-" * 80)
        for symbol, df in successful.items():
            print(f"  {symbol:20} - {len(df):,} rows ({df['timestamp'].min()} to {df['timestamp'].max()})")

        # Calculate some basic stats
        print("\n" + "=" * 80)
        print("Data Summary:")
        print("=" * 80)

        total_rows = sum(len(df) for df in successful.values())
        avg_rows = total_rows / len(successful) if successful else 0

        print(f"Total data points: {total_rows:,}")
        print(f"Average per symbol: {avg_rows:,.0f}")
        print(f"Expected for {days_back} days @ 1-min: ~{days_back * 24 * 60:,} bars")

        # Show correlation potential
        if len(successful) >= 2:
            print(f"\n✅ You have {len(successful)} symbols with data - enough for correlation analysis!")
            print("\nNext steps:")
            print("  1. Calculate returns for each symbol")
            print("  2. Compute rolling correlation matrix")
            print("  3. Perform regime detection")
            print("\nExample:")
            print("  symbols_list = list(successful.keys())")
            print("  data_dict = successful  # Your data is already here!")

    if failed:
        print("\n\n❌ Failed to fetch data for:")
        print("-" * 80)
        for symbol, error in list(failed.items())[:10]:  # Show first 10 failures
            error_short = error[:60] + "..." if len(error) > 60 else error
            print(f"  {symbol:20} - {error_short}")

        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")

    print("\n" + "=" * 80)
    print("Tips for better results:")
    print("=" * 80)
    print("1. Use major pairs (BTC-USD, ETH-USD) - they have the most complete data")
    print("2. Shorter time ranges work better for 1-minute data (1-30 days)")
    print("3. For longer history, use higher intervals (1h, 1d)")
    print("4. Some pairs may be delisted or have gaps in historical data")
    print("\nTo fetch more symbols, extend the sample_pairs list in the code.")

    return successful, failed


if __name__ == "__main__":
    successful, failed = main()
