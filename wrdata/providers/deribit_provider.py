"""
Deribit provider for crypto derivatives and options.

Deribit is the LEADING platform for Bitcoin and Ethereum options/futures.
FREE API - No key required for market data!

This is one of the ONLY providers with actual crypto options data!

API Docs: https://docs.deribit.com/
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    OptionsContractInfo
)


class DeribitProvider(BaseProvider):
    """
    Deribit provider for crypto derivatives and options.

    FREE features (no API key):
    - BTC & ETH options (ONLY provider with crypto options!)
    - Futures data
    - Historical data
    - Order book snapshots
    - Trade history
    - Volatility index

    This is UNIQUE - actual cryptocurrency options data!
    """

    def __init__(self, api_key: Optional[str] = None, testnet: bool = False):
        super().__init__(name="deribit", api_key=api_key)

        if testnet:
            self.base_url = "https://test.deribit.com/api/v2"
        else:
            self.base_url = "https://www.deribit.com/api/v2"

        self.testnet = testnet

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """Fetch historical futures/perpetual data from Deribit."""
        try:
            # Deribit uses specific instrument names
            # e.g., BTC-PERPETUAL, ETH-PERPETUAL
            symbol = symbol.upper()
            if 'PERPETUAL' not in symbol and 'BTC' in symbol:
                symbol = 'BTC-PERPETUAL'
            elif 'PERPETUAL' not in symbol and 'ETH' in symbol:
                symbol = 'ETH-PERPETUAL'

            # Map intervals
            interval_map = {
                "1m": "1",
                "5m": "5",
                "15m": "15",
                "30m": "30",
                "1h": "60",
                "4h": "240",
                "1d": "1D",
                "1D": "1D",
            }

            resolution = interval_map.get(interval, "1D")

            # Convert to timestamps (milliseconds)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

            url = f"{self.base_url}/public/get_tradingview_chart_data"
            params = {
                "instrument_name": symbol,
                "start_timestamp": start_ts,
                "end_timestamp": end_ts,
                "resolution": resolution
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('error'):
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"Deribit error: {data['error'].get('message', 'Unknown error')}"
                )

            result = data.get('result', {})
            timestamps = result.get('ticks', [])
            opens = result.get('open', [])
            highs = result.get('high', [])
            lows = result.get('low', [])
            closes = result.get('close', [])
            volumes = result.get('volume', [])

            if not timestamps:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            records = []
            for i in range(len(timestamps)):
                dt = datetime.fromtimestamp(timestamps[i] / 1000)
                records.append({
                    'Date': dt.strftime('%Y-%m-%d'),
                    'open': float(opens[i]) if i < len(opens) else 0,
                    'high': float(highs[i]) if i < len(highs) else 0,
                    'low': float(lows[i]) if i < len(lows) else 0,
                    'close': float(closes[i]) if i < len(closes) else 0,
                    'volume': float(volumes[i]) if i < len(volumes) else 0,
                })

            return DataResponse(
                symbol=symbol, provider=self.name, data=records,
                metadata={'interval': interval, 'records': len(records), 'source': 'Deribit'},
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Deribit error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """Fetch crypto options chain from Deribit - UNIQUE FEATURE!"""
        try:
            # Deribit supports BTC and ETH options
            symbol = request.symbol.upper()
            currency = 'BTC' if 'BTC' in symbol else 'ETH'

            # Get all instruments for the currency
            url = f"{self.base_url}/public/get_instruments"
            params = {
                "currency": currency,
                "kind": "option",  # Options only
                "expired": "false"
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('error'):
                return OptionsChainResponse(
                    symbol=symbol, provider=self.name,
                    snapshot_timestamp=datetime.utcnow(), success=False,
                    error=f"Deribit error: {data['error'].get('message', 'Unknown error')}"
                )

            instruments = data.get('result', [])

            # Filter by expiration if specified
            if request.expiration_date:
                exp_str = request.expiration_date.strftime('%d%b%y').upper()
                instruments = [i for i in instruments if exp_str in i['instrument_name']]

            calls = []
            puts = []

            # Get detailed data for each option
            for instrument in instruments[:50]:  # Limit to avoid rate limits
                name = instrument['instrument_name']
                strike = instrument['strike']
                exp_timestamp = instrument['expiration_timestamp'] / 1000
                expiration = datetime.fromtimestamp(exp_timestamp).date()

                # Determine option type from name
                is_call = '-C' in name
                is_put = '-P' in name

                # Get current quote
                quote_url = f"{self.base_url}/public/ticker"
                quote_params = {"instrument_name": name}
                quote_resp = requests.get(quote_url, params=quote_params, timeout=5)

                if quote_resp.status_code == 200:
                    quote_data = quote_resp.json().get('result', {})

                    contract = OptionsContractInfo(
                        symbol=name,
                        strike=float(strike),
                        expiration=expiration,
                        option_type='call' if is_call else 'put',
                        bid=float(quote_data.get('best_bid_price', 0) or 0),
                        ask=float(quote_data.get('best_ask_price', 0) or 0),
                        last=float(quote_data.get('last_price', 0) or 0),
                        volume=int(quote_data.get('stats', {}).get('volume', 0) or 0),
                        open_interest=int(quote_data.get('open_interest', 0) or 0),
                        implied_volatility=float(quote_data.get('mark_iv', 0) or 0) / 100,
                        delta=float(quote_data.get('greeks', {}).get('delta', 0) or 0),
                        gamma=float(quote_data.get('greeks', {}).get('gamma', 0) or 0),
                        theta=float(quote_data.get('greeks', {}).get('theta', 0) or 0),
                        vega=float(quote_data.get('greeks', {}).get('vega', 0) or 0)
                    )

                    if is_call:
                        calls.append(contract)
                    else:
                        puts.append(contract)

            # Get underlying price
            underlying_url = f"{self.base_url}/public/ticker"
            underlying_params = {"instrument_name": f"{currency}-PERPETUAL"}
            underlying_resp = requests.get(underlying_url, params=underlying_params, timeout=5)
            underlying_price = 0
            if underlying_resp.status_code == 200:
                underlying_price = underlying_resp.json().get('result', {}).get('last_price', 0)

            return OptionsChainResponse(
                symbol=symbol,
                provider=self.name,
                calls=calls,
                puts=puts,
                snapshot_timestamp=datetime.utcnow(),
                underlying_price=float(underlying_price),
                success=True
            )

        except Exception as e:
            return OptionsChainResponse(
                symbol=request.symbol, provider=self.name,
                snapshot_timestamp=datetime.utcnow(), success=False,
                error=f"Deribit error: {str(e)}"
            )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Get available option expiration dates for BTC or ETH."""
        try:
            currency = 'BTC' if 'BTC' in symbol.upper() else 'ETH'

            url = f"{self.base_url}/public/get_instruments"
            params = {
                "currency": currency,
                "kind": "option",
                "expired": "false"
            }

            response = requests.get(url, params=params, timeout=30)
            data = response.json()

            if data.get('error'):
                return []

            instruments = data.get('result', [])
            expirations = set()

            for instrument in instruments:
                exp_timestamp = instrument['expiration_timestamp'] / 1000
                exp_date = datetime.fromtimestamp(exp_timestamp).date()
                expirations.add(exp_date)

            return sorted(list(expirations))

        except:
            return []

    def validate_connection(self) -> bool:
        try:
            url = f"{self.base_url}/public/test"
            response = requests.get(url, timeout=5)
            data = response.json()
            return data.get('result', {}).get('version') is not None
        except:
            return False

    def supports_historical_options(self) -> bool:
        return True  # Deribit supports crypto options!
