"""
Binance provider for fetching cryptocurrency OHLCV data.
Uses ccxt library for unified exchange interface.
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


class BinanceProvider(BaseProvider):
    """
    Binance provider implementation using ccxt.
    Supports crypto spot and futures OHLCV data.
    Does not support options (Binance doesn't offer options trading).
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Binance provider.

        Args:
            api_key: Optional Binance API key (increases rate limits)
            api_secret: Optional Binance API secret
        """
        super().__init__(name="binance", api_key=api_key)

        # Initialize ccxt Binance exchange
        config = {
            'enableRateLimit': True,  # Enable built-in rate limiting
            'options': {
                'defaultType': 'spot',  # Default to spot market
            }
        }

        # Add API credentials if provided
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret

        self.exchange = ccxt.binance(config)
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
        Fetch historical OHLCV data from Binance.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval (1m, 5m, 15m, 1h, 1d, etc.)
            **kwargs: Additional parameters like 'market_type' (spot/future)

        Returns:
            DataResponse with OHLCV data
        """
        try:
            # Parse dates to timestamps (milliseconds)
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

            # Map common intervals to ccxt/Binance format
            interval_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '4h': '4h',
                '1d': '1d',
                '1w': '1w',
                '1M': '1M',
            }

            timeframe = interval_map.get(interval, interval)

            # Switch market type if specified
            market_type = kwargs.get('market_type', 'spot')
            if market_type in ['future', 'futures']:
                self.exchange.options['defaultType'] = 'future'
            else:
                self.exchange.options['defaultType'] = 'spot'

            # Fetch OHLCV data
            # ccxt returns: [timestamp, open, high, low, close, volume]
            all_ohlcv = []

            # Binance limits responses to 1000 candles, so we need to paginate
            current_start = start_ts
            limit = 1000  # Maximum per request

            while current_start < end_ts:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    since=current_start,
                    limit=limit
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # Update start time for next iteration
                last_timestamp = ohlcv[-1][0]

                # Break if we've reached the end or no new data
                if last_timestamp >= end_ts or last_timestamp <= current_start:
                    break

                current_start = last_timestamp + 1

            # Filter data to exact date range
            all_ohlcv = [
                candle for candle in all_ohlcv
                if start_ts <= candle[0] <= end_ts
            ]

            if not all_ohlcv:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol} in the specified date range"
                )

            # Convert to list of dicts with proper column names
            data = []
            for candle in all_ohlcv:
                data.append({
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                })

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=data,
                metadata={
                    'interval': interval,
                    'timeframe': timeframe,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(data),
                    'market_type': market_type,
                },
                success=True
            )

        except ccxt.NetworkError as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Network error: {str(e)}"
            )
        except ccxt.ExchangeError as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Exchange error: {str(e)}"
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Binance does not support options trading.

        Raises:
            NotImplementedError: Always, as Binance doesn't offer options
        """
        raise NotImplementedError(
            "Binance does not support options trading. "
            "Use a different provider for options data."
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """
        Binance does not support options trading.

        Returns:
            Empty list (no options available)
        """
        return []

    def validate_connection(self) -> bool:
        """
        Validate that the Binance connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Try to fetch exchange status
            status = self.exchange.fetch_status()

            # Check if exchange is operational
            if status and status.get('status') == 'ok':
                return True

            # Fallback: try fetching a known ticker
            ticker = self.exchange.fetch_ticker('BTC/USDT')
            return ticker is not None and 'last' in ticker

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """
        Binance does not support options.

        Returns:
            False
        """
        return False

    def get_supported_symbols(self) -> List[str]:
        """
        Get list of all trading pairs available on Binance.

        Returns:
            List of symbol strings (e.g., ['BTC/USDT', 'ETH/USDT', ...])
        """
        try:
            markets = self.exchange.load_markets()
            return list(markets.keys())
        except Exception as e:
            print(f"Error fetching Binance symbols: {e}")
            return []

    def get_market_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed market information for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')

        Returns:
            Dictionary with market info or None if not found
        """
        try:
            markets = self.exchange.load_markets()
            return markets.get(symbol)
        except Exception as e:
            print(f"Error fetching market info for {symbol}: {e}")
            return None
