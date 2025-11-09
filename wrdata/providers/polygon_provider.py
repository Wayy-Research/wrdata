"""
Polygon.io provider for premium US market data.

Polygon.io is the gold standard for US market data.
Best-in-class quality, reliability, and coverage.

Get your API key: https://polygon.io/dashboard/signup
Free tier: 100 API calls/day, 5 calls/minute

Paid plans from $99/month for unlimited access.

API Docs: https://polygon.io/docs/stocks/getting-started
"""

import requests
from typing import Optional, List
from datetime import datetime, date, timedelta
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class PolygonProvider(BaseProvider):
    """
    Polygon.io provider for premium US market data.

    Best-in-class data for:
    - US Stocks & ETFs
    - Options chains
    - Forex
    - Cryptocurrency
    - Real-time quotes
    - Historical OHLCV

    Free tier: 100 calls/day
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="polygon", api_key=api_key)

        if not api_key:
            raise ValueError(
                "Polygon.io API key required. "
                "Get one at: https://polygon.io/dashboard/signup\n"
                "Free tier: 100 calls/day"
            )

        self.base_url = "https://api.polygon.io"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical stock data from Polygon.io.

        Args:
            symbol: Stock ticker (e.g., "AAPL", "MSFT")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval - "1m", "5m", "15m", "30m", "1h", "1d"
            adjusted: Whether to adjust for splits (default: True)
            sort: Sort order - "asc" or "desc" (default: "asc")

        Returns:
            DataResponse with OHLCV data
        """
        try:
            symbol = symbol.upper()
            adjusted = kwargs.get('adjusted', True)
            sort = kwargs.get('sort', 'asc')

            # Map interval to Polygon timespan/multiplier
            interval_map = {
                "1m": ("minute", 1),
                "5m": ("minute", 5),
                "15m": ("minute", 15),
                "30m": ("minute", 30),
                "1h": ("hour", 1),
                "2h": ("hour", 2),
                "4h": ("hour", 4),
                "1d": ("day", 1),
                "1D": ("day", 1),
                "1wk": ("week", 1),
                "1mo": ("month", 1),
            }

            if interval not in interval_map:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"Unsupported interval: {interval}. Use: {list(interval_map.keys())}"
                )

            timespan, multiplier = interval_map[interval]

            # Build URL
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_date}/{end_date}"

            # Parameters
            params = {
                "adjusted": str(adjusted).lower(),
                "sort": sort,
                "limit": 50000,  # Max results per request
            }

            # Make request
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if data.get('status') == 'ERROR':
                error_msg = data.get('error', 'Unknown error')
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"Polygon API error: {error_msg}"
                )

            # Check for results
            if 'results' not in data or not data['results']:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol} from {start_date} to {end_date}"
                )

            # Convert to standard format
            records = []
            for bar in data['results']:
                # Polygon uses millisecond timestamps
                timestamp = bar.get('t', 0) / 1000
                date_obj = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': date_obj.strftime('%Y-%m-%d'),
                    'open': float(bar.get('o', 0)),
                    'high': float(bar.get('h', 0)),
                    'low': float(bar.get('l', 0)),
                    'close': float(bar.get('c', 0)),
                    'volume': int(bar.get('v', 0)),
                })

            if not records:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data in results for {symbol}"
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
                    'source': 'Polygon.io',
                    'adjusted': adjusted,
                    'query_count': data.get('queryCount', 0),
                    'results_count': data.get('resultsCount', 0),
                },
                success=True
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = "Invalid API key or unauthorized"
            elif e.response.status_code == 403:
                error_msg = "API key doesn't have access to this endpoint (upgrade required)"
            elif e.response.status_code == 429:
                error_msg = "Rate limit exceeded. Free tier: 5 calls/min, 100 calls/day"
            else:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"

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
                error=f"Polygon API error: {str(e)}"
            )

    def get_last_quote(self, symbol: str) -> dict:
        """
        Get the last quote for a symbol.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with quote data
        """
        try:
            symbol = symbol.upper()
            url = f"{self.base_url}/v2/last/nbbo/{symbol}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('status') != 'OK':
                return {}

            result = data.get('results', {})
            return {
                'symbol': symbol,
                'bid': result.get('P'),  # Bid price
                'ask': result.get('p'),  # Ask price
                'bid_size': result.get('S'),  # Bid size
                'ask_size': result.get('s'),  # Ask size
                'timestamp': result.get('t'),
            }

        except Exception as e:
            print(f"Failed to get last quote: {e}")
            return {}

    def get_previous_close(self, symbol: str) -> dict:
        """
        Get previous day's close for a symbol.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with previous close data
        """
        try:
            symbol = symbol.upper()
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/prev"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'results' not in data or not data['results']:
                return {}

            result = data['results'][0]
            return {
                'symbol': symbol,
                'open': result.get('o'),
                'high': result.get('h'),
                'low': result.get('l'),
                'close': result.get('c'),
                'volume': result.get('v'),
                'vwap': result.get('vw'),  # Volume weighted average price
                'timestamp': result.get('t'),
            }

        except Exception as e:
            print(f"Failed to get previous close: {e}")
            return {}

    def get_ticker_details(self, symbol: str) -> dict:
        """
        Get detailed information about a ticker.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with ticker details
        """
        try:
            symbol = symbol.upper()
            url = f"{self.base_url}/v3/reference/tickers/{symbol}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('status') != 'OK':
                return {}

            result = data.get('results', {})
            return {
                'symbol': result.get('ticker'),
                'name': result.get('name'),
                'market': result.get('market'),
                'locale': result.get('locale'),
                'primary_exchange': result.get('primary_exchange'),
                'type': result.get('type'),
                'currency_name': result.get('currency_name'),
                'cik': result.get('cik'),
                'composite_figi': result.get('composite_figi'),
                'share_class_figi': result.get('share_class_figi'),
                'description': result.get('description'),
                'homepage_url': result.get('homepage_url'),
                'total_employees': result.get('total_employees'),
                'list_date': result.get('list_date'),
                'market_cap': result.get('market_cap'),
            }

        except Exception as e:
            print(f"Failed to get ticker details: {e}")
            return {}

    def get_market_status(self) -> dict:
        """
        Get current market status.

        Returns:
            Dictionary with market status
        """
        try:
            url = f"{self.base_url}/v1/marketstatus/now"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data

        except Exception as e:
            print(f"Failed to get market status: {e}")
            return {}

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Fetch options chain from Polygon.io.

        Polygon.io has excellent options support on paid plans.
        Free tier has limited options access.
        """
        try:
            symbol = request.symbol.upper()

            # Get options contracts
            url = f"{self.base_url}/v3/reference/options/contracts"
            params = {
                'underlying_ticker': symbol,
                'limit': 1000,
            }

            if request.expiry:
                params['expiration_date'] = request.expiry.strftime('%Y-%m-%d')

            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if data.get('status') != 'OK':
                return OptionsChainResponse(
                    symbol=symbol,
                    provider=self.name,
                    snapshot_timestamp=datetime.utcnow(),
                    success=False,
                    error="Polygon API error"
                )

            contracts = data.get('results', [])

            if not contracts:
                return OptionsChainResponse(
                    symbol=symbol,
                    provider=self.name,
                    snapshot_timestamp=datetime.utcnow(),
                    success=False,
                    error=f"No options contracts found for {symbol}"
                )

            return OptionsChainResponse(
                symbol=symbol,
                provider=self.name,
                snapshot_timestamp=datetime.utcnow(),
                success=True,
                metadata={
                    'contracts_found': len(contracts),
                    'source': 'Polygon.io'
                }
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                error_msg = "Options data requires paid Polygon.io plan"
            else:
                error_msg = f"HTTP error: {e.response.status_code}"

            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=datetime.utcnow(),
                success=False,
                error=error_msg
            )

        except Exception as e:
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=datetime.utcnow(),
                success=False,
                error=f"Polygon options error: {str(e)}"
            )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Get available option expiration dates."""
        # Options data requires paid plan
        # Implement when needed
        return []

    def validate_connection(self) -> bool:
        """
        Validate Polygon.io API connection.

        Tests by fetching market status.
        """
        try:
            url = f"{self.base_url}/v1/marketstatus/now"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()

            data = response.json()
            return data.get('market') is not None

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """Polygon.io supports options on paid plans."""
        return True


# Polygon.io market types
POLYGON_MARKETS = {
    'stocks': 'US Stocks & ETFs',
    'options': 'Options (paid plans)',
    'crypto': 'Cryptocurrency',
    'fx': 'Foreign Exchange (Forex)',
    'indices': 'Market Indices',
}

# Polygon.io timespans
POLYGON_TIMESPANS = {
    'minute': 'Minute bars',
    'hour': 'Hourly bars',
    'day': 'Daily bars',
    'week': 'Weekly bars',
    'month': 'Monthly bars',
    'quarter': 'Quarterly bars',
    'year': 'Yearly bars',
}
