"""
Tiingo provider for stocks, crypto, and news data.

Tiingo offers high-quality financial data with news sentiment.
Free tier: 500 API calls/hour, 1000/day

Get your free API key: https://www.tiingo.com/account/api/token
No credit card required!

API Docs: https://www.tiingo.com/documentation/general/overview
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class TiingoProvider(BaseProvider):
    """
    Tiingo provider for stocks, crypto, and news.

    Free tier includes:
    - 500 API calls/hour
    - 1,000 API calls/day
    - Stocks (US & International)
    - Cryptocurrency
    - News with sentiment analysis
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="tiingo", api_key=api_key)

        if not api_key:
            raise ValueError(
                "Tiingo API key required. "
                "Get FREE key at: https://www.tiingo.com/account/api/token\n"
                "Free tier: 500/hour, 1000/day"
            )

        self.base_url = "https://api.tiingo.com"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}"
        }

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical stock data from Tiingo."""
        try:
            symbol = symbol.upper()

            # Build URL
            url = f"{self.base_url}/tiingo/daily/{symbol}/prices"

            params = {
                "startDate": start_date,
                "endDate": end_date,
                "format": "json"
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for bar in data:
                records.append({
                    'Date': bar.get('date', '')[:10],
                    'open': float(bar.get('open', 0)),
                    'high': float(bar.get('high', 0)),
                    'low': float(bar.get('low', 0)),
                    'close': float(bar.get('close', 0)),
                    'volume': int(bar.get('volume', 0)),
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Tiingo'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Tiingo error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """Tiingo does not support options."""
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Tiingo does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/tiingo/daily/aapl"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
