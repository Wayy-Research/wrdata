"""
TD Ameritrade API provider for US market data.

NOTE: TD Ameritrade is being integrated with Charles Schwab.
The API is still operational but new registrations may be limited.
Existing API keys continue to work.

Free tier includes real-time quotes, historical data, and options chains!

API Docs: https://developer.tdameritrade.com/apis
"""

import requests
from typing import Optional, List
from datetime import datetime, date, timedelta
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    OptionsContractInfo
)


class TDAmeritradeProvider(BaseProvider):
    """
    TD Ameritrade provider for US stocks and options.

    Features:
    - Real-time quotes (delayed 15 min for free)
    - Historical price data
    - Options chains with Greeks
    - Fundamentals
    - Market hours

    NOTE: TD Ameritrade is transitioning to Charles Schwab.
    Existing API keys work, but new registrations may be unavailable.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="tdameritrade", api_key=api_key)

        if not api_key:
            raise ValueError(
                "TD Ameritrade API key required. "
                "NOTE: TD Ameritrade is transitioning to Charles Schwab. "
                "New API registrations may be limited."
            )

        self.base_url = "https://api.tdameritrade.com/v1"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical stock data from TD Ameritrade."""
        try:
            symbol = symbol.upper()

            # Convert to milliseconds timestamps
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

            # Map intervals
            interval_map = {
                "1m": ("minute", 1),
                "5m": ("minute", 5),
                "15m": ("minute", 15),
                "30m": ("minute", 30),
                "1h": ("minute", 60),
                "1d": ("daily", 1),
                "1D": ("daily", 1),
                "1w": ("weekly", 1),
            }

            period_type, frequency = interval_map.get(interval, ("daily", 1))

            url = f"{self.base_url}/marketdata/{symbol}/pricehistory"
            params = {
                "apikey": self.api_key,
                "periodType": period_type,
                "frequencyType": period_type,
                "frequency": frequency,
                "startDate": start_ts,
                "endDate": end_ts,
                "needExtendedHoursData": False
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('empty', True):
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            candles = data.get('candles', [])

            if not candles:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for candle in candles:
                timestamp = candle['datetime'] / 1000
                dt = datetime.fromtimestamp(timestamp)

                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': int(candle['volume']),
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'TD Ameritrade'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"TD Ameritrade error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """Fetch options chain from TD Ameritrade."""
        try:
            symbol = request.symbol.upper()

            url = f"{self.base_url}/marketdata/chains"
            params = {
                "apikey": self.api_key,
                "symbol": symbol,
                "includeQuotes": "TRUE"
            }

            if request.expiration_date:
                params['fromDate'] = request.expiration_date.strftime('%Y-%m-%d')
                params['toDate'] = request.expiration_date.strftime('%Y-%m-%d')

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'FAILED':
                return OptionsChainResponse(
                    symbol=symbol, provider=self.name,
                    snapshot_timestamp=datetime.utcnow(), success=False,
                    error=f"Failed to fetch options for {symbol}"
                )

            calls = []
            puts = []

            # Parse call options
            for exp_date, strikes in data.get('callExpDateMap', {}).items():
                for strike_price, contracts in strikes.items():
                    for contract in contracts:
                        calls.append(OptionsContractInfo(
                            symbol=contract['symbol'],
                            strike=float(strike_price),
                            expiration=datetime.strptime(exp_date.split(':')[0], '%Y-%m-%d').date(),
                            option_type='call',
                            bid=float(contract.get('bid', 0)),
                            ask=float(contract.get('ask', 0)),
                            last=float(contract.get('last', 0)),
                            volume=int(contract.get('totalVolume', 0)),
                            open_interest=int(contract.get('openInterest', 0)),
                            implied_volatility=float(contract.get('volatility', 0) or 0) / 100,
                            delta=float(contract.get('delta', 0) or 0),
                            gamma=float(contract.get('gamma', 0) or 0),
                            theta=float(contract.get('theta', 0) or 0),
                            vega=float(contract.get('vega', 0) or 0)
                        ))

            # Parse put options
            for exp_date, strikes in data.get('putExpDateMap', {}).items():
                for strike_price, contracts in strikes.items():
                    for contract in contracts:
                        puts.append(OptionsContractInfo(
                            symbol=contract['symbol'],
                            strike=float(strike_price),
                            expiration=datetime.strptime(exp_date.split(':')[0], '%Y-%m-%d').date(),
                            option_type='put',
                            bid=float(contract.get('bid', 0)),
                            ask=float(contract.get('ask', 0)),
                            last=float(contract.get('last', 0)),
                            volume=int(contract.get('totalVolume', 0)),
                            open_interest=int(contract.get('openInterest', 0)),
                            implied_volatility=float(contract.get('volatility', 0) or 0) / 100,
                            delta=float(contract.get('delta', 0) or 0),
                            gamma=float(contract.get('gamma', 0) or 0),
                            theta=float(contract.get('theta', 0) or 0),
                            vega=float(contract.get('vega', 0) or 0)
                        ))

            return OptionsChainResponse(
                symbol=symbol,
                provider=self.name,
                calls=calls,
                puts=puts,
                snapshot_timestamp=datetime.utcnow(),
                underlying_price=float(data.get('underlyingPrice', 0)),
                success=True
            )

        except Exception as e:
            return OptionsChainResponse(
                symbol=request.symbol, provider=self.name,
                snapshot_timestamp=datetime.utcnow(), success=False,
                error=f"TD Ameritrade error: {str(e)}"
            )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Get available option expiration dates."""
        try:
            symbol = symbol.upper()
            url = f"{self.base_url}/marketdata/chains"
            params = {
                "apikey": self.api_key,
                "symbol": symbol
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            expirations = set()
            for exp_date in data.get('callExpDateMap', {}).keys():
                date_str = exp_date.split(':')[0]
                expirations.add(datetime.strptime(date_str, '%Y-%m-%d').date())

            return sorted(list(expirations))

        except:
            return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/marketdata/quotes"
            params = {
                "apikey": self.api_key,
                "symbol": "AAPL"
            }
            response = requests.get(url, params=params, timeout=5)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return True  # TD Ameritrade supports options!
