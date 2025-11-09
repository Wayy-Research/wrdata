"""
Coinbase Advanced Trade API provider.

The new Coinbase Advanced Trade API replaces the legacy Coinbase Pro API.
FREE API - No key required for market data!

For trading, you'll need API credentials from Coinbase.

API Docs: https://docs.cloud.coinbase.com/advanced-trade-api/docs
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class CoinbaseAdvancedProvider(BaseProvider):
    """
    Coinbase Advanced Trade API provider.

    FREE features (no API key for market data):
    - Real-time market data
    - Historical candles
    - Order book snapshots
    - 24h stats
    - All trading pairs

    API key required for:
    - Trading operations
    - Account information
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        super().__init__(name="coinbase_advanced", api_key=api_key)
        self.api_secret = api_secret
        self.base_url = "https://api.coinbase.com/api/v3/brokerage"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from Coinbase Advanced."""
        try:
            # Coinbase format: BTC-USD
            if '-' not in symbol:
                symbol = symbol.upper().replace('USDT', '-USDT').replace('USD', '-USD')
                if '-' not in symbol:
                    symbol = f"{symbol}-USD"

            # Map intervals
            interval_map = {
                "1m": "ONE_MINUTE",
                "5m": "FIVE_MINUTE",
                "15m": "FIFTEEN_MINUTE",
                "30m": "THIRTY_MINUTE",
                "1h": "ONE_HOUR",
                "2h": "TWO_HOUR",
                "6h": "SIX_HOUR",
                "1d": "ONE_DAY",
                "1D": "ONE_DAY",
            }

            granularity = interval_map.get(interval, "ONE_DAY")

            # Convert to timestamps (Unix seconds)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

            url = f"{self.base_url}/products/{symbol}/candles"
            params = {
                "start": start_ts,
                "end": end_ts,
                "granularity": granularity
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            candles = data.get('candles', [])

            if not candles:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for candle in candles:
                timestamp = int(candle['start'])
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle['volume']),
                })

            # Coinbase returns newest first, reverse it
            records.reverse()

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Coinbase Advanced'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Coinbase Advanced error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Coinbase Advanced does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/products/BTC-USD"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
