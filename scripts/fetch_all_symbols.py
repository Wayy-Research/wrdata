#!/usr/bin/env python3
"""
Fetch all available symbols from every provider in wrdata.

This script extracts symbols from:
- Crypto exchanges (via CCXT): Binance, Kraken, KuCoin, OKX, Bybit, Bitfinex,
  Gate.io, Gemini, Huobi, Coinbase, etc.
- Coinbase Advanced Trade API
- Stock/Equity providers: Finnhub, Polygon, Alpha Vantage, Tiingo, IEX Cloud, Alpaca
- Alternative data: FRED, CoinGecko, CryptoCompare, Messari, Kalshi, Deribit

Output: CSV files in ./symbols/ directory, one per provider.

Usage:
    python scripts/fetch_all_symbols.py

    # Or with custom output directory
    python scripts/fetch_all_symbols.py --output /path/to/output

    # Or fetch only specific providers
    python scripts/fetch_all_symbols.py --providers binance,coinbase,finnhub
"""

import os
import sys
import csv
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from wrdata.core.config import load_settings, settings


# =============================================================================
# CCXT-Based Crypto Exchanges
# =============================================================================

# US-friendly exchanges first, then international
CCXT_EXCHANGES = [
    # US-friendly
    'binanceus', 'kraken', 'gemini', 'coinbase', 'bitstamp',
    # International (may be restricted in US)
    'kucoin', 'okx', 'bitfinex', 'gateio', 'huobi',
    'bitget', 'mexc', 'phemex',
    # Note: bybit removed - geo-blocked in US
]

def fetch_ccxt_symbols(exchange_id: str) -> Dict[str, Any]:
    """Fetch all symbols from a CCXT-supported exchange."""
    try:
        import ccxt

        if not hasattr(ccxt, exchange_id):
            return {'success': False, 'error': f'Exchange {exchange_id} not supported by CCXT'}

        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({'enableRateLimit': True})

        markets = exchange.load_markets()

        symbols = []
        for symbol, market in markets.items():
            symbols.append({
                'symbol': symbol,
                'base': market.get('base', ''),
                'quote': market.get('quote', ''),
                'type': market.get('type', ''),
                'active': market.get('active', True),
                'spot': market.get('spot', False),
                'futures': market.get('future', False),
                'swap': market.get('swap', False),
            })

        return {
            'success': True,
            'provider': f'ccxt_{exchange_id}',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': f'ccxt_{exchange_id}', 'error': str(e)}


# =============================================================================
# Coinbase Advanced Trade API
# =============================================================================

def fetch_coinbase_advanced_symbols() -> Dict[str, Any]:
    """Fetch all products from Coinbase Advanced Trade API."""
    try:
        from wrdata.providers.coinbase_advanced_provider import CoinbaseAdvancedProvider

        provider = CoinbaseAdvancedProvider(
            api_key=settings.COINBASE_KEY,
            api_secret=settings.COINBASE_PRIVATE_KEY
        )

        result = provider.get_products()

        if not result.get('success'):
            # Try unauthenticated
            url = "https://api.coinbase.com/api/v3/brokerage/products"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            result = {'success': True, 'data': response.json()}

        products = result.get('data', {}).get('products', [])

        symbols = []
        for p in products:
            symbols.append({
                'symbol': p.get('product_id', ''),
                'base': p.get('base_currency_id', ''),
                'quote': p.get('quote_currency_id', ''),
                'type': p.get('product_type', ''),
                'status': p.get('status', ''),
                'trading_disabled': p.get('trading_disabled', False),
            })

        return {
            'success': True,
            'provider': 'coinbase_advanced',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'coinbase_advanced', 'error': str(e)}


# =============================================================================
# Stock/Equity Providers
# =============================================================================

def fetch_finnhub_symbols() -> Dict[str, Any]:
    """Fetch all stock symbols from Finnhub."""
    try:
        api_key = settings.FINNHUB_API_KEY
        if not api_key:
            return {'success': False, 'provider': 'finnhub', 'error': 'No API key configured'}

        symbols = []

        # US stocks
        exchanges = ['US', 'NYSE', 'NASDAQ']
        for exchange in exchanges:
            url = f"https://finnhub.io/api/v1/stock/symbol?exchange={exchange}&token={api_key}"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    symbols.append({
                        'symbol': item.get('symbol', ''),
                        'name': item.get('description', ''),
                        'type': item.get('type', ''),
                        'exchange': exchange,
                        'currency': item.get('currency', ''),
                        'figi': item.get('figi', ''),
                    })
            time.sleep(0.5)  # Rate limiting

        # Deduplicate
        seen = set()
        unique = []
        for s in symbols:
            if s['symbol'] not in seen:
                seen.add(s['symbol'])
                unique.append(s)

        return {
            'success': True,
            'provider': 'finnhub',
            'count': len(unique),
            'symbols': unique
        }
    except Exception as e:
        return {'success': False, 'provider': 'finnhub', 'error': str(e)}


def fetch_polygon_symbols() -> Dict[str, Any]:
    """Fetch all tickers from Polygon.io."""
    try:
        api_key = settings.POLYGON_API_KEY
        if not api_key:
            return {'success': False, 'provider': 'polygon', 'error': 'No API key configured'}

        symbols = []
        cursor = None

        while True:
            url = f"https://api.polygon.io/v3/reference/tickers?active=true&limit=1000&apiKey={api_key}"
            if cursor:
                url += f"&cursor={cursor}"

            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                break

            data = response.json()
            results = data.get('results', [])

            for item in results:
                symbols.append({
                    'symbol': item.get('ticker', ''),
                    'name': item.get('name', ''),
                    'type': item.get('type', ''),
                    'market': item.get('market', ''),
                    'locale': item.get('locale', ''),
                    'currency': item.get('currency_name', ''),
                    'exchange': item.get('primary_exchange', ''),
                })

            cursor = data.get('next_cursor')
            if not cursor or not results:
                break

            time.sleep(0.2)  # Rate limiting

        return {
            'success': True,
            'provider': 'polygon',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'polygon', 'error': str(e)}


def fetch_alpaca_symbols() -> Dict[str, Any]:
    """Fetch all assets from Alpaca."""
    try:
        api_key = settings.ALPACA_API_KEY
        api_secret = settings.ALPACA_API_SECRET

        if not api_key or not api_secret:
            return {'success': False, 'provider': 'alpaca', 'error': 'No API key configured'}

        # Use paper trading endpoint
        url = "https://paper-api.alpaca.markets/v2/assets"
        headers = {
            'APCA-API-KEY-ID': api_key,
            'APCA-API-SECRET-KEY': api_secret,
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        symbols = []
        for item in data:
            symbols.append({
                'symbol': item.get('symbol', ''),
                'name': item.get('name', ''),
                'exchange': item.get('exchange', ''),
                'asset_class': item.get('class', ''),
                'status': item.get('status', ''),
                'tradable': item.get('tradable', False),
                'shortable': item.get('shortable', False),
                'fractionable': item.get('fractionable', False),
            })

        return {
            'success': True,
            'provider': 'alpaca',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'alpaca', 'error': str(e)}


def fetch_tiingo_symbols() -> Dict[str, Any]:
    """Fetch all supported tickers from Tiingo."""
    try:
        api_key = settings.TIINGO_API_KEY
        if not api_key:
            return {'success': False, 'provider': 'tiingo', 'error': 'No API key configured'}

        # Tiingo provides a CSV of all supported tickers
        url = f"https://api.tiingo.com/iex?token={api_key}"
        headers = {'Content-Type': 'application/json'}

        # Get supported tickers list
        tickers_url = "https://api.tiingo.com/tiingo/daily/meta"
        response = requests.get(
            "https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip",
            timeout=60
        )

        symbols = []
        if response.status_code == 200:
            import zipfile
            import io

            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                for filename in z.namelist():
                    if filename.endswith('.csv'):
                        with z.open(filename) as f:
                            import csv
                            reader = csv.DictReader(io.TextIOWrapper(f, 'utf-8'))
                            for row in reader:
                                symbols.append({
                                    'symbol': row.get('ticker', ''),
                                    'name': row.get('name', ''),
                                    'exchange': row.get('exchange', ''),
                                    'asset_type': row.get('assetType', ''),
                                    'price_currency': row.get('priceCurrency', ''),
                                    'start_date': row.get('startDate', ''),
                                    'end_date': row.get('endDate', ''),
                                })

        return {
            'success': True,
            'provider': 'tiingo',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'tiingo', 'error': str(e)}


def fetch_twelvedata_symbols() -> Dict[str, Any]:
    """Fetch all symbols from Twelve Data."""
    try:
        api_key = settings.TWELVE_DATA_API_KEY

        # Twelve Data has a free symbols endpoint
        url = "https://api.twelvedata.com/stocks"
        if api_key:
            url += f"?apikey={api_key}"

        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()

        symbols = []
        for item in data.get('data', []):
            symbols.append({
                'symbol': item.get('symbol', ''),
                'name': item.get('name', ''),
                'exchange': item.get('exchange', ''),
                'country': item.get('country', ''),
                'currency': item.get('currency', ''),
                'type': item.get('type', ''),
            })

        return {
            'success': True,
            'provider': 'twelvedata',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'twelvedata', 'error': str(e)}


def fetch_iexcloud_symbols() -> Dict[str, Any]:
    """Fetch all symbols from IEX Cloud."""
    try:
        api_key = os.environ.get('IEX_API_KEY') or os.environ.get('IEX_CLOUD_API_KEY')
        if not api_key:
            return {'success': False, 'provider': 'iexcloud', 'error': 'No API key configured'}

        url = f"https://cloud.iexapis.com/stable/ref-data/symbols?token={api_key}"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        symbols = []
        for item in data:
            symbols.append({
                'symbol': item.get('symbol', ''),
                'name': item.get('name', ''),
                'exchange': item.get('exchange', ''),
                'type': item.get('type', ''),
                'region': item.get('region', ''),
                'currency': item.get('currency', ''),
                'iex_id': item.get('iexId', ''),
            })

        return {
            'success': True,
            'provider': 'iexcloud',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'iexcloud', 'error': str(e)}


# =============================================================================
# Alternative Data Providers
# =============================================================================

def fetch_coingecko_symbols() -> Dict[str, Any]:
    """Fetch all coins from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/coins/list"
        headers = {}

        api_key = settings.COINGECKO_API_KEY
        if api_key:
            headers['x-cg-demo-api-key'] = api_key

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        symbols = []
        for item in data:
            symbols.append({
                'symbol': item.get('symbol', '').upper(),
                'id': item.get('id', ''),
                'name': item.get('name', ''),
            })

        return {
            'success': True,
            'provider': 'coingecko',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'coingecko', 'error': str(e)}


def fetch_fred_symbols() -> Dict[str, Any]:
    """Fetch popular FRED series IDs."""
    try:
        api_key = settings.FRED_API_KEY
        if not api_key:
            return {'success': False, 'provider': 'fred', 'error': 'No API key configured'}

        # FRED has thousands of series - fetch popular categories
        categories = [
            32991,   # GDP
            32992,   # Employment
            32455,   # Interest Rates
            32145,   # Inflation
            33060,   # Housing
        ]

        symbols = []

        for cat_id in categories:
            url = f"https://api.stlouisfed.org/fred/category/series?category_id={cat_id}&api_key={api_key}&file_type=json&limit=1000"

            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('seriess', []):
                    symbols.append({
                        'symbol': item.get('id', ''),
                        'name': item.get('title', ''),
                        'frequency': item.get('frequency', ''),
                        'units': item.get('units', ''),
                        'seasonal_adjustment': item.get('seasonal_adjustment', ''),
                        'last_updated': item.get('last_updated', ''),
                    })
            time.sleep(0.3)

        # Deduplicate
        seen = set()
        unique = []
        for s in symbols:
            if s['symbol'] not in seen:
                seen.add(s['symbol'])
                unique.append(s)

        return {
            'success': True,
            'provider': 'fred',
            'count': len(unique),
            'symbols': unique
        }
    except Exception as e:
        return {'success': False, 'provider': 'fred', 'error': str(e)}


# =============================================================================
# DEX Data Providers
# =============================================================================

# Major DEX networks to fetch pools from
DEX_NETWORKS = [
    'eth',          # Ethereum
    'bsc',          # BNB Chain
    'polygon_pos',  # Polygon
    'arbitrum',     # Arbitrum
    'optimism',     # Optimism
    'base',         # Base
    'avax',         # Avalanche
    'solana',       # Solana
    'fantom',       # Fantom
]


def fetch_geckoterminal_networks() -> Dict[str, Any]:
    """Fetch all supported networks from GeckoTerminal."""
    try:
        url = "https://api.geckoterminal.com/api/v2/networks"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        symbols = []
        for item in data.get('data', []):
            attrs = item.get('attributes', {})
            symbols.append({
                'network_id': item.get('id', ''),
                'name': attrs.get('name', ''),
                'coingecko_asset_platform_id': attrs.get('coingecko_asset_platform_id', ''),
            })

        return {
            'success': True,
            'provider': 'geckoterminal_networks',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'geckoterminal_networks', 'error': str(e)}


def fetch_geckoterminal_pools(network: str = 'eth') -> Dict[str, Any]:
    """Fetch top pools from a GeckoTerminal network."""
    try:
        symbols = []

        # Fetch multiple pages of pools
        for page in range(1, 6):  # Get top 5 pages (250 pools per network)
            url = f"https://api.geckoterminal.com/api/v2/networks/{network}/pools"
            params = {"page": page}

            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                break

            data = response.json()
            pools = data.get('data', [])

            if not pools:
                break

            for item in pools:
                attrs = item.get('attributes', {})
                pool_id = item.get('id', '')

                # Extract address from pool_id (format: network_address)
                address = pool_id.split('_', 1)[-1] if '_' in pool_id else pool_id

                symbols.append({
                    'pool_address': address,
                    'network': network,
                    'name': attrs.get('name', ''),
                    'dex': attrs.get('dex_id', ''),
                    'base_token': attrs.get('base_token_price_usd', ''),
                    'price_usd': attrs.get('base_token_price_usd', ''),
                    'volume_24h': attrs.get('volume_usd', {}).get('h24', 0) if isinstance(attrs.get('volume_usd'), dict) else 0,
                    'reserve_usd': attrs.get('reserve_in_usd', ''),
                    'pool_created_at': attrs.get('pool_created_at', ''),
                })

            time.sleep(2)  # Rate limit: 30 req/min

        return {
            'success': True,
            'provider': f'geckoterminal_{network}',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': f'geckoterminal_{network}', 'error': str(e)}


def fetch_dexscreener_trending() -> Dict[str, Any]:
    """Fetch trending pairs from DEX Screener via search."""
    try:
        # Search for major tokens to get active pairs
        search_terms = ['ETH', 'BTC', 'USDT', 'USDC', 'SOL', 'PEPE', 'DOGE', 'SHIB']
        all_pairs = []
        seen_addresses = set()

        for term in search_terms:
            url = f"https://api.dexscreener.com/latest/dex/search?q={term}"
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()
                pairs = data.get('pairs', [])

                for pair in pairs[:100]:  # Limit per search term
                    pair_addr = pair.get('pairAddress', '')
                    if pair_addr and pair_addr not in seen_addresses:
                        seen_addresses.add(pair_addr)

                        base_token = pair.get('baseToken', {})
                        quote_token = pair.get('quoteToken', {})

                        all_pairs.append({
                            'pair_address': pair_addr,
                            'chain': pair.get('chainId', ''),
                            'dex': pair.get('dexId', ''),
                            'base_symbol': base_token.get('symbol', ''),
                            'base_name': base_token.get('name', ''),
                            'base_address': base_token.get('address', ''),
                            'quote_symbol': quote_token.get('symbol', ''),
                            'quote_address': quote_token.get('address', ''),
                            'price_usd': pair.get('priceUsd', ''),
                            'price_native': pair.get('priceNative', ''),
                            'volume_24h': pair.get('volume', {}).get('h24', 0) if isinstance(pair.get('volume'), dict) else 0,
                            'liquidity_usd': pair.get('liquidity', {}).get('usd', 0) if isinstance(pair.get('liquidity'), dict) else 0,
                            'fdv': pair.get('fdv', ''),
                            'pair_created_at': pair.get('pairCreatedAt', ''),
                        })

            time.sleep(0.5)  # Rate limiting

        return {
            'success': True,
            'provider': 'dexscreener',
            'count': len(all_pairs),
            'symbols': all_pairs
        }
    except Exception as e:
        return {'success': False, 'provider': 'dexscreener', 'error': str(e)}


def fetch_messari_symbols() -> Dict[str, Any]:
    """Fetch all assets from Messari."""
    try:
        url = "https://data.messari.io/api/v2/assets?limit=500"

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        symbols = []
        for item in data.get('data', []):
            symbols.append({
                'symbol': item.get('symbol', ''),
                'id': item.get('id', ''),
                'name': item.get('name', ''),
                'slug': item.get('slug', ''),
            })

        return {
            'success': True,
            'provider': 'messari',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'messari', 'error': str(e)}


def fetch_kalshi_symbols() -> Dict[str, Any]:
    """Fetch all markets from Kalshi with RSA-PSS authentication."""
    try:
        import base64
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import serialization

        # Get credentials from settings or environment
        api_key = getattr(settings, 'KALSHI_KEY', None) or os.environ.get('KALSHI_KEY')
        private_key_str = getattr(settings, 'KALSHI_PRIVATE_KEY', None) or os.environ.get('KALSHI_PRIVATE_KEY')

        if not api_key or not private_key_str:
            return {'success': False, 'provider': 'kalshi', 'error': 'No KALSHI_KEY or KALSHI_PRIVATE_KEY configured'}

        # Normalize private key (handle escaped newlines)
        if '\\n' in private_key_str:
            private_key_str = private_key_str.replace('\\n', '\n')

        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_str.encode('utf-8'),
            password=None
        )

        # Build signature
        timestamp_ms = str(int(time.time() * 1000))
        method = "GET"
        path = "/trade-api/v2/markets"  # Sign without query params

        message = f"{timestamp_ms}{method}{path}"
        signature = private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH  # Kalshi requires DIGEST_LENGTH (32 bytes)
            ),
            hashes.SHA256()
        )
        sig_b64 = base64.b64encode(signature).decode('utf-8')

        headers = {
            'KALSHI-ACCESS-KEY': api_key,
            'KALSHI-ACCESS-SIGNATURE': sig_b64,
            'KALSHI-ACCESS-TIMESTAMP': timestamp_ms,
        }

        # Fetch markets with pagination
        # New Production API: https://api.elections.kalshi.com (as of 2024)
        # Old Production API: https://trading-api.kalshi.com (deprecated)
        base_url = "https://api.elections.kalshi.com"
        all_symbols = []
        cursor = None

        while True:
            url = f"{base_url}/trade-api/v2/markets?limit=1000"
            if cursor:
                url += f"&cursor={cursor}"

            # Re-sign for each request (timestamp changes)
            timestamp_ms = str(int(time.time() * 1000))
            message = f"{timestamp_ms}{method}{path}"
            signature = private_key.sign(
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH  # Kalshi requires DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
            headers['KALSHI-ACCESS-SIGNATURE'] = base64.b64encode(signature).decode('utf-8')
            headers['KALSHI-ACCESS-TIMESTAMP'] = timestamp_ms

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            markets = data.get('markets', [])
            for item in markets:
                all_symbols.append({
                    'symbol': item.get('ticker', ''),
                    'title': item.get('title', ''),
                    'subtitle': item.get('subtitle', ''),
                    'status': item.get('status', ''),
                    'category': item.get('category', ''),
                    'event_ticker': item.get('event_ticker', ''),
                    'yes_bid': item.get('yes_bid', ''),
                    'yes_ask': item.get('yes_ask', ''),
                    'no_bid': item.get('no_bid', ''),
                    'no_ask': item.get('no_ask', ''),
                    'volume': item.get('volume', ''),
                    'open_interest': item.get('open_interest', ''),
                    'close_time': item.get('close_time', ''),
                })

            cursor = data.get('cursor')
            if not cursor or not markets:
                break

            time.sleep(0.2)  # Rate limiting

        return {
            'success': True,
            'provider': 'kalshi',
            'count': len(all_symbols),
            'symbols': all_symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'kalshi', 'error': str(e)}


def fetch_deribit_symbols() -> Dict[str, Any]:
    """Fetch all instruments from Deribit."""
    try:
        symbols = []

        for currency in ['BTC', 'ETH']:
            url = f"https://www.deribit.com/api/v2/public/get_instruments?currency={currency}"

            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('result', []):
                    symbols.append({
                        'symbol': item.get('instrument_name', ''),
                        'base_currency': item.get('base_currency', ''),
                        'quote_currency': item.get('quote_currency', ''),
                        'kind': item.get('kind', ''),
                        'option_type': item.get('option_type', ''),
                        'strike': item.get('strike', ''),
                        'expiration': item.get('expiration_timestamp', ''),
                        'is_active': item.get('is_active', False),
                    })

        return {
            'success': True,
            'provider': 'deribit',
            'count': len(symbols),
            'symbols': symbols
        }
    except Exception as e:
        return {'success': False, 'provider': 'deribit', 'error': str(e)}


# =============================================================================
# Main Script
# =============================================================================

ALL_FETCHERS = {
    # Crypto via CCXT (centralized exchanges)
    **{f'ccxt_{ex}': lambda ex=ex: fetch_ccxt_symbols(ex) for ex in CCXT_EXCHANGES},

    # Direct crypto providers
    'coinbase_advanced': fetch_coinbase_advanced_symbols,
    'coingecko': fetch_coingecko_symbols,
    'deribit': fetch_deribit_symbols,

    # DEX providers (decentralized exchanges)
    'geckoterminal_networks': fetch_geckoterminal_networks,
    'dexscreener': fetch_dexscreener_trending,
    **{f'dex_{net}': lambda net=net: fetch_geckoterminal_pools(net) for net in DEX_NETWORKS},

    # Prediction markets
    'kalshi': fetch_kalshi_symbols,

    # Stock providers
    'finnhub': fetch_finnhub_symbols,
    'alpaca': fetch_alpaca_symbols,
    'twelvedata': fetch_twelvedata_symbols,

    # Economic data
    'fred': fetch_fred_symbols,

    # Removed: messari, polygon, tiingo, iexcloud (redundant), bybit (geo-blocked)
}


def save_to_csv(result: Dict[str, Any], output_dir: Path):
    """Save symbols to CSV file."""
    provider = result.get('provider', 'unknown')
    symbols = result.get('symbols', [])

    if not symbols:
        return

    output_file = output_dir / f"{provider}_symbols.csv"

    # Get all unique keys from symbols
    all_keys = set()
    for s in symbols:
        all_keys.update(s.keys())
    fieldnames = sorted(all_keys)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(symbols)

    print(f"  Saved {len(symbols):,} symbols to {output_file.name}")


def main():
    parser = argparse.ArgumentParser(description='Fetch all symbols from wrdata providers')
    parser.add_argument('--output', '-o', default='./symbols', help='Output directory for CSV files')
    parser.add_argument('--providers', '-p', help='Comma-separated list of providers to fetch (default: all)')
    parser.add_argument('--parallel', '-j', type=int, default=4, help='Number of parallel fetchers')
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which providers to fetch
    if args.providers:
        providers = [p.strip() for p in args.providers.split(',')]
        fetchers = {k: v for k, v in ALL_FETCHERS.items() if k in providers}
    else:
        fetchers = ALL_FETCHERS

    print(f"\n{'='*60}")
    print(f"Fetching symbols from {len(fetchers)} providers")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"{'='*60}\n")

    results = []
    errors = []

    # Fetch in parallel
    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        future_to_provider = {
            executor.submit(fetcher): name
            for name, fetcher in fetchers.items()
        }

        for future in as_completed(future_to_provider):
            provider = future_to_provider[future]
            try:
                result = future.result()
                if result.get('success'):
                    print(f"✓ {provider}: {result.get('count', 0):,} symbols")
                    save_to_csv(result, output_dir)
                    results.append(result)
                else:
                    error_msg = result.get('error', 'Unknown error')
                    print(f"✗ {provider}: {error_msg}")
                    errors.append({'provider': provider, 'error': error_msg})
            except Exception as e:
                print(f"✗ {provider}: Exception - {str(e)}")
                errors.append({'provider': provider, 'error': str(e)})

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Successful: {len(results)}")
    print(f"Failed: {len(errors)}")

    total_symbols = sum(r.get('count', 0) for r in results)
    print(f"Total symbols fetched: {total_symbols:,}")

    if errors:
        print(f"\nFailed providers:")
        for e in errors:
            print(f"  - {e['provider']}: {e['error']}")

    # Save summary
    summary_file = output_dir / "_summary.csv"
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['provider', 'symbol_count', 'status', 'error'])
        for r in results:
            writer.writerow([r.get('provider'), r.get('count', 0), 'success', ''])
        for e in errors:
            writer.writerow([e['provider'], 0, 'failed', e['error']])

    print(f"\nSummary saved to {summary_file}")
    print(f"CSV files saved to {output_dir.absolute()}")


if __name__ == '__main__':
    main()
