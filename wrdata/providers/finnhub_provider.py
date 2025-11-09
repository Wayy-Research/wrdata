"""
Finnhub provider for global stock market data.

Finnhub provides real-time and historical data for stocks, forex, and crypto.
Free tier includes WebSocket streaming!

Get your free API key: https://finnhub.io/register
Free tier: 60 calls/minute, WebSocket streaming included

API Docs: https://finnhub.io/docs/api
"""

import requests
from typing import Optional, List
from datetime import datetime, date, timedelta
import time
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class FinnhubProvider(BaseProvider):
    """
    Finnhub provider for global stock market data.

    Free tier: 60 API calls/minute, WebSocket streaming
    Covers 60+ stock exchanges worldwide.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="finnhub", api_key=api_key)

        if not api_key:
            raise ValueError(
                "Finnhub API key required. Get one free at: "
                "https://finnhub.io/register"
            )

        self.base_url = "https://finnhub.io/api/v1"

        # Rate limiting (60 calls/minute free tier)
        self.calls_per_minute = 60
        self.min_call_interval = 60.0 / self.calls_per_minute  # ~1 second
        self.last_call_time = 0

    def _rate_limit(self):
        """Enforce rate limiting (60 calls/minute for free tier)."""
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
        Fetch historical stock data from Finnhub.

        Args:
            symbol: Stock ticker (e.g., "AAPL", "MSFT")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval - "1", "5", "15", "30", "60", "D", "W", "M"
                     (1 min, 5 min, 15 min, 30 min, 60 min, day, week, month)

        Returns:
            DataResponse with OHLCV data
        """
        try:
            symbol = symbol.upper()

            # Convert interval to Finnhub format
            interval_map = {
                "1m": "1",
                "5m": "5",
                "15m": "15",
                "30m": "30",
                "1h": "60",
                "60m": "60",
                "1d": "D",
                "1D": "D",
                "1wk": "W",
                "1mo": "M",
            }
            finnhub_interval = interval_map.get(interval, "D")

            # Convert dates to Unix timestamps
            start = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

            # Rate limit
            self._rate_limit()

            # Build request - use stock/candle endpoint
            url = f"{self.base_url}/stock/candle"
            params = {
                'symbol': symbol,
                'resolution': finnhub_interval,
                'from': start,
                'to': end,
                'token': self.api_key
            }

            # Make request
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get('s') == 'no_data':
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol}"
                )

            if 's' not in data or data['s'] != 'ok':
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"Invalid response from Finnhub: {data}"
                )

            # Convert to standard format
            records = []
            timestamps = data.get('t', [])
            opens = data.get('o', [])
            highs = data.get('h', [])
            lows = data.get('l', [])
            closes = data.get('c', [])
            volumes = data.get('v', [])

            for i in range(len(timestamps)):
                # Convert Unix timestamp to date string
                date_str = datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d')

                records.append({
                    'Date': date_str,
                    'open': float(opens[i]),
                    'high': float(highs[i]),
                    'low': float(lows[i]),
                    'close': float(closes[i]),
                    'volume': int(volumes[i]),
                })

            if not records:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data in date range {start_date} to {end_date}"
                )

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'interval': interval,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(records),
                    'source': 'Finnhub',
                    'resolution': finnhub_interval
                },
                success=True
            )

        except requests.exceptions.RequestException as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Finnhub API request failed: {str(e)}"
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def get_quote(self, symbol: str) -> dict:
        """
        Get real-time quote for a symbol.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with quote data

        Example:
            >>> provider = FinnhubProvider(api_key="...")
            >>> quote = provider.get_quote("AAPL")
            >>> print(f"AAPL: ${quote['c']}")  # current price
        """
        try:
            symbol = symbol.upper()
            self._rate_limit()

            url = f"{self.base_url}/quote"
            params = {
                'symbol': symbol,
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get quote: {e}")
            return {}

    def get_company_profile(self, symbol: str) -> dict:
        """
        Get company profile information.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with company data
        """
        try:
            symbol = symbol.upper()
            self._rate_limit()

            url = f"{self.base_url}/stock/profile2"
            params = {
                'symbol': symbol,
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get company profile: {e}")
            return {}

    def get_company_news(self, symbol: str, start_date: str, end_date: str) -> List[dict]:
        """
        Get company news.

        Args:
            symbol: Stock ticker
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD

        Returns:
            List of news articles
        """
        try:
            symbol = symbol.upper()
            self._rate_limit()

            url = f"{self.base_url}/company-news"
            params = {
                'symbol': symbol,
                'from': start_date,
                'to': end_date,
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get company news: {e}")
            return []

    def search_symbols(self, query: str) -> List[dict]:
        """
        Search for stock symbols.

        Args:
            query: Search query (e.g., "Apple", "AAPL")

        Returns:
            List of matching symbols
        """
        try:
            self._rate_limit()

            url = f"{self.base_url}/search"
            params = {
                'q': query,
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('result', [])

        except Exception as e:
            print(f"Failed to search symbols: {e}")
            return []

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Finnhub does not provide options chain data.
        Use TradierProvider or AlpacaProvider for options.
        """
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="Finnhub does not provide options data. Use Tradier or Alpaca instead."
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Finnhub does not provide options data."""
        return []

    def validate_connection(self) -> bool:
        """
        Validate Finnhub API connection.

        Tests by fetching a simple quote.
        """
        try:
            self._rate_limit()

            url = f"{self.base_url}/quote"
            params = {
                'symbol': 'AAPL',
                'token': self.api_key
            }

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()
            # Valid response should have current price
            return 'c' in data and data['c'] > 0

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """Finnhub does not support options data."""
        return False


# Popular Finnhub endpoints
FINNHUB_ENDPOINTS = {
    'quote': 'Real-time quote',
    'candle': 'Historical OHLCV',
    'profile2': 'Company profile',
    'company-news': 'Company news',
    'search': 'Symbol search',
    'recommendation': 'Analyst recommendations',
    'price-target': 'Price targets',
    'earnings': 'Earnings data',
    'financials': 'Financial statements',
    'metrics': 'Financial metrics',
    'peers': 'Peer companies',
    'split': 'Stock splits',
    'dividend': 'Dividends',
}
