"""
CryptoCompare provider for cryptocurrency data.

CryptoCompare offers crypto market data, news, and social metrics.
FREE tier available with generous limits!

Get your FREE API key: https://www.cryptocompare.com/cryptopian/api-keys
Free tier: 100,000 calls/month

API Docs: https://min-api.cryptocompare.com/documentation
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class CryptoCompareProvider(BaseProvider):
    """
    CryptoCompare provider for cryptocurrency data.

    Free tier includes:
    - 100,000 API calls per month
    - 5,000+ cryptocurrencies
    - Historical OHLCV data
    - Real-time prices
    - News and social data
    - Market aggregation

    Optional API key for higher limits.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="cryptocompare", api_key=api_key)
        self.base_url = "https://min-api.cryptocompare.com/data"
        self.headers = {}

        if api_key:
            self.headers['authorization'] = f'Apikey {api_key}'

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from CryptoCompare."""
        try:
            # CryptoCompare uses fsym (from symbol) and tsym (to symbol)
            # Default to USD as quote currency
            symbol = symbol.upper().replace('USDT', '').replace('USD', '')
            tsym = "USD"

            # Map intervals to endpoints
            if interval in ["1m", "5m", "15m", "30m", "1h"]:
                endpoint = "v2/histominute"
                aggregate = 1
                if interval == "5m":
                    aggregate = 5
                elif interval == "15m":
                    aggregate = 15
                elif interval == "30m":
                    aggregate = 30
                elif interval == "1h":
                    aggregate = 60
            elif interval in ["1d", "1D"]:
                endpoint = "v2/histoday"
                aggregate = 1
            else:
                endpoint = "v2/histoday"
                aggregate = 1

            # Convert to timestamps
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

            url = f"{self.base_url}/{endpoint}"
            params = {
                "fsym": symbol,
                "tsym": tsym,
                "toTs": end_ts,
                "limit": 2000,  # Max data points
                "aggregate": aggregate
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('Response') == 'Error':
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"CryptoCompare error: {data.get('Message', 'Unknown error')}"
                )

            candles = data.get('Data', {}).get('Data', [])

            if not candles:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            # Filter by date range
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            records = []
            for candle in candles:
                timestamp = candle['time']
                dt = datetime.fromtimestamp(timestamp)

                if start_dt <= dt.date() <= end_dt:
                    records.append({
                        'Date': dt.strftime('%Y-%m-%d'),
                        'open': float(candle.get('open', 0)),
                        'high': float(candle.get('high', 0)),
                        'low': float(candle.get('low', 0)),
                        'close': float(candle.get('close', 0)),
                        'volume': float(candle.get('volumefrom', 0)),
                    })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'CryptoCompare'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"CryptoCompare error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="CryptoCompare does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/price"
            params = {"fsym": "BTC", "tsyms": "USD"}
            response = requests.get(url, headers=self.headers, params=params, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
