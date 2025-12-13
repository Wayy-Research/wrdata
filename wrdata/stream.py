"""
DataStream - The dead-simple API for market data.

Zero configuration required. Just import and go.

Examples:
    >>> from wrdata import DataStream
    >>> stream = DataStream()
    >>> df = stream.get("AAPL", start="2024-01-01", end="2024-12-31")
    >>> print(df.head())
"""

from typing import Optional, List, Dict, Any, Union, Callable, AsyncIterator
from datetime import datetime, date
import polars as pl
from decimal import Decimal
import asyncio

from wrdata.providers.base import BaseProvider
from wrdata.providers.yfinance_provider import YFinanceProvider
from wrdata.models.schemas import (
    DataRequest,
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
)
from wrdata.core.config import settings

# Streaming imports (lazy loaded to avoid dependency issues)
from wrdata.streaming.base import StreamMessage


class DataStream:
    """
    The main entry point for wrdata - a dead-simple API for market data.

    Features:
    - Zero configuration for basic use (uses free providers)
    - Plug-and-play provider support (add API keys when ready)
    - Smart provider routing based on asset type
    - Automatic fallbacks on provider failure
    - Clean Polars DataFrame output (blazing fast!)

    Usage:
        Basic (free providers):
        >>> stream = DataStream()
        >>> df = stream.get("AAPL")

        With API keys (better rate limits):
        >>> stream = DataStream(
        ...     finnhub_key="...",
        ...     polygon_key="..."
        ... )

        Options chains:
        >>> chain = stream.options("SPY", expiry="2024-12-20")

        Multiple symbols:
        >>> data = stream.get_many(["AAPL", "GOOGL", "MSFT"])
    """

    def __init__(
        self,
        # Economic data (free with API key)
        fred_key: Optional[str] = None,

        # Stock market data (free tier with WebSocket!)
        finnhub_key: Optional[str] = None,

        # Broker API keys (data + trading)
        alpaca_key: Optional[str] = None,
        alpaca_secret: Optional[str] = None,
        alpaca_paper: bool = True,  # Use paper trading by default

        # Interactive Brokers (TWS/Gateway connection)
        ibkr_host: str = "127.0.0.1",
        ibkr_port: int = 7497,  # 7497 = paper, 7496 = live
        ibkr_client_id: int = 1,
        ibkr_readonly: bool = False,

        # Premium data provider keys (optional)
        polygon_key: Optional[str] = None,
        alphavantage_key: Optional[str] = None,
        twelvedata_key: Optional[str] = None,

        # Configuration
        default_provider: Optional[str] = None,
        fallback_enabled: bool = True,

        # Future: Cache configuration (Phase 3)
        cache_url: Optional[str] = None,
        cache_token: Optional[str] = None,
        cache_org: Optional[str] = None,
    ):
        """
        Initialize DataStream.

        Args:
            polygon_key: Polygon.io API key (premium)
            alphavantage_key: Alpha Vantage API key
            twelvedata_key: Twelve Data API key
            default_provider: Override default provider selection
            fallback_enabled: Enable automatic fallback to alternate providers
            cache_url: InfluxDB URL for caching (coming in Phase 3)
            cache_token: InfluxDB token
            cache_org: InfluxDB organization
        """
        self.fallback_enabled = fallback_enabled
        self.default_provider = default_provider

        # Initialize providers
        self.providers: Dict[str, BaseProvider] = {}

        # Always include YFinance (free, no key required)
        self._add_yfinance_provider()

        # Add FRED if API key provided (or use from env)
        fred_key = fred_key or settings.FRED_API_KEY
        self._add_fred_provider(fred_key)

        # Add Alpha Vantage if API key provided (or use from env)
        alphavantage_key = alphavantage_key or settings.ALPHA_VANTAGE_API_KEY
        self._add_alphavantage_provider(alphavantage_key)

        # Add Coinbase (no API key required for public data)
        self._add_coinbase_provider()

        # Add CoinGecko (no API key required for basic use)
        self._add_coingecko_provider()

        # Add Kraken (no API key required for public data)
        self._add_kraken_provider()

        # Add CCXT exchanges for expanded crypto coverage
        self._add_ccxt_exchanges()

        # Add Finnhub if API key provided (or use from env)
        finnhub_key = finnhub_key or settings.FINNHUB_API_KEY
        self._add_finnhub_provider(finnhub_key)

        # Add Alpaca if API keys provided (or use from env)
        alpaca_key = alpaca_key or settings.ALPACA_API_KEY
        alpaca_secret = alpaca_secret or settings.ALPACA_API_SECRET
        self._add_alpaca_provider(alpaca_key, alpaca_secret, alpaca_paper)

        # Add Interactive Brokers if enabled
        # Note: IBKR requires TWS/Gateway running, so we don't auto-enable
        self._add_ibkr_provider(ibkr_host, ibkr_port, ibkr_client_id, ibkr_readonly)

        # TODO: Add Polygon, TwelveData, Tradier providers
        # Will implement next

        # Provider priority by asset type
        self._provider_priority = {
            'equity': ['ibkr', 'alpaca', 'finnhub', 'alphavantage', 'yfinance'],
            'stock': ['ibkr', 'alpaca', 'finnhub', 'alphavantage', 'yfinance'],
            'etf': ['ibkr', 'alpaca', 'finnhub', 'yfinance'],
            'option': ['ibkr'],  # IBKR is the best for options
            'future': ['ibkr'],  # IBKR only for futures
            'index': ['yfinance'],
            'forex': ['ibkr', 'alphavantage', 'yfinance'],
            'crypto': ['coinbase', 'kraken', 'ccxt_kucoin', 'ccxt_okx', 'ccxt_gateio', 'yfinance', 'coingecko', 'ccxt_bitfinex', 'ccxt_binance', 'ccxt_bybit'],
            'cryptocurrency': ['coinbase', 'kraken', 'ccxt_kucoin', 'ccxt_okx', 'ccxt_gateio', 'yfinance', 'coingecko', 'ccxt_bitfinex', 'ccxt_binance', 'ccxt_bybit'],
            'economic': ['fred'],  # FRED for economic data
        }

        # Cache configuration (Phase 3)
        self.cache_enabled = cache_url is not None
        self.cache_url = cache_url
        self.cache_token = cache_token
        self.cache_org = cache_org

        # Initialize streaming manager (lazy import)
        from wrdata.streaming.manager import StreamManager
        self.stream_manager = StreamManager()

        # Add streaming providers
        self._init_streaming_providers(
            finnhub_key,
            alpaca_key, alpaca_secret, alpaca_paper,
            ibkr_host, ibkr_port, ibkr_client_id
        )

    def _add_yfinance_provider(self):
        """Add Yahoo Finance provider (always available)."""
        try:
            self.providers['yfinance'] = YFinanceProvider()
        except Exception as e:
            print(f"Warning: Could not initialize YFinance provider: {e}")

    def _add_fred_provider(self, api_key: Optional[str]):
        """Add FRED economic data provider if API key available."""
        if not api_key:
            return  # FRED requires an API key

        try:
            from wrdata.providers.fred_provider import FREDProvider
            self.providers['fred'] = FREDProvider(api_key=api_key)
        except Exception as e:
            print(f"Warning: Could not initialize FRED provider: {e}")

    def _add_alphavantage_provider(self, api_key: Optional[str]):
        """Add Alpha Vantage provider if API key available."""
        if not api_key:
            return  # Alpha Vantage requires an API key

        try:
            from wrdata.providers.alphavantage_provider import AlphaVantageProvider
            self.providers['alphavantage'] = AlphaVantageProvider(api_key=api_key)
        except Exception as e:
            print(f"Warning: Could not initialize Alpha Vantage provider: {e}")

    def _add_coinbase_provider(self):
        """Add Coinbase provider (no API key required for public data)."""
        try:
            from wrdata.providers.coinbase_provider import CoinbaseProvider
            self.providers['coinbase'] = CoinbaseProvider()
        except Exception as e:
            print(f"Warning: Could not initialize Coinbase provider: {e}")

    def _add_coingecko_provider(self):
        """Add CoinGecko provider (no API key required for basic use)."""
        try:
            from wrdata.providers.coingecko_provider import CoinGeckoProvider
            self.providers['coingecko'] = CoinGeckoProvider()
        except Exception as e:
            print(f"Warning: Could not initialize CoinGecko provider: {e}")

    def _add_kraken_provider(self):
        """Add Kraken provider (no API key required for public data)."""
        try:
            from wrdata.providers.kraken_provider import KrakenProvider
            self.providers['kraken'] = KrakenProvider()
        except Exception as e:
            print(f"Warning: Could not initialize Kraken provider: {e}")

    def _add_ccxt_exchanges(self):
        """Add major cryptocurrency exchanges via CCXT (100+ exchanges available)."""
        try:
            from wrdata.providers.ccxt_provider import CCXTProvider

            # Add major exchanges (free, no API key required for public data)
            major_exchanges = [
                'binance',    # 7-8 years of 1-minute data, best for historical data
                'bybit',      # Fast-growing crypto derivatives exchange
                'okx',        # Top-tier global exchange
                'kucoin',     # Wide variety of altcoins
                'gateio',     # Extensive crypto selection
                'bitfinex',   # Professional trading platform
            ]

            for exchange_id in major_exchanges:
                try:
                    provider = CCXTProvider(exchange_id=exchange_id)
                    self.providers[f'ccxt_{exchange_id}'] = provider
                except Exception as e:
                    # Silent fail - CCXT exchanges are optional
                    print(f"Warning: Could not initialize CCXT {exchange_id}: {e}")
                    pass

        except Exception as e:
            print(f"Warning: Could not initialize CCXT providers: {e}")

    def _add_finnhub_provider(self, api_key: Optional[str]):
        """Add Finnhub provider if API key available."""
        if not api_key:
            return  # Finnhub requires an API key

        try:
            from wrdata.providers.finnhub_provider import FinnhubProvider
            self.providers['finnhub'] = FinnhubProvider(api_key=api_key)
        except Exception as e:
            print(f"Warning: Could not initialize Finnhub provider: {e}")

    def _add_alpaca_provider(self, api_key: Optional[str], api_secret: Optional[str], paper: bool):
        """Add Alpaca broker provider if API keys available."""
        if not api_key or not api_secret:
            return  # Alpaca requires both key and secret

        try:
            from wrdata.providers.alpaca_provider import AlpacaProvider
            self.providers['alpaca'] = AlpacaProvider(
                api_key=api_key,
                api_secret=api_secret,
                paper=paper
            )
        except Exception as e:
            print(f"Warning: Could not initialize Alpaca provider: {e}")

    def _add_ibkr_provider(self, host: str, port: int, client_id: int, readonly: bool):
        """Add Interactive Brokers provider if TWS/Gateway is running."""
        try:
            from wrdata.providers.ibkr_provider import IBKRProvider
            provider = IBKRProvider(
                host=host,
                port=port,
                client_id=client_id,
                readonly=readonly
            )
            # Try to connect - if it fails, don't add the provider
            if provider.connect():
                self.providers['ibkr'] = provider
            # Note: We don't print warning if TWS isn't running - it's optional
        except Exception as e:
            # Silent fail - IBKR is optional and requires external software
            pass

    def _init_streaming_providers(
        self,
        finnhub_key: Optional[str],
        alpaca_key: Optional[str],
        alpaca_secret: Optional[str],
        alpaca_paper: bool,
        ibkr_host: str,
        ibkr_port: int,
        ibkr_client_id: int
    ):
        """Initialize WebSocket streaming providers."""
        try:
            # Add Coinbase streaming (free, no auth required for public data)
            from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider
            coinbase_stream = CoinbaseStreamProvider()
            self.stream_manager.add_provider('coinbase_stream', coinbase_stream)
        except Exception as e:
            print(f"Warning: Could not initialize Coinbase streaming: {e}")

        # Add Finnhub streaming if API key provided (FREE WebSocket!)
        if finnhub_key:
            try:
                from wrdata.streaming.finnhub_stream import FinnhubStreamProvider
                finnhub_stream = FinnhubStreamProvider(api_key=finnhub_key)
                self.stream_manager.add_provider('finnhub_stream', finnhub_stream)
            except Exception as e:
                print(f"Warning: Could not initialize Finnhub streaming: {e}")

        # Add Alpaca streaming if API keys provided (FREE WebSocket + trading!)
        if alpaca_key and alpaca_secret:
            try:
                from wrdata.streaming.alpaca_stream import AlpacaStreamProvider
                alpaca_stream = AlpacaStreamProvider(
                    api_key=alpaca_key,
                    api_secret=alpaca_secret,
                    paper=alpaca_paper
                )
                self.stream_manager.add_provider('alpaca_stream', alpaca_stream)
            except Exception as e:
                print(f"Warning: Could not initialize Alpaca streaming: {e}")

        # Add IBKR streaming if TWS/Gateway is available
        # Use different client_id for streaming (client_id + 1)
        try:
            from wrdata.streaming.ibkr_stream import IBKRStreamProvider
            ibkr_stream = IBKRStreamProvider(
                host=ibkr_host,
                port=ibkr_port,
                client_id=ibkr_client_id + 1  # Different client ID for streaming
            )
            self.stream_manager.add_provider('ibkr_stream', ibkr_stream)
        except Exception:
            # Silent fail - IBKR streaming is optional
            pass

    def get(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        asset_type: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> pl.DataFrame:
        """
        Get historical market data for a symbol.

        This is the main method you'll use 90% of the time.
        It returns a clean Polars DataFrame ready for analysis.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "BTCUSDT")
            start: Start date as "YYYY-MM-DD" (default: 1 year ago)
            end: End date as "YYYY-MM-DD" (default: today)
            interval: Time interval - "1m", "5m", "15m", "1h", "1d", "1wk", "1mo"
            asset_type: Asset type - auto-detected if not specified
            provider: Force specific provider (default: auto-select best)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume

        Examples:
            >>> # Get 1 year of daily data (default)
            >>> df = stream.get("AAPL")

            >>> # Get crypto data (auto-detected from symbol)
            >>> df = stream.get("BTCUSDT")

            >>> # Get specific date range
            >>> df = stream.get("AAPL", start="2024-01-01", end="2024-12-31")

            >>> # Get intraday data
            >>> df = stream.get("AAPL", interval="5m", start="2024-11-07")
        """
        # Auto-detect asset type if not provided
        if asset_type is None:
            asset_type = self._detect_asset_type(symbol)

        # Set defaults for dates if not provided
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")
        if start is None:
            # Default to 1 year ago
            start = (datetime.now().replace(year=datetime.now().year - 1)).strftime("%Y-%m-%d")

        # Create request
        request = DataRequest(
            symbol=symbol,
            start_date=start,
            end_date=end,
            interval=interval,
            asset_type=asset_type,
            provider=provider or self.default_provider
        )

        # Select provider
        provider_name = self._select_provider(request)

        # Try primary provider
        response = self._fetch_with_fallback(request, provider_name)

        # Convert to DataFrame
        return self._response_to_dataframe(response)

    def fast_get(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        provider: str = "coinbase",
        max_concurrent: int = 10,
    ) -> pl.DataFrame:
        """
        Fast parallel fetch for large historical data pulls.

        Uses async parallel requests to fetch data 5-20x faster than
        the standard sequential approach. Best for:
        - Large date ranges (months/years of data)
        - Fine-grained intervals (1m, 5m)
        - Crypto data from exchanges with pagination limits

        Supported providers:
        - "coinbase": Best for USD pairs (XRP-USD, BTC-USD, ETH-USD) - FASTEST
        - "kraken": Good for USD pairs, limited history
        - "binance": Wide selection, requires non-US IP
        - "okx", "kucoin", "gateio", "bybit": Additional CCXT exchanges

        Args:
            symbol: Trading pair (e.g., "BTC-USD", "XRP/USDT", "ETHUSDT")
            start: Start date as "YYYY-MM-DD" (default: 1 year ago)
            end: End date as "YYYY-MM-DD" (default: today)
            interval: Time interval - "1m", "5m", "15m", "1h", "1d"
            provider: Exchange to use (default: "coinbase")
            max_concurrent: Maximum parallel requests (default: 10)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume

        Examples:
            >>> # Fast fetch 1 year of daily XRP data from Coinbase
            >>> df = stream.fast_get("XRP-USD")

            >>> # Fast fetch 1 year of 1-minute BTC data
            >>> df = stream.fast_get("BTC-USD", interval="1m")

            >>> # Use specific date range
            >>> df = stream.fast_get("ETH-USD", start="2024-01-01", end="2024-12-31")
        """
        import asyncio
        from wrdata.utils.async_fetch import AsyncCCXTFetcher, AsyncOHLCVFetcher

        # Set defaults for dates if not provided
        if end is None:
            end = datetime.now().strftime("%Y-%m-%d")
        if start is None:
            start = (datetime.now().replace(year=datetime.now().year - 1)).strftime("%Y-%m-%d")

        # Choose fetcher based on provider
        # Direct aiohttp fetchers are faster for supported exchanges
        direct_providers = ['coinbase', 'binance', 'kraken']

        async def _async_fetch():
            if provider.lower() in direct_providers:
                # Use direct aiohttp fetcher (faster)
                fetcher = AsyncOHLCVFetcher(
                    provider=provider.lower(),
                    max_concurrent=max_concurrent,
                )
                return await fetcher.fetch(symbol, start, end, interval)
            else:
                # Use CCXT for other exchanges
                fetcher = AsyncCCXTFetcher(
                    exchange_id=provider.lower(),
                    max_concurrent=max_concurrent,
                )
                return await fetcher.fetch(symbol, start, end, interval)

        # Run async fetch
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create task
                import nest_asyncio
                nest_asyncio.apply()
                data = loop.run_until_complete(_async_fetch())
            else:
                data = asyncio.run(_async_fetch())
        except RuntimeError:
            # No event loop - create one
            data = asyncio.run(_async_fetch())

        if not data:
            return pl.DataFrame()

        # Convert to DataFrame
        df = pl.DataFrame(data)

        # Parse timestamp
        if 'timestamp' in df.columns:
            df = df.with_columns(
                pl.col('timestamp').str.to_datetime().alias('timestamp')
            )
            df = df.sort('timestamp')

        return df

    def get_many(
        self,
        symbols: List[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        asset_type: str = "equity",
        provider: Optional[str] = None,
        min_coverage: float = 0.70,
        forward_fill: bool = True,
        drop_low_coverage: bool = True,
    ) -> pl.DataFrame:
        """
        Get historical data for multiple symbols as a single combined DataFrame.

        Returns a DataFrame with 'symbol' and 'timestamp' columns that can be
        used as a composite index for multi-symbol analysis.

        Automatically filters out symbols with insufficient data coverage and
        forward-fills gaps for cleaner correlation analysis.

        Args:
            symbols: List of ticker symbols
            start: Start date as "YYYY-MM-DD"
            end: End date as "YYYY-MM-DD"
            interval: Time interval
            asset_type: Asset type
            provider: Force specific provider (default: auto-select best)
            min_coverage: Minimum data coverage threshold (0.70 = 70%). Symbols with
                         less coverage are excluded if drop_low_coverage is True.
            forward_fill: Fill gaps in data using forward fill method (default: True)
            drop_low_coverage: If True, exclude symbols with coverage below min_coverage (default: True)

        Returns:
            Combined DataFrame with columns: symbol, timestamp, open, high, low, close, volume

        Example:
            >>> # Get combined crypto data with automatic filtering
            >>> df = stream.get_many(
            ...     ["BTC-USD", "ETH-USD", "SOL-USD"],
            ...     interval="1m",
            ...     asset_type="crypto"
            ... )
            >>> # Data is ready for correlation analysis
            >>> df.group_by('symbol').count()
            >>> # Pivot for correlation matrix
            >>> pivot_df = df.pivot(
            ...     values='close',
            ...     index='timestamp',
            ...     columns='symbol'
            ... )
        """
        # Fetch data for all symbols
        results = {}

        for symbol in symbols:
            try:
                df = self.get(
                    symbol=symbol,
                    start=start,
                    end=end,
                    interval=interval,
                    asset_type=asset_type,
                    provider=provider
                )
                if not df.is_empty():
                    results[symbol] = df
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")

        if not results:
            return pl.DataFrame()

        # Apply coverage filtering if requested
        if start and end and drop_low_coverage and min_coverage > 0:
            from datetime import datetime

            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            days = (end_dt - start_dt).days

            # Expected rows per day by interval (for 24/7 crypto markets)
            interval_to_rows_per_day = {
                '1m': 60 * 24, '5m': 12 * 24, '15m': 4 * 24, '30m': 2 * 24,
                '1h': 24, '2h': 12, '4h': 6, '6h': 4, '12h': 2, '1d': 1,
            }
            rows_per_day = interval_to_rows_per_day.get(interval, 1)
            expected_rows = days * rows_per_day

            # Filter by coverage
            filtered_results = {}
            excluded_count = 0

            for symbol, df in results.items():
                actual_rows = len(df)
                coverage = actual_rows / expected_rows if expected_rows > 0 else 1.0

                if coverage >= min_coverage:
                    filtered_results[symbol] = df
                else:
                    excluded_count += 1
                    print(f"Excluding {symbol}: {actual_rows} rows ({coverage*100:.1f}% coverage, need {min_coverage*100:.0f}%)")

            if excluded_count > 0:
                print(f"Excluded {excluded_count} symbols with coverage < {min_coverage*100:.0f}%")

            results = filtered_results

        if not results:
            print("No symbols meet the minimum coverage threshold")
            return pl.DataFrame()

        # Normalize and combine DataFrames
        combined_dfs = []
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

            # Forward fill gaps if requested
            if forward_fill and 'timestamp' in df_normalized.columns:
                fill_cols = [c for c in numeric_cols if c in df_normalized.columns]
                if fill_cols:
                    df_normalized = df_normalized.with_columns([
                        pl.col(c).forward_fill() for c in fill_cols
                    ])

            # Add symbol column
            df_with_symbol = df_normalized.with_columns(
                pl.lit(symbol).alias('symbol')
            )
            combined_dfs.append(df_with_symbol)

        # Concatenate all DataFrames
        combined = pl.concat(combined_dfs, how='vertical')

        # Sort by symbol and timestamp for better organization
        if 'timestamp' in combined.columns:
            combined = combined.sort(['symbol', 'timestamp'])
        else:
            combined = combined.sort('symbol')

        return combined

    def options(
        self,
        symbol: str,
        expiry: Optional[Union[str, date]] = None,
        option_type: Optional[str] = None,
        strike_min: Optional[float] = None,
        strike_max: Optional[float] = None,
    ) -> pl.DataFrame:
        """
        Get options chain data for a symbol.

        Args:
            symbol: Underlying symbol (e.g., "AAPL", "SPY")
            expiry: Expiration date as "YYYY-MM-DD" or date object (default: nearest expiry)
            option_type: Filter by "call" or "put" (default: both)
            strike_min: Minimum strike price
            strike_max: Maximum strike price

        Returns:
            DataFrame with options chain data

        Example:
            >>> # Get full options chain for nearest expiry
            >>> chain = stream.options("SPY")

            >>> # Get specific expiry
            >>> chain = stream.options("SPY", expiry="2024-12-20")

            >>> # Get only calls near current price
            >>> chain = stream.options("SPY", option_type="call", strike_min=580, strike_max=600)
        """
        # Convert string date to date object if needed
        if isinstance(expiry, str):
            expiry = datetime.strptime(expiry, "%Y-%m-%d").date()

        # Create request
        request = OptionsChainRequest(
            symbol=symbol,
            expiration_date=expiry,
            option_type=option_type,
            strike_min=Decimal(str(strike_min)) if strike_min else None,
            strike_max=Decimal(str(strike_max)) if strike_max else None,
        )

        # Use YFinance for options (supports options chains)
        if 'yfinance' not in self.providers:
            raise ValueError("YFinance provider not available for options data")

        provider = self.providers['yfinance']
        response = provider.fetch_options_chain(request)

        if not response.success:
            raise ValueError(f"Failed to fetch options: {response.error}")

        # Convert to DataFrame
        return self._options_to_dataframe(response)

    def get_expirations(self, symbol: str) -> List[date]:
        """
        Get available expiration dates for options on a symbol.

        Args:
            symbol: Underlying symbol

        Returns:
            List of available expiration dates

        Example:
            >>> expirations = stream.get_expirations("SPY")
            >>> print(expirations[:5])  # Show first 5
        """
        if 'yfinance' not in self.providers:
            raise ValueError("YFinance provider not available")

        provider = self.providers['yfinance']
        return provider.get_available_expirations(symbol)

    def search_symbol(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for symbols across multiple providers.

        Returns a list of matching symbols with their details including
        the correct symbol format, source provider, description, and asset type.

        Args:
            query: Search query (e.g., "bitcoin", "apple", "ETH")
            limit: Maximum number of results to return (default: 10)

        Returns:
            List of dictionaries with symbol information:
            - symbol: The trading symbol in the correct format
            - name: Full name/description
            - type: Asset type (stock, crypto, etf, etc.)
            - provider: The provider where this result came from
            - exchange: Exchange/market (if applicable)

        Examples:
            >>> # Search for Bitcoin
            >>> results = stream.search_symbol("bitcoin")
            >>> print(results[0])
            {
                'symbol': 'BTC-USD',
                'name': 'Bitcoin USD',
                'type': 'cryptocurrency',
                'provider': 'yfinance',
                'exchange': 'CCC'
            }

            >>> # Search for Ethereum across providers
            >>> results = stream.search_symbol("ethereum")
            >>> for r in results:
            ...     print(f"{r['symbol']:15} from {r['provider']}")
            ETH-USD         from yfinance
            ETH/USD         from kraken
            ethereum        from coingecko
        """
        results = []
        seen_symbols = set()

        # 1. Search YFinance (stocks, ETFs, major crypto)
        if 'yfinance' in self.providers and len(results) < limit:
            try:
                import yfinance as yf
                search_results = yf.Search(query, max_results=min(limit, 10))

                for result in search_results.quotes:
                    symbol = result.get('symbol', '')
                    if symbol and symbol not in seen_symbols:
                        seen_symbols.add(symbol)
                        results.append({
                            'symbol': symbol,
                            'name': result.get('longname') or result.get('shortname', ''),
                            'type': result.get('quoteType', '').lower(),
                            'provider': 'yfinance',
                            'exchange': result.get('exchange', ''),
                        })
                        if len(results) >= limit:
                            break
            except Exception as e:
                print(f"Warning: YFinance search failed: {e}")

        # 2. Search CoinGecko (comprehensive crypto database)
        if 'coingecko' in self.providers and len(results) < limit:
            try:
                import requests
                provider = self.providers['coingecko']

                # Search CoinGecko's coin list
                url = f"{provider.base_url}/search"
                params = {"query": query}
                response = requests.get(url, headers=provider.headers, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    for coin in data.get('coins', [])[:limit - len(results)]:
                        symbol_id = coin.get('id', '')
                        if symbol_id and symbol_id not in seen_symbols:
                            seen_symbols.add(symbol_id)
                            results.append({
                                'symbol': symbol_id,
                                'name': coin.get('name', ''),
                                'type': 'cryptocurrency',
                                'provider': 'coingecko',
                                'exchange': 'CoinGecko',
                            })
                            if len(results) >= limit:
                                break
            except Exception as e:
                print(f"Warning: CoinGecko search failed: {e}")

        # 3. Search Kraken (major crypto pairs)
        if 'kraken' in self.providers and len(results) < limit:
            try:
                import requests
                provider = self.providers['kraken']

                # Get Kraken asset pairs
                url = f"{provider.base_url}/public/AssetPairs"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('error') is None and data.get('result'):
                        query_upper = query.upper()
                        for pair_name, pair_data in data['result'].items():
                            altname = pair_data.get('altname', '')
                            # Match query in pair name
                            if query_upper in altname or query_upper in pair_name:
                                if altname and altname not in seen_symbols:
                                    seen_symbols.add(altname)
                                    base = pair_data.get('base', '')
                                    quote = pair_data.get('quote', '')
                                    results.append({
                                        'symbol': altname,
                                        'name': f"{base}/{quote}",
                                        'type': 'cryptocurrency',
                                        'provider': 'kraken',
                                        'exchange': 'Kraken',
                                    })
                                    if len(results) >= limit:
                                        break
            except Exception as e:
                print(f"Warning: Kraken search failed: {e}")

        # 4. Search Coinbase (major crypto pairs)
        if 'coinbase' in self.providers and len(results) < limit:
            try:
                import requests
                provider = self.providers['coinbase']

                # Get Coinbase products
                url = f"{provider.base_url}/products"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    products = response.json()
                    query_upper = query.upper()
                    for product in products:
                        product_id = product.get('id', '')
                        base_currency = product.get('base_currency', '')
                        # Match query in product
                        if query_upper in product_id or query_upper in base_currency:
                            if product_id and product_id not in seen_symbols:
                                seen_symbols.add(product_id)
                                results.append({
                                    'symbol': product_id,
                                    'name': product.get('display_name', product_id),
                                    'type': 'cryptocurrency',
                                    'provider': 'coinbase',
                                    'exchange': 'Coinbase',
                                })
                                if len(results) >= limit:
                                    break
            except Exception as e:
                print(f"Warning: Coinbase search failed: {e}")

        # 5. Search CCXT exchanges (100+ exchanges via unified API)
        if len(results) < limit:
            # Search across available CCXT exchanges
            ccxt_providers = [name for name in self.providers.keys() if name.startswith('ccxt_')]

            for provider_name in ccxt_providers:
                if len(results) >= limit:
                    break

                try:
                    provider = self.providers[provider_name]
                    # Use the provider's search method
                    if hasattr(provider, 'search_symbols'):
                        exchange_results = provider.search_symbols(query, limit - len(results))

                        for result in exchange_results:
                            symbol = result.get('symbol', '')
                            if symbol and symbol not in seen_symbols:
                                seen_symbols.add(symbol)
                                results.append(result)
                                if len(results) >= limit:
                                    break
                except Exception as e:
                    # Silent fail - individual exchanges may have issues
                    pass

        return results[:limit]

    def _get_recommended_provider(self, asset_type: str) -> str:
        """
        Get the recommended provider for an asset type.

        Args:
            asset_type: Asset type string

        Returns:
            Recommended provider name
        """
        # Use the first available provider from the priority list
        asset_type_lower = asset_type.lower()
        if asset_type_lower in self._provider_priority:
            for provider in self._provider_priority[asset_type_lower]:
                if provider in self.providers:
                    return provider

        # Fallback to first available provider
        if self.providers:
            return list(self.providers.keys())[0]

        return 'unknown'

    # ========================================================================
    # REAL-TIME STREAMING METHODS (Phase 2)
    # ========================================================================

    async def stream(
        self,
        symbol: str,
        stream_type: str = "ticker",
        interval: str = "1m",
        provider: Optional[str] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Stream real-time market data.

        This is an async generator - use with `async for`.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "AAPL")
            stream_type: Type of stream - "ticker" (trades) or "kline" (candles)
            interval: For kline streams - "1m", "5m", "1h", etc.
            provider: Force specific provider (auto-select if None)

        Yields:
            StreamMessage objects with real-time data

        Examples:
            >>> # Stream live Bitcoin prices
            >>> async for tick in stream.stream("BTCUSDT"):
            ...     print(f"BTC: ${tick.price}")

            >>> # Stream 1-minute candles
            >>> async for candle in stream.stream("ETHUSDT", stream_type="kline", interval="1m"):
            ...     print(f"ETH Close: ${candle.close}")
        """
        if stream_type == "ticker":
            async for message in self.stream_manager.subscribe_ticker(symbol, provider):
                yield message
        elif stream_type == "kline":
            async for message in self.stream_manager.subscribe_kline(symbol, interval, provider):
                yield message
        else:
            raise ValueError(f"Unknown stream type: {stream_type}")

    def subscribe(
        self,
        symbol: str,
        callback: Callable[[StreamMessage], None],
        stream_type: str = "ticker",
        interval: str = "1m",
        provider: Optional[str] = None
    ):
        """
        Subscribe to real-time data with a callback function.

        This is the callback-based API - simpler than async generators.
        The callback will be called for each new message.

        Args:
            symbol: Trading symbol
            callback: Function to call with each message
            stream_type: Type of stream - "ticker" or "kline"
            interval: For kline streams - time interval
            provider: Force specific provider (auto-select if None)

        Examples:
            >>> # Simple callback
            >>> def on_price(msg):
            ...     print(f"{msg.symbol}: ${msg.price}")
            >>> stream.subscribe("BTCUSDT", on_price)

            >>> # Async callback
            >>> async def on_candle(msg):
            ...     await save_to_database(msg)
            >>> stream.subscribe("ETHUSDT", on_candle, stream_type="kline")
        """
        # Create and run async task in background
        async def _run_subscription():
            if stream_type == "ticker":
                await self.stream_manager.subscribe_ticker(symbol, provider, callback)
            elif stream_type == "kline":
                await self.stream_manager.subscribe_kline(symbol, interval, provider, callback)

        # Run in background task
        task = asyncio.create_task(_run_subscription())
        return task

    async def stream_many(
        self,
        symbols: List[str],
        callback: Optional[Callable[[StreamMessage], None]] = None,
        stream_type: str = "ticker",
        provider: Optional[str] = None
    ):
        """
        Stream multiple symbols simultaneously.

        Args:
            symbols: List of trading symbols
            callback: Optional callback for each message
            stream_type: Type of stream - "ticker" or "kline"
            provider: Force specific provider (auto-select if None)

        Example:
            >>> async def on_tick(msg):
            ...     print(f"{msg.symbol}: ${msg.price}")
            >>>
            >>> await stream.stream_many(
            ...     ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            ...     callback=on_tick
            ... )
        """
        await self.stream_manager.subscribe_many(symbols, stream_type, provider, callback)

    async def disconnect_streams(self):
        """
        Disconnect all active WebSocket streams.

        Call this when you're done streaming to clean up connections.

        Example:
            >>> # After streaming
            >>> await stream.disconnect_streams()
        """
        await self.stream_manager.disconnect_all()

    # ========================================================================
    # END STREAMING METHODS
    # ========================================================================

    def _detect_asset_type(self, symbol: str) -> str:
        """
        Auto-detect asset type from symbol pattern.

        Args:
            symbol: Trading symbol

        Returns:
            Asset type string
        """
        symbol_upper = symbol.upper()

        # Crypto patterns
        if any(pair in symbol_upper for pair in ['USDT', 'USDC', 'BUSD', 'USD', 'BTC', 'ETH']):
            # Common crypto pairs
            if symbol_upper.endswith('USDT') or symbol_upper.endswith('USDC') or symbol_upper.endswith('BUSD'):
                return 'crypto'
            if '-USD' in symbol_upper or '-BTC' in symbol_upper or '-ETH' in symbol_upper:
                return 'crypto'

        # Forex patterns (6 chars, all caps, e.g., EURUSD)
        if len(symbol_upper) == 6 and symbol_upper.isalpha():
            # Could be forex like EURUSD, GBPJPY
            return 'forex'

        # Economic indicators (typically short codes)
        economic_symbols = ['GDP', 'CPI', 'UNRATE', 'DGS10', 'FEDFUNDS', 'PAYEMS']
        if symbol_upper in economic_symbols:
            return 'economic'

        # Default to equity (stocks, ETFs)
        return 'equity'

    def _select_provider(self, request: DataRequest) -> str:
        """
        Select the best provider for a request.

        Priority:
        1. Explicitly specified provider
        2. Best provider for asset type
        3. First available provider
        """
        # Explicit provider specified
        if request.provider:
            if request.provider in self.providers:
                return request.provider
            else:
                print(f"Warning: Provider '{request.provider}' not available, using fallback")

        # Select based on asset type
        asset_type = request.asset_type.lower()
        if asset_type in self._provider_priority:
            for provider in self._provider_priority[asset_type]:
                if provider in self.providers:
                    return provider

        # Fallback to first available
        if self.providers:
            return list(self.providers.keys())[0]

        raise ValueError("No providers available")

    def _fetch_with_fallback(
        self,
        request: DataRequest,
        primary_provider: str
    ) -> DataResponse:
        """
        Fetch data with automatic fallback on failure.
        """
        # Try primary provider
        if primary_provider in self.providers:
            provider = self.providers[primary_provider]
            try:
                response = provider.fetch_timeseries(
                    symbol=request.symbol,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    interval=request.interval
                )

                if response.success:
                    return response

                print(f"Primary provider {primary_provider} failed: {response.error}")

            except Exception as e:
                print(f"Primary provider {primary_provider} error: {e}")

        # Try fallback providers if enabled
        if self.fallback_enabled:
            # Get priority list for this asset type
            asset_type = request.asset_type.lower()
            priority_list = self._provider_priority.get(asset_type, [])

            # Try providers in priority order
            for provider_name in priority_list:
                if provider_name == primary_provider:
                    continue  # Skip primary, we already tried it

                if provider_name not in self.providers:
                    continue  # Provider not available

                provider = self.providers[provider_name]

                try:
                    print(f"Trying fallback provider: {provider_name}")
                    response = provider.fetch_timeseries(
                        symbol=request.symbol,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        interval=request.interval
                    )

                    if response.success:
                        return response

                except Exception as e:
                    print(f"Fallback provider {provider_name} error: {e}")
                    continue

            # If priority list didn't work, try remaining providers
            for provider_name, provider in self.providers.items():
                if provider_name == primary_provider:
                    continue
                if provider_name in priority_list:
                    continue  # Already tried

                try:
                    print(f"Trying fallback provider: {provider_name}")
                    response = provider.fetch_timeseries(
                        symbol=request.symbol,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        interval=request.interval
                    )

                    if response.success:
                        return response

                except Exception as e:
                    print(f"Fallback provider {provider_name} error: {e}")
                    continue

        # All providers failed
        return DataResponse(
            symbol=request.symbol,
            provider=primary_provider,
            data=[],
            success=False,
            error="All providers failed to fetch data"
        )

    def _response_to_dataframe(self, response: DataResponse) -> pl.DataFrame:
        """
        Convert DataResponse to Polars DataFrame.
        """
        if not response.success or not response.data:
            return pl.DataFrame()

        # Data is already a list of dicts from providers
        # Create Polars DataFrame directly
        df = pl.DataFrame(response.data)

        # Normalize column names to lowercase for consistency
        df = df.rename({col: col.lower().replace(' ', '_') for col in df.columns})

        # Normalize column names and handle timestamps
        # Check for various timestamp column names
        timestamp_cols = ['timestamp', 'date', 'datetime']
        for col in timestamp_cols:
            if col in df.columns:
                # Try multiple parsing strategies
                # Use strict=True and catch exceptions, or check for nulls
                parsed = False
                original_df = df.clone()

                # Define parsing strategies in order of specificity
                parsing_strategies = [
                    # ISO format with microseconds
                    lambda c: pl.col(c).str.strptime(pl.Datetime, format='%Y-%m-%dT%H:%M:%S%.f', strict=False),
                    # ISO format without microseconds
                    lambda c: pl.col(c).str.strptime(pl.Datetime, format='%Y-%m-%dT%H:%M:%S', strict=False),
                    # ISO format with timezone
                    lambda c: pl.col(c).str.strptime(pl.Datetime, format='%Y-%m-%dT%H:%M:%S%:z', strict=False),
                    # Simple date format (YYYY-MM-DD)
                    lambda c: pl.col(c).str.strptime(pl.Datetime, format='%Y-%m-%d', strict=False),
                    # Polars auto-parse
                    lambda c: pl.col(c).str.to_datetime(),
                ]

                for strategy in parsing_strategies:
                    if parsed:
                        break
                    try:
                        test_df = original_df.with_columns(
                            strategy(col).alias('timestamp')
                        )
                        # Check if parsing produced non-null values
                        non_null_count = len(test_df) - test_df['timestamp'].null_count()
                        if non_null_count > 0:
                            df = test_df
                            parsed = True
                    except Exception:
                        pass

                if not parsed:
                    # If all else fails, keep original column renamed
                    if col != 'timestamp':
                        df = df.rename({col: 'timestamp'})

                if col != 'timestamp' and 'timestamp' in df.columns:
                    df = df.drop(col)
                break

        # Sort by timestamp if present
        if 'timestamp' in df.columns:
            df = df.sort('timestamp')

        return df

    def _options_to_dataframe(self, response: OptionsChainResponse) -> pl.DataFrame:
        """
        Convert OptionsChainResponse to Polars DataFrame.
        """
        if not response.success or not response.contracts:
            return pl.DataFrame()

        # Convert contracts to list of dicts (they might be Pydantic or dicts)
        data = []
        for contract in response.contracts:
            if hasattr(contract, 'model_dump'):
                data.append(contract.model_dump())
            else:
                data.append(contract)

        # Create Polars DataFrame
        df = pl.DataFrame(data)

        return df

    def status(self) -> Dict[str, Any]:
        """
        Get status of all providers.

        Returns:
            Dictionary with provider status information

        Example:
            >>> status = stream.status()
            >>> print(status)
            {
                'yfinance': {'connected': True, 'supports_options': True},
                'binance': {'connected': True, 'supports_options': False}
            }
        """
        status = {}

        for name, provider in self.providers.items():
            try:
                is_connected = provider.validate_connection()
                status[name] = {
                    'connected': is_connected,
                    'supports_options': hasattr(provider, 'fetch_options_chain'),
                    'supports_historical_options': provider.supports_historical_options(),
                }
            except Exception as e:
                status[name] = {
                    'connected': False,
                    'error': str(e)
                }

        return status

    def __repr__(self) -> str:
        """String representation."""
        providers = ", ".join(self.providers.keys())
        return f"DataStream(providers=[{providers}])"
