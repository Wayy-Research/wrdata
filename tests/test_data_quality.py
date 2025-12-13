#!/usr/bin/env python3
"""
Data Quality Check Script for wrdata providers.

Tests each provider's ability to return valid data with proper timestamps.
"""

import polars as pl
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import traceback


def check_data_quality(df: pl.DataFrame, provider_name: str) -> Dict[str, Any]:
    """
    Check data quality for a DataFrame returned by a provider.

    Args:
        df: DataFrame to check
        provider_name: Name of the provider for logging

    Returns:
        Dictionary with quality metrics
    """
    result = {
        'provider': provider_name,
        'row_count': len(df),
        'columns': list(df.columns),
        'issues': [],
        'timestamp_info': {},
        'numeric_info': {},
        'valid': True
    }

    if df.is_empty():
        result['issues'].append('Empty DataFrame')
        result['valid'] = False
        return result

    # Check for timestamp column
    timestamp_cols = [c for c in df.columns if c.lower() in ['timestamp', 'date', 'datetime']]
    if not timestamp_cols:
        result['issues'].append('No timestamp column found')
        result['valid'] = False
    else:
        ts_col = timestamp_cols[0]
        result['timestamp_info']['column'] = ts_col
        result['timestamp_info']['dtype'] = str(df[ts_col].dtype)

        # Check for null timestamps
        null_count = df[ts_col].null_count()
        result['timestamp_info']['null_count'] = null_count
        if null_count > 0:
            result['issues'].append(f'{null_count} null timestamps ({null_count/len(df)*100:.1f}%)')
            result['valid'] = False

        # Check timestamp range
        try:
            if df[ts_col].dtype == pl.Datetime or str(df[ts_col].dtype).startswith('Datetime'):
                non_null = df.filter(pl.col(ts_col).is_not_null())
                if len(non_null) > 0:
                    result['timestamp_info']['min'] = str(non_null[ts_col].min())
                    result['timestamp_info']['max'] = str(non_null[ts_col].max())
        except Exception as e:
            result['timestamp_info']['parse_error'] = str(e)

    # Check numeric columns
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        if col in df.columns:
            col_info = {
                'dtype': str(df[col].dtype),
                'null_count': df[col].null_count(),
            }

            # Get stats for non-null values
            non_null = df.filter(pl.col(col).is_not_null())
            if len(non_null) > 0:
                col_info['min'] = float(non_null[col].min())
                col_info['max'] = float(non_null[col].max())
                col_info['mean'] = float(non_null[col].mean())

            result['numeric_info'][col] = col_info

            if col_info['null_count'] > 0:
                result['issues'].append(f'{col}: {col_info["null_count"]} nulls')

    return result


def test_yfinance_provider():
    """Test YFinance provider with stocks and crypto."""
    print("\n" + "="*60)
    print("Testing YFinance Provider")
    print("="*60)

    from wrdata import DataStream
    stream = DataStream()

    results = []

    # Test stock data (daily)
    print("\n[1] Testing AAPL daily data...")
    try:
        df = stream.get("AAPL", start="2024-01-01", end="2024-12-01", interval="1d", provider="yfinance")
        result = check_data_quality(df, "yfinance_stock_daily")
        results.append(result)
        print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
        print(f"   Columns: {result['columns']}")
        print(f"   Timestamp info: {result['timestamp_info']}")
        if result['issues']:
            print(f"   Issues: {result['issues']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        traceback.print_exc()
        results.append({'provider': 'yfinance_stock_daily', 'valid': False, 'issues': [str(e)]})

    # Test stock data (intraday 1m)
    print("\n[2] Testing AAPL 1m intraday data (last 7 days)...")
    try:
        end = datetime.now()
        start = end - timedelta(days=7)
        df = stream.get(
            "AAPL",
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1m",
            provider="yfinance"
        )
        result = check_data_quality(df, "yfinance_stock_1m")
        results.append(result)
        print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
        print(f"   Timestamp info: {result['timestamp_info']}")
        if result['issues']:
            print(f"   Issues: {result['issues']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append({'provider': 'yfinance_stock_1m', 'valid': False, 'issues': [str(e)]})

    # Test crypto via yfinance
    print("\n[3] Testing BTC-USD via yfinance...")
    try:
        df = stream.get("BTC-USD", start="2024-01-01", end="2024-12-01", interval="1d", provider="yfinance")
        result = check_data_quality(df, "yfinance_crypto_daily")
        results.append(result)
        print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
        print(f"   Timestamp info: {result['timestamp_info']}")
        if result['issues']:
            print(f"   Issues: {result['issues']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append({'provider': 'yfinance_crypto_daily', 'valid': False, 'issues': [str(e)]})

    return results


def test_coinbase_provider():
    """Test Coinbase provider with crypto pairs."""
    print("\n" + "="*60)
    print("Testing Coinbase Provider")
    print("="*60)

    from wrdata import DataStream
    stream = DataStream()

    results = []

    # Test daily BTC
    print("\n[1] Testing BTC-USD daily data...")
    try:
        df = stream.get("BTC-USD", start="2024-01-01", end="2024-12-01", interval="1d", provider="coinbase")
        result = check_data_quality(df, "coinbase_daily")
        results.append(result)
        print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
        print(f"   Columns: {result['columns']}")
        print(f"   Timestamp info: {result['timestamp_info']}")
        if result['issues']:
            print(f"   Issues: {result['issues']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append({'provider': 'coinbase_daily', 'valid': False, 'issues': [str(e)]})

    # Test 1h ETH
    print("\n[2] Testing ETH-USD 1h data...")
    try:
        df = stream.get("ETH-USD", start="2024-11-01", end="2024-12-01", interval="1h", provider="coinbase")
        result = check_data_quality(df, "coinbase_1h")
        results.append(result)
        print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
        print(f"   Timestamp info: {result['timestamp_info']}")
        if result['issues']:
            print(f"   Issues: {result['issues']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append({'provider': 'coinbase_1h', 'valid': False, 'issues': [str(e)]})

    return results


def test_kraken_provider():
    """Test Kraken provider."""
    print("\n" + "="*60)
    print("Testing Kraken Provider")
    print("="*60)

    from wrdata import DataStream
    stream = DataStream()

    results = []

    # Test BTC/USD
    print("\n[1] Testing XBTUSD daily data...")
    try:
        df = stream.get("XBT/USD", start="2024-01-01", end="2024-12-01", interval="1d", provider="kraken")
        result = check_data_quality(df, "kraken_daily")
        results.append(result)
        print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
        print(f"   Columns: {result['columns']}")
        print(f"   Timestamp info: {result['timestamp_info']}")
        if result['issues']:
            print(f"   Issues: {result['issues']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append({'provider': 'kraken_daily', 'valid': False, 'issues': [str(e)]})

    return results


def test_coingecko_provider():
    """Test CoinGecko provider."""
    print("\n" + "="*60)
    print("Testing CoinGecko Provider")
    print("="*60)

    from wrdata import DataStream
    stream = DataStream()

    results = []

    # Test bitcoin
    print("\n[1] Testing bitcoin market data...")
    try:
        df = stream.get("bitcoin", start="2024-01-01", end="2024-12-01", interval="1d", provider="coingecko")
        result = check_data_quality(df, "coingecko_daily")
        results.append(result)
        print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
        print(f"   Columns: {result['columns']}")
        print(f"   Timestamp info: {result['timestamp_info']}")
        if result['issues']:
            print(f"   Issues: {result['issues']}")
    except Exception as e:
        print(f"   ERROR: {e}")
        results.append({'provider': 'coingecko_daily', 'valid': False, 'issues': [str(e)]})

    return results


def test_ccxt_providers():
    """Test CCXT-based providers (binance, kucoin, etc.)."""
    print("\n" + "="*60)
    print("Testing CCXT Providers")
    print("="*60)

    from wrdata import DataStream
    stream = DataStream()

    results = []

    # List of CCXT providers to test
    ccxt_providers = [
        ('ccxt_kucoin', 'BTC/USDT'),
        ('ccxt_okx', 'BTC/USDT'),
        ('ccxt_gateio', 'BTC/USDT'),
        ('ccxt_bitfinex', 'BTC/USD'),
    ]

    for provider_name, symbol in ccxt_providers:
        print(f"\n[{provider_name}] Testing {symbol} daily data...")
        try:
            if provider_name in stream.providers:
                df = stream.get(symbol, start="2024-11-01", end="2024-12-01", interval="1d", provider=provider_name)
                result = check_data_quality(df, provider_name)
                results.append(result)
                print(f"   Rows: {result['row_count']}, Valid: {result['valid']}")
                print(f"   Timestamp info: {result['timestamp_info']}")
                if result['issues']:
                    print(f"   Issues: {result['issues']}")
            else:
                print(f"   SKIPPED: Provider not available")
                results.append({'provider': provider_name, 'valid': False, 'issues': ['Provider not available']})
        except Exception as e:
            print(f"   ERROR: {e}")
            results.append({'provider': provider_name, 'valid': False, 'issues': [str(e)]})

    return results


def print_summary(all_results: List[Dict[str, Any]]):
    """Print summary of all test results."""
    print("\n" + "="*60)
    print("DATA QUALITY SUMMARY")
    print("="*60)

    valid_count = sum(1 for r in all_results if r.get('valid', False))
    total_count = len(all_results)

    print(f"\nOverall: {valid_count}/{total_count} tests passed")
    print("\nDetailed Results:")
    print("-"*60)

    for result in all_results:
        status = "PASS" if result.get('valid', False) else "FAIL"
        provider = result.get('provider', 'unknown')
        row_count = result.get('row_count', 0)
        issues = result.get('issues', [])

        print(f"\n{provider}:")
        print(f"  Status: {status}")
        print(f"  Rows: {row_count}")
        if issues:
            print(f"  Issues:")
            for issue in issues:
                print(f"    - {issue}")

        ts_info = result.get('timestamp_info', {})
        if ts_info:
            print(f"  Timestamp column: {ts_info.get('column', 'N/A')}")
            print(f"  Timestamp dtype: {ts_info.get('dtype', 'N/A')}")
            print(f"  Null timestamps: {ts_info.get('null_count', 'N/A')}")

    # Summary of providers with issues
    failed = [r for r in all_results if not r.get('valid', False)]
    if failed:
        print("\n" + "="*60)
        print("PROVIDERS WITH ISSUES:")
        print("="*60)
        for r in failed:
            print(f"  - {r.get('provider', 'unknown')}: {', '.join(r.get('issues', ['Unknown error']))}")


def main():
    """Run all data quality tests."""
    print("\n" + "="*60)
    print("WRDATA PROVIDER DATA QUALITY CHECK")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")

    all_results = []

    # Test each provider
    all_results.extend(test_yfinance_provider())
    all_results.extend(test_coinbase_provider())
    all_results.extend(test_kraken_provider())
    all_results.extend(test_coingecko_provider())
    all_results.extend(test_ccxt_providers())

    # Print summary
    print_summary(all_results)

    print(f"\nCompleted at: {datetime.now().isoformat()}")

    return all_results


if __name__ == "__main__":
    main()
