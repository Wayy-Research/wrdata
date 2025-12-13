"""
Async parallel OHLCV fetcher for high-speed historical data retrieval.

Instead of sequential pagination, this module pre-calculates time windows
and fetches them concurrently, dramatically speeding up large data pulls.

Example:
    # 1 year of 1-minute data in ~10 seconds instead of ~5 minutes
    fetcher = AsyncOHLCVFetcher(exchange_id='binance', max_concurrent=10)
    data = await fetcher.fetch('BTC/USDT', start='2024-01-01', end='2024-12-01', interval='1m')
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time


@dataclass
class TimeWindow:
    """A time window for parallel fetching."""
    start_ts: int  # milliseconds
    end_ts: int    # milliseconds
    index: int     # for ordering results


@dataclass
class FetchResult:
    """Result from a single window fetch."""
    window: TimeWindow
    data: List[List]  # OHLCV candles
    success: bool
    error: Optional[str] = None


class AsyncOHLCVFetcher:
    """
    High-speed parallel OHLCV data fetcher using asyncio.

    Key features:
    - Pre-calculates time windows for parallel fetching
    - Rate limiting with semaphores
    - Automatic retries with exponential backoff
    - Result merging and deduplication

    Typical speedup: 5-20x faster than sequential fetching.
    """

    # Provider-specific configurations
    PROVIDER_CONFIG = {
        'binance': {
            'max_candles': 1000,
            'rate_limit_per_sec': 10,
            'base_url': 'https://api.binance.com/api/v3/klines',
        },
        'coinbase': {
            'max_candles': 300,
            'rate_limit_per_sec': 5,
            'base_url': 'https://api.exchange.coinbase.com/products/{symbol}/candles',
        },
        'kraken': {
            'max_candles': 720,
            'rate_limit_per_sec': 3,
            'base_url': 'https://api.kraken.com/0/public/OHLC',
        },
    }

    # Interval to milliseconds
    INTERVAL_MS = {
        '1m': 60 * 1000,
        '3m': 3 * 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '2h': 2 * 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '6h': 6 * 60 * 60 * 1000,
        '12h': 12 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000,
        '1w': 7 * 24 * 60 * 60 * 1000,
    }

    def __init__(
        self,
        provider: str = 'binance',
        max_concurrent: int = 10,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize the async fetcher.

        Args:
            provider: Exchange/provider name ('binance', 'coinbase', 'kraken')
            max_concurrent: Maximum concurrent requests (default: 10)
            max_retries: Max retries per failed request (default: 3)
            timeout: Request timeout in seconds (default: 30)
        """
        self.provider = provider.lower()
        self.config = self.PROVIDER_CONFIG.get(self.provider, self.PROVIDER_CONFIG['binance'])
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.timeout = timeout

        # Rate limiting
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._rate_limiter: Optional[asyncio.Semaphore] = None

    def _calculate_time_windows(
        self,
        start_ts: int,
        end_ts: int,
        interval: str,
    ) -> List[TimeWindow]:
        """
        Pre-calculate all time windows for parallel fetching.

        Args:
            start_ts: Start timestamp in milliseconds
            end_ts: End timestamp in milliseconds
            interval: Candle interval (e.g., '1m', '1h', '1d')

        Returns:
            List of TimeWindow objects
        """
        ms_per_candle = self.INTERVAL_MS.get(interval, 60 * 1000)
        max_candles = self.config['max_candles']
        window_size_ms = max_candles * ms_per_candle

        windows = []
        current_start = start_ts
        index = 0

        while current_start < end_ts:
            window_end = min(current_start + window_size_ms, end_ts)
            windows.append(TimeWindow(
                start_ts=current_start,
                end_ts=window_end,
                index=index,
            ))
            current_start = window_end
            index += 1

        return windows

    async def _fetch_window_binance(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        window: TimeWindow,
        interval: str,
    ) -> FetchResult:
        """Fetch a single window from Binance."""
        params = {
            'symbol': symbol.replace('/', '').replace('-', ''),
            'interval': interval,
            'startTime': window.start_ts,
            'endTime': window.end_ts,
            'limit': self.config['max_candles'],
        }

        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    async with session.get(
                        self.config['base_url'],
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            # Binance format: [open_time, open, high, low, close, volume, ...]
                            # Convert to standard: [timestamp, open, high, low, close, volume]
                            candles = [
                                [c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
                                for c in data
                            ]
                            return FetchResult(window=window, data=candles, success=True)
                        elif response.status == 429:
                            # Rate limited - wait and retry
                            await asyncio.sleep(2 ** attempt)
                        else:
                            text = await response.text()
                            return FetchResult(
                                window=window, data=[], success=False,
                                error=f"HTTP {response.status}: {text[:200]}"
                            )
                except asyncio.TimeoutError:
                    if attempt == self.max_retries - 1:
                        return FetchResult(window=window, data=[], success=False, error="Timeout")
                    await asyncio.sleep(1)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        return FetchResult(window=window, data=[], success=False, error=str(e))
                    await asyncio.sleep(1)

        return FetchResult(window=window, data=[], success=False, error="Max retries exceeded")

    async def _fetch_window_coinbase(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        window: TimeWindow,
        interval: str,
    ) -> FetchResult:
        """Fetch a single window from Coinbase."""
        # Coinbase granularity in seconds
        granularity_map = {
            '1m': 60, '5m': 300, '15m': 900,
            '1h': 3600, '6h': 21600, '1d': 86400,
        }
        granularity = granularity_map.get(interval, 86400)

        # Normalize symbol to Coinbase format (BTC-USD)
        if '/' in symbol:
            symbol = symbol.replace('/', '-')
        elif '-' not in symbol:
            # Try to split (BTCUSD -> BTC-USD)
            for quote in ['USD', 'USDT', 'EUR', 'GBP', 'BTC', 'ETH']:
                if symbol.upper().endswith(quote):
                    base = symbol[:-len(quote)]
                    symbol = f"{base}-{quote}"
                    break

        url = self.config['base_url'].format(symbol=symbol.upper())

        # Coinbase uses ISO format
        start_iso = datetime.utcfromtimestamp(window.start_ts / 1000).isoformat()
        end_iso = datetime.utcfromtimestamp(window.end_ts / 1000).isoformat()

        params = {
            'start': start_iso,
            'end': end_iso,
            'granularity': granularity,
        }

        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    async with session.get(
                        url,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, dict) and 'message' in data:
                                return FetchResult(
                                    window=window, data=[], success=False,
                                    error=data['message']
                                )
                            # Coinbase format: [timestamp, low, high, open, close, volume]
                            # Convert to standard: [timestamp_ms, open, high, low, close, volume]
                            candles = [
                                [c[0] * 1000, float(c[3]), float(c[2]), float(c[1]), float(c[4]), float(c[5])]
                                for c in data
                            ]
                            return FetchResult(window=window, data=candles, success=True)
                        elif response.status == 429:
                            await asyncio.sleep(2 ** attempt)
                        else:
                            text = await response.text()
                            return FetchResult(
                                window=window, data=[], success=False,
                                error=f"HTTP {response.status}: {text[:200]}"
                            )
                except asyncio.TimeoutError:
                    if attempt == self.max_retries - 1:
                        return FetchResult(window=window, data=[], success=False, error="Timeout")
                    await asyncio.sleep(1)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        return FetchResult(window=window, data=[], success=False, error=str(e))
                    await asyncio.sleep(1)

        return FetchResult(window=window, data=[], success=False, error="Max retries exceeded")

    async def _fetch_window(
        self,
        session: aiohttp.ClientSession,
        symbol: str,
        window: TimeWindow,
        interval: str,
    ) -> FetchResult:
        """Route to appropriate provider fetch method."""
        if self.provider == 'binance':
            return await self._fetch_window_binance(session, symbol, window, interval)
        elif self.provider == 'coinbase':
            return await self._fetch_window_coinbase(session, symbol, window, interval)
        else:
            # Default to binance-style
            return await self._fetch_window_binance(session, symbol, window, interval)

    async def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = '1d',
        progress_callback: Optional[callable] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV data in parallel.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT', 'ETH-USD')
            start: Start date as 'YYYY-MM-DD'
            end: End date as 'YYYY-MM-DD'
            interval: Candle interval (default: '1d')
            progress_callback: Optional callback(completed, total) for progress

        Returns:
            List of OHLCV dictionaries sorted by timestamp
        """
        # Parse dates to timestamps
        start_ts = int(datetime.strptime(start, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end, '%Y-%m-%d').timestamp() * 1000)

        # Calculate windows
        windows = self._calculate_time_windows(start_ts, end_ts, interval)

        if not windows:
            return []

        # Initialize semaphore for concurrency control
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            # Create tasks for all windows
            tasks = [
                self._fetch_window(session, symbol, window, interval)
                for window in windows
            ]

            # Execute all tasks concurrently
            results: List[FetchResult] = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Sort results by window index
        results.sort(key=lambda r: r.window.index)

        # Merge all candles
        all_candles = []
        failed_windows = 0
        for result in results:
            if result.success:
                all_candles.extend(result.data)
            else:
                failed_windows += 1

        # Deduplicate by timestamp
        seen = set()
        unique_candles = []
        for candle in all_candles:
            ts = candle[0]
            if ts not in seen:
                seen.add(ts)
                unique_candles.append(candle)

        # Sort by timestamp
        unique_candles.sort(key=lambda c: c[0])

        # Convert to dict format
        data = []
        for candle in unique_candles:
            timestamp, open_p, high, low, close, volume = candle
            data.append({
                'timestamp': datetime.utcfromtimestamp(timestamp / 1000).isoformat(),
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
            })

        # Log performance
        candles_per_sec = len(data) / elapsed if elapsed > 0 else 0
        print(f"Fetched {len(data):,} candles in {elapsed:.1f}s ({candles_per_sec:,.0f}/sec) "
              f"from {len(windows)} windows ({failed_windows} failed)")

        return data


class AsyncCCXTFetcher:
    """
    Async OHLCV fetcher using CCXT's async support.

    Uses ccxt.async_support for native async exchange access.
    """

    INTERVAL_MS = AsyncOHLCVFetcher.INTERVAL_MS

    def __init__(
        self,
        exchange_id: str = 'binance',
        max_concurrent: int = 10,
        max_retries: int = 3,
    ):
        self.exchange_id = exchange_id
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self._exchange = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def _get_exchange(self):
        """Lazy initialize async exchange."""
        if self._exchange is None:
            import ccxt.async_support as ccxt_async
            if not hasattr(ccxt_async, self.exchange_id):
                raise ValueError(f"Exchange '{self.exchange_id}' not supported by CCXT")
            exchange_class = getattr(ccxt_async, self.exchange_id)
            self._exchange = exchange_class({
                'enableRateLimit': True,
                'timeout': 30000,
            })
            try:
                await self._exchange.load_markets()
            except Exception as e:
                await self._exchange.close()
                self._exchange = None
                raise RuntimeError(f"Failed to connect to {self.exchange_id}: {e}")
        return self._exchange

    async def _fetch_window(
        self,
        symbol: str,
        start_ts: int,
        end_ts: int,
        interval: str,
        limit: int,
    ) -> Tuple[List, Optional[str]]:
        """Fetch a single time window."""
        exchange = await self._get_exchange()

        async with self._semaphore:
            for attempt in range(self.max_retries):
                try:
                    ohlcv = await exchange.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=interval,
                        since=start_ts,
                        limit=limit,
                    )
                    return ohlcv, None
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        return [], str(e)
                    await asyncio.sleep(0.5 * (attempt + 1))

        return [], "Max retries exceeded"

    async def fetch(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = '1d',
    ) -> List[Dict[str, Any]]:
        """
        Fetch OHLCV data in parallel using CCXT async.

        Args:
            symbol: Trading pair in CCXT format (e.g., 'BTC/USDT')
            start: Start date 'YYYY-MM-DD'
            end: End date 'YYYY-MM-DD'
            interval: Candle interval

        Returns:
            List of OHLCV dictionaries
        """
        exchange = await self._get_exchange()

        # Normalize symbol
        if '-' in symbol:
            symbol = symbol.replace('-', '/')

        # Check if symbol exists
        if symbol not in exchange.markets:
            # Try common variations
            base = symbol.split('/')[0] if '/' in symbol else symbol[:-4]
            for quote in ['USDT', 'USD', 'USDC', 'BUSD']:
                alt = f"{base}/{quote}"
                if alt in exchange.markets:
                    symbol = alt
                    break

        # Parse dates
        start_ts = int(datetime.strptime(start, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end, '%Y-%m-%d').timestamp() * 1000)

        # Calculate window parameters
        ms_per_candle = self.INTERVAL_MS.get(interval, 60 * 1000)
        limit = 1000 if self.exchange_id == 'binance' else 500
        window_size = limit * ms_per_candle

        # Generate all time windows
        windows = []
        current = start_ts
        while current < end_ts:
            windows.append(current)
            current += window_size

        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        start_time = time.time()

        # Fetch all windows in parallel
        tasks = [
            self._fetch_window(symbol, w, min(w + window_size, end_ts), interval, limit)
            for w in windows
        ]

        results = await asyncio.gather(*tasks)

        # Close exchange connection
        if self._exchange:
            try:
                await self._exchange.close()
            except Exception:
                pass
            self._exchange = None

        elapsed = time.time() - start_time

        # Merge results
        all_candles = []
        errors = 0
        for ohlcv, error in results:
            if error:
                errors += 1
            else:
                all_candles.extend(ohlcv)

        # Deduplicate and filter by end date
        seen = set()
        unique = []
        for candle in all_candles:
            ts = candle[0]
            if ts <= end_ts and ts not in seen:
                seen.add(ts)
                unique.append(candle)

        unique.sort(key=lambda c: c[0])

        # Convert to dict format
        data = []
        for c in unique:
            data.append({
                'timestamp': datetime.utcfromtimestamp(c[0] / 1000).isoformat(),
                'open': float(c[1]),
                'high': float(c[2]),
                'low': float(c[3]),
                'close': float(c[4]),
                'volume': float(c[5]),
            })

        rate = len(data) / elapsed if elapsed > 0 else 0
        print(f"Fetched {len(data):,} candles in {elapsed:.1f}s ({rate:,.0f}/sec) "
              f"via {self.exchange_id} ({errors} errors)")

        return data


# Convenience function for quick fetching
async def fast_fetch(
    symbol: str,
    start: str,
    end: str,
    interval: str = '1d',
    provider: str = 'binance',
    max_concurrent: int = 10,
) -> List[Dict[str, Any]]:
    """
    Quick async fetch for OHLCV data.

    Usage:
        import asyncio
        from wrdata.utils.async_fetch import fast_fetch

        data = asyncio.run(fast_fetch('BTC/USDT', '2024-01-01', '2024-12-01', '1m'))
    """
    fetcher = AsyncCCXTFetcher(
        exchange_id=provider,
        max_concurrent=max_concurrent,
    )
    return await fetcher.fetch(symbol, start, end, interval)
