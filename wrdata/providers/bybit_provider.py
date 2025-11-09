"""
Bybit provider for cryptocurrency derivatives and spot trading.

Bybit is a major crypto derivatives exchange.
FREE API - No key required for market data!

API Docs: https://bybit-exchange.github.io/docs/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class BybitProvider(BaseProvider):
    """
    Bybit provider for cryptocurrency data.

    FREE features (no API key):
    - Spot & derivatives data
    - Historical klines
    - Real-time tickers
    - Order book data
    - Unlimited public endpoints
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="bybit", api_key=api_key)
        self.base_url = "https://api.bybit.com"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from Bybit."""
        try:
            symbol = symbol.upper()

            # Map intervals
            interval_map = {
                "1m": "1", "5m": "5", "15m": "15", "30m": "30",
                "1h": "60", "4h": "240", "1d": "D", "1D": "D", "1w": "W"
            }

            bybit_interval = interval_map.get(interval, "D")

            # Convert to timestamps (milliseconds)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

            url = f"{self.base_url}/v5/market/kline"
            params = {
                "category": "spot",
                "symbol": symbol,
                "interval": bybit_interval,
                "start": start_ts,
                "end": end_ts,
                "limit": 1000
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('retCode') != 0:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"Bybit error: {data.get('retMsg', 'Unknown error')}"
                )

            klines = data.get('result', {}).get('list', [])

            if not klines:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for kline in reversed(klines):  # Bybit returns newest first
                timestamp = int(kline[0]) / 1000
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Bybit'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Bybit error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Bybit does not provide traditional options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/v5/market/time"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get('retCode') == 0
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
