"""
Alpaca Options Data Provider for wrdata.

Alpaca provides comprehensive options data including:
- Real-time option chain snapshots with Greeks
- Historical option bars, trades, and quotes (since Feb 2024)
- Multi-leg strategy support

API Docs: https://docs.alpaca.markets/docs/options-trading
Data Docs: https://docs.alpaca.markets/docs/historical-option-data

Data Plans:
- Basic (Free): IEX data for equities, indicative feed for options (15-min delay)
- Algo Trader Plus: Full OPRA consolidated feed (real-time)
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import re
import logging

from wrdata.providers.base import BaseProvider

logger = logging.getLogger(__name__)
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    OptionsChainData,
    OptionsGreeks,
    OptionsTimeseriesRequest,
    OptionsTimeseriesResponse,
)


class AlpacaOptionsProvider(BaseProvider):
    """
    Alpaca Options Data Provider.

    Provides historical and real-time options data from Alpaca's Market Data API.

    Features:
    - Option chain snapshots with Greeks (delta, gamma, theta, vega)
    - Historical option bars (OHLCV) since February 2024
    - Historical trades and quotes
    - Underlying equity data

    Authentication:
        Requires Alpaca API key and secret. Get them at:
        https://app.alpaca.markets/signup

    Example:
        >>> provider = AlpacaOptionsProvider(
        ...     api_key="your_key",
        ...     api_secret="your_secret"
        ... )
        >>> chain = provider.fetch_options_chain(
        ...     OptionsChainRequest(symbol="SPY")
        ... )
    """

    # Alpaca API endpoints
    DATA_BASE_URL = "https://data.alpaca.markets"
    PAPER_BASE_URL = "https://paper-api.alpaca.markets"
    LIVE_BASE_URL = "https://api.alpaca.markets"

    # OCC option symbol regex pattern
    # Format: SYMBOL + YYMMDD + C/P + strike (8 digits, no decimal)
    # Example: SPY240119C00500000 = SPY Jan 19 2024 $500 Call
    OCC_PATTERN = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper: bool = True,
    ):
        """
        Initialize Alpaca Options Provider.

        Args:
            api_key: Alpaca API key ID
            api_secret: Alpaca API secret key
            paper: Use paper trading endpoint (default True)
        """
        super().__init__(name="alpaca_options", api_key=api_key)

        if not api_key or not api_secret:
            raise ValueError(
                "Alpaca API key and secret required. "
                "Get them at: https://app.alpaca.markets/signup"
            )

        self.api_secret = api_secret
        self.paper = paper

        # Set trading endpoint based on paper/live mode
        self.trading_url = self.PAPER_BASE_URL if paper else self.LIVE_BASE_URL

        # Authentication headers
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
            "Accept": "application/json",
        }

        # Cache for contract info
        self._contract_cache: Dict[str, Dict] = {}

    def validate_connection(self) -> bool:
        """
        Validate API connection by checking account status.

        Returns:
            True if connection is valid
        """
        try:
            url = f"{self.trading_url}/v2/account"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            return "account_number" in data or "id" in data

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """
        Alpaca supports historical options data since February 2024.

        Returns:
            True - Alpaca has historical option bars/trades/quotes
        """
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
        Fetch historical price data for underlying equity.

        Args:
            symbol: Stock/ETF ticker (e.g., "SPY", "AAPL")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval - "1m", "5m", "15m", "1h", "1d"

        Returns:
            DataResponse with OHLCV data
        """
        try:
            symbol = symbol.upper()

            # Map interval to Alpaca timeframe
            interval_map = {
                "1m": "1Min",
                "5m": "5Min",
                "15m": "15Min",
                "30m": "30Min",
                "1h": "1Hour",
                "1d": "1Day",
                "1D": "1Day",
                "1wk": "1Week",
            }

            timeframe = interval_map.get(interval, "1Day")

            # Build URL for stock bars
            url = f"{self.DATA_BASE_URL}/v2/stocks/{symbol}/bars"

            params = {
                "start": start_date,
                "end": end_date,
                "timeframe": timeframe,
                "adjustment": "raw",
                "feed": "iex",  # Use free IEX feed (sip requires subscription)
                "limit": 10000,
            }

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            bars = data.get("bars", [])

            if not bars:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for {symbol}",
                )

            # Convert to standard format (use `or 0` for None safety)
            records = []
            for bar in bars:
                records.append(
                    {
                        "Date": bar.get("t", ""),
                        "open": float(bar.get("o") or 0),
                        "high": float(bar.get("h") or 0),
                        "low": float(bar.get("l") or 0),
                        "close": float(bar.get("c") or 0),
                        "volume": int(bar.get("v") or 0),
                        "vwap": float(bar.get("vw") or 0),
                        "trade_count": int(bar.get("n") or 0),
                    }
                )

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    "interval": interval,
                    "timeframe": timeframe,
                    "start_date": start_date,
                    "end_date": end_date,
                    "records": len(records),
                    "source": "Alpaca",
                    "paper": self.paper,
                },
                success=True,
            )

        except requests.exceptions.HTTPError as e:
            error_msg = self._parse_http_error(e)
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=error_msg,
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Alpaca API error: {str(e)}",
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """
        Fetch current options chain snapshot with Greeks.

        Args:
            request: OptionsChainRequest with symbol and filters

        Returns:
            OptionsChainResponse with calls and puts data
        """
        try:
            symbol = request.symbol.upper()

            # Get option chain snapshot (includes Greeks!)
            url = f"{self.DATA_BASE_URL}/v1beta1/options/snapshots/{symbol}"

            params = {
                "feed": "indicative",  # or "opra" for paid subscribers
                "limit": 1000,
            }

            # Add expiration filter if specified
            if request.expiration_date:
                params["expiration_date"] = request.expiration_date.strftime("%Y-%m-%d")

            # Add strike filters if specified
            if request.min_strike:
                params["strike_price_gte"] = str(request.min_strike)
            if request.max_strike:
                params["strike_price_lte"] = str(request.max_strike)

            # Add option type filter
            if request.option_type:
                params["type"] = request.option_type.lower()  # "call" or "put"

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            snapshots = data.get("snapshots", {})

            if not snapshots:
                return OptionsChainResponse(
                    symbol=symbol,
                    provider=self.name,
                    snapshot_timestamp=datetime.now(timezone.utc),
                    success=False,
                    error=f"No options chain data for {symbol}",
                )

            # Parse snapshots into calls and puts
            calls = []
            puts = []
            expirations_set = set()
            underlying_price = None

            for contract_symbol, snapshot in snapshots.items():
                # Parse OCC symbol to extract details
                parsed = self._parse_occ_symbol(contract_symbol)
                if not parsed:
                    continue

                exp_date, option_type, strike = parsed
                expirations_set.add(exp_date)

                # Extract quote data
                quote = snapshot.get("latestQuote", {})
                trade = snapshot.get("latestTrade", {})
                greeks_data = snapshot.get("greeks", {})

                # Get implied volatility
                iv = snapshot.get("impliedVolatility")

                # Build Greeks object
                greeks = None
                if greeks_data:
                    greeks = OptionsGreeks(
                        delta=greeks_data.get("delta"),
                        gamma=greeks_data.get("gamma"),
                        theta=greeks_data.get("theta"),
                        vega=greeks_data.get("vega"),
                        rho=greeks_data.get("rho"),
                    )

                # Calculate mid price
                bid = Decimal(str(quote.get("bp", 0))) if quote.get("bp") else None
                ask = Decimal(str(quote.get("ap", 0))) if quote.get("ap") else None
                last_price = Decimal(str(trade.get("p", 0))) if trade.get("p") else None

                mark_price = None
                if bid and ask:
                    mark_price = (bid + ask) / 2

                # Build option data
                option_data = OptionsChainData(
                    contract_symbol=contract_symbol,
                    option_type=option_type,
                    strike_price=Decimal(str(strike)),
                    expiration_date=exp_date,
                    bid=bid,
                    ask=ask,
                    last_price=last_price,
                    mark_price=mark_price,
                    volume=trade.get("s"),  # trade size
                    open_interest=snapshot.get("openInterest"),
                    greeks=greeks,
                    implied_volatility=iv,
                    underlying_price=(
                        Decimal(str(snapshot.get("underlyingPrice", 0)))
                        if snapshot.get("underlyingPrice")
                        else None
                    ),
                )

                # Track underlying price
                if option_data.underlying_price and not underlying_price:
                    underlying_price = option_data.underlying_price

                # Add to appropriate list
                if option_type == "call":
                    calls.append(option_data)
                else:
                    puts.append(option_data)

            # Sort by expiration, then strike
            calls.sort(key=lambda x: (x.expiration_date, x.strike_price))
            puts.sort(key=lambda x: (x.expiration_date, x.strike_price))

            # Sort expirations
            available_expirations = sorted(list(expirations_set))

            return OptionsChainResponse(
                symbol=symbol,
                provider=self.name,
                snapshot_timestamp=datetime.now(timezone.utc),
                underlying_price=underlying_price,
                calls=calls,
                puts=puts,
                available_expirations=available_expirations,
                metadata={
                    "total_contracts": len(calls) + len(puts),
                    "call_count": len(calls),
                    "put_count": len(puts),
                    "expiration_count": len(available_expirations),
                    "source": "Alpaca",
                    "feed": params.get("feed", "indicative"),
                    "paper": self.paper,
                },
                success=True,
            )

        except requests.exceptions.HTTPError as e:
            error_msg = self._parse_http_error(e)
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=datetime.now(timezone.utc),
                success=False,
                error=error_msg,
            )

        except Exception as e:
            logger.error(f"Alpaca options error for {request.symbol}: {e}")
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=self.name,
                snapshot_timestamp=datetime.now(timezone.utc),
                success=False,
                error=f"Alpaca options error: {str(e)}",
            )

    def fetch_options_timeseries(
        self, request: OptionsTimeseriesRequest
    ) -> OptionsTimeseriesResponse:
        """
        Fetch historical options data (bars, trades, or quotes).

        Alpaca provides historical option data since February 2024.

        Args:
            request: OptionsTimeseriesRequest with contract or underlying symbol

        Returns:
            OptionsTimeseriesResponse with historical data
        """
        try:
            # Determine what to fetch
            if request.contract_symbol:
                # Fetch specific contract history
                return self._fetch_contract_bars(request)
            elif request.underlying_symbol:
                # Fetch all contracts for underlying (limited)
                return self._fetch_underlying_options_bars(request)
            else:
                return OptionsTimeseriesResponse(
                    symbol="",
                    provider=self.name,
                    data=[],
                    success=False,
                    error="Must specify contract_symbol or underlying_symbol",
                )

        except Exception as e:
            return OptionsTimeseriesResponse(
                symbol=request.contract_symbol or request.underlying_symbol or "",
                provider=self.name,
                data=[],
                success=False,
                error=f"Alpaca options timeseries error: {str(e)}",
            )

    def _fetch_contract_bars(
        self, request: OptionsTimeseriesRequest
    ) -> OptionsTimeseriesResponse:
        """Fetch historical bars for a specific option contract."""
        contract = request.contract_symbol.upper()

        # Map interval to Alpaca timeframe
        interval_map = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "1h": "1Hour",
            "1d": "1Day",
            "1D": "1Day",
        }
        timeframe = interval_map.get(request.interval, "1Day")

        url = f"{self.DATA_BASE_URL}/v1beta1/options/bars"

        params = {
            "symbols": contract,
            "start": request.start_date,
            "end": request.end_date,
            "timeframe": timeframe,
            "limit": 10000,
        }

        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        bars = data.get("bars", {}).get(contract, [])

        if not bars:
            return OptionsTimeseriesResponse(
                symbol=contract,
                provider=self.name,
                data=[],
                success=False,
                error=f"No historical data for {contract}",
            )

        # Convert to records
        records = []
        for bar in bars:
            records.append(
                {
                    "timestamp": bar.get("t"),
                    "open": float(bar.get("o", 0)),
                    "high": float(bar.get("h", 0)),
                    "low": float(bar.get("l", 0)),
                    "close": float(bar.get("c", 0)),
                    "volume": int(bar.get("v", 0)),
                    "trade_count": int(bar.get("n", 0)),
                    "vwap": float(bar.get("vw", 0)) if bar.get("vw") else None,
                }
            )

        return OptionsTimeseriesResponse(
            symbol=contract,
            provider=self.name,
            data=records,
            metadata={
                "interval": request.interval,
                "timeframe": timeframe,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "records": len(records),
                "source": "Alpaca",
            },
            success=True,
        )

    def _fetch_underlying_options_bars(
        self, request: OptionsTimeseriesRequest
    ) -> OptionsTimeseriesResponse:
        """Fetch historical bars for multiple contracts of an underlying."""
        underlying = request.underlying_symbol.upper()

        # First, get current chain to find contract symbols
        chain_request = OptionsChainRequest(
            symbol=underlying,
            expiration_date=request.expiration_date,
            option_type=request.option_type,
        )

        chain = self.fetch_options_chain(chain_request)

        if not chain.success:
            return OptionsTimeseriesResponse(
                symbol=underlying,
                provider=self.name,
                data=[],
                success=False,
                error=f"Could not get options chain: {chain.error}",
            )

        # Get all contract symbols
        all_contracts = [c.contract_symbol for c in chain.calls + chain.puts]

        if not all_contracts:
            return OptionsTimeseriesResponse(
                symbol=underlying,
                provider=self.name,
                data=[],
                success=False,
                error=f"No contracts found for {underlying}",
            )

        # Limit to avoid huge requests (fetch first 50 contracts)
        contracts_to_fetch = all_contracts[:50]

        # Map interval to Alpaca timeframe
        interval_map = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "1h": "1Hour",
            "1d": "1Day",
            "1D": "1Day",
        }
        timeframe = interval_map.get(request.interval, "1Day")

        url = f"{self.DATA_BASE_URL}/v1beta1/options/bars"

        params = {
            "symbols": ",".join(contracts_to_fetch),
            "start": request.start_date,
            "end": request.end_date,
            "timeframe": timeframe,
            "limit": 10000,
        }

        response = requests.get(url, headers=self.headers, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()
        all_bars = data.get("bars", {})

        # Flatten into records with contract info
        records = []
        for contract, bars in all_bars.items():
            parsed = self._parse_occ_symbol(contract)
            if not parsed:
                continue

            exp_date, option_type, strike = parsed

            for bar in bars:
                records.append(
                    {
                        "contract_symbol": contract,
                        "underlying": underlying,
                        "expiration": exp_date.isoformat(),
                        "option_type": option_type,
                        "strike": strike,
                        "timestamp": bar.get("t"),
                        "open": float(bar.get("o", 0)),
                        "high": float(bar.get("h", 0)),
                        "low": float(bar.get("l", 0)),
                        "close": float(bar.get("c", 0)),
                        "volume": int(bar.get("v", 0)),
                        "trade_count": int(bar.get("n", 0)),
                        "vwap": float(bar.get("vw", 0)) if bar.get("vw") else None,
                    }
                )

        # Sort by timestamp, then contract
        records.sort(key=lambda x: (x["timestamp"], x["contract_symbol"]))

        return OptionsTimeseriesResponse(
            symbol=underlying,
            provider=self.name,
            data=records,
            metadata={
                "interval": request.interval,
                "timeframe": timeframe,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "records": len(records),
                "contracts_fetched": len(contracts_to_fetch),
                "contracts_with_data": len(all_bars),
                "source": "Alpaca",
            },
            success=True,
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """
        Get available option expiration dates for a symbol.

        Args:
            symbol: Underlying stock/ETF ticker

        Returns:
            List of available expiration dates, sorted ascending
        """
        try:
            # Use options chain endpoint to get expirations
            chain = self.fetch_options_chain(OptionsChainRequest(symbol=symbol))

            if chain.success:
                return chain.available_expirations

            return []

        except Exception:
            return []

    def get_option_quotes(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical option quotes (bid/ask).

        Args:
            symbols: List of OCC option symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Max records to return

        Returns:
            List of quote records
        """
        try:
            url = f"{self.DATA_BASE_URL}/v1beta1/options/quotes"

            params = {
                "symbols": ",".join(symbols),
                "start": start_date,
                "end": end_date,
                "limit": limit,
            }

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            all_quotes = data.get("quotes", {})

            records = []
            for symbol, quotes in all_quotes.items():
                for q in quotes:
                    records.append(
                        {
                            "symbol": symbol,
                            "timestamp": q.get("t"),
                            "bid_price": float(q.get("bp", 0)),
                            "ask_price": float(q.get("ap", 0)),
                            "bid_size": int(q.get("bs", 0)),
                            "ask_size": int(q.get("as", 0)),
                            "bid_exchange": q.get("bx"),
                            "ask_exchange": q.get("ax"),
                        }
                    )

            return records

        except Exception as e:
            logger.error(f"Failed to get option quotes: {e}")
            return []

    def get_option_trades(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical option trades.

        Args:
            symbols: List of OCC option symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Max records to return

        Returns:
            List of trade records
        """
        try:
            url = f"{self.DATA_BASE_URL}/v1beta1/options/trades"

            params = {
                "symbols": ",".join(symbols),
                "start": start_date,
                "end": end_date,
                "limit": limit,
            }

            response = requests.get(
                url, headers=self.headers, params=params, timeout=30
            )
            response.raise_for_status()

            data = response.json()
            all_trades = data.get("trades", {})

            records = []
            for symbol, trades in all_trades.items():
                for t in trades:
                    records.append(
                        {
                            "symbol": symbol,
                            "timestamp": t.get("t"),
                            "price": float(t.get("p", 0)),
                            "size": int(t.get("s", 0)),
                            "exchange": t.get("x"),
                            "conditions": t.get("c", []),
                        }
                    )

            return records

        except Exception as e:
            logger.error(f"Failed to get option trades: {e}")
            return []

    def get_latest_option_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest quote for a single option contract.

        Args:
            symbol: OCC option symbol

        Returns:
            Quote data dict or None
        """
        try:
            url = f"{self.DATA_BASE_URL}/v1beta1/options/quotes/latest"

            params = {"symbols": symbol}

            response = requests.get(
                url, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()

            data = response.json()
            quotes = data.get("quotes", {})

            if symbol in quotes:
                q = quotes[symbol]
                return {
                    "symbol": symbol,
                    "timestamp": q.get("t"),
                    "bid_price": float(q.get("bp", 0)),
                    "ask_price": float(q.get("ap", 0)),
                    "bid_size": int(q.get("bs", 0)),
                    "ask_size": int(q.get("as", 0)),
                }

            return None

        except Exception:
            return None

    def _parse_occ_symbol(self, symbol: str) -> Optional[tuple]:
        """
        Parse OCC option symbol to extract components.

        OCC Format: SYMBOL + YYMMDD + C/P + STRIKE (8 digits)
        Example: SPY240119C00500000 = SPY Jan 19 2024 $500 Call

        Args:
            symbol: OCC option symbol

        Returns:
            Tuple of (expiration_date, option_type, strike_price) or None
        """
        match = self.OCC_PATTERN.match(symbol)
        if not match:
            return None

        underlying, date_str, cp, strike_str = match.groups()

        # Parse expiration date (YYMMDD)
        try:
            exp_date = datetime.strptime(date_str, "%y%m%d").date()
        except ValueError:
            return None

        # Parse option type
        option_type = "call" if cp == "C" else "put"

        # Parse strike (last 8 digits, divide by 1000 for actual price)
        strike = float(strike_str) / 1000.0

        return (exp_date, option_type, strike)

    def build_occ_symbol(
        self, underlying: str, expiration: date, option_type: str, strike: float
    ) -> str:
        """
        Build OCC option symbol from components.

        Args:
            underlying: Stock ticker (e.g., "SPY")
            expiration: Expiration date
            option_type: "call" or "put"
            strike: Strike price

        Returns:
            OCC symbol string
        """
        # Format: SYMBOL + YYMMDD + C/P + STRIKE (8 digits, strike * 1000)
        date_str = expiration.strftime("%y%m%d")
        cp = "C" if option_type.lower() == "call" else "P"
        strike_int = int(strike * 1000)
        strike_str = f"{strike_int:08d}"

        return f"{underlying.upper()}{date_str}{cp}{strike_str}"

    def _parse_http_error(self, error: requests.exceptions.HTTPError) -> str:
        """Parse HTTP error into user-friendly message."""
        status_code = error.response.status_code

        if status_code == 401:
            return "Invalid API credentials - check your API key and secret"
        elif status_code == 403:
            return "Access forbidden - you may need Algo Trader Plus subscription for this data"
        elif status_code == 404:
            return "Resource not found - symbol may not have options"
        elif status_code == 429:
            return "Rate limit exceeded - please slow down requests"
        else:
            try:
                error_body = error.response.json()
                return f"HTTP {status_code}: {error_body.get('message', error.response.text)}"
            except Exception:
                return f"HTTP {status_code}: {error.response.text}"
