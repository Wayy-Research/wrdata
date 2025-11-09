"""
KuCoin provider for cryptocurrency trading.

KuCoin is a major global crypto exchange with 700+ trading pairs.
FREE API - No key required for market data!

API Docs: https://docs.kucoin.com/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class KuCoinProvider(BaseProvider):
    """
    KuCoin provider for cryptocurrency data.

    FREE features (no API key):
    - 700+ trading pairs
    - Historical klines
    - Real-time tickers
    - Order book data
    - 24h stats
    - Unlimited public endpoints

    API key required for:
    - Trading operations
    - Higher rate limits
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="kucoin", api_key=api_key)
        self.base_url = "https://api.kucoin.com"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from KuCoin."""
        try:
            # KuCoin format: BTC-USDT
            if '-' not in symbol:
                symbol = symbol.upper().replace('USDT', '-USDT')
                if '-' not in symbol:
                    symbol = f"{symbol}-USDT"

            # Map intervals
            interval_map = {
                "1m": "1min",
                "5m": "5min",
                "15m": "15min",
                "30m": "30min",
                "1h": "1hour",
                "4h": "4hour",
                "1d": "1day",
                "1D": "1day",
                "1w": "1week",
            }

            kucoin_interval = interval_map.get(interval, "1day")

            # Convert to timestamps (Unix seconds)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

            url = f"{self.base_url}/api/v1/market/candles"
            params = {
                "symbol": symbol,
                "type": kucoin_interval,
                "startAt": start_ts,
                "endAt": end_ts
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '200000':
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"KuCoin error: {data.get('msg', 'Unknown error')}"
                )

            candles = data.get('data', [])

            if not candles:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for candle in candles:
                # KuCoin format: [time, open, close, high, low, volume, turnover]
                timestamp = int(candle[0])
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(candle[1]),
                    'high': float(candle[3]),
                    'low': float(candle[4]),
                    'close': float(candle[2]),
                    'volume': float(candle[5]),
                })

            # KuCoin returns newest first, reverse it
            records.reverse()

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'KuCoin'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"KuCoin error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="KuCoin does not provide traditional options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v1/status"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get('code') == '200000'
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
