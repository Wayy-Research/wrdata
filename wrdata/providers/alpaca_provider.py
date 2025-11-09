"""
Alpaca broker provider for US stock market data and trading.

Alpaca is a commission-free stock brokerage with a powerful API.
Perfect for algorithmic trading!

Get your free API keys: https://app.alpaca.markets/signup
Free tier: Real-time IEX data + paper trading

API Docs: https://docs.alpaca.markets/
"""

import requests
from typing import Optional, List
from datetime import datetime, date, timedelta
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class AlpacaProvider(BaseProvider):
    """
    Alpaca broker provider for US stock market data and trading.

    Free tier includes:
    - Real-time IEX stock quotes
    - Historical data (up to 6 years)
    - WebSocket streaming
    - Paper trading account
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper: bool = True
    ):
        super().__init__(name="alpaca", api_key=api_key)

        if not api_key or not api_secret:
            raise ValueError(
                "Alpaca API key and secret required. "
                "Get free keys at: https://app.alpaca.markets/signup"
            )

        self.api_secret = api_secret
        self.paper = paper

        # Use paper trading or live URLs
        if paper:
            self.base_url = "https://paper-api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"
            self.data_url = "https://data.alpaca.markets"

        # Set up auth headers
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret
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
        Fetch historical stock data from Alpaca.

        Args:
            symbol: Stock ticker (e.g., "AAPL", "MSFT")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval - "1Min", "5Min", "15Min", "1Hour", "1Day"

        Returns:
            DataResponse with OHLCV data
        """
        try:
            symbol = symbol.upper()

            # Map interval to Alpaca timeframe
            interval_map = {
                "1m": "1Min",
                "5m": "5Min",
                "15m": "15Min",
                "30m": "30Min",
                "1h": "1Hour",
                "1d": "1Day",
                "1D": "1Day",
            }
            timeframe = interval_map.get(interval, "1Day")

            # Determine endpoint based on timeframe
            if timeframe.endswith("Min") or timeframe.endswith("Hour"):
                endpoint = "bars"
            else:
                endpoint = "bars"

            # Build request - using v2 API
            url = f"{self.data_url}/v2/stocks/{symbol}/bars"
            params = {
                'start': start_date,
                'end': end_date,
                'timeframe': timeframe,
                'limit': 10000,  # Max bars to return
                'adjustment': 'split',  # Adjust for splits
                'feed': 'iex',  # IEX feed (free tier)
            }

            # Make request
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if 'bars' not in data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol}"
                )

            bars = data.get('bars', [])
            if not bars:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No bars returned for {symbol}"
                )

            # Convert to standard format
            records = []
            for bar in bars:
                # Parse timestamp
                timestamp = bar.get('t', '')
                if 'T' in timestamp:
                    date_str = timestamp.split('T')[0]
                else:
                    date_str = timestamp[:10]

                records.append({
                    'Date': date_str,
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
                    'source': 'Alpaca IEX',
                    'timeframe': timeframe,
                    'next_page_token': data.get('next_page_token')
                },
                success=True
            )

        except requests.exceptions.RequestException as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Alpaca API request failed: {str(e)}"
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def get_latest_quote(self, symbol: str) -> dict:
        """
        Get latest quote for a symbol.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with latest quote data
        """
        try:
            symbol = symbol.upper()
            url = f"{self.data_url}/v2/stocks/{symbol}/quotes/latest"
            params = {'feed': 'iex'}

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('quote', {})

        except Exception as e:
            print(f"Failed to get latest quote: {e}")
            return {}

    def get_latest_trade(self, symbol: str) -> dict:
        """
        Get latest trade for a symbol.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with latest trade data
        """
        try:
            symbol = symbol.upper()
            url = f"{self.data_url}/v2/stocks/{symbol}/trades/latest"
            params = {'feed': 'iex'}

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('trade', {})

        except Exception as e:
            print(f"Failed to get latest trade: {e}")
            return {}

    def get_snapshot(self, symbol: str) -> dict:
        """
        Get market snapshot for a symbol (combines quote, trade, bar data).

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with snapshot data
        """
        try:
            symbol = symbol.upper()
            url = f"{self.data_url}/v2/stocks/{symbol}/snapshot"
            params = {'feed': 'iex'}

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get snapshot: {e}")
            return {}

    def get_account(self) -> dict:
        """
        Get account information.

        Returns:
            Dictionary with account details
        """
        try:
            url = f"{self.base_url}/v2/account"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get account: {e}")
            return {}

    def get_positions(self) -> List[dict]:
        """
        Get all open positions.

        Returns:
            List of position dictionaries
        """
        try:
            url = f"{self.base_url}/v2/positions"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get positions: {e}")
            return []

    def get_orders(self, status: str = "open") -> List[dict]:
        """
        Get orders.

        Args:
            status: Order status - "open", "closed", "all"

        Returns:
            List of order dictionaries
        """
        try:
            url = f"{self.base_url}/v2/orders"
            params = {'status': status}

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get orders: {e}")
            return []

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Alpaca does not provide options data.
        Use Tradier or IBKR for options.
        """
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="Alpaca does not provide options data. Use Tradier or IBKR instead."
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Alpaca does not provide options data."""
        return []

    def validate_connection(self) -> bool:
        """
        Validate Alpaca API connection.

        Tests by fetching account information.
        """
        try:
            url = f"{self.base_url}/v2/account"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()

            data = response.json()
            # Valid response should have account_number
            return 'account_number' in data

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """Alpaca does not support options data."""
        return False


# Alpaca data feeds
ALPACA_FEEDS = {
    'iex': 'IEX feed (free tier)',
    'sip': 'SIP feed (consolidated, paid plans)',
    'otc': 'OTC markets (paid plans)',
}

# Alpaca timeframes
ALPACA_TIMEFRAMES = {
    '1Min': '1 minute bars',
    '5Min': '5 minute bars',
    '15Min': '15 minute bars',
    '30Min': '30 minute bars',
    '1Hour': '1 hour bars',
    '1Day': 'Daily bars',
}
