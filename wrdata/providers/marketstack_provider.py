"""
Marketstack provider for global stock market data.

Marketstack offers real-time and historical stock data for 70+ exchanges worldwide.
FREE tier: 1,000 requests/month

Get your FREE API key: https://marketstack.com/product
No credit card required!

API Docs: https://marketstack.com/documentation
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class MarketstackProvider(BaseProvider):
    """
    Marketstack provider for global stock data.

    Free tier includes:
    - 1,000 API requests per month
    - 70+ global stock exchanges
    - Real-time & historical data
    - 50+ years of history
    - Intraday data
    - No credit card required
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="marketstack", api_key=api_key)

        if not api_key:
            raise ValueError(
                "Marketstack API key required. "
                "Get FREE key at: https://marketstack.com/product\n"
                "Free tier: 1,000 requests/month"
            )

        self.base_url = "http://api.marketstack.com/v1"  # Free tier uses HTTP

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical stock data from Marketstack."""
        try:
            symbol = symbol.upper()

            # Marketstack uses end-of-day (EOD) for daily data
            url = f"{self.base_url}/eod"
            params = {
                "access_key": self.api_key,
                "symbols": symbol,
                "date_from": start_date,
                "date_to": end_date,
                "limit": 1000
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"Marketstack error: {data['error'].get('message', 'Unknown error')}"
                )

            bars = data.get('data', [])

            if not bars:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for bar in bars:
                records.append({
                    'Date': bar['date'][:10],
                    'open': float(bar.get('open', 0) or 0),
                    'high': float(bar.get('high', 0) or 0),
                    'low': float(bar.get('low', 0) or 0),
                    'close': float(bar.get('close', 0) or 0),
                    'volume': int(bar.get('volume', 0) or 0),
                })

            # Marketstack returns newest first, reverse it
            records.reverse()

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Marketstack'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Marketstack error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Marketstack does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/eod/latest"
            params = {
                "access_key": self.api_key,
                "symbols": "AAPL",
                "limit": 1
            }
            response = requests.get(url, params=params, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
