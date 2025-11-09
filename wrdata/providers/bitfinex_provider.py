"""
Bitfinex provider for cryptocurrency trading.

Bitfinex is one of the oldest and largest crypto exchanges.
FREE API - No key required for market data!

API Docs: https://docs.bitfinex.com/docs
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class BitfinexProvider(BaseProvider):
    """
    Bitfinex provider for cryptocurrency data.

    FREE features (no API key):
    - 400+ trading pairs
    - Historical candles
    - Real-time tickers
    - Order book data
    - Trades history
    - Unlimited public endpoints

    API key required for:
    - Trading operations
    - Account information
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="bitfinex", api_key=api_key)
        self.base_url = "https://api-pub.bitfinex.com/v2"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from Bitfinex."""
        try:
            # Bitfinex format: tBTCUSD (trading pairs start with 't')
            symbol = symbol.upper().replace('-', '').replace('_', '')
            if not symbol.startswith('t'):
                symbol = f"t{symbol}"

            # Map intervals
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "4h": "4h",
                "1d": "1D",
                "1D": "1D",
                "1w": "1W",
            }

            bitfinex_interval = interval_map.get(interval, "1D")

            # Convert to timestamps (milliseconds)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

            # Bitfinex candles endpoint
            url = f"{self.base_url}/candles/trade:{bitfinex_interval}:{symbol}/hist"
            params = {
                "start": start_ts,
                "end": end_ts,
                "limit": 10000,
                "sort": 1  # Sort ascending
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data or isinstance(data, dict):
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for candle in data:
                # Bitfinex format: [MTS, OPEN, CLOSE, HIGH, LOW, VOLUME]
                timestamp = candle[0] / 1000
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(candle[1]),
                    'high': float(candle[3]),
                    'low': float(candle[4]),
                    'close': float(candle[2]),
                    'volume': float(candle[5]),
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Bitfinex'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Bitfinex error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Bitfinex does not provide traditional options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/platform/status"
            response = requests.get(url, timeout=5)
            data = response.json()
            # Returns [1] when operational, [0] when in maintenance
            return data == [1]
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
