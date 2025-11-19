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

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical OHLCV data from the exchange.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT', 'ETH/USD')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval (1m, 5m, 15m, 1h, 1d, etc.)
            **kwargs: Additional parameters

        Returns:
            DataResponse with OHLCV data
        """
        try:
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

            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=start_ts,
                limit=None  # Fetch all data in range
            )

            # Filter by end date
            ohlcv = [candle for candle in ohlcv if candle[0] <= end_ts]

            if not ohlcv:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="No data found for the specified date range"
                )

            # Convert to standard format
            data = []
            for candle in ohlcv:
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
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=str(e)
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
