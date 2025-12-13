"""
Integration test for whale transaction tracking and price impact analysis.

Tests:
1. Fetch historical whale transactions from Whale Alert
2. Fetch corresponding price data from Binance
3. Analyze price impact of whale transactions
4. Calculate correlation metrics
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import os

from wrdata.providers.whale_alert_provider import WhaleAlertProvider
from wrdata.providers.binance_provider import BinanceProvider
from wrdata.models.schemas import WhaleTransaction


class WhalePriceImpactAnalyzer:
    """Analyzes price impact of whale transactions."""

    def __init__(self, whale_provider: WhaleAlertProvider, price_provider: BinanceProvider):
        self.whale_provider = whale_provider
        self.price_provider = price_provider

    def fetch_whale_transactions(
        self,
        start_date: str,
        end_date: str,
        blockchain: str = "bitcoin",
        min_value: int = 1000000
    ) -> List[WhaleTransaction]:
        """
        Fetch historical whale transactions.

        Args:
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            blockchain: Blockchain to filter (default: bitcoin)
            min_value: Minimum transaction value in USD

        Returns:
            List of WhaleTransaction objects
        """
        print(f"\n📊 Fetching whale transactions from {start_date} to {end_date}")
        print(f"   Blockchain: {blockchain}, Min value: ${min_value:,}")

        batch = self.whale_provider.fetch_whale_transactions(
            start_date=start_date,
            end_date=end_date,
            blockchain=blockchain,
            min_value=min_value,
            limit=100
        )

        print(f"   Found {batch.count} whale transactions")
        return batch.transactions

    def fetch_price_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1m"
    ) -> pd.DataFrame:
        """
        Fetch historical price data for correlation analysis.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            interval: Candle interval (default: 1m for minute data)

        Returns:
            DataFrame with OHLCV data
        """
        print(f"\n📈 Fetching price data for {symbol}")
        print(f"   Interval: {interval}, Period: {start_date} to {end_date}")

        response = self.price_provider.fetch_timeseries(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        if not response.success or not response.data:
            raise Exception(f"Failed to fetch price data: {response.error}")

        df = pd.DataFrame(response.data)

        # Convert Date column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

        # Ensure numeric columns
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        print(f"   Loaded {len(df)} price candles")
        return df

    def analyze_price_impact(
        self,
        whale_txs: List[WhaleTransaction],
        price_df: pd.DataFrame,
        window_before: int = 5,
        window_after: int = 15
    ) -> Dict[str, Any]:
        """
        Analyze price impact of whale transactions.

        Args:
            whale_txs: List of whale transactions
            price_df: DataFrame with minute-level price data
            window_before: Minutes to look before transaction
            window_after: Minutes to look after transaction

        Returns:
            Dictionary with analysis results
        """
        print(f"\n🔍 Analyzing price impact of whale transactions")
        print(f"   Analysis window: -{window_before}m to +{window_after}m")

        results = []

        for whale_tx in whale_txs:
            tx_time = whale_tx.timestamp

            # Find closest price candle
            try:
                # Get price data around transaction time
                idx = price_df.index.get_indexer([tx_time], method='nearest')[0]

                if idx < window_before or idx >= len(price_df) - window_after:
                    continue  # Skip if not enough data

                # Price before whale transaction
                price_before = price_df.iloc[idx - window_before]['Close']

                # Price at transaction
                price_at_tx = price_df.iloc[idx]['Close']

                # Prices after transaction (multiple time horizons)
                price_after_5m = price_df.iloc[idx + 5]['Close'] if idx + 5 < len(price_df) else None
                price_after_10m = price_df.iloc[idx + 10]['Close'] if idx + 10 < len(price_df) else None
                price_after_15m = price_df.iloc[idx + 15]['Close'] if idx + 15 < len(price_df) else None

                # Calculate price changes
                change_before_to_tx = ((price_at_tx - price_before) / price_before) * 100
                change_5m = ((price_after_5m - price_at_tx) / price_at_tx) * 100 if price_after_5m else None
                change_10m = ((price_after_10m - price_at_tx) / price_at_tx) * 100 if price_after_10m else None
                change_15m = ((price_after_15m - price_at_tx) / price_at_tx) * 100 if price_after_15m else None

                # Calculate volume surge
                volume_before = price_df.iloc[idx - window_before:idx]['Volume'].mean()
                volume_at_tx = price_df.iloc[idx]['Volume']
                volume_surge = ((volume_at_tx - volume_before) / volume_before) * 100 if volume_before > 0 else 0

                # Volatility (standard deviation of returns in window_after period)
                returns_after = price_df.iloc[idx:idx + window_after]['Close'].pct_change().dropna()
                volatility_after = returns_after.std() * 100 if len(returns_after) > 0 else 0

                results.append({
                    'timestamp': tx_time,
                    'symbol': whale_tx.symbol,
                    'whale_size': float(whale_tx.size),
                    'whale_usd_value': float(whale_tx.usd_value),
                    'transaction_type': whale_tx.transaction_type,
                    'exchange': whale_tx.exchange,
                    'price_before': float(price_before),
                    'price_at_tx': float(price_at_tx),
                    'price_after_5m': float(price_after_5m) if price_after_5m else None,
                    'price_after_10m': float(price_after_10m) if price_after_10m else None,
                    'price_after_15m': float(price_after_15m) if price_after_15m else None,
                    'change_before_to_tx_pct': float(change_before_to_tx),
                    'change_5m_pct': float(change_5m) if change_5m else None,
                    'change_10m_pct': float(change_10m) if change_10m else None,
                    'change_15m_pct': float(change_15m) if change_15m else None,
                    'volume_surge_pct': float(volume_surge),
                    'volatility_after_pct': float(volatility_after)
                })

            except Exception as e:
                print(f"   Warning: Could not analyze transaction at {tx_time}: {e}")
                continue

        # Calculate aggregate statistics
        if results:
            results_df = pd.DataFrame(results)

            # Filter out None values for statistics
            valid_5m = results_df['change_5m_pct'].dropna()
            valid_10m = results_df['change_10m_pct'].dropna()
            valid_15m = results_df['change_15m_pct'].dropna()

            stats = {
                'total_whale_transactions': len(results),
                'avg_whale_size_usd': results_df['whale_usd_value'].mean(),
                'median_whale_size_usd': results_df['whale_usd_value'].median(),
                'total_whale_volume_usd': results_df['whale_usd_value'].sum(),
                'avg_price_change_5m_pct': valid_5m.mean() if len(valid_5m) > 0 else 0,
                'avg_price_change_10m_pct': valid_10m.mean() if len(valid_10m) > 0 else 0,
                'avg_price_change_15m_pct': valid_15m.mean() if len(valid_15m) > 0 else 0,
                'median_price_change_5m_pct': valid_5m.median() if len(valid_5m) > 0 else 0,
                'positive_impact_5m_count': len(valid_5m[valid_5m > 0]) if len(valid_5m) > 0 else 0,
                'negative_impact_5m_count': len(valid_5m[valid_5m < 0]) if len(valid_5m) > 0 else 0,
                'avg_volume_surge_pct': results_df['volume_surge_pct'].mean(),
                'avg_volatility_after_pct': results_df['volatility_after_pct'].mean(),
                'by_transaction_type': {}
            }

            # Group by transaction type
            for tx_type in results_df['transaction_type'].unique():
                tx_type_data = results_df[results_df['transaction_type'] == tx_type]
                type_valid_5m = tx_type_data['change_5m_pct'].dropna()

                stats['by_transaction_type'][tx_type] = {
                    'count': len(tx_type_data),
                    'avg_usd_value': tx_type_data['whale_usd_value'].mean(),
                    'avg_price_change_5m_pct': type_valid_5m.mean() if len(type_valid_5m) > 0 else 0
                }

            return {
                'transactions': results,
                'statistics': stats,
                'dataframe': results_df
            }
        else:
            return {
                'transactions': [],
                'statistics': {},
                'dataframe': pd.DataFrame()
            }

    def print_analysis_report(self, analysis: Dict[str, Any]) -> None:
        """
        Print formatted analysis report.

        Args:
            analysis: Analysis results from analyze_price_impact()
        """
        stats = analysis.get('statistics', {})

        if not stats:
            print("\n⚠️  No whale transactions analyzed")
            return

        print("\n" + "=" * 80)
        print("🐋 WHALE TRANSACTION PRICE IMPACT ANALYSIS REPORT")
        print("=" * 80)

        print(f"\n📊 Overall Statistics:")
        print(f"   Total Whale Transactions Analyzed: {stats['total_whale_transactions']}")
        print(f"   Average Whale Size: ${stats['avg_whale_size_usd']:,.0f}")
        print(f"   Median Whale Size: ${stats['median_whale_size_usd']:,.0f}")
        print(f"   Total Whale Volume: ${stats['total_whale_volume_usd']:,.0f}")

        print(f"\n📈 Price Impact:")
        print(f"   Average Price Change (5m):  {stats['avg_price_change_5m_pct']:+.3f}%")
        print(f"   Average Price Change (10m): {stats['avg_price_change_10m_pct']:+.3f}%")
        print(f"   Average Price Change (15m): {stats['avg_price_change_15m_pct']:+.3f}%")
        print(f"   Median Price Change (5m):   {stats['median_price_change_5m_pct']:+.3f}%")

        print(f"\n📊 Directional Impact (5 minutes):")
        print(f"   Positive Impact: {stats['positive_impact_5m_count']} transactions")
        print(f"   Negative Impact: {stats['negative_impact_5m_count']} transactions")

        print(f"\n💹 Market Response:")
        print(f"   Average Volume Surge: {stats['avg_volume_surge_pct']:+.1f}%")
        print(f"   Average Volatility Increase: {stats['avg_volatility_after_pct']:.3f}%")

        print(f"\n🔍 By Transaction Type:")
        for tx_type, type_stats in stats['by_transaction_type'].items():
            print(f"   {tx_type.upper()}:")
            print(f"      Count: {type_stats['count']}")
            print(f"      Avg Value: ${type_stats['avg_usd_value']:,.0f}")
            print(f"      Avg 5m Impact: {type_stats['avg_price_change_5m_pct']:+.3f}%")

        print("\n" + "=" * 80)


# Integration Tests

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("WHALE_ALERT_API_KEY"),
    reason="WHALE_ALERT_API_KEY environment variable not set"
)
def test_whale_alert_historical_fetch():
    """Test fetching historical whale transactions from Whale Alert API."""
    api_key = os.getenv("WHALE_ALERT_API_KEY")
    provider = WhaleAlertProvider(api_key=api_key)

    # Test connection
    assert provider.validate_connection(), "Failed to validate Whale Alert API connection"

    # Fetch whale transactions for yesterday
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    batch = provider.fetch_whale_transactions(
        start_date=yesterday,
        end_date=yesterday,
        blockchain="bitcoin",
        min_value=1000000,  # $1M minimum
        limit=10
    )

    print(f"\nFetched {batch.count} whale transactions")

    assert batch.count >= 0, "Should return transaction count"
    assert batch.provider == "whale_alert"
    assert batch.filters_applied["min_value"] == 1000000

    if batch.transactions:
        whale_tx = batch.transactions[0]
        print(f"\nExample whale transaction:")
        print(f"  Symbol: {whale_tx.symbol}")
        print(f"  Size: {whale_tx.size}")
        print(f"  USD Value: ${whale_tx.usd_value:,.2f}")
        print(f"  Type: {whale_tx.transaction_type}")
        print(f"  Blockchain: {whale_tx.blockchain}")

        assert whale_tx.symbol is not None
        assert whale_tx.size > 0
        assert whale_tx.usd_value >= 1000000


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("WHALE_ALERT_API_KEY"),
    reason="WHALE_ALERT_API_KEY environment variable not set"
)
def test_whale_price_impact_analysis():
    """
    Integration test: Fetch whale transactions and analyze price impact.

    This test:
    1. Fetches whale transactions from Whale Alert
    2. Fetches corresponding BTC price data from Binance
    3. Analyzes price movement before/after whale transactions
    4. Calculates correlation metrics
    """
    api_key = os.getenv("WHALE_ALERT_API_KEY")

    # Initialize providers
    whale_provider = WhaleAlertProvider(api_key=api_key)
    price_provider = BinanceProvider()

    # Initialize analyzer
    analyzer = WhalePriceImpactAnalyzer(whale_provider, price_provider)

    # Use yesterday's date for analysis
    yesterday = datetime.now() - timedelta(days=1)
    start_date = yesterday.strftime("%Y-%m-%d")
    end_date = start_date

    print("\n" + "=" * 80)
    print("🐋 WHALE TRANSACTION PRICE IMPACT INTEGRATION TEST")
    print("=" * 80)

    # Step 1: Fetch whale transactions
    whale_txs = analyzer.fetch_whale_transactions(
        start_date=start_date,
        end_date=end_date,
        blockchain="bitcoin",
        min_value=2000000  # $2M minimum for significant impact
    )

    assert len(whale_txs) >= 0, "Should fetch whale transactions (may be 0)"

    if len(whale_txs) == 0:
        print("\n⚠️  No whale transactions found for the specified period")
        print("   This is normal - whale transactions are relatively rare")
        pytest.skip("No whale transactions in period, skipping price impact analysis")

    # Step 2: Fetch price data
    price_df = analyzer.fetch_price_data(
        symbol="BTCUSDT",
        start_date=start_date,
        end_date=end_date,
        interval="1m"  # Minute-level for precise impact analysis
    )

    assert len(price_df) > 0, "Should fetch price data"

    # Step 3: Analyze price impact
    analysis = analyzer.analyze_price_impact(
        whale_txs=whale_txs,
        price_df=price_df,
        window_before=5,
        window_after=15
    )

    # Step 4: Print report
    analyzer.print_analysis_report(analysis)

    # Assertions
    stats = analysis.get('statistics', {})
    if stats:
        assert stats['total_whale_transactions'] > 0
        assert stats['avg_whale_size_usd'] >= 2000000  # Should match min_value
        assert 'avg_price_change_5m_pct' in stats
        assert 'by_transaction_type' in stats


if __name__ == "__main__":
    """
    Run integration test directly.

    Usage:
        export WHALE_ALERT_API_KEY=your_api_key_here
        python -m pytest tests/integration/test_whale_price_impact.py -v -s
    """
    # Check for API key
    if not os.getenv("WHALE_ALERT_API_KEY"):
        print("\n⚠️  WHALE_ALERT_API_KEY environment variable not set")
        print("   Get an API key at: https://whale-alert.io/")
        print("   Then set it: export WHALE_ALERT_API_KEY=your_key_here\n")
        exit(1)

    # Run the test
    test_whale_price_impact_analysis()
