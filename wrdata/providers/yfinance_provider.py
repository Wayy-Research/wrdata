"""
YFinance provider for fetching stock and options data.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import math
import yfinance as yf

from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    OptionsChainData,
    OptionsGreeks,
    OptionsTimeseriesRequest,
    OptionsTimeseriesResponse,
)


class YFinanceProvider(BaseProvider):
    """
    YFinance provider implementation.
    Supports stock data and current options chains (not historical options).
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="yfinance", api_key=api_key)

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical timeseries data using yfinance.
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                **kwargs
            )

            if df.empty:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol}"
                )

            # Convert DataFrame to list of dicts
            df.reset_index(inplace=True)
            data = df.to_dict('records')

            # Convert timestamps to strings
            for record in data:
                if 'Date' in record:
                    record['Date'] = record['Date'].isoformat()
                if 'Datetime' in record:
                    record['Datetime'] = record['Datetime'].isoformat()

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=data,
                metadata={
                    'interval': interval,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(data)
                },
                success=True
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=str(e)
            )

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Fetch current options chain data using yfinance.
        """
        try:
            ticker = yf.Ticker(request.symbol)

            # Get available expiration dates
            available_expirations = []
            try:
                exp_dates = ticker.options
                available_expirations = [
                    datetime.strptime(exp, '%Y-%m-%d').date()
                    for exp in exp_dates
                ]
            except Exception as e:
                return OptionsChainResponse(
                    symbol=request.symbol,
                    provider=self.name,
                    snapshot_timestamp=datetime.utcnow(),
                    success=False,
                    error=f"Failed to get expiration dates: {str(e)}"
                )

            # If no expiration specified, use the nearest one
            if request.expiration_date is None:
                if not available_expirations:
                    return OptionsChainResponse(
                        symbol=request.symbol,
                        provider=self.name,
                        snapshot_timestamp=datetime.utcnow(),
                        success=False,
                        error="No options available for this symbol"
                    )
                expiration_date = available_expirations[0]
            else:
                expiration_date = request.expiration_date

            # Fetch options chain for the expiration date
            exp_str = expiration_date.strftime('%Y-%m-%d')
            opt_chain = ticker.option_chain(exp_str)

            # Get current underlying price
            try:
                info = ticker.info
                underlying_price = Decimal(str(info.get('currentPrice', 0)))
            except:
                underlying_price = None

            # Parse calls
            calls = []
            if opt_chain.calls is not None and not opt_chain.calls.empty:
                calls = self._parse_options_dataframe(
                    opt_chain.calls,
                    "call",
                    expiration_date,
                    underlying_price,
                    request
                )

            # Parse puts
            puts = []
            if opt_chain.puts is not None and not opt_chain.puts.empty:
                puts = self._parse_options_dataframe(
                    opt_chain.puts,
                    "put",
                    expiration_date,
                    underlying_price,
                    request
                )

            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=datetime.utcnow(),
                underlying_price=underlying_price,
                calls=calls,
                puts=puts,
                available_expirations=available_expirations,
                success=True
            )

        except Exception as e:
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=datetime.utcnow(),
                success=False,
                error=str(e)
            )

    def _parse_options_dataframe(
        self,
        df,
        option_type: str,
        expiration_date: date,
        underlying_price: Optional[Decimal],
        request: OptionsChainRequest
    ) -> List[OptionsChainData]:
        """
        Parse yfinance options DataFrame into OptionsChainData objects.
        """
        options_list = []

        for _, row in df.iterrows():
            strike = Decimal(str(row.get('strike', 0)))

            # Apply strike filters if specified
            if request.min_strike is not None and strike < request.min_strike:
                continue
            if request.max_strike is not None and strike > request.max_strike:
                continue

            # Helper functions to safely convert values, handling NaN
            def safe_float(val):
                """Safely convert to float, handling NaN."""
                if val is None:
                    return None
                try:
                    if math.isnan(val):
                        return None
                    return float(val)
                except (ValueError, TypeError):
                    return None

            def safe_int(val):
                """Safely convert to int, handling NaN."""
                if val is None:
                    return None
                try:
                    if math.isnan(val):
                        return None
                    return int(val)
                except (ValueError, TypeError):
                    return None

            def safe_decimal(val):
                """Safely convert to Decimal, handling NaN."""
                if val is None:
                    return None
                try:
                    if math.isnan(val):
                        return None
                    return Decimal(str(val))
                except (ValueError, TypeError):
                    return None

            # Parse greeks
            greeks = OptionsGreeks(
                delta=safe_float(row.get('delta')),
                gamma=safe_float(row.get('gamma')),
                theta=safe_float(row.get('theta')),
                vega=safe_float(row.get('vega')),
                rho=safe_float(row.get('rho')),
            )

            # Calculate intrinsic and extrinsic value
            last_price = safe_decimal(row.get('lastPrice'))
            intrinsic_value = None
            in_the_money = None

            if underlying_price is not None and last_price is not None and last_price > 0:
                if option_type == "call":
                    intrinsic_value = max(Decimal(0), underlying_price - strike)
                    in_the_money = underlying_price > strike
                else:  # put
                    intrinsic_value = max(Decimal(0), strike - underlying_price)
                    in_the_money = strike > underlying_price

            extrinsic_value = None
            if intrinsic_value is not None and last_price is not None and last_price > 0:
                extrinsic_value = last_price - intrinsic_value

            options_data = OptionsChainData(
                contract_symbol=str(row.get('contractSymbol', '')),
                option_type=option_type,
                strike_price=strike,
                expiration_date=expiration_date,
                bid=safe_decimal(row.get('bid')),
                ask=safe_decimal(row.get('ask')),
                last_price=last_price,
                mark_price=None,  # YFinance doesn't provide mark price directly
                volume=safe_int(row.get('volume')),
                open_interest=safe_int(row.get('openInterest')),
                greeks=greeks if any([greeks.delta, greeks.gamma, greeks.theta, greeks.vega, greeks.rho]) else None,
                implied_volatility=safe_float(row.get('impliedVolatility')),
                intrinsic_value=intrinsic_value,
                extrinsic_value=extrinsic_value,
                in_the_money=in_the_money,
                underlying_price=underlying_price
            )

            options_list.append(options_data)

        return options_list

    def get_available_expirations(self, symbol: str) -> List[date]:
        """
        Get list of available expiration dates for a symbol.
        """
        try:
            ticker = yf.Ticker(symbol)
            exp_dates = ticker.options
            return [
                datetime.strptime(exp, '%Y-%m-%d').date()
                for exp in exp_dates
            ]
        except Exception:
            return []

    def validate_connection(self) -> bool:
        """
        Validate that yfinance is working by fetching a known symbol.
        """
        try:
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            return info is not None and len(info) > 0
        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """
        YFinance does not support historical options data.
        """
        return False
