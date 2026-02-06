"""
Polymarket prediction market data provider.

Provides access to Polymarket prediction markets via three free, unauthenticated APIs:
- Gamma API: Market discovery, events, search, tags
- CLOB API: Historical price timeseries, order books, midpoint/last trade prices
- Data API: Public trade history

API Documentation:
- Gamma: https://gamma-api.polymarket.com
- CLOB: https://clob.polymarket.com
- Data: https://data-api.polymarket.com
"""

import json
import requests
import polars as pl
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any

from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse


class PolymarketProvider(BaseProvider):
    """
    Polymarket prediction market data provider.

    All read endpoints are unauthenticated and free to use.
    Prices are probabilities in [0.0, 1.0].
    """

    GAMMA_URL = "https://gamma-api.polymarket.com"
    CLOB_URL = "https://clob.polymarket.com"
    DATA_URL = "https://data-api.polymarket.com"

    # Fidelity options for /prices-history
    FIDELITY_1MIN = 1
    FIDELITY_5MIN = 5
    FIDELITY_15MIN = 15
    FIDELITY_1HR = 60
    FIDELITY_6HR = 360
    FIDELITY_1DAY = 1440

    def __init__(self) -> None:
        super().__init__(name="polymarket")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "wrdata-polymarket-client/1.0",
                "Accept": "application/json",
            }
        )

    # ========================================================================
    # Market Discovery (Gamma API)
    # ========================================================================

    def fetch_events(
        self,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        tag_slug: Optional[str] = None,
        order: Optional[str] = None,
        ascending: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch events (groups of related markets) from Polymarket.

        Args:
            active: Filter to active events only.
            closed: Filter to closed events only.
            limit: Max results per page.
            offset: Pagination offset.
            tag_slug: Filter by tag slug (e.g., "politics", "crypto").
            order: Field to order by (e.g., "volume", "startDate").
            ascending: Sort ascending if True.

        Returns:
            List of event dictionaries.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()
        if tag_slug:
            params["tag_slug"] = tag_slug
        if order:
            params["order"] = order
        if ascending is not None:
            params["ascending"] = str(ascending).lower()

        resp = self.session.get(f"{self.GAMMA_URL}/events", params=params, timeout=15)
        resp.raise_for_status()
        events = resp.json()

        # Parse JSON-encoded fields on nested markets
        for event in events:
            for market in event.get("markets", []):
                self._parse_gamma_market_fields(market)

        return events

    def fetch_event(self, event_id_or_slug: str) -> Dict[str, Any]:
        """
        Fetch a single event by ID or slug.

        Args:
            event_id_or_slug: Gamma event ID or slug.

        Returns:
            Event dict with nested markets.
        """
        resp = self.session.get(
            f"{self.GAMMA_URL}/events/{event_id_or_slug}", timeout=15
        )
        resp.raise_for_status()
        event = resp.json()

        for market in event.get("markets", []):
            self._parse_gamma_market_fields(market)

        return event

    def fetch_markets(
        self,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
        tag_slug: Optional[str] = None,
        order: Optional[str] = None,
        ascending: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch individual markets from Polymarket Gamma API.

        Args:
            active: Filter to active markets only.
            closed: Filter to closed markets only.
            limit: Max results per page.
            offset: Pagination offset.
            tag_slug: Filter by tag slug.
            order: Field to order by.
            ascending: Sort ascending if True.

        Returns:
            List of market dictionaries.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()
        if tag_slug:
            params["tag_slug"] = tag_slug
        if order:
            params["order"] = order
        if ascending is not None:
            params["ascending"] = str(ascending).lower()

        resp = self.session.get(f"{self.GAMMA_URL}/markets", params=params, timeout=15)
        resp.raise_for_status()
        markets = resp.json()

        for market in markets:
            self._parse_gamma_market_fields(market)

        return markets

    def fetch_market(self, market_id_or_slug: str) -> Dict[str, Any]:
        """
        Fetch a single market by condition ID or slug.

        Args:
            market_id_or_slug: Gamma market condition_id or slug.

        Returns:
            Market dictionary with parsed fields.
        """
        resp = self.session.get(
            f"{self.GAMMA_URL}/markets/{market_id_or_slug}", timeout=15
        )
        resp.raise_for_status()
        market = resp.json()
        self._parse_gamma_market_fields(market)
        return market

    def search_markets(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search Polymarket using the public search endpoint.

        Args:
            query: Search string (e.g., "bitcoin", "election").
            limit: Max results.

        Returns:
            List of matching market dictionaries.
        """
        params: Dict[str, Any] = {"query": query, "limit": limit}
        resp = self.session.get(
            f"{self.GAMMA_URL}/public-search", params=params, timeout=15
        )
        resp.raise_for_status()
        results = resp.json()

        # The response may be a list of markets or a dict with markets key
        markets = results if isinstance(results, list) else results.get("markets", [])

        for market in markets:
            self._parse_gamma_market_fields(market)

        return markets

    def fetch_tags(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch available category tags.

        Args:
            limit: Max tags to return.

        Returns:
            List of tag dictionaries with label and slug.
        """
        resp = self.session.get(
            f"{self.GAMMA_URL}/tags", params={"limit": limit}, timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    # ========================================================================
    # Historical Data (CLOB API)
    # ========================================================================

    def fetch_price_history(
        self,
        token_id: str,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        interval: Optional[str] = None,
        fidelity: int = FIDELITY_1HR,
    ) -> pl.DataFrame:
        """
        Fetch historical price timeseries for a CLOB token.

        Args:
            token_id: The clob_token_id (NOT condition_id). Each outcome
                (YES/NO) has its own token_id.
            start_ts: Start timestamp (Unix seconds). Defaults to 30 days ago.
            end_ts: End timestamp (Unix seconds). Defaults to now.
            interval: Interval string (unused by CLOB, here for interface compat).
            fidelity: Granularity in minutes. Use class constants:
                FIDELITY_1MIN=1, FIDELITY_5MIN=5, FIDELITY_15MIN=15,
                FIDELITY_1HR=60, FIDELITY_6HR=360, FIDELITY_1DAY=1440.

        Returns:
            Polars DataFrame with columns: timestamp, price.
        """
        now = int(datetime.now(timezone.utc).timestamp())
        if end_ts is None:
            end_ts = now
        if start_ts is None:
            start_ts = end_ts - 30 * 86400  # 30 days

        params: Dict[str, Any] = {
            "market": token_id,
            "startTs": start_ts,
            "endTs": end_ts,
            "fidelity": fidelity,
        }

        resp = self.session.get(
            f"{self.CLOB_URL}/prices-history", params=params, timeout=15
        )
        resp.raise_for_status()
        data = resp.json()

        # Response is {"history": [{"t": 1234567890, "p": "0.65"}, ...]}
        history = data.get("history", [])

        if not history:
            return pl.DataFrame({"timestamp": [], "price": []}).cast(
                {"timestamp": pl.Datetime, "price": pl.Float64}
            )

        rows = [
            {
                "timestamp": datetime.fromtimestamp(point["t"], tz=timezone.utc),
                "price": float(point["p"]),
            }
            for point in history
        ]

        df = pl.DataFrame(rows)
        return df.sort("timestamp")

    def fetch_market_history(
        self,
        market_id_or_slug: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fidelity: int = FIDELITY_1HR,
    ) -> pl.DataFrame:
        """
        Convenience: fetch YES and NO price history for a market.

        Resolves market -> clob_token_ids, then fetches price history
        for both outcomes and joins them.

        Args:
            market_id_or_slug: Market condition_id or slug.
            start_date: Start date as "YYYY-MM-DD".
            end_date: End date as "YYYY-MM-DD".
            fidelity: Granularity in minutes (default: 1 hour).

        Returns:
            Polars DataFrame with columns: timestamp, yes_price, no_price.
        """
        market = self.fetch_market(market_id_or_slug)

        token_ids = market.get("clobTokenIds", [])
        outcomes = market.get("outcomes", [])

        if not token_ids or len(token_ids) < 1:
            raise ValueError(
                f"Market '{market_id_or_slug}' has no CLOB token IDs. "
                "It may not be traded on the CLOB."
            )

        # Convert dates to timestamps
        start_ts = None
        end_ts = None
        if start_date:
            start_ts = int(
                datetime.strptime(start_date, "%Y-%m-%d")
                .replace(tzinfo=timezone.utc)
                .timestamp()
            )
        if end_date:
            end_ts = int(
                (
                    datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    + timedelta(days=1)
                ).timestamp()
            )

        # Fetch history for each outcome token
        result_df: Optional[pl.DataFrame] = None

        for i, tid in enumerate(token_ids):
            outcome_label = outcomes[i] if i < len(outcomes) else f"outcome_{i}"
            col_name = f"{outcome_label.lower()}_price"

            df = self.fetch_price_history(
                token_id=tid,
                start_ts=start_ts,
                end_ts=end_ts,
                fidelity=fidelity,
            )

            if df.is_empty():
                continue

            df = df.rename({"price": col_name})

            if result_df is None:
                result_df = df
            else:
                result_df = result_df.join(df, on="timestamp", how="outer_coalesce")

        if result_df is None:
            return pl.DataFrame(
                {"timestamp": [], "yes_price": [], "no_price": []}
            ).cast(
                {
                    "timestamp": pl.Datetime,
                    "yes_price": pl.Float64,
                    "no_price": pl.Float64,
                }
            )

        return result_df.sort("timestamp")

    # ========================================================================
    # Order Book & Live Pricing (CLOB API)
    # ========================================================================

    def fetch_orderbook(self, token_id: str) -> Dict[str, Any]:
        """
        Fetch the current order book for a CLOB token.

        Args:
            token_id: The clob_token_id for one outcome.

        Returns:
            Dict with "bids" and "asks" lists of [price, size].
        """
        resp = self.session.get(
            f"{self.CLOB_URL}/book",
            params={"token_id": token_id},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_market_orderbook(
        self, market_id_or_slug: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Convenience: fetch order books for both YES and NO tokens of a market.

        Args:
            market_id_or_slug: Market condition_id or slug.

        Returns:
            Dict like {"Yes": {"bids": [...], "asks": [...]},
                        "No": {"bids": [...], "asks": [...]}}.
        """
        market = self.fetch_market(market_id_or_slug)
        token_ids = market.get("clobTokenIds", [])
        outcomes = market.get("outcomes", [])

        result: Dict[str, Dict[str, Any]] = {}

        for i, tid in enumerate(token_ids):
            label = outcomes[i] if i < len(outcomes) else f"outcome_{i}"
            result[label] = self.fetch_orderbook(tid)

        return result

    def fetch_midpoint(self, token_id: str) -> Optional[float]:
        """
        Get current midpoint price for a token.

        Args:
            token_id: The clob_token_id.

        Returns:
            Midpoint price as float, or None if unavailable.
        """
        resp = self.session.get(
            f"{self.CLOB_URL}/midpoint",
            params={"token_id": token_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        mid = data.get("mid")
        return float(mid) if mid is not None else None

    def fetch_last_trade_price(self, token_id: str) -> Optional[float]:
        """
        Get last trade price for a token.

        Args:
            token_id: The clob_token_id.

        Returns:
            Last trade price as float, or None if unavailable.
        """
        resp = self.session.get(
            f"{self.CLOB_URL}/last-trade-price",
            params={"token_id": token_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        price = data.get("price")
        return float(price) if price is not None else None

    # ========================================================================
    # Trade History (Data API)
    # ========================================================================

    def fetch_trades(
        self,
        market: Optional[str] = None,
        event_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch public trade history.

        Args:
            market: Filter by condition_id (market).
            event_id: Filter by event ID.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            List of trade dictionaries.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if market:
            params["market"] = market
        if event_id:
            params["event_id"] = event_id

        resp = self.session.get(f"{self.DATA_URL}/trades", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ========================================================================
    # BaseProvider Interface
    # ========================================================================

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs: Any,
    ) -> DataResponse:
        """
        Standard DataStream interface - maps to fetch_market_history().

        Symbol can be a market slug or condition_id.
        """
        fidelity_map = {
            "1m": self.FIDELITY_1MIN,
            "5m": self.FIDELITY_5MIN,
            "15m": self.FIDELITY_15MIN,
            "1h": self.FIDELITY_1HR,
            "6h": self.FIDELITY_6HR,
            "1d": self.FIDELITY_1DAY,
        }
        fidelity = fidelity_map.get(interval, self.FIDELITY_1HR)

        try:
            df = self.fetch_market_history(
                market_id_or_slug=symbol,
                start_date=start_date,
                end_date=end_date,
                fidelity=fidelity,
            )

            if df.is_empty():
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="No data returned",
                )

            data = df.to_dicts()
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=data,
                success=True,
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=str(e),
            )

    def fetch_options_chain(self, request: Any) -> Any:
        raise NotImplementedError("Polymarket does not provide options data")

    def get_available_expirations(self, symbol: str) -> List[date]:
        raise NotImplementedError("Polymarket does not provide options data")

    def validate_connection(self) -> bool:
        """Check connectivity to Polymarket Gamma API."""
        try:
            resp = self.session.get(
                f"{self.GAMMA_URL}/markets",
                params={"limit": 1},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    @staticmethod
    def _parse_gamma_market_fields(market: Dict[str, Any]) -> None:
        """
        Parse JSON-encoded string fields from Gamma API in-place.

        Gamma returns outcomes, outcomePrices, and clobTokenIds as
        JSON-encoded strings like '["Yes","No"]'. This decodes them
        to native Python lists.
        """
        for field in ("outcomes", "outcomePrices", "clobTokenIds"):
            val = market.get(field)
            if isinstance(val, str):
                try:
                    market[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    market[field] = []


if __name__ == "__main__":
    provider = PolymarketProvider()

    print("Testing Polymarket Provider...")

    print("\n1. Fetching active events:")
    events = provider.fetch_events(active=True, limit=3)
    for e in events:
        title = e.get("title", "Untitled")
        n_markets = len(e.get("markets", []))
        print(f"  {title} ({n_markets} markets)")

    print("\n2. Searching for 'bitcoin':")
    results = provider.search_markets("bitcoin", limit=3)
    for m in results:
        q = m.get("question", m.get("title", "?"))
        print(f"  {q}")

    print("\n3. Fetching tags:")
    tags = provider.fetch_tags(limit=5)
    for t in tags:
        print(f"  {t.get('label', t.get('slug', '?'))}")

    print("\n4. Validate connection:")
    print(f"  Connected: {provider.validate_connection()}")

    print("\nPolymarket provider test complete!")
