"""
Tradier provider for US stocks and options data.

Tradier is a brokerage that offers FREE market data API!
Perfect for options trading and real-time quotes.

Get your FREE API key: https://developer.tradier.com/getting_started
NO CREDIT CARD REQUIRED!

Sandbox (paper trading): FREE, unlimited
Production: FREE with account (no minimum deposit)

API Docs: https://documentation.tradier.com/brokerage-api
"""

import requests
from typing import Optional, List
from datetime import datetime, date, timedelta
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class TradierProvider(BaseProvider):
    """
    Tradier provider for US stocks and options data.

    FREE features:
    - Real-time stock quotes
    - Options chains (complete data!)
    - Historical data
    - Market calendar
    - Company search

    No credit card required for sandbox!
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sandbox: bool = True
    ):
        super().__init__(name="tradier", api_key=api_key)

        if not api_key:
            raise ValueError(
                "Tradier API key required. "
                "Get FREE key at: https://developer.tradier.com/getting_started\n"
                "No credit card required!"
            )

        self.sandbox = sandbox

        # Sandbox vs Production URLs
        if sandbox:
            self.base_url = "https://sandbox.tradier.com/v1"
        else:
            self.base_url = "https://api.tradier.com/v1"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
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
        Fetch historical stock data from Tradier.

        Args:
            symbol: Stock ticker (e.g., "AAPL", "MSFT")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval - "1d" (daily), "1wk" (weekly), "1mo" (monthly)

        Returns:
            DataResponse with OHLCV data
        """
        try:
            symbol = symbol.upper()

            # Map interval to Tradier interval
            interval_map = {
                "1d": "daily",
                "1D": "daily",
                "1wk": "weekly",
                "1mo": "monthly",
            }

            tradier_interval = interval_map.get(interval, "daily")

            # Build URL
            url = f"{self.base_url}/markets/history"

            # Parameters
            params = {
                "symbol": symbol,
                "start": start_date,
                "end": end_date,
                "interval": tradier_interval,
            }

            # Make request
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if 'history' not in data or data['history'] is None:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No historical data found for {symbol}"
                )

            history = data['history']

            # Check if day exists (single result vs array)
            if 'day' not in history:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data in date range for {symbol}"
                )

            days = history['day']

            # Handle single day vs multiple days
            if isinstance(days, dict):
                days = [days]
            elif not isinstance(days, list):
                days = []

            if not days:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data returned for {symbol}"
                )

            # Convert to standard format
            records = []
            for day in days:
                records.append({
                    'Date': day.get('date'),
                    'open': float(day.get('open', 0)),
                    'high': float(day.get('high', 0)),
                    'low': float(day.get('low', 0)),
                    'close': float(day.get('close', 0)),
                    'volume': int(day.get('volume', 0)),
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
                    'source': 'Tradier',
                    'sandbox': self.sandbox,
                },
                success=True
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                error_msg = "Invalid API key or unauthorized"
            elif e.response.status_code == 429:
                error_msg = "Rate limit exceeded (120 requests/minute)"
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
                error=f"Tradier API error: {str(e)}"
            )

    def get_quote(self, symbol: str) -> dict:
        """
        Get real-time quote for a symbol.

        Args:
            symbol: Stock ticker

        Returns:
            Dictionary with quote data
        """
        try:
            symbol = symbol.upper()
            url = f"{self.base_url}/markets/quotes"

            params = {"symbols": symbol}

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'quotes' not in data or 'quote' not in data['quotes']:
                return {}

            quote = data['quotes']['quote']

            return {
                'symbol': quote.get('symbol'),
                'description': quote.get('description'),
                'last': quote.get('last'),
                'bid': quote.get('bid'),
                'ask': quote.get('ask'),
                'bid_size': quote.get('bidsize'),
                'ask_size': quote.get('asksize'),
                'volume': quote.get('volume'),
                'open': quote.get('open'),
                'high': quote.get('high'),
                'low': quote.get('low'),
                'close': quote.get('close'),
                'prev_close': quote.get('prevclose'),
                'change': quote.get('change'),
                'change_percentage': quote.get('change_percentage'),
                'average_volume': quote.get('average_volume'),
                'last_volume': quote.get('last_volume'),
                'trade_date': quote.get('trade_date'),
                'type': quote.get('type'),
            }

        except Exception as e:
            print(f"Failed to get quote: {e}")
            return {}

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Fetch options chain from Tradier.

        This is FREE! Full options chains at no cost.
        """
        try:
            symbol = request.symbol.upper()

            # Get options expirations
            url = f"{self.base_url}/markets/options/expirations"
            params = {"symbol": symbol}

            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'expirations' not in data or data['expirations'] is None:
                return OptionsChainResponse(
                    symbol=symbol,
                    provider=self.name,
                    snapshot_timestamp=datetime.utcnow(),
                    success=False,
                    error=f"No options expirations found for {symbol}"
                )

            expirations = data['expirations'].get('date', [])

            if not expirations:
                return OptionsChainResponse(
                    symbol=symbol,
                    provider=self.name,
                    snapshot_timestamp=datetime.utcnow(),
                    success=False,
                    error=f"No options available for {symbol}"
                )

            # Use requested expiry or first available
            if request.expiry:
                expiry_str = request.expiry.strftime('%Y-%m-%d')
                if expiry_str not in expirations:
                    return OptionsChainResponse(
                        symbol=symbol,
                        provider=self.name,
                        snapshot_timestamp=datetime.utcnow(),
                        success=False,
                        error=f"No options for expiry {expiry_str}. Available: {expirations[:5]}"
                    )
            else:
                expiry_str = expirations[0]

            # Get options chain for this expiry
            chain_url = f"{self.base_url}/markets/options/chains"
            chain_params = {
                "symbol": symbol,
                "expiration": expiry_str,
                "greeks": "true"  # Include Greeks if available
            }

            chain_response = requests.get(chain_url, headers=self.headers, params=chain_params, timeout=30)
            chain_response.raise_for_status()

            chain_data = chain_response.json()

            if 'options' not in chain_data or chain_data['options'] is None:
                return OptionsChainResponse(
                    symbol=symbol,
                    provider=self.name,
                    snapshot_timestamp=datetime.utcnow(),
                    success=False,
                    error=f"No options chain data for {symbol}"
                )

            options = chain_data['options'].get('option', [])

            # Ensure it's a list
            if isinstance(options, dict):
                options = [options]

            return OptionsChainResponse(
                symbol=symbol,
                provider=self.name,
                snapshot_timestamp=datetime.utcnow(),
                success=True,
                metadata={
                    'expiration': expiry_str,
                    'contracts_found': len(options),
                    'expirations_available': len(expirations),
                    'source': 'Tradier',
                    'sandbox': self.sandbox,
                }
            )

        except Exception as e:
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=datetime.utcnow(),
                success=False,
                error=f"Tradier options error: {str(e)}"
            )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Get available option expiration dates."""
        try:
            symbol = symbol.upper()
            url = f"{self.base_url}/markets/options/expirations"
            params = {"symbol": symbol}

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'expirations' not in data or data['expirations'] is None:
                return []

            expirations = data['expirations'].get('date', [])

            # Convert to date objects
            result = []
            for exp_str in expirations:
                exp_date = datetime.strptime(exp_str, '%Y-%m-%d').date()
                result.append(exp_date)

            return result

        except Exception as e:
            print(f"Failed to get expirations: {e}")
            return []

    def get_option_strikes(self, symbol: str, expiration: str) -> List[float]:
        """
        Get available strike prices for a symbol and expiration.

        Args:
            symbol: Stock ticker
            expiration: Expiration date (YYYY-MM-DD)

        Returns:
            List of strike prices
        """
        try:
            symbol = symbol.upper()
            url = f"{self.base_url}/markets/options/strikes"
            params = {
                "symbol": symbol,
                "expiration": expiration
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'strikes' not in data or data['strikes'] is None:
                return []

            strikes = data['strikes'].get('strike', [])

            # Convert to floats
            return [float(strike) for strike in strikes]

        except Exception as e:
            print(f"Failed to get strikes: {e}")
            return []

    def get_market_calendar(self) -> dict:
        """
        Get market calendar (trading days, holidays).

        Returns:
            Dictionary with calendar data
        """
        try:
            url = f"{self.base_url}/markets/calendar"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            print(f"Failed to get calendar: {e}")
            return {}

    def get_market_clock(self) -> dict:
        """
        Get current market status.

        Returns:
            Dictionary with market clock data
        """
        try:
            url = f"{self.base_url}/markets/clock"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('clock', {})

        except Exception as e:
            print(f"Failed to get market clock: {e}")
            return {}

    def validate_connection(self) -> bool:
        """
        Validate Tradier API connection.

        Tests by fetching market clock.
        """
        try:
            url = f"{self.base_url}/markets/clock"
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()

            data = response.json()
            return 'clock' in data

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """Tradier supports options data (FREE!)."""
        return True


# Tradier market data types
TRADIER_QUOTE_TYPES = {
    'stock': 'Common Stock',
    'option': 'Option Contract',
    'etf': 'Exchange Traded Fund',
    'index': 'Market Index',
    'mutual_fund': 'Mutual Fund',
}

# Tradier intervals
TRADIER_INTERVALS = {
    'daily': 'Daily bars',
    'weekly': 'Weekly bars',
    'monthly': 'Monthly bars',
}
