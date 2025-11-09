"""
OKX provider for cryptocurrency trading.

OKX (formerly OKEx) is a major global crypto exchange.
FREE API - No key required for market data!

API Docs: https://www.okx.com/docs-v5/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class OKXProvider(BaseProvider):
    """
    OKX provider for cryptocurrency data.

    FREE features (no API key):
    - Spot, futures, perpetual data
    - Historical candlesticks
    - Real-time tickers
    - Order book snapshots
    - Unlimited public endpoints
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="okx", api_key=api_key)
        self.base_url = "https://www.okx.com"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from OKX."""
        try:
            # OKX format: BTC-USDT
            if 'USDT' in symbol.upper() and '-' not in symbol:
                symbol = symbol.upper().replace('USDT', '-USDT')

            # Map intervals
            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1H", "4h": "4H", "1d": "1D", "1D": "1D", "1w": "1W"
            }

            okx_interval = interval_map.get(interval, "1D")

            # Convert to timestamps (milliseconds)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

            url = f"{self.base_url}/api/v5/market/candles"
            params = {
                "instId": symbol,
                "bar": okx_interval,
                "before": start_ts,
                "after": end_ts,
                "limit": 300
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '0':
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"OKX error: {data.get('msg', 'Unknown error')}"
                )

            candles = data.get('data', [])

            if not candles:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for candle in reversed(candles):  # OKX returns newest first
                timestamp = int(candle[0]) / 1000
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5]),
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'OKX'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"OKX error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="OKX options require separate implementation"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v5/public/time"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get('code') == '0'
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
