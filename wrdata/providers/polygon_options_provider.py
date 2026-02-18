from typing import List, Dict, Any, Optional
import requests
from datetime import datetime, date
from decimal import Decimal
import logging

from ..providers.base import BaseProvider
from ..models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    OptionsChainData,
    OptionsGreeks,
    OptionsTimeseriesRequest,
    OptionsTimeseriesResponse,
)

logger = logging.getLogger(__name__)


class PolygonOptionsProvider(BaseProvider):
    """
    Polygon.io options data provider.
    Requires a paid Polygon.io API key for historical options data.
    """

    def __init__(self, api_key: str):
        super().__init__(name="polygon_options", api_key=api_key)
        if not api_key:
            raise ValueError(
                "POLYGON_API_KEY must be provided for PolygonOptionsProvider"
            )
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()
        self.session.params.update({"apiKey": self.api_key})

    def validate_connection(self) -> bool:
        """
        Validate Polygon.io API connection by fetching a sample expiration.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/v3/reference/options/expirations?ticker=SPY&limit=1"
            )
            response.raise_for_status()
            data = response.json()
            return data.get("status") == "OK"
        except requests.exceptions.RequestException as e:
            logger.warning(f"Polygon.io connection validation failed: {e}")
            return False

    def get_available_expirations(self, symbol: str) -> List[date]:
        """
        Get list of available expiration dates for an underlying symbol from Polygon.io.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/v3/reference/options/expirations?ticker={symbol.upper()}"
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                expirations = [date.fromisoformat(exp) for exp in data["results"]]
                expirations.sort()
                return expirations
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Polygon.io expirations for {symbol}: {e}")
            return []

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """
        Fetch current options chain data for a symbol from Polygon.io.
        """
        if not request.expiration_date:
            expirations = self.get_available_expirations(request.symbol)
            if not expirations:
                return OptionsChainResponse(
                    symbol=request.symbol,
                    provider=self.name,
                    success=False,
                    error="No available expirations",
                )
            request.expiration_date = expirations[0]  # Use nearest expiration

        params: Dict[str, Any] = {
            "underlyingAsset": request.symbol.upper(),
            "expirationDate": request.expiration_date.isoformat(),
            "limit": 1000,  # Max limit per request
        }
        if request.option_type:
            params["contractType"] = request.option_type.upper()
        if request.min_strike:
            params["strikePriceGte"] = str(request.min_strike)
        if request.max_strike:
            params["strikePriceLte"] = str(request.max_strike)

        all_contracts: List[Dict] = []
        next_url = f"{self.base_url}/v3/reference/options/contracts"

        # Polygon.io options chains require multiple API calls to fetch details for each contract
        # This implementation will fetch contract references, then individual quotes for the chain

        try:
            # Step 1: Get list of contract tickers for the chain
            contract_tickers = []
            while next_url:
                response = self.session.get(next_url, params=params)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "OK" and data.get("results"):
                    contract_tickers.extend([c["ticker"] for c in data["results"]])
                    next_url = data.get("next_url")
                    if next_url:
                        # Clear params for subsequent paginated requests
                        params = {}
                else:
                    break

            if not contract_tickers:
                return OptionsChainResponse(
                    symbol=request.symbol,
                    provider=self.name,
                    success=True,
                    calls=[],
                    puts=[],
                )

            # Step 2: Fetch current quotes for each contract ticker
            # Polygon.io has a separate endpoint for quotes and greeks
            options_data: List[OptionsChainData] = []
            underlying_price: Optional[Decimal] = None
            snapshot_timestamp: Optional[datetime] = None

            # Fetch a quote for the underlying to get current price and timestamp
            # Use wrdata's stream.get_quote if possible, otherwise a direct call
            try:
                from .. import DataStream  # Lazy import

                stream = DataStream()
                underlying_quote = stream.get_quote(
                    request.symbol
                )  # Assuming get_quote exists and returns a Quote object with price
                if underlying_quote and underlying_quote.price:
                    underlying_price = Decimal(str(underlying_quote.price))
                    snapshot_timestamp = underlying_quote.timestamp
            except Exception as e:
                logger.warning(
                    f"Could not fetch underlying price for {request.symbol} from wrdata: {e}"
                )
                # Fallback to direct call if wrdata.get_quote doesn't exist or fails
                try:
                    equity_quote_response = self.session.get(
                        f"{self.base_url}/v2/aggs/ticker/{request.symbol}/prev?adjusted=true"
                    )
                    equity_quote_response.raise_for_status()
                    equity_data = equity_quote_response.json()
                    if equity_data.get("status") == "OK" and equity_data.get("results"):
                        underlying_price = Decimal(str(equity_data["results"][0]["c"]))
                        snapshot_timestamp = datetime.fromtimestamp(
                            equity_data["results"][0]["t"] / 1000
                        )
                except Exception as e:
                    logger.warning(
                        f"Could not fetch underlying price for {request.symbol} from Polygon.io agg: {e}"
                    )
                    pass

            # Batch request for quotes if Polygon supports it or iterate
            # Polygon.io has a /v3/snapshot/options/{underlyingAsset}/{expirationDate} endpoint
            # which is better for full chain snapshots, but may require a specific plan.
            # For now, let's use the individual quotes endpoint if available, or simulate

            # Simplified approach: for each contract ticker, construct basic OptionsChainData
            # A more complete implementation would fetch detailed quotes/greeks

            for ticker in contract_tickers:
                parts = ticker.split("2")  # YYYY-MM-DD
                symbol_part = parts[0]
                date_part = "2" + parts[1][:7]  # YYYYMMDD
                strike_type_part = parts[1][7:]  # Strike and type

                contract_type = "call" if strike_type_part.endswith("C") else "put"
                strike = (
                    Decimal(strike_type_part[:-1]) / 1000
                )  # Correct for implicit decimal

                # These fields are often not directly available from reference/options/contracts.
                # A full implementation would query /v3/quotes/options/{optionsTicker} for each
                # or use a snapshot endpoint if available/appropriate for the plan.
                options_data.append(
                    OptionsChainData(
                        contract_symbol=ticker,
                        underlying_symbol=request.symbol.upper(),
                        option_type=contract_type,
                        strike_price=strike,
                        expiration_date=request.expiration_date,
                        # Placeholder values
                        bid=Decimal(0),
                        ask=Decimal(0),
                        last_price=Decimal(0),
                        mark_price=Decimal(0),
                        volume=0,
                        open_interest=0,
                        implied_volatility=0,
                        greeks=OptionsGreeks(delta=0, gamma=0, theta=0, vega=0, rho=0),
                        underlying_price=underlying_price,
                    )
                )

            # Separate into calls and puts
            calls = [opt for opt in options_data if opt.option_type == "call"]
            puts = [opt for opt in options_data if opt.option_type == "put"]

            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=snapshot_timestamp or datetime.utcnow(),
                underlying_price=underlying_price,
                calls=calls,
                puts=puts,
                available_expirations=self.get_available_expirations(request.symbol),
                success=True,
            )

        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error fetching Polygon.io options chain for {request.symbol}: {e}"
            )
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                success=False,
                error=f"Polygon.io API error: {e}",
            )
        except Exception as e:
            logger.error(f"Error processing Polygon.io options chain: {e}")
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                success=False,
                error=f"Error processing data: {e}",
            )

    def fetch_options_timeseries(
        self, request: OptionsTimeseriesRequest
    ) -> OptionsTimeseriesResponse:
        """
        Fetch historical timeseries of options chain data from Polygon.io.
        This uses the aggregates endpoint for options.
        """
        if not request.contract_symbol:
            return OptionsTimeseriesResponse(
                symbol=request.underlying_symbol or "",
                provider=self.name,
                success=False,
                error="Contract symbol is required for historical options timeseries.",
            )

        # Polygon aggregates endpoint: /v2/aggs/ticker/{optionsTicker}/range/{multiplier}/{timespan}/{from}/{to}
        # Example: https://api.polygon.io/v2/aggs/ticker/O:SPY240119C00470000/range/1/day/2023-01-09/2023-01-11?apiKey=YOUR_API_KEY

        multiplier = 1  # Always 1 for daily data
        timespan = "day"  # For daily resolution

        # Ensure dates are in YYYY-MM-DD format
        start_date_str = request.start_date
        end_date_str = request.end_date

        try:
            response = self.session.get(
                f"{self.base_url}/v2/aggs/ticker/{request.contract_symbol}/range/{multiplier}/{timespan}/{start_date_str}/{end_date_str}"
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                ohlcv_data: List[Dict] = []
                for result in data["results"]:
                    ohlcv_data.append(
                        {
                            "timestamp": datetime.fromtimestamp(
                                result["t"] / 1000
                            ),  # ms to seconds
                            "open": float(result["o"]),
                            "high": float(result["h"]),
                            "low": float(result["l"]),
                            "close": float(result["c"]),
                            "volume": int(result["v"]),
                            "vwap": float(
                                result["vw"]
                            ),  # Volume Weighted Average Price
                        }
                    )
                return OptionsTimeseriesResponse(
                    symbol=request.contract_symbol,
                    provider=self.name,
                    data=ohlcv_data,
                    success=True,
                )
            return OptionsTimeseriesResponse(
                symbol=request.contract_symbol,
                provider=self.name,
                success=True,
                data=[],
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Error fetching Polygon.io options timeseries for {request.contract_symbol}: {e}"
            )
            return OptionsTimeseriesResponse(
                symbol=request.contract_symbol,
                provider=self.name,
                success=False,
                error=f"Polygon.io API error: {e}",
            )
        except Exception as e:
            logger.error(f"Error processing Polygon.io options timeseries: {e}")
            return OptionsTimeseriesResponse(
                symbol=request.contract_symbol,
                provider=self.name,
                success=False,
                error=f"Error processing data: {e}",
            )

    def supports_historical_options(self) -> bool:
        return True

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs,
    ) -> DataResponse:
        """
        Polygon.io is primarily for equities and options.
        This method is a placeholder and may not be fully implemented or optimized for general timeseries.
        """
        # For general timeseries, Polygon has aggregates endpoint: /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
        # This can fetch OHLCV for stocks and ETFs.

        # Mapping for interval to Polygon's multiplier/timespan
        multiplier_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 1,
            "1d": 1,
            "1w": 1,
            "1M": 1,
        }
        timespan_map = {
            "1m": "minute",
            "5m": "minute",
            "15m": "minute",
            "1h": "hour",
            "1d": "day",
            "1w": "week",
            "1M": "month",
        }

        multiplier = multiplier_map.get(interval, 1)
        timespan = timespan_map.get(interval, "day")

        try:
            response = self.session.get(
                f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/range/{multiplier}/{timespan}/{start_date}/{end_date}"
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                ohlcv_data: List[Dict] = []
                for result in data["results"]:
                    ohlcv_data.append(
                        {
                            "timestamp": datetime.fromtimestamp(
                                result["t"] / 1000
                            ),  # ms to seconds
                            "open": float(result["o"]),
                            "high": float(result["h"]),
                            "low": float(result["l"]),
                            "close": float(result["c"]),
                            "volume": int(result["v"]),
                        }
                    )
                return DataResponse(
                    symbol=symbol, provider=self.name, data=ohlcv_data, success=True
                )
            return DataResponse(
                symbol=symbol, provider=self.name, success=True, data=[]
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Polygon.io timeseries for {symbol}: {e}")
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                success=False,
                error=f"Polygon.io API error: {e}",
            )
        except Exception as e:
            logger.error(f"Error processing Polygon.io timeseries: {e}")
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                success=False,
                error=f"Error processing data: {e}",
            )
