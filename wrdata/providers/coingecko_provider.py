"""
CoinGecko provider for cryptocurrency market data.

CoinGecko is the world's largest crypto data aggregator.
FREE - No API key required for demo tier!

Optional API key for higher limits.

API Docs: https://www.coingecko.com/en/api/documentation
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class CoinGeckoProvider(BaseProvider):
    """
    CoinGecko provider for cryptocurrency data.

    FREE features (no API key):
    - 10-50 calls/minute (demo tier)
    - 10,000+ cryptocurrencies
    - Market data & rankings
    - Historical prices
    - No registration required!

    Optional API key for:
    - Higher rate limits
    - More data points
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="coingecko", api_key=api_key)

        if api_key:
            self.base_url = "https://pro-api.coingecko.com/api/v3"
            self.headers = {"x-cg-pro-api-key": api_key}
        else:
            self.base_url = "https://api.coingecko.com/api/v3"
            self.headers = {}

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from CoinGecko."""
        try:
            # CoinGecko uses coin IDs, not symbols
            # Common conversions
            symbol_map = {
                'BTC': 'bitcoin', 'ETH': 'ethereum', 'USDT': 'tether',
                'BNB': 'binancecoin', 'SOL': 'solana', 'XRP': 'ripple',
                'ADA': 'cardano', 'DOGE': 'dogecoin'
            }

            coin_id = symbol_map.get(symbol.upper(), symbol.lower())

            # Convert dates to timestamps
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

            url = f"{self.base_url}/coins/{coin_id}/market_chart/range"
            params = {
                "vs_currency": "usd",
                "from": start_ts,
                "to": end_ts
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'prices' not in data or not data['prices']:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for price_point in data['prices']:
                timestamp = price_point[0] / 1000
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(price_point[1]),
                    'high': float(price_point[1]),
                    'low': float(price_point[1]),
                    'close': float(price_point[1]),
                    'volume': 0,
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'CoinGecko'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"CoinGecko error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="CoinGecko does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/ping"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
