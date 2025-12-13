"""
Example: Fetch 1-minute Coinbase data and perform regime detection on correlations.

This script demonstrates how to:
1. Get all tradable products from Coinbase
2. Fetch 1-minute historical data for multiple symbols
3. Calculate rolling correlations
4. Perform regime detection on the correlation matrix
"""

from wrdata import DataStream
from wrdata.providers.coinbase_provider import CoinbaseProvider
import polars as pl
import numpy as np
from datetime import datetime, timedelta

def main():
    # Initialize stream
    stream = DataStream()

    # Get Coinbase products
    coinbase = CoinbaseProvider()
    products = coinbase.get_products()

    # Filter for USD pairs that are actively trading
    usd_pairs = [
        p['id'] for p in products
        if p['id'].endswith('-USDC')
        and p.get('status') == 'online'
        and p.get('trading_disabled') == False
    ]

    print(f"Found {len(usd_pairs)} active USD trading pairs on Coinbase")
    print(f"Sample pairs: {usd_pairs[:10]}")

    # For this example, let's use a subset of major coins
    # (fetching all pairs would take a while)
    major_pairs = [
        'BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'XRP-USD',
        'DOGE-USD', 'MATIC-USD', 'LINK-USD', 'AVAX-USD', 'DOT-USD'
    ]

    # Calculate date range (past year)
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

    print(f"\nFetching 1-minute data from {start_date} to {end_date}")
    print(f"Pairs to fetch: {major_pairs}")
    print("\nNote: Coinbase API may have data limits for 1-minute bars over long periods.")
    print("If you get empty results, try a shorter time range (e.g., 7-30 days)\n")

    # Fetch 1-minute data from Coinbase
    data = stream.get_many(
        symbols=major_pairs,
        start=start_date,
        end=end_date,
        interval="1m",
        asset_type="crypto",
        provider="coinbase"
    )

    # Check results
    print("\nFetch Results:")
    print("-" * 60)
    for symbol, df in data.items():
        if df.is_empty():
            print(f"{symbol:15} - No data")
        else:
            print(f"{symbol:15} - {len(df):,} rows, {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Filter out empty DataFrames
    valid_data = {k: v for k, v in data.items() if not v.is_empty()}

    if len(valid_data) < 2:
        print("\nNot enough data for correlation analysis. Try a shorter date range.")
        return

    print(f"\n{len(valid_data)} pairs have valid data for correlation analysis")

    # Calculate returns for correlation analysis
    print("\nCalculating returns...")
    returns_data = {}

    for symbol, df in valid_data.items():
        # Sort by timestamp and calculate log returns
        df = df.sort('timestamp')
        df = df.with_columns([
            (pl.col('close').log() - pl.col('close').log().shift(1)).alias('log_return')
        ])
        returns_data[symbol] = df.select(['timestamp', 'log_return']).drop_nulls()

    # Align all timestamps (find common timestamps across all pairs)
    # This is a simple approach - for production you might want to resample to common intervals
    print("\nAligning timestamps across pairs...")

    # Get common timestamps
    timestamp_sets = [set(df['timestamp'].to_list()) for df in returns_data.values()]
    common_timestamps = set.intersection(*timestamp_sets)

    print(f"Found {len(common_timestamps)} common timestamps across all pairs")

    if len(common_timestamps) < 100:
        print("Not enough common data points for meaningful correlation analysis.")
        return

    # Build correlation matrix over rolling windows
    print("\nCalculating rolling correlations...")

    # Convert to a unified DataFrame with symbols as columns
    # This is a simplified example - you might want to use more sophisticated alignment
    combined_returns = {}
    for symbol, df in returns_data.items():
        # Filter to common timestamps
        df_filtered = df.filter(pl.col('timestamp').is_in(sorted(common_timestamps)))
        combined_returns[symbol] = df_filtered.sort('timestamp')['log_return'].to_numpy()

    # Calculate correlation matrix
    symbols = list(combined_returns.keys())
    n_symbols = len(symbols)

    # Simple rolling correlation with a fixed window
    window = 60 * 24  # 24 hours of 1-minute data

    print(f"\nUsing rolling window of {window} periods (24 hours)")
    print(f"Correlation matrix size: {n_symbols}x{n_symbols}")

    # Calculate correlation for the most recent window
    returns_matrix = np.array([combined_returns[s] for s in symbols])

    if returns_matrix.shape[1] < window:
        print(f"Not enough data for the rolling window. Need {window}, have {returns_matrix.shape[1]}")
        return

    # Get the most recent window
    recent_returns = returns_matrix[:, -window:]

    # Calculate correlation matrix
    corr_matrix = np.corrcoef(recent_returns)

    print("\nCorrelation Matrix (most recent 24 hours):")
    print("-" * 80)

    # Print correlation matrix
    header = "Symbol".ljust(15) + "".join([s.replace('-USD', '').ljust(8) for s in symbols])
    print(header)
    print("-" * 80)

    for i, symbol in enumerate(symbols):
        row = symbol.replace('-USD', '').ljust(15)
        for j in range(n_symbols):
            row += f"{corr_matrix[i, j]:7.2f} "
        print(row)

    # Simple regime detection based on average correlation
    avg_corr = np.mean(corr_matrix[np.triu_indices_from(corr_matrix, k=1)])

    print("\n" + "=" * 80)
    print(f"Average Correlation: {avg_corr:.3f}")

    if avg_corr > 0.7:
        regime = "HIGH CORRELATION - Market moving together (risk-on/risk-off regime)"
    elif avg_corr > 0.4:
        regime = "MODERATE CORRELATION - Mixed market regime"
    else:
        regime = "LOW CORRELATION - Diversified market regime"

    print(f"Market Regime: {regime}")
    print("=" * 80)

    # Find pairs with highest and lowest correlation
    print("\nHighest Correlations:")
    print("-" * 80)

    corr_pairs = []
    for i in range(n_symbols):
        for j in range(i+1, n_symbols):
            corr_pairs.append((symbols[i], symbols[j], corr_matrix[i, j]))

    corr_pairs.sort(key=lambda x: x[2], reverse=True)

    for pair1, pair2, corr in corr_pairs[:5]:
        print(f"{pair1:15} <-> {pair2:15} : {corr:.3f}")

    print("\nLowest Correlations:")
    print("-" * 80)
    for pair1, pair2, corr in corr_pairs[-5:]:
        print(f"{pair1:15} <-> {pair2:15} : {corr:.3f}")

    print("\n✅ Analysis complete!")
    print("\nTo save this data, you can export the DataFrames:")
    print("  df.write_csv('btc_1m.csv')")
    print("  df.write_parquet('btc_1m.parquet')")

if __name__ == "__main__":
    main()
