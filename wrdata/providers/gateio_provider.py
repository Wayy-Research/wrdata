"""
Gate.io provider for cryptocurrency trading.

Gate.io is a major global crypto exchange with 1,400+ trading pairs.
FREE API - No key required for market data!

API Docs: https://www.gate.io/docs/developers/apiv4/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class GateIOProvider(BaseProvider):
    """
    Gate.io provider for cryptocurrency data.

    FREE features (no API key):
    - 1,400+ trading pairs
    - Historical candlesticks
    - Real-time tickers
    - Order book data
    - Market stats
    - Unlimited public endpoints

    API key required for:
    - Trading operations
    - Higher rate limits
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="gateio", api_key=api_key)
        self.base_url = "https://api.gateio.ws/api/v4"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from Gate.io."""
        try:
            # Gate.io format: BTC_USDT
            symbol = symbol.upper().replace('-', '_')
            if '_' not in symbol:
                symbol = f"{symbol}_USDT"

            # Map intervals
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1d",
                "1D": "1d",
                "1w": "7d",
            }

            gateio_interval = interval_map.get(interval, "1d")

            # Convert to timestamps (Unix seconds)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

            url = f"{self.base_url}/spot/candlesticks"
            params = {
                "currency_pair": symbol,
                "interval": gateio_interval,
                "from": start_ts,
                "to": end_ts,
                "limit": 1000
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for candle in data:
                # Gate.io format: [timestamp, volume, close, high, low, open]
                timestamp = int(candle[0])
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(candle[5]),
                    'high': float(candle[3]),
                    'low': float(candle[4]),
                    'close': float(candle[2]),
                    'volume': float(candle[1]),
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Gate.io'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Gate.io error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Gate.io does not provide traditional options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/spot/currencies/BTC"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
