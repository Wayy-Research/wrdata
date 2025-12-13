"""
Fetch 1-minute crypto data from ANY available source.

Let wrdata's fallback system find data wherever it exists.
"""

from wrdata import DataStream
from datetime import datetime, timedelta
import polars as pl

def main():
    # Initialize stream with fallback enabled (default)
    stream = DataStream()

    print("=" * 80)
    print("Fetching 1-Minute Crypto Data from Any Available Source")
    print("=" * 80)

    # Major crypto symbols in various formats
    # wrdata will try multiple providers automatically
    symbols = [
        # Try different formats - wrdata will normalize
        'BTC-USD',    # Coinbase format
        'ETH-USD',
        'SOL-USD',
        'AVAX-USD',
        'MATIC-USD',
        'LINK-USD',
        'DOGE-USD',
        'XRP-USD',
        'ADA-USD',
        'DOT-USD',
        'ATOM-USD',
        'UNI-USD',
        'LTC-USD',
        'BCH-USD',
        'NEAR-USD',
    ]

    # Use reasonable time range for 1-minute data
    # Most providers limit high-frequency data to recent periods
    days_back = 7

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print(f"\nSymbols to fetch: {len(symbols)}")
    print(f"Date range: {start_date} to {end_date} ({days_back} days)")
    print(f"Interval: 1-minute bars")
    print("\nLetting wrdata find data from any available provider...")
    print("(coinbase, yfinance, kraken, coingecko, ccxt exchanges)")
    print("\n" + "=" * 80)

    # Fetch with automatic provider selection and fallback
    data = stream.get_many(
        symbols=symbols,
        start=start_date,
        end=end_date,
        interval="1m",
        asset_type="crypto",
        # NO provider specified - let it find the best source
    )

    # Analyze results
    successful = {k: v for k, v in data.items() if not v.is_empty()}
    failed = {k: v for k, v in data.items() if v.is_empty()}

    print("\n" + "=" * 80)
    print(f"Results: {len(successful)}/{len(symbols)} successful")
    print("=" * 80)

    if successful:
        print("\n✅ Successfully fetched data:")
        print("-" * 80)
        for symbol, df in successful.items():
            rows = len(df)
            start_ts = df['timestamp'].min()
            end_ts = df['timestamp'].max()
            print(f"{symbol:15} - {rows:,} rows ({start_ts} to {end_ts})")

        total_rows = sum(len(df) for df in successful.values())
        print("-" * 80)
        print(f"Total data points: {total_rows:,}")
        print(f"Average per symbol: {total_rows / len(successful):,.0f}")

        # Calculate expected bars
        expected = days_back * 24 * 60
        coverage = (total_rows / len(successful) / expected) * 100 if expected > 0 else 0
        print(f"Expected bars/symbol: ~{expected:,}")
        print(f"Coverage: ~{coverage:.1f}%")

        print("\n" + "=" * 80)
        print("Sample data from first successful symbol:")
        print("=" * 80)
        first_symbol = list(successful.keys())[0]
        first_df = successful[first_symbol]
        print(f"\n{first_symbol}:")
        print(first_df.head(10))

        print("\n" + "=" * 80)
        print("Ready for correlation analysis!")
        print("=" * 80)
        print(f"\nYou have {len(successful)} crypto assets with 1-minute data")
        print("Next steps:")
        print("  1. Calculate log returns")
        print("  2. Compute rolling correlations")
        print("  3. Detect regime changes")
        print("\nYour data is in the 'data' dictionary:")
        print("  successful_data = {k: v for k, v in data.items() if not v.is_empty()}")

        return successful

    else:
        print("\n❌ No data found for any symbols")
        print("\nTroubleshooting:")
        print("  1. Check internet connection")
        print("  2. Try a shorter date range (1-3 days)")
        print("  3. Try using daily data (interval='1d') for longer history")

        return {}


if __name__ == "__main__":
    successful_data = main()

    # Make data available for interactive use
    if successful_data:
        print("\n✅ Data stored in 'successful_data' variable")
        print("\nExample - Calculate returns for BTC-USD:")
        print("  btc_df = successful_data['BTC-USD']")
        print("  btc_returns = btc_df.with_columns([")
        print("      (pl.col('close').log() - pl.col('close').log().shift(1)).alias('log_return')")
        print("  ])")
