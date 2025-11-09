"""
Alpha Vantage provider.

Provides stock, forex, and crypto market data.

Get your free API key: https://www.alphavantage.co/support/#api-key

Free tier limits:
- 5 API calls per minute
- 500 API calls per day
"""

import requests
import time
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class AlphaVantageProvider(BaseProvider):
    """
    Alpha Vantage provider for stocks, forex, and crypto data.

    Free tier: 5 calls/min, 500 calls/day
    Premium tiers available for higher limits.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="alphavantage", api_key=api_key)
        self.base_url = "https://www.alphavantage.co/query"

        if not api_key:
            raise ValueError(
                "Alpha Vantage API key required. Get one free at: "
                "https://www.alphavantage.co/support/#api-key"
            )

        # Rate limiting
        self.last_call_time = 0
        self.min_call_interval = 12  # 5 calls/min = 12 seconds between calls

    def _rate_limit(self):
        """Enforce rate limiting (5 calls/minute for free tier)."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_call_interval:
            sleep_time = self.min_call_interval - elapsed
            time.sleep(sleep_time)
        self.last_call_time = time.time()

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical timeseries data from Alpha Vantage.

        Args:
            symbol: Stock ticker (e.g., "AAPL") or forex pair (e.g., "EUR/USD")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval - "1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"

        Returns:
            DataResponse with timeseries data
        """
        try:
            # Rate limit
            self._rate_limit()

            # Determine data type and function
            if '/' in symbol or len(symbol) == 6:
                # Forex pair (EUR/USD or EURUSD)
                return self._fetch_forex(symbol, start_date, end_date, interval)
            else:
                # Stock symbol
                return self._fetch_stock(symbol, start_date, end_date, interval)

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _fetch_stock(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str
    ) -> DataResponse:
        """Fetch stock data from Alpha Vantage."""
        try:
            # Map interval to Alpha Vantage function
            if interval in ['1m', '5m', '15m', '30m', '60m']:
                # Intraday data
                function = 'TIME_SERIES_INTRADAY'
                interval_param = interval
            else:
                # Daily data
                function = 'TIME_SERIES_DAILY'
                interval_param = None

            # Build request
            params = {
                'function': function,
                'symbol': symbol,
                'apikey': self.api_key,
                'outputsize': 'full',
                'datatype': 'json'
            }

            if interval_param:
                params['interval'] = interval_param

            # Make request
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if 'Error Message' in data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=data['Error Message']
                )

            if 'Note' in data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="API call frequency limit reached. Please wait."
                )

            # Extract time series data
            time_series_key = None
            for key in data.keys():
                if 'Time Series' in key:
                    time_series_key = key
                    break

            if not time_series_key:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="No time series data in response"
                )

            time_series = data[time_series_key]

            # Convert to standard format
            records = []
            for timestamp, values in time_series.items():
                # Filter by date range
                ts_date = timestamp.split()[0]  # Get date part
                if ts_date < start_date or ts_date > end_date:
                    continue

                records.append({
                    'Date': timestamp,
                    'open': float(values.get('1. open', 0)),
                    'high': float(values.get('2. high', 0)),
                    'low': float(values.get('3. low', 0)),
                    'close': float(values.get('4. close', 0)),
                    'volume': int(values.get('5. volume', 0)),
                })

            if not records:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found in date range {start_date} to {end_date}"
                )

            # Sort by date (oldest first)
            records.sort(key=lambda x: x['Date'])

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'interval': interval,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(records),
                    'source': 'Alpha Vantage'
                },
                success=True
            )

        except requests.exceptions.RequestException as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Alpha Vantage API request failed: {str(e)}"
            )

    def _fetch_forex(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str
    ) -> DataResponse:
        """Fetch forex data from Alpha Vantage."""
        try:
            # Parse forex pair
            if '/' in symbol:
                from_currency, to_currency = symbol.split('/')
            else:
                # Assume format like EURUSD
                from_currency = symbol[:3]
                to_currency = symbol[3:]

            # Map interval to function
            if interval in ['1m', '5m', '15m', '30m', '60m']:
                function = 'FX_INTRADAY'
                interval_param = interval
            else:
                function = 'FX_DAILY'
                interval_param = None

            # Build request
            params = {
                'function': function,
                'from_symbol': from_currency.upper(),
                'to_symbol': to_currency.upper(),
                'apikey': self.api_key,
                'outputsize': 'full',
                'datatype': 'json'
            }

            if interval_param:
                params['interval'] = interval_param

            # Make request
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if 'Error Message' in data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=data['Error Message']
                )

            if 'Note' in data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="API call frequency limit reached. Please wait."
                )

            # Extract time series
            time_series_key = None
            for key in data.keys():
                if 'Time Series' in key:
                    time_series_key = key
                    break

            if not time_series_key:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="No time series data in response"
                )

            time_series = data[time_series_key]

            # Convert to standard format
            records = []
            for timestamp, values in time_series.items():
                ts_date = timestamp.split()[0]
                if ts_date < start_date or ts_date > end_date:
                    continue

                records.append({
                    'Date': timestamp,
                    'open': float(values.get('1. open', 0)),
                    'high': float(values.get('2. high', 0)),
                    'low': float(values.get('3. low', 0)),
                    'close': float(values.get('4. close', 0)),
                    'volume': 0,  # Forex doesn't have volume
                })

            if not records:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found in date range"
                )

            records.sort(key=lambda x: x['Date'])

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'pair': f"{from_currency}/{to_currency}",
                    'interval': interval,
                    'records': len(records)
                },
                success=True
            )

        except requests.exceptions.RequestException as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Alpha Vantage forex request failed: {str(e)}"
            )

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """Alpha Vantage does not provide options chain data in free tier."""
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="Options data not available in Alpha Vantage free tier"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Alpha Vantage does not provide options data in free tier."""
        return []

    def validate_connection(self) -> bool:
        """
        Validate Alpha Vantage API connection.

        Tests by fetching a simple quote.
        """
        try:
            # Rate limit
            self._rate_limit()

            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': 'AAPL',
                'apikey': self.api_key
            }

            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()

            # Check if we got valid data
            return 'Global Quote' in data

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """Alpha Vantage free tier does not support options."""
        return False
