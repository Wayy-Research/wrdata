#!/usr/bin/env python3
"""
Provider Setup Script for wrdata.

This script helps you:
1. Test which providers work without credentials
2. Set up API keys for providers that need them
3. Save credentials to .env file
4. Verify all providers work correctly
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import getpass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# Provider information
PROVIDERS = {
    # FREE - No API key required
    "yfinance": {
        "name": "Yahoo Finance",
        "requires_key": False,
        "test_symbol": "AAPL",
        "asset_type": "equity",
        "description": "Free stock/ETF/crypto data, no limits",
    },
    "coinbase": {
        "name": "Coinbase",
        "requires_key": False,
        "test_symbol": "BTC-USD",
        "asset_type": "crypto",
        "description": "Free crypto OHLCV data",
    },
    "kraken": {
        "name": "Kraken",
        "requires_key": False,
        "test_symbol": "XXBTZUSD",
        "asset_type": "crypto",
        "description": "Free crypto OHLCV data",
    },
    # CCXT exchanges (free public API)
    "ccxt_kucoin": {
        "name": "KuCoin (CCXT)",
        "requires_key": False,
        "test_symbol": "BTC/USDT",
        "asset_type": "crypto",
        "description": "Free crypto data via CCXT",
    },
    "ccxt_okx": {
        "name": "OKX (CCXT)",
        "requires_key": False,
        "test_symbol": "BTC/USDT",
        "asset_type": "crypto",
        "description": "Free crypto data via CCXT",
    },
    "ccxt_gateio": {
        "name": "Gate.io (CCXT)",
        "requires_key": False,
        "test_symbol": "BTC/USDT",
        "asset_type": "crypto",
        "description": "Free crypto data via CCXT",
    },
    "ccxt_bitfinex": {
        "name": "Bitfinex (CCXT)",
        "requires_key": False,
        "test_symbol": "BTC/USD",
        "asset_type": "crypto",
        "description": "Free crypto data via CCXT",
    },

    # FREE - API key required (free to get)
    "alphavantage": {
        "name": "Alpha Vantage",
        "requires_key": True,
        "env_vars": ["ALPHA_VANTAGE_API_KEY"],
        "test_symbol": "AAPL",
        "asset_type": "equity",
        "description": "Free stock data (5 calls/min, 500/day)",
        "signup_url": "https://www.alphavantage.co/support/#api-key",
    },
    "fred": {
        "name": "FRED (Federal Reserve)",
        "requires_key": True,
        "env_vars": ["FRED_API_KEY"],
        "test_symbol": "GDP",
        "asset_type": "economic",
        "description": "Free economic data (unlimited)",
        "signup_url": "https://fred.stlouisfed.org/docs/api/api_key.html",
    },
    "finnhub": {
        "name": "Finnhub",
        "requires_key": True,
        "env_vars": ["FINNHUB_API_KEY"],
        "test_symbol": "AAPL",
        "asset_type": "equity",
        "description": "Free stock data + WebSocket (60 calls/min)",
        "signup_url": "https://finnhub.io/register",
    },
    "twelvedata": {
        "name": "Twelve Data",
        "requires_key": True,
        "env_vars": ["TWELVE_DATA_API_KEY"],
        "test_symbol": "AAPL",
        "asset_type": "equity",
        "description": "Free stock/forex/crypto (8 calls/min)",
        "signup_url": "https://twelvedata.com/apikey",
    },
    "coingecko": {
        "name": "CoinGecko",
        "requires_key": True,
        "env_vars": ["COINGECKO_API_KEY"],
        "test_symbol": "bitcoin",
        "asset_type": "crypto",
        "description": "Free crypto market data (requires free API key)",
        "signup_url": "https://www.coingecko.com/en/api/pricing",
    },
    "tiingo": {
        "name": "Tiingo",
        "requires_key": True,
        "env_vars": ["TIINGO_API_KEY"],
        "test_symbol": "AAPL",
        "asset_type": "equity",
        "description": "Freemium stock/crypto data",
        "signup_url": "https://api.tiingo.com/account/api/token",
    },

    # BROKER - Free paper trading
    "alpaca": {
        "name": "Alpaca",
        "requires_key": True,
        "env_vars": ["ALPACA_API_KEY", "ALPACA_API_SECRET"],
        "test_symbol": "AAPL",
        "asset_type": "equity",
        "description": "Free paper trading + real-time IEX data",
        "signup_url": "https://app.alpaca.markets/signup",
    },
}


def load_existing_env() -> Dict[str, str]:
    """Load existing .env file if it exists."""
    env_path = Path(__file__).parent.parent / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def save_env_file(env_vars: Dict[str, str]):
    """Save credentials to .env file."""
    env_path = Path(__file__).parent.parent / ".env"

    # Read existing file to preserve comments and structure
    lines = []
    if env_path.exists():
        with open(env_path) as f:
            lines = f.readlines()

    # Update values in existing lines
    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in env_vars:
                new_lines.append(f"{key}={env_vars[key]}\n")
                updated_keys.add(key)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # Add any new keys that weren't in the file
    for key, value in env_vars.items():
        if key not in updated_keys and value:
            new_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)

    print(f"\nCredentials saved to: {env_path}")


def test_provider(provider_name: str, stream) -> Dict[str, Any]:
    """Test a single provider and return results."""
    info = PROVIDERS.get(provider_name, {})
    result = {
        "provider": provider_name,
        "name": info.get("name", provider_name),
        "success": False,
        "rows": 0,
        "error": None,
    }

    try:
        # Check if provider is available
        if provider_name not in stream.providers:
            result["error"] = "Provider not initialized"
            return result

        # Test fetch
        test_symbol = info.get("test_symbol", "AAPL")
        end = datetime.now()
        start = end - timedelta(days=30)

        df = stream.get(
            test_symbol,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1d",
            provider=provider_name
        )

        if df is not None and len(df) > 0:
            result["success"] = True
            result["rows"] = len(df)
        else:
            result["error"] = "No data returned"

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


def test_all_providers(env_vars: Dict[str, str]) -> List[Dict[str, Any]]:
    """Test all configured providers."""
    print("\n" + "="*60)
    print("TESTING PROVIDERS")
    print("="*60)

    # Set environment variables
    for key, value in env_vars.items():
        if value:
            os.environ[key] = value

    # Import after setting env vars
    from wrdata import DataStream

    # Initialize stream with all available providers
    stream = DataStream(
        alphavantage_key=env_vars.get("ALPHA_VANTAGE_API_KEY"),
        fred_key=env_vars.get("FRED_API_KEY"),
        finnhub_key=env_vars.get("FINNHUB_API_KEY"),
        alpaca_key=env_vars.get("ALPACA_API_KEY"),
        alpaca_secret=env_vars.get("ALPACA_API_SECRET"),
    )

    results = []

    # Test each provider
    for provider_name, info in PROVIDERS.items():
        print(f"\nTesting {info['name']}...", end=" ", flush=True)

        # Skip if requires key and not configured
        if info.get("requires_key"):
            env_var = info.get("env_vars", [])[0] if info.get("env_vars") else None
            if env_var and not env_vars.get(env_var):
                print("SKIPPED (no API key)")
                results.append({
                    "provider": provider_name,
                    "name": info["name"],
                    "success": False,
                    "error": "No API key configured",
                    "rows": 0,
                })
                continue

        result = test_provider(provider_name, stream)
        results.append(result)

        if result["success"]:
            print(f"OK ({result['rows']} rows)")
        else:
            print(f"FAILED: {result['error']}")

    return results


def print_summary(results: List[Dict[str, Any]]):
    """Print test summary."""
    print("\n" + "="*60)
    print("PROVIDER STATUS SUMMARY")
    print("="*60)

    working = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\nWorking: {len(working)}/{len(results)} providers")

    if working:
        print("\n[WORKING]")
        for r in working:
            print(f"  + {r['name']}: {r['rows']} rows")

    if failed:
        print("\n[NEEDS ATTENTION]")
        for r in failed:
            print(f"  - {r['name']}: {r['error']}")

    return len(working), len(failed)


def interactive_setup():
    """Interactive setup wizard."""
    print("\n" + "="*60)
    print("WRDATA PROVIDER SETUP WIZARD")
    print("="*60)
    print("\nThis will help you configure API keys for data providers.")
    print("Most providers offer FREE API keys with generous limits.\n")

    # Load existing credentials
    env_vars = load_existing_env()
    print(f"Found existing .env file with {len(env_vars)} settings.\n")

    # Group providers
    no_key_providers = {k: v for k, v in PROVIDERS.items() if not v.get("requires_key")}
    free_key_providers = {k: v for k, v in PROVIDERS.items()
                         if v.get("requires_key") and "signup_url" in v
                         and k not in ["alpaca"]}
    broker_providers = {k: v for k, v in PROVIDERS.items() if k == "alpaca"}

    print("="*60)
    print("STEP 1: Testing No-Key Providers")
    print("="*60)
    print(f"\n{len(no_key_providers)} providers work without any API key:")
    for name, info in no_key_providers.items():
        print(f"  - {info['name']}: {info['description']}")

    print("\n" + "="*60)
    print("STEP 2: Free API Key Providers")
    print("="*60)
    print("\nThe following providers need FREE API keys:")

    for provider_name, info in free_key_providers.items():
        env_var = info.get("env_vars", [])[0] if info.get("env_vars") else None
        current_value = env_vars.get(env_var, "") if env_var else ""

        print(f"\n--- {info['name']} ---")
        print(f"Description: {info['description']}")
        print(f"Sign up: {info.get('signup_url', 'N/A')}")

        if current_value:
            print(f"Current key: {current_value[:8]}...{current_value[-4:]}")
            update = input("Update this key? (y/N): ").strip().lower()
            if update != 'y':
                continue

        if env_var:
            new_key = input(f"Enter {env_var} (or press Enter to skip): ").strip()
            if new_key:
                env_vars[env_var] = new_key

    print("\n" + "="*60)
    print("STEP 3: Broker Providers (Optional)")
    print("="*60)

    for provider_name, info in broker_providers.items():
        print(f"\n--- {info['name']} ---")
        print(f"Description: {info['description']}")
        print(f"Sign up: {info.get('signup_url', 'N/A')}")

        setup = input(f"Set up {info['name']}? (y/N): ").strip().lower()
        if setup == 'y':
            for env_var in info.get("env_vars", []):
                current = env_vars.get(env_var, "")
                if current:
                    print(f"Current {env_var}: {current[:8]}...")
                new_val = input(f"Enter {env_var} (or Enter to keep): ").strip()
                if new_val:
                    env_vars[env_var] = new_val

    # Save credentials
    print("\n" + "="*60)
    print("STEP 4: Save Configuration")
    print("="*60)

    save = input("\nSave credentials to .env file? (Y/n): ").strip().lower()
    if save != 'n':
        save_env_file(env_vars)

    # Test all providers
    print("\n" + "="*60)
    print("STEP 5: Testing All Providers")
    print("="*60)

    test = input("\nTest all providers now? (Y/n): ").strip().lower()
    if test != 'n':
        results = test_all_providers(env_vars)
        working, failed = print_summary(results)

        print(f"\n{'='*60}")
        print(f"Setup complete! {working} providers working.")
        print(f"{'='*60}")

    return env_vars


def quick_test():
    """Quick test without interactive setup."""
    print("\n" + "="*60)
    print("WRDATA QUICK PROVIDER TEST")
    print("="*60)

    env_vars = load_existing_env()
    results = test_all_providers(env_vars)
    working, failed = print_summary(results)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Setup and test wrdata providers")
    parser.add_argument("--test", action="store_true", help="Quick test without setup")
    parser.add_argument("--setup", action="store_true", help="Interactive setup wizard")

    args = parser.parse_args()

    if args.test:
        quick_test()
    else:
        interactive_setup()
