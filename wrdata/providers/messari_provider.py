"""
Messari provider for cryptocurrency data and research.

Messari offers crypto market data, metrics, and professional research.
FREE tier available with generous limits!

Get your FREE API key: https://messari.io/api
Free tier: 20 requests/minute, 1000/day

API Docs: https://messari.io/api/docs
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class MessariProvider(BaseProvider):
    """
    Messari provider for cryptocurrency data and research.

    Free tier includes:
    - 20 requests per minute
    - 1,000 requests per day
    - 3,000+ cryptocurrencies
    - Market data & metrics
    - Historical prices
    - On-chain metrics
    - Research reports metadata
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="messari", api_key=api_key)
        self.base_url = "https://data.messari.io/api/v1"
        self.headers = {}

        if api_key:
            self.headers['x-messari-api-key'] = api_key

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical crypto data from Messari."""
        try:
            # Messari uses asset slugs or symbols
            # Common format: bitcoin, ethereum, etc.
            symbol_map = {
                'BTC': 'bitcoin',
                'ETH': 'ethereum',
                'BNB': 'bnb',
                'SOL': 'solana',
                'ADA': 'cardano',
                'XRP': 'xrp',
                'DOGE': 'dogecoin'
            }

            asset_key = symbol_map.get(symbol.upper(), symbol.lower())

            # Map intervals
            interval_map = {
                "1m": "1m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "1d": "1d",
                "1D": "1d",
                "1w": "1w",
            }

            messari_interval = interval_map.get(interval, "1d")

            # Messari uses ISO 8601 format for dates
            url = f"{self.base_url}/assets/{asset_key}/metrics/price/time-series"
            params = {
                "start": start_date,
                "end": end_date,
                "interval": messari_interval,
                "format": "json"
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'status' in data and data['status'].get('error_code'):
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"Messari error: {data['status'].get('error_message', 'Unknown error')}"
                )

            values = data.get('data', {}).get('values', [])

            if not values:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for value in values:
                # Messari format: [timestamp_ms, open, high, low, close, volume]
                timestamp = value[0] / 1000
                dt = datetime.fromtimestamp(timestamp)

                # Check if we have OHLCV or just close price
                if len(value) >= 6:
                    records.append({
                        'Date': dt.strftime('%Y-%m-%d'),
                        'open': float(value[1]) if value[1] else 0,
                        'high': float(value[2]) if value[2] else 0,
                        'low': float(value[3]) if value[3] else 0,
                        'close': float(value[4]) if value[4] else 0,
                        'volume': float(value[5]) if value[5] else 0,
                    })
                else:
                    # Just price data
                    price = float(value[1]) if len(value) > 1 and value[1] else 0
                    records.append({
                        'Date': dt.strftime('%Y-%m-%d'),
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': 0,
                    })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Messari'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Messari error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Messari does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/assets/bitcoin/metrics"
            response = requests.get(url, headers=self.headers, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
