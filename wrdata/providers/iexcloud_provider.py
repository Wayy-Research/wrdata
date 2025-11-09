"""
IEX Cloud provider for US stock market data.

IEX Cloud offers high-quality US stock data with generous free tier.
Free tier: 500,000 messages/month

Get your FREE API key: https://iexcloud.io/console/
No credit card required for free tier!

API Docs: https://iexcloud.io/docs/api/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class IEXCloudProvider(BaseProvider):
    """
    IEX Cloud provider for US stock data.

    Free tier includes:
    - 500,000 messages per month
    - US stocks (real-time IEX data)
    - Historical data
    - Company fundamentals
    - News
    - No credit card required!
    """

    def __init__(self, api_key: Optional[str] = None, sandbox: bool = False):
        super().__init__(name="iexcloud", api_key=api_key)

        if not api_key:
            raise ValueError(
                "IEX Cloud API key required. "
                "Get FREE key at: https://iexcloud.io/console/\n"
                "Free tier: 500,000 messages/month"
            )

        if sandbox:
            self.base_url = "https://sandbox.iexapis.com/stable"
        else:
            self.base_url = "https://cloud.iexapis.com/stable"

        self.sandbox = sandbox

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical stock data from IEX Cloud."""
        try:
            symbol = symbol.upper()

            # IEX Cloud uses different endpoints for different intervals
            if interval in ["1d", "1D"]:
                # Historical daily data
                url = f"{self.base_url}/stock/{symbol}/chart/date/{start_date}"
                params = {"token": self.api_key, "chartByDay": "true"}

                # For date range, we need to make multiple requests
                # IEX Cloud doesn't have a direct date range endpoint
                # Using the 'max' range for simplicity
                url = f"{self.base_url}/stock/{symbol}/chart/max"
                params = {"token": self.api_key}

                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not data:
                    return DataResponse(
                        symbol=symbol, provider=self.name, data=[], success=False,
                        error=f"No data for {symbol}"
                    )

                # Filter by date range
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

                records = []
                for bar in data:
                    bar_date = datetime.strptime(bar['date'], "%Y-%m-%d").date()
                    if start_dt <= bar_date <= end_dt:
                        records.append({
                            'Date': bar['date'],
                            'open': float(bar.get('open', 0) or 0),
                            'high': float(bar.get('high', 0) or 0),
                            'low': float(bar.get('low', 0) or 0),
                            'close': float(bar.get('close', 0) or 0),
                            'volume': int(bar.get('volume', 0) or 0),
                        })

                return DataResponse(
                    symbol=symbol, provider=self.name, data=records,
                    metadata={'interval': interval, 'records': len(records), 'source': 'IEX Cloud'},
                    success=True
                )

            else:
                # Intraday data
                url = f"{self.base_url}/stock/{symbol}/intraday-prices"
                params = {"token": self.api_key}

                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not data:
                    return DataResponse(
                        symbol=symbol, provider=self.name, data=[], success=False,
                        error=f"No intraday data for {symbol}"
                    )

                records = []
                for bar in data:
                    if bar.get('date') and bar.get('minute'):
                        dt_str = f"{bar['date']} {bar['minute']}"
                        records.append({
                            'Date': dt_str,
                            'open': float(bar.get('open', 0) or 0),
                            'high': float(bar.get('high', 0) or 0),
                            'low': float(bar.get('low', 0) or 0),
                            'close': float(bar.get('close', 0) or 0),
                            'volume': int(bar.get('volume', 0) or 0),
                        })

                return DataResponse(
                    symbol=symbol, provider=self.name, data=records,
                    metadata={'interval': interval, 'records': len(records), 'source': 'IEX Cloud'},
                    success=True
                )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"IEX Cloud error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """IEX Cloud does not support options in free tier."""
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="IEX Cloud does not provide options data in free tier"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/stock/aapl/quote"
            params = {"token": self.api_key}
            response = requests.get(url, params=params, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False
