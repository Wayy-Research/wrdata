"""
TwelveData provider for multi-asset market data.

TwelveData offers excellent global coverage with generous free tier.
Free tier: 800 API calls/day, 8 calls/minute

Get your free API key: https://twelvedata.com/pricing
No credit card required!

API Docs: https://twelvedata.com/docs
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class TwelveDataProvider(BaseProvider):
    """
    TwelveData provider for global market data.

    Free tier includes:
    - 800 API calls/day
    - 8 calls/minute
    - Stocks, Forex, Crypto, ETFs, Indices
    - Real-time & historical data
    - WebSocket streaming (1 symbol)
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="twelvedata", api_key=api_key)

        if not api_key:
            raise ValueError(
                "TwelveData API key required. "
                "Get FREE key at: https://twelvedata.com/pricing\n"
                "Free tier: 800 calls/day, no credit card!"
            )

        self.base_url = "https://api.twelvedata.com"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical data from TwelveData.

        Args:
            symbol: Ticker (e.g., "AAPL", "EUR/USD", "BTC/USD")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month
            exchange: Optional exchange (e.g., "NASDAQ")
            timezone: Optional timezone (default: America/New_York)

        Returns:
            DataResponse with OHLCV data
        """
        try:
            symbol = symbol.upper()

            # Map common intervals
            interval_map = {
                "1m": "1min",
                "5m": "5min",
                "15m": "15min",
                "30m": "30min",
                "1h": "1h",
                "1d": "1day",
                "1D": "1day",
                "1wk": "1week",
                "1mo": "1month",
            }

            td_interval = interval_map.get(interval, interval)

            # Build URL
            url = f"{self.base_url}/time_series"

            # Parameters
            params = {
                "symbol": symbol,
                "interval": td_interval,
                "start_date": start_date,
                "end_date": end_date,
                "apikey": self.api_key,
                "format": "JSON",
                "outputsize": 5000,
            }

            # Optional parameters
            if 'exchange' in kwargs:
                params['exchange'] = kwargs['exchange']
            if 'timezone' in kwargs:
                params['timezone'] = kwargs['timezone']

            # Make request
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if 'status' in data and data['status'] == 'error':
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"TwelveData error: {data.get('message', 'Unknown error')}"
                )

            # Check for values
            if 'values' not in data or not data['values']:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol}"
                )

            # Convert to standard format
            records = []
            for bar in reversed(data['values']):  # Reverse to chronological order
                records.append({
                    'Date': bar.get('datetime', '')[:10],  # Extract date
                    'open': float(bar.get('open', 0)),
                    'high': float(bar.get('high', 0)),
                    'low': float(bar.get('low', 0)),
                    'close': float(bar.get('close', 0)),
                    'volume': int(float(bar.get('volume', 0))),
                })

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'interval': interval,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(records),
                    'source': 'TwelveData',
                    'currency': data['meta'].get('currency') if 'meta' in data else None,
                    'exchange': data['meta'].get('exchange') if 'meta' in data else None,
                },
                success=True
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = "Invalid API key"
            elif e.response.status_code == 429:
                error_msg = "Rate limit exceeded (8 calls/min, 800 calls/day)"
            else:
                error_msg = f"HTTP {e.response.status_code}"

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=error_msg
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"TwelveData error: {str(e)}"
            )

    def get_quote(self, symbol: str, **kwargs) -> dict:
        """Get real-time quote."""
        try:
            url = f"{self.base_url}/quote"
            params = {"symbol": symbol.upper(), "apikey": self.api_key}

            if 'exchange' in kwargs:
                params['exchange'] = kwargs['exchange']

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get quote: {e}")
            return {}

    def get_price(self, symbol: str, **kwargs) -> dict:
        """Get current price."""
        try:
            url = f"{self.base_url}/price"
            params = {"symbol": symbol.upper(), "apikey": self.api_key}

            if 'exchange' in kwargs:
                params['exchange'] = kwargs['exchange']

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get price: {e}")
            return {}

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """TwelveData does not support options."""
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="TwelveData does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """TwelveData does not support options."""
        return []

    def validate_connection(self) -> bool:
        """Validate API connection."""
        try:
            url = f"{self.base_url}/time_series"
            params = {
                "symbol": "AAPL",
                "interval": "1day",
                "outputsize": 1,
                "apikey": self.api_key
            }

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()
            return 'values' in data or 'status' in data

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """TwelveData does not support options."""
        return False
