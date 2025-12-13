"""
Coinbase provider for crypto market data.

Public market data available without authentication.
Supports historical OHLCV data via REST API.

For real-time streaming, see coinbase_stream.py

API Docs: https://docs.cloud.coinbase.com/exchange/docs
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class CoinbaseProvider(BaseProvider):
    """
    Coinbase Pro/Advanced Trade provider for crypto historical data.

    No API key required for public market data.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        super().__init__(name="coinbase", api_key=api_key)
        self.base_url = "https://api.exchange.coinbase.com"
        self.api_secret = api_secret

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical candle data from Coinbase.

        Args:
            symbol: Trading pair (e.g., "BTC-USD", "ETH-USD")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Granularity - "1m", "5m", "15m", "1h", "6h", "1d"

        Returns:
            DataResponse with OHLCV data
        """
        try:
            # Normalize symbol (add dash if missing)
            if '-' not in symbol:
                # Try to split common crypto pairs
                symbol = self._normalize_symbol(symbol)

            # Map interval to Coinbase granularity (in seconds)
            granularity_map = {
                '1m': 60,
                '5m': 300,
                '15m': 900,
                '1h': 3600,
                '6h': 21600,
                '1d': 86400,
            }
            granularity = granularity_map.get(interval, 86400)

            # Convert dates to datetime
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # Coinbase limits to 300 candles per request - paginate if needed
            max_candles = 300
            chunk_seconds = granularity * max_candles

            url = f"{self.base_url}/products/{symbol}/candles"
            all_candles = []

            current_start = start_dt
            while current_start < end_dt:
                # Calculate chunk end (max 300 candles worth)
                from datetime import timedelta
                chunk_end = min(current_start + timedelta(seconds=chunk_seconds), end_dt)

                params = {
                    'start': current_start.isoformat(),
                    'end': chunk_end.isoformat(),
                    'granularity': granularity
                }

                # Make request
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()

                candles = response.json()

                # Check if it's an error response
                if isinstance(candles, dict) and 'message' in candles:
                    return DataResponse(
                        symbol=symbol,
                        provider=self.name,
                        data=[],
                        success=False,
                        error=candles['message']
                    )

                if candles:
                    all_candles.extend(candles)

                # Move to next chunk
                current_start = chunk_end

            if not all_candles:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol}"
                )

            # Coinbase returns: [timestamp, low, high, open, close, volume]
            # Deduplicate by timestamp (in case of overlap)
            seen_timestamps = set()
            records = []
            for candle in all_candles:
                ts = candle[0]
                if ts not in seen_timestamps:
                    seen_timestamps.add(ts)
                    timestamp = datetime.fromtimestamp(ts)
                    records.append({
                        'Date': timestamp.isoformat(),
                        'open': float(candle[3]),
                        'high': float(candle[2]),
                        'low': float(candle[1]),
                        'close': float(candle[4]),
                        'volume': float(candle[5]),
                    })

            # Sort by date (oldest first)
            records.sort(key=lambda x: x['Date'])

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'interval': interval,
                    'granularity': granularity,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(records),
                    'source': 'Coinbase Exchange'
                },
                success=True
            )

        except requests.exceptions.RequestException as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Coinbase API request failed: {str(e)}"
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Coinbase format (e.g., BTC-USD).

        Args:
            symbol: Symbol like "BTCUSD" or "BTC-USD"

        Returns:
            Normalized symbol with dash
        """
        symbol = symbol.upper()

        # Already has dash
        if '-' in symbol:
            return symbol

        # Common base currencies
        quote_currencies = ['USD', 'USDT', 'EUR', 'GBP', 'BTC', 'ETH']

        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-{quote}"

        # Default: assume USD
        return f"{symbol}-USD"

    def get_products(self) -> List[dict]:
        """
        Get list of all available trading pairs on Coinbase.

        Returns:
            List of product dictionaries

        Example:
            >>> provider = CoinbaseProvider()
            >>> products = provider.get_products()
            >>> for product in products[:5]:
            ...     print(f"{product['id']}: {product['display_name']}")
        """
        try:
            url = f"{self.base_url}/products"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            products = response.json()
            return products

        except Exception as e:
            print(f"Failed to get Coinbase products: {e}")
            return []

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """Coinbase does not provide options data."""
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="Coinbase does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Coinbase does not provide options data."""
        return []

    def validate_connection(self) -> bool:
        """
        Validate Coinbase API connection.

        Tests by fetching server time.
        """
        try:
            url = f"{self.base_url}/time"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            return 'iso' in data or 'epoch' in data

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """Coinbase does not support options."""
        return False


# Popular Coinbase trading pairs
POPULAR_PAIRS = [
    'BTC-USD', 'ETH-USD', 'BNB-USD', 'SOL-USD', 'ADA-USD',
    'XRP-USD', 'DOT-USD', 'DOGE-USD', 'AVAX-USD', 'MATIC-USD',
    'LINK-USD', 'UNI-USD', 'ATOM-USD', 'LTC-USD', 'BCH-USD',
    'NEAR-USD', 'ALGO-USD', 'VET-USD', 'FIL-USD', 'TRX-USD',
]
