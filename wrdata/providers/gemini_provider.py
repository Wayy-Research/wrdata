"""
Gemini provider for cryptocurrency trading.

Gemini is a regulated US crypto exchange founded by the Winklevoss twins.
FREE API - No key required for market data!

API Docs: https://docs.gemini.com/rest-api/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class GeminiProvider(BaseProvider):
    """
    Gemini provider for cryptocurrency data.

    FREE features (no API key):
    - US-regulated exchange
    - Real-time market data
    - Historical candles
    - Order book data
    - Recent trades
    - Unlimited public endpoints

    API key required for:
    - Trading operations
    - Account information
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="gemini", api_key=api_key)
        self.base_url = "https://api.gemini.com/v2"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from Gemini."""
        try:
            # Gemini format: btcusd (lowercase, no separator)
            symbol = symbol.lower().replace('-', '').replace('_', '')

            # Map intervals
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1hr",
                "6h": "6hr",
                "1d": "1day",
                "1D": "1day",
            }

            gemini_interval = interval_map.get(interval, "1day")

            url = f"{self.base_url}/candles/{symbol}/{gemini_interval}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            # Convert to date objects for filtering
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            records = []
            for candle in data:
                # Gemini format: [timestamp_ms, open, high, low, close, volume]
                timestamp = candle[0] / 1000
                dt = datetime.fromtimestamp(timestamp)

                # Filter by date range
                if start_dt <= dt.date() <= end_dt:
                    records.append({
                        'Date': dt.strftime('%Y-%m-%d'),
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5]),
                    })

            # Gemini returns newest first, reverse for chronological order
            records.reverse()

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Gemini'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Gemini error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Gemini does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/ticker/btcusd"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
