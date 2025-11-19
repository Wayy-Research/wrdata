"""
Kalshi prediction market data provider.

Provides access to Kalshi prediction markets including:
- Market listings and search
- Market details and event information
- Orderbook data
- Historical probability tracking

API Documentation: https://docs.kalshi.com/
"""

import requests
import polars as pl
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import re

from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse


class KalshiProvider(BaseProvider):
    """
    Kalshi prediction market data provider.

    Public API endpoints require no authentication for market data.
    Trading functionality requires API key (not implemented yet).
    """

    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="kalshi", api_key=api_key)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "wrdata-kalshi-client/1.0",
            "Accept": "application/json"
        })

    def fetch_markets(
        self,
        series_ticker: Optional[str] = None,
        status: str = "open",
        category: Optional[str] = None,
        limit: int = 100,
        cursor: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch list of prediction markets from Kalshi.

        Args:
            series_ticker: Filter by series (e.g., 'KXHIGHNY')
            status: 'open', 'closed', or 'settled'
            category: Filter by category (economics, politics, etc.)
            limit: Maximum number of results
            cursor: Pagination cursor for next page

        Returns:
            List of market dictionaries with ticker, title, price, volume
        """
        params = {
            "status": status,
            "limit": limit
        }

        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor

        try:
            response = self.session.get(
                f"{self.BASE_URL}/markets",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            markets = []
            for market in data.get("markets", []):
                # Parse market data
                market_data = {
                    "ticker": market.get("ticker"),
                    "title": market.get("title"),
                    "subtitle": market.get("subtitle"),
                    "yes_price": market.get("yes_price"),  # cents
                    "no_price": market.get("no_price"),
                    "volume": market.get("volume", 0),
                    "open_interest": market.get("open_interest", 0),
                    "category": market.get("category"),
                    "status": market.get("status"),
                    "close_date": market.get("close_date"),
                    "expiration_date": market.get("expiration_date"),
                    "strike_price": self._extract_strike_price(market.get("title", "")),
                    "underlying_symbol": self._extract_underlying_symbol(market.get("title", ""))
                }

                # Filter by category if specified
                if category and market_data["category"] != category:
                    continue

                markets.append(market_data)

            return markets

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch Kalshi markets: {str(e)}")

    def fetch_market_details(self, market_ticker: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific market.

        Args:
            market_ticker: The market ticker (e.g., 'KXHIGHNY-25DEC31-B5000')

        Returns:
            Dictionary with detailed market information
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/markets/{market_ticker}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            market = data.get("market", {})

            return {
                "ticker": market.get("ticker"),
                "title": market.get("title"),
                "subtitle": market.get("subtitle"),
                "yes_price": market.get("yes_price"),
                "no_price": market.get("no_price"),
                "volume": market.get("volume", 0),
                "open_interest": market.get("open_interest", 0),
                "category": market.get("category"),
                "status": market.get("status"),
                "close_date": market.get("close_date"),
                "expiration_date": market.get("expiration_date"),
                "result": market.get("result"),
                "strike_price": self._extract_strike_price(market.get("title", "")),
                "underlying_symbol": self._extract_underlying_symbol(market.get("title", "")),
                "can_close_early": market.get("can_close_early"),
                "expiration_value": market.get("expiration_value"),
                "last_price": market.get("last_price"),
                "previous_yes_price": market.get("previous_yes_price")
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch market details for {market_ticker}: {str(e)}")

    def fetch_orderbook(self, market_ticker: str) -> Dict[str, List[List]]:
        """
        Get current orderbook for a market.

        Args:
            market_ticker: The market ticker

        Returns:
            Dictionary with yes_bids and no_bids
            Format: [[price, quantity], [price, quantity], ...]
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/markets/{market_ticker}/orderbook",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            orderbook = data.get("orderbook", {})

            return {
                "yes_bids": orderbook.get("yes", []),
                "no_bids": orderbook.get("no", [])
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch orderbook for {market_ticker}: {str(e)}")

    def fetch_market_history(
        self,
        market_ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Fetch historical probability data for a market.

        Note: Kalshi API may have limited historical data.
        This method attempts to reconstruct history from available data.

        Args:
            market_ticker: The market ticker
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Polars DataFrame with timestamp, yes_price, no_price, volume
        """
        # TODO: Implement when Kalshi provides historical endpoint
        # For now, return empty DataFrame with schema

        return pl.DataFrame({
            "timestamp": [],
            "yes_price": [],
            "no_price": [],
            "volume": []
        })

    def search_markets(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search markets by keyword.

        Args:
            query: Search query (e.g., 'bitcoin', 'SPX', 'CPI')
            limit: Maximum results

        Returns:
            List of matching markets
        """
        # Fetch all open markets and filter by query
        all_markets = self.fetch_markets(status="open", limit=200)

        query_lower = query.lower()
        matches = []

        for market in all_markets:
            title_lower = market.get("title", "").lower()
            subtitle_lower = market.get("subtitle", "").lower()

            if query_lower in title_lower or query_lower in subtitle_lower:
                matches.append(market)

            if len(matches) >= limit:
                break

        return matches

    def _extract_strike_price(self, title: str) -> Optional[float]:
        """
        Extract strike price from market title.

        Examples:
        "Will BTC close above $100,000?" → 100000
        "Will SPX be above 5000?" → 5000
        "Will CPI be above 3%?" → 3.0
        """
        # Try to find numbers with common patterns
        patterns = [
            r'\$[\d,]+\.?\d*',  # $100,000 or $5000.50
            r'[\d,]+\.?\d*%',   # 3.5%
            r'\b[\d,]+\.?\d*\b' # Plain numbers
        ]

        for pattern in patterns:
            matches = re.findall(pattern, title)
            if matches:
                # Take the first match and clean it
                strike_str = matches[0].replace('$', '').replace(',', '').replace('%', '')
                try:
                    return float(strike_str)
                except ValueError:
                    continue

        return None

    def _extract_underlying_symbol(self, title: str) -> Optional[str]:
        """
        Extract underlying symbol from market title.

        Examples:
        "Will BTC close above $100k?" → "BTCUSD"
        "Will SPX be above 5000?" → "SPX"
        "Will NVDA reach $200?" → "NVDA"
        "Will CPI be above 3%?" → "CPIAUCSL"
        "Will unemployment be below 4%?" → "UNRATE"
        """
        title_upper = title.upper()

        # Known mappings for crypto
        crypto_map = {
            'BTC': 'BTCUSD',
            'BITCOIN': 'BTCUSD',
            'ETH': 'ETHUSD',
            'ETHEREUM': 'ETHUSD',
            'SOL': 'SOLUSD',
            'SOLANA': 'SOLUSD'
        }

        # Known mappings for economic indicators
        econ_map = {
            'CPI': 'CPIAUCSL',
            'INFLATION': 'CPIAUCSL',
            'UNEMPLOYMENT': 'UNRATE',
            'GDP': 'GDP',
            'FED FUNDS': 'FEDFUNDS',
            'INTEREST RATE': 'FEDFUNDS'
        }

        # Check crypto
        for key, symbol in crypto_map.items():
            if key in title_upper:
                return symbol

        # Check economic indicators
        for key, symbol in econ_map.items():
            if key in title_upper:
                return symbol

        # Check for stock tickers (2-5 uppercase letters)
        ticker_match = re.search(r'\b([A-Z]{2,5})\b', title_upper)
        if ticker_match:
            ticker = ticker_match.group(1)
            # Exclude common words
            if ticker not in ['WILL', 'CLOSE', 'ABOVE', 'BELOW', 'THE', 'AND', 'OR']:
                return ticker

        return None

    # BaseProvider abstract methods (not applicable for Kalshi)

    def fetch_timeseries(self, symbol: str, start_date: str, end_date: str,
                        interval: str = "1d", **kwargs) -> DataResponse:
        """
        Kalshi doesn't provide traditional timeseries data.
        Use fetch_market_history() for probability history instead.
        """
        raise NotImplementedError(
            "Kalshi provider does not support timeseries. Use fetch_market_history() instead."
        )

    def fetch_options_chain(self, request):
        raise NotImplementedError("Kalshi does not provide options data")

    def get_available_expirations(self, symbol: str) -> List[date]:
        raise NotImplementedError("Kalshi does not provide options data")

    def validate_connection(self) -> bool:
        """
        Validate that we can connect to Kalshi API.
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/markets",
                params={"limit": 1},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


if __name__ == "__main__":
    # Test the provider
    provider = KalshiProvider()

    print("Testing Kalshi Provider...")
    print("\n1. Fetching open markets:")
    markets = provider.fetch_markets(limit=5)
    for m in markets:
        print(f"  {m['ticker']}: {m['title']} ({m['yes_price']}¢)")

    if markets:
        print(f"\n2. Fetching details for {markets[0]['ticker']}:")
        details = provider.fetch_market_details(markets[0]['ticker'])
        print(f"  Volume: {details['volume']}")
        print(f"  Strike: {details['strike_price']}")
        print(f"  Underlying: {details['underlying_symbol']}")

        print(f"\n3. Fetching orderbook:")
        orderbook = provider.fetch_orderbook(markets[0]['ticker'])
        print(f"  YES bids: {orderbook['yes_bids'][:3]}")
        print(f"  NO bids: {orderbook['no_bids'][:3]}")

    print(f"\n4. Searching for 'bitcoin':")
    btc_markets = provider.search_markets("bitcoin", limit=3)
    for m in btc_markets:
        print(f"  {m['title']} ({m['yes_price']}¢)")

    print("\n✅ Kalshi provider test complete!")
