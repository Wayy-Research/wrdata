"""
User-facing symbol operations for the wrdata package.

This module provides simple, high-level functions for searching,
validating, and getting metadata for symbols. It uses yfinance
as the primary search/validation backend with provider-specific
symbol resolution for cross-provider compatibility.
"""

import asyncio
import logging
from functools import partial
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Common crypto symbol mappings: canonical → provider-specific
_CRYPTO_PROVIDER_MAP: Dict[str, Dict[str, str]] = {
    "BTC": {
        "yfinance": "BTC-USD", "coingecko": "bitcoin", "kraken": "XXBTZUSD",
        "coinbase": "BTC-USD", "binance": "BTCUSDT", "twelvedata": "BTC/USD",
    },
    "ETH": {
        "yfinance": "ETH-USD", "coingecko": "ethereum", "kraken": "XETHZUSD",
        "coinbase": "ETH-USD", "binance": "ETHUSDT", "twelvedata": "ETH/USD",
    },
    "SOL": {
        "yfinance": "SOL-USD", "coingecko": "solana", "kraken": "SOLUSD",
        "coinbase": "SOL-USD", "binance": "SOLUSDT", "twelvedata": "SOL/USD",
    },
    "DOGE": {
        "yfinance": "DOGE-USD", "coingecko": "dogecoin", "kraken": "XDGUSD",
        "coinbase": "DOGE-USD", "binance": "DOGEUSDT", "twelvedata": "DOGE/USD",
    },
    "XRP": {
        "yfinance": "XRP-USD", "coingecko": "ripple", "kraken": "XXRPZUSD",
        "coinbase": "XRP-USD", "binance": "XRPUSDT", "twelvedata": "XRP/USD",
    },
    "ADA": {
        "yfinance": "ADA-USD", "coingecko": "cardano", "kraken": "ADAUSD",
        "coinbase": "ADA-USD", "binance": "ADAUSDT", "twelvedata": "ADA/USD",
    },
    "AVAX": {
        "yfinance": "AVAX-USD", "coingecko": "avalanche-2", "kraken": "AVAXUSD",
        "coinbase": "AVAX-USD", "binance": "AVAXUSDT", "twelvedata": "AVAX/USD",
    },
    "DOT": {
        "yfinance": "DOT-USD", "coingecko": "polkadot", "kraken": "DOTUSD",
        "coinbase": "DOT-USD", "binance": "DOTUSDT", "twelvedata": "DOT/USD",
    },
    "LINK": {
        "yfinance": "LINK-USD", "coingecko": "chainlink", "kraken": "LINKUSD",
        "coinbase": "LINK-USD", "binance": "LINKUSDT", "twelvedata": "LINK/USD",
    },
    "ATOM": {
        "yfinance": "ATOM-USD", "coingecko": "cosmos", "kraken": "ATOMUSD",
        "coinbase": "ATOM-USD", "binance": "ATOMUSDT", "twelvedata": "ATOM/USD",
    },
}

# Forex pair mappings
_FOREX_PROVIDER_MAP: Dict[str, Dict[str, str]] = {
    "EURUSD": {"yfinance": "EURUSD=X", "twelvedata": "EUR/USD"},
    "GBPUSD": {"yfinance": "GBPUSD=X", "twelvedata": "GBP/USD"},
    "USDJPY": {"yfinance": "USDJPY=X", "twelvedata": "USD/JPY"},
    "AUDUSD": {"yfinance": "AUDUSD=X", "twelvedata": "AUD/USD"},
    "USDCAD": {"yfinance": "USDCAD=X", "twelvedata": "USD/CAD"},
    "USDCHF": {"yfinance": "USDCHF=X", "twelvedata": "USD/CHF"},
    "NZDUSD": {"yfinance": "NZDUSD=X", "twelvedata": "NZD/USD"},
    "EURGBP": {"yfinance": "EURGBP=X", "twelvedata": "EUR/GBP"},
    "EURJPY": {"yfinance": "EURJPY=X", "twelvedata": "EUR/JPY"},
    "GBPJPY": {"yfinance": "GBPJPY=X", "twelvedata": "GBP/JPY"},
}


def search(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for symbols using yfinance's search API.

    Returns a list of dicts with keys: symbol, name, type, provider, exchange.
    """
    import yfinance as yf

    results = []
    seen = set()

    try:
        search_results = yf.Search(query, max_results=min(limit, 10))
        for result in search_results.quotes:
            symbol = result.get("symbol", "")
            if symbol and symbol not in seen:
                seen.add(symbol)
                results.append({
                    "symbol": symbol,
                    "name": result.get("longname") or result.get("shortname", ""),
                    "type": result.get("quoteType", "").lower(),
                    "provider": "yfinance",
                    "exchange": result.get("exchange", ""),
                })
                if len(results) >= limit:
                    break
    except Exception as e:
        logger.warning(f"yfinance search failed for '{query}': {e}")

    return results


def validate(symbol: str) -> bool:
    """
    Validate that a symbol exists by checking yfinance for price data.
    """
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        # Fast check: look for a current price in fast_info
        fast = ticker.fast_info
        if hasattr(fast, "last_price") and fast.last_price is not None:
            return True
        # Fallback: check if history returns any rows
        hist = ticker.history(period="5d")
        return len(hist) > 0
    except Exception:
        return False


def resolve(symbol: str, provider: str) -> Optional[str]:
    """
    Resolve a canonical symbol to a provider-specific format.

    Handles crypto, forex, and equity symbols. For equities, most providers
    use the same ticker so we return the symbol as-is.
    """
    symbol_upper = symbol.upper()
    provider_lower = provider.lower()

    # Check crypto mappings by trying all known canonical forms
    for canonical, mapping in _CRYPTO_PROVIDER_MAP.items():
        if symbol_upper in (
            canonical,
            f"{canonical}-USD",
            f"{canonical}/USD",
            f"{canonical}USDT",
        ):
            if provider_lower in mapping:
                return mapping[provider_lower]
            # Fallback for unmapped providers
            if provider_lower in ("yfinance", "yahoo", "coinbase"):
                return f"{canonical}-USD"
            if provider_lower == "binance":
                return f"{canonical}USDT"
            if provider_lower == "coingecko":
                return canonical.lower()
            return f"{canonical}-USD"

    # Check forex mappings (strip yfinance's =X suffix if present)
    forex_key = symbol_upper.replace("=X", "")
    if forex_key in _FOREX_PROVIDER_MAP:
        mapping = _FOREX_PROVIDER_MAP[forex_key]
        if provider_lower in mapping:
            return mapping[provider_lower]
        return forex_key

    # For equities: most providers use the same ticker
    return symbol_upper


def get_metadata(symbol: str) -> Optional[Dict]:
    """
    Get metadata for a symbol from yfinance.

    Returns a dict with: name, sector, industry, market_cap, currency, exchange, etc.
    """
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or len(info) <= 1:
            return None

        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", ""),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
            "quote_type": info.get("quoteType"),
            "country": info.get("country"),
            "website": info.get("website"),
            "description": info.get("longBusinessSummary", "")[:500] if info.get("longBusinessSummary") else None,
        }
    except Exception as e:
        logger.warning(f"Failed to get metadata for {symbol}: {e}")
        return None


def get_economic_calendar(horizon: str = "3month") -> List[Dict]:
    """
    Fetch economic calendar data from Alpha Vantage.

    :param horizon: The time horizon for the calendar. Can be "3month", "6month", or "12month".
    """
    import requests
    import csv
    from io import StringIO
    from .core.config import settings

    if not settings.has_alpha_vantage_key:
        raise ValueError("Alpha Vantage API key not configured.")

    url = f"https://www.alphavantage.co/query?function=ECONOMIC_CALENDAR&horizon={horizon}&apikey={settings.ALPHA_VANTAGE_API_KEY}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)

        events = []
        for row in reader:
            events.append(dict(row))

        return events

    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching economic calendar: {e}")
        return []


# --- Async Wrappers ---

async def search_async(query: str, limit: int = 10) -> List[Dict]:
    """Async wrapper for search."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(search, query, limit=limit))

async def validate_async(symbol: str) -> bool:
    """Async wrapper for validate."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(validate, symbol))

async def resolve_async(symbol: str, provider: str) -> Optional[str]:
    """Async wrapper for resolve."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(resolve, symbol, provider=provider))

async def get_metadata_async(symbol: str) -> Optional[Dict]:
    """Async wrapper for get_metadata."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(get_metadata, symbol))

async def get_economic_calendar_async(horizon: str = "3month") -> List[Dict]:
    """Async wrapper for get_economic_calendar."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(get_economic_calendar, horizon=horizon))
