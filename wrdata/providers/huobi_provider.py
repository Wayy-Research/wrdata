"""
Huobi (HTX) provider for cryptocurrency trading.

Huobi (now HTX) is a major global crypto exchange.
FREE API - No key required for market data!

API Docs: https://huobiapi.github.io/docs/spot/v1/en/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class HuobiProvider(BaseProvider):
    """
    Huobi (HTX) provider for cryptocurrency data.

    FREE features (no API key):
    - 600+ trading pairs
    - Historical klines
    - Real-time market data
    - Order book snapshots
    - Trade history
    - Unlimited public endpoints
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="huobi", api_key=api_key)
        self.base_url = "https://api.huobi.pro"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from Huobi."""
        try:
            # Huobi format: btcusdt (lowercase, no separator)
            symbol = symbol.lower().replace('-', '').replace('_', '')

            # Map intervals
            interval_map = {
                "1m": "1min",
                "5m": "5min",
                "15m": "15min",
                "30m": "30min",
                "1h": "60min",
                "4h": "4hour",
                "1d": "1day",
                "1D": "1day",
                "1w": "1week",
            }

            huobi_interval = interval_map.get(interval, "1day")

            url = f"{self.base_url}/market/history/kline"
            params = {
                "symbol": symbol,
                "period": huobi_interval,
                "size": 2000  # Max allowed
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"Huobi error: {data.get('err-msg', 'Unknown error')}"
                )

            klines = data.get('data', [])

            if not klines:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            # Filter by date range
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            records = []
            for kline in klines:
                # Huobi format: {id: timestamp, open, close, low, high, amount, vol, count}
                timestamp = kline['id']
                dt = datetime.fromtimestamp(timestamp)

                if start_dt <= dt.date() <= end_dt:
                    records.append({
                        'Date': dt.strftime('%Y-%m-%d'),
                        'open': float(kline['open']),
                        'high': float(kline['high']),
                        'low': float(kline['low']),
                        'close': float(kline['close']),
                        'volume': float(kline['amount']),
                    })

            # Huobi returns newest first, reverse it
            records.reverse()

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Huobi'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Huobi error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Huobi does not provide traditional options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/v1/common/timestamp"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get('status') == 'ok'
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
