"""
Fetch data for all requested symbols with verbose provider information.

Shows which provider successfully retrieved data for each symbol.
"""

from wrdata import DataStream
from datetime import datetime, timedelta
import polars as pl

def fetch_with_provider_info(stream, symbol, start_date, end_date, interval="1m", asset_type="crypto"):
    """
    Fetch data and track which provider succeeded.

    Returns:
        tuple: (df, provider_name, error_msg)
    """
    # Manually try each provider to see which one works
    providers_to_try = [
        'coinbase', 'yfinance', 'kraken', 'coingecko',
        'ccxt_bybit', 'ccxt_okx', 'ccxt_kucoin',
        'ccxt_gateio', 'ccxt_bitfinex'
    ]

    for provider_name in providers_to_try:
        try:
            df = stream.get(
                symbol=symbol,
                start=start_date,
                end=end_date,
                interval=interval,
                asset_type=asset_type,
                provider=provider_name
            )

            if not df.is_empty():
                return (df, provider_name, None)

        except Exception as e:
            continue

    # All providers failed
    return (pl.DataFrame(), None, "No provider found data")


def main():
    stream = DataStream()

    # Your list of symbols
    symbols = [
        'ALCX-USD', 'BARD-USD', 'ATOM-USD', 'CVX-USD', 'SKY-USD',
        'EDGE-USD', 'AVAX-USD', 'ZORA-USD', 'KSM-USD', 'COOKIE-USD',
        'CRV-USD', 'AERGO-USD', 'ACX-USD', 'ALLO-USD', 'YFI-USD',
        'FARM-USD', 'LOKA-USD', 'AST-USD', 'T-USD', 'CAKE-USD',
        'PENGU-USD'
    ]

    # Use shorter time range for 1-minute data
    days_back = 7
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    print("=" * 80)
    print(f"Fetching {len(symbols)} symbols with provider tracking")
    print("=" * 80)
    print(f"Date range: {start_date} to {end_date} ({days_back} days)")
    print(f"Interval: 1-minute bars")
    print("\nTesting each symbol across all providers...\n")

    results = {}
    provider_stats = {}

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol:20}", end=" ", flush=True)

        df, provider, error = fetch_with_provider_info(
            stream, symbol, start_date, end_date, interval="1m"
        )

        if not df.is_empty():
            results[symbol] = df
            provider_stats[symbol] = provider
            print(f"✅ {provider:15} - {len(df):,} rows")
        else:
            print(f"❌ No data")

    print("\n" + "=" * 80)
    print(f"Results: {len(results)}/{len(symbols)} symbols found")
    print("=" * 80)

    if results:
        # Show provider breakdown
        print("\nProvider Breakdown:")
        print("-" * 80)
        provider_counts = {}
        for provider in provider_stats.values():
            provider_counts[provider] = provider_counts.get(provider, 0) + 1

        for provider, count in sorted(provider_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {provider:20} - {count} symbols")

        # Create combined DataFrame
        print("\n" + "=" * 80)
        print("Creating combined DataFrame...")
        print("=" * 80)

        combined_dfs = []
        # Ensure all DataFrames have the same columns and types
        standard_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        for symbol, df in results.items():
            # Select only standard columns (skip metadata)
            available_cols = [c for c in standard_cols if c in df.columns]
            df_normalized = df.select(available_cols)

            # Cast numeric columns to float64 for consistency
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                if col in df_normalized.columns:
                    df_normalized = df_normalized.with_columns(
                        pl.col(col).cast(pl.Float64)
                    )

            # Add symbol column
            df_with_symbol = df_normalized.with_columns(
                pl.lit(symbol).alias('symbol')
            )
            combined_dfs.append(df_with_symbol)

        combined = pl.concat(combined_dfs, how='vertical')

        if 'timestamp' in combined.columns:
            combined = combined.sort(['symbol', 'timestamp'])
        else:
            combined = combined.sort('symbol')

        print(f"\n✅ Combined DataFrame created!")
        print(f"   Total rows: {len(combined):,}")
        print(f"   Symbols: {combined['symbol'].n_unique()}")
        print(f"   Columns: {', '.join(combined.columns)}")

        print("\n" + "=" * 80)
        print("Data Preview:")
        print("=" * 80)
        print(combined.head(20))

        print("\n" + "=" * 80)
        print("Summary by Symbol:")
        print("=" * 80)
        summary = combined.group_by('symbol').agg([
            pl.count().alias('rows'),
            pl.col('close').mean().alias('avg_price'),
            pl.col('timestamp').min().alias('start'),
            pl.col('timestamp').max().alias('end')
        ]).sort('symbol')
        print(summary)

        return combined, list(results.keys()), provider_stats

    else:
        print("\n❌ No data found for any symbols")
        print("\nTroubleshooting:")
        print("  1. Some symbols may not exist on any exchange")
        print("  2. Try longer interval (1h, 1d) for more data availability")
        print("  3. Try different symbols (BTC-USD, ETH-USD are always available)")

        return None, [], {}


if __name__ == "__main__":
    print("IMPORTANT: Restart your Python kernel before running this!\n")
    df, working_symbols, provider_map = main()

    if df is not None:
        print("\n" + "=" * 80)
        print("Data ready for correlation analysis!")
        print("=" * 80)
        print("\nVariables available:")
        print("  df              - Combined DataFrame")
        print("  working_symbols - List of symbols with data")
        print("  provider_map    - Dict mapping symbol -> provider")
        print("\nExample - Calculate returns:")
        print("  returns = df.sort(['symbol', 'timestamp']).with_columns([")
        print("      pl.col('close').log().diff().over('symbol').alias('log_return')")
        print("  ])")
