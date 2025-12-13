"""
Generic CCXT provider for accessing 100+ cryptocurrency exchanges.

CCXT (CryptoCurrency eXchange Trading Library) provides a unified API
for interacting with cryptocurrency exchanges worldwide.

Supported exchanges: Binance, Coinbase, Kraken, Bybit, OKX, KuCoin,
Gate.io, Bitfinex, Gemini, Huobi, and 90+ more.

API Docs: https://docs.ccxt.com/
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import ccxt

from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
)


class CCXTProvider(BaseProvider):
    """
    Generic CCXT provider for cryptocurrency market data.

    Can connect to any of the 100+ exchanges supported by CCXT.

    Features:
    - Unified API across all exchanges
    - Historical OHLCV data
    - Real-time ticker data
    - Order book data
    - Recent trades

    Popular exchanges:
    - binance, coinbase, kraken, bybit, okx, kucoin
    - gateio, bitfinex, gemini, huobi, bitget
    - mexc, bitmart, bingx, and many more
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        **exchange_params
    ):
        """
        Initialize CCXT provider for a specific exchange.

        Args:
            exchange_id: CCXT exchange ID (e.g., 'binance', 'kraken', 'coinbase')
            api_key: Optional API key for the exchange
            api_secret: Optional API secret
            **exchange_params: Additional exchange-specific parameters
        """
        super().__init__(name=f"ccxt_{exchange_id}", api_key=api_key)

        # Get the exchange class from ccxt
        if not hasattr(ccxt, exchange_id):
            raise ValueError(
                f"Exchange '{exchange_id}' not supported by CCXT. "
                f"Available exchanges: {', '.join(ccxt.exchanges[:20])}..."
            )

        exchange_class = getattr(ccxt, exchange_id)

        # Configure exchange
        config = {
            'enableRateLimit': True,
            'timeout': 30000,
        }

        # Add API credentials if provided
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret

        # Add custom parameters
        config.update(exchange_params)

        # Initialize exchange
        self.exchange = exchange_class(config)
        self.exchange_id = exchange_id

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to CCXT format (slash-separated).

        Converts 'BTC-USD' -> 'BTC/USD', 'ETH-USDT' -> 'ETH/USDT'

        Args:
            symbol: Symbol in any format

        Returns:
            Symbol in CCXT format (slash-separated)
        """
        # Replace dash with slash for CCXT
        if '-' in symbol:
            symbol = symbol.replace('-', '/')

        return symbol

    def _find_symbol_on_exchange(self, symbol: str) -> Optional[str]:
        """
        Try to find a matching symbol on the exchange.

        CCXT exchanges may have different symbol formats or naming.
        This method tries common variations.

        Args:
            symbol: Symbol to find

        Returns:
            Matching symbol on exchange, or None if not found
        """
        try:
            # Load markets if not already loaded
            if not self.exchange.markets:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"  Loading markets for {self.exchange_id}...")
                self.exchange.load_markets()
                logger.debug(f"  Loaded {len(self.exchange.markets)} markets for {self.exchange_id}")

            # Normalize to slash format
            normalized = self._normalize_symbol(symbol)

            # First: Try exact match
            if normalized in self.exchange.markets:
                return normalized

            # Second: Try common variations
            base_quote = normalized.split('/')
            if len(base_quote) == 2:
                base, quote = base_quote

                # For USD pairs, prioritize USDT (most common on crypto exchanges)
                # Then try other stablecoins
                if quote == 'USD':
                    variations_to_try = ['USDT', 'USDC', 'USD', 'BUSD', 'TUSD', 'DAI']
                elif quote == 'USDT':
                    variations_to_try = ['USDT', 'USD', 'USDC', 'BUSD']
                elif quote == 'USDC':
                    variations_to_try = ['USDC', 'USDT', 'USD', 'BUSD']
                else:
                    # For other quotes, just try the original
                    variations_to_try = [quote]

                for alt_quote in variations_to_try:
                    alt_symbol = f"{base}/{alt_quote}"
                    if alt_symbol in self.exchange.markets:
                        import logging
                        logger = logging.getLogger(__name__)
                        if alt_quote != quote:
                            logger.info(f"  {symbol} → {alt_symbol} on {self.exchange_id}")
                        return alt_symbol

            # No variation found
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"  No match for {symbol} on {self.exchange_id} (tried: {variations_to_try})")
            return None

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"  Symbol lookup exception for {symbol} on {self.exchange_id}: {e}")
            return None

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical OHLCV data from the exchange with automatic pagination.

        Handles large date ranges by making multiple paginated requests.
        For Binance: fetches up to 7-8 years of 1-minute data automatically.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT', 'ETH/USD', 'BTC-USD')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval (1m, 5m, 15m, 1h, 1d, etc.)
            **kwargs: Additional parameters

        Returns:
            DataResponse with OHLCV data
        """
        try:
            # Find the symbol on this exchange
            import logging
            logger = logging.getLogger(__name__)

            exchange_symbol = self._find_symbol_on_exchange(symbol)

            if not exchange_symbol:
                error_msg = f"Symbol {symbol} not found on {self.exchange_id}"
                logger.warning(f"  {error_msg}")
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=error_msg
                )

            # Parse dates to timestamps (milliseconds)
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

            # Map intervals to ccxt format
            interval_map = {
                '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m',
                '30m': '30m', '1h': '1h', '2h': '2h', '4h': '4h',
                '6h': '6h', '12h': '12h', '1d': '1d', '1w': '1w', '1M': '1M',
            }

            timeframe = interval_map.get(interval, interval)

            # Check if exchange supports this timeframe
            if self.exchange.timeframes and timeframe not in self.exchange.timeframes:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"Timeframe {timeframe} not supported by {self.exchange_id}"
                )

            # Fetch OHLCV data with pagination
            all_ohlcv = []
            current_ts = start_ts

            # Limit per request (most exchanges support 500-1000)
            limit = 1000 if self.exchange_id == 'binance' else 500

            # Calculate milliseconds per candle for this interval
            interval_to_ms = {
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
                '1M': 30 * 24 * 60 * 60 * 1000,  # Approximate
            }
            ms_per_candle = interval_to_ms.get(timeframe, 60 * 1000)

            # Paginate through data
            max_iterations = 10000  # Safety limit
            iterations = 0

            # Estimate total iterations needed
            total_ms = end_ts - start_ts
            estimated_iterations = (total_ms // (ms_per_candle * limit)) + 1

            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Starting pagination for {symbol} on {self.exchange_id}: ~{estimated_iterations} requests needed")

            while current_ts < end_ts and iterations < max_iterations:
                try:
                    # Fetch batch
                    ohlcv = self.exchange.fetch_ohlcv(
                        symbol=exchange_symbol,
                        timeframe=timeframe,
                        since=current_ts,
                        limit=limit
                    )

                    if not ohlcv:
                        break

                    # Add to results
                    all_ohlcv.extend(ohlcv)

                    # Update current_ts to continue from last candle
                    last_ts = ohlcv[-1][0]

                    # If we got less than limit, we've reached the end
                    if len(ohlcv) < limit:
                        break

                    # Move to next batch (add 1ms to avoid duplicate)
                    current_ts = last_ts + ms_per_candle

                    iterations += 1

                    # Log progress every 50 requests
                    if iterations % 50 == 0:
                        progress_pct = (iterations / estimated_iterations) * 100 if estimated_iterations > 0 else 0
                        logger.info(f"  {symbol}: Fetched {len(all_ohlcv):,} candles ({iterations}/{int(estimated_iterations)} requests, {progress_pct:.0f}%)")

                    # Rate limiting (be nice to the exchange)
                    if iterations % 5 == 0:
                        import time
                        time.sleep(0.1)  # 100ms pause every 5 requests

                except Exception as e:
                    # If we have some data, return it; otherwise raise
                    if all_ohlcv:
                        break
                    else:
                        raise e

            # Log completion
            logger.info(f"  {symbol}: Pagination complete - fetched {len(all_ohlcv):,} candles in {iterations} requests")

            # Filter by end date and remove duplicates
            seen_timestamps = set()
            filtered_ohlcv = []
            for candle in all_ohlcv:
                if candle[0] <= end_ts and candle[0] not in seen_timestamps:
                    seen_timestamps.add(candle[0])
                    filtered_ohlcv.append(candle)

            if not filtered_ohlcv:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="No data found for the specified date range"
                )

            # Convert to standard format
            data = []
            for candle in filtered_ohlcv:
                timestamp, open_price, high, low, close, volume = candle
                data.append({
                    'timestamp': datetime.fromtimestamp(timestamp / 1000).isoformat(),
                    'open': float(open_price),
                    'high': float(high),
                    'low': float(low),
                    'close': float(close),
                    'volume': float(volume)
                })

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=data,
                success=True,
                metadata={
                    'exchange_symbol': exchange_symbol,
                    'exchange': self.exchange_id,
                    'requests_made': iterations,
                    'candles_fetched': len(data),
                }
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"{self.exchange_id}: {str(e)}"
            )

    def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for trading pairs on this exchange.

        Args:
            query: Search query (e.g., 'BTC', 'ETH', 'SOL')
            limit: Maximum number of results

        Returns:
            List of symbol information dicts
        """
        try:
            # Load markets if not already loaded
            if not self.exchange.markets:
                self.exchange.load_markets()

            results = []
            query_upper = query.upper()

            # Search through available markets
            for symbol, market in self.exchange.markets.items():
                # Match query in symbol or base/quote currency
                if (query_upper in symbol or
                    query_upper in market.get('base', '') or
                    query_upper in market.get('quote', '')):

                    results.append({
                        'symbol': symbol,
                        'name': f"{market.get('base', '')}/{market.get('quote', '')}",
                        'type': market.get('type', 'spot'),
                        'provider': self.name,
                        'exchange': self.exchange_id.title(),
                        'active': market.get('active', True),
                    })

                    if len(results) >= limit:
                        break

            return results

        except Exception as e:
            print(f"Warning: CCXT {self.exchange_id} search failed: {e}")
            return []

    def get_available_exchanges(self) -> List[str]:
        """Get list of all exchanges supported by CCXT."""
        return ccxt.exchanges

    def validate_connection(self) -> bool:
        """Validate connection to exchange."""
        try:
            # Try to load markets
            self.exchange.load_markets()
            return True
        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """CCXT providers generally don't support options."""
        return False

    def get_available_expirations(self, symbol: str) -> List[date]:
        """CCXT providers don't support options, so no expirations."""
        return []

    def fetch_options_chain(
        self, request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """CCXT providers generally don't support options."""
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            contracts=[],
            success=False,
            error="Options trading not supported on most crypto exchanges"
        )
