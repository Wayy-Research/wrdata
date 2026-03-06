"""
Symbiotic Protocol data provider.

Fetches restaking protocol data (TVL, vaults, operators, flows) from:
1. DefiLlama REST API (always works, no key) — TVL history, token breakdown
2. The Graph subgraph (if available) — vault entities, operators, delegation events
3. Alchemy RPC (if key provided) — real-time contract reads for live state

Symbiotic is a permissionless restaking protocol on Ethereum that allows
any ERC-20 token to be used as collateral for securing networks.
"""

import logging
import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
)
from wrdata.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFILLAMA_BASE = "https://api.llama.fi"
DEFILLAMA_PROTOCOL_SLUG = "symbiotic"

# Symbiotic subgraph on The Graph (decentralized)
SUBGRAPH_URL = (
    "https://gateway.thegraph.com/api/{api_key}/subgraphs/id/"
    "2gM6pYBdNjVFWHbCkB7fCqoGJjduMDjdJMRaQT8CiDgX"
)

# Hosted fallback (no key needed, may be deprecated)
SUBGRAPH_HOSTED_URL = (
    "https://api.studio.thegraph.com/query/90004/symbiotic/version/latest"
)


class SymbioticProvider(BaseProvider):
    """
    Data provider for the Symbiotic restaking protocol.

    Data source layering (graceful degradation):
    1. DefiLlama — TVL history, token breakdown (always available)
    2. The Graph subgraph — vault/operator entities (if key or hosted endpoint)
    3. Alchemy RPC — live contract state (if key provided)
    """

    def __init__(
        self,
        alchemy_api_key: Optional[str] = None,
        thegraph_api_key: Optional[str] = None,
    ) -> None:
        super().__init__(name="symbiotic")
        self._alchemy_key = alchemy_api_key
        self._thegraph_key = thegraph_api_key
        self._client: Optional[httpx.Client] = None
        self._proto_cache: Optional[Dict[str, Any]] = None
        self._proto_cache_ts: float = 0.0

    # ------------------------------------------------------------------
    # Lazy httpx client
    # ------------------------------------------------------------------

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=30.0, follow_redirects=True)
        return self._client

    def close(self) -> None:
        if self._client and not self._client.is_closed:
            self._client.close()

    # ------------------------------------------------------------------
    # BaseProvider required methods
    # ------------------------------------------------------------------

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs: Any,
    ) -> DataResponse:
        """Fetch TVL history from DefiLlama.

        Args:
            symbol: "TVL" for protocol-level TVL.
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            interval: ignored (daily granularity from DefiLlama)
            **kwargs: data_type="tvl"|"flows" supported
        """
        data_type = kwargs.get("data_type", "tvl")
        try:
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ).timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ).timestamp())

            if data_type == "flows":
                rows = self._fetch_daily_flows_raw(start_ts, end_ts)
            else:
                rows = self._fetch_tvl_history_raw(start_ts, end_ts)

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=rows,
                metadata={
                    "data_type": data_type,
                    "source": "defillama",
                    "start": start_date,
                    "end": end_date,
                },
            )
        except Exception as e:
            logger.error(f"Symbiotic fetch_timeseries error: {e}")
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=str(e),
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """Restaking protocol — no options chain."""
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.now(timezone.utc),
            calls=[],
            puts=[],
            success=False,
            error="Symbiotic is a restaking protocol, not an options market",
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """No expirations — restaking is not options."""
        return []

    def validate_connection(self) -> bool:
        """Ping DefiLlama to verify connectivity."""
        try:
            resp = self.client.get(
                f"{DEFILLAMA_BASE}/protocol/{DEFILLAMA_PROTOCOL_SLUG}"
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Custom public methods
    # ------------------------------------------------------------------

    def fetch_protocol_summary(self) -> Dict[str, Any]:
        """Protocol overview: TVL, vault/operator count, collateral breakdown, 24h change."""
        try:
            proto = self._get_protocol_data()

            tvl = proto.get("currentChainTvls", {})
            total_tvl = sum(
                v for k, v in tvl.items()
                if not k.startswith("staking") and not k.endswith("-staking")
            )

            # Calculate 24h change from TVL history
            tvl_history = proto.get("tvl", [])
            change_24h = 0.0
            change_24h_pct = 0.0
            if len(tvl_history) >= 2:
                latest = tvl_history[-1].get("totalLiquidityUSD", 0)
                prev = tvl_history[-2].get("totalLiquidityUSD", 0)
                change_24h = latest - prev
                if prev > 0:
                    change_24h_pct = (change_24h / prev) * 100

            # Collateral breakdown from chainTvls
            collateral = self._extract_collateral_breakdown(proto)

            # Vault/operator counts from subgraph (best-effort)
            vault_count = 0
            operator_count = 0
            try:
                vaults = self.fetch_vaults(limit=1, skip=0)
                vault_count = vaults.get("total_count", 0)
                operators = self.fetch_operators(limit=1)
                operator_count = operators.get("total_count", 0)
            except Exception:
                pass

            return {
                "tvl": round(total_tvl, 2),
                "tvl_formatted": self._format_usd(total_tvl),
                "change_24h": round(change_24h, 2),
                "change_24h_pct": round(change_24h_pct, 2),
                "vault_count": vault_count,
                "operator_count": operator_count,
                "collateral_tokens": len(collateral),
                "chains": list(tvl.keys()),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"fetch_protocol_summary error: {e}")
            return {
                "tvl": 0,
                "tvl_formatted": "$0",
                "change_24h": 0,
                "change_24h_pct": 0,
                "vault_count": 0,
                "operator_count": 0,
                "collateral_tokens": 0,
                "chains": [],
                "error": str(e),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

    def fetch_vaults(self, limit: int = 50, skip: int = 0) -> Dict[str, Any]:
        """Fetch vault list from subgraph."""
        query = """
        query Vaults($first: Int!, $skip: Int!) {
            vaults(
                first: $first
                skip: $skip
                orderBy: activeStake
                orderDirection: desc
            ) {
                id
                collateral
                activeStake
                slasher
                epochDuration
                depositWhitelist
                isDepositLimit
                createdTimestamp
                createdBlockNumber
            }
        }
        """
        try:
            data = self._query_subgraph(query, {"first": limit, "skip": skip})
            vaults = data.get("vaults", [])

            # Also get total count
            count_query = """
            query { vaultCounter(id: "counter") { count } }
            """
            count_data = self._query_subgraph(count_query, {})
            total = 0
            counter = count_data.get("vaultCounter")
            if counter:
                total = int(counter.get("count", 0))

            return {
                "vaults": [self._format_vault(v) for v in vaults],
                "total_count": total if total > 0 else len(vaults),
                "source": "subgraph",
            }
        except Exception as e:
            logger.warning(f"Subgraph vault query failed: {e}")
            return {"vaults": [], "total_count": 0, "source": "unavailable", "error": str(e)}

    def fetch_operators(self, limit: int = 50) -> Dict[str, Any]:
        """Fetch operator list from subgraph."""
        query = """
        query Operators($first: Int!) {
            operators(
                first: $first
                orderBy: createdTimestamp
                orderDirection: desc
            ) {
                id
                networkOptInsCount
                vaultOptInsCount
                createdTimestamp
                createdBlockNumber
            }
        }
        """
        try:
            data = self._query_subgraph(query, {"first": limit})
            operators = data.get("operators", [])

            count_query = """
            query { operatorCounter(id: "counter") { count } }
            """
            count_data = self._query_subgraph(count_query, {})
            total = 0
            counter = count_data.get("operatorCounter")
            if counter:
                total = int(counter.get("count", 0))

            return {
                "operators": [self._format_operator(o) for o in operators],
                "total_count": total if total > 0 else len(operators),
                "source": "subgraph",
            }
        except Exception as e:
            logger.warning(f"Subgraph operator query failed: {e}")
            return {"operators": [], "total_count": 0, "source": "unavailable", "error": str(e)}

    def fetch_daily_flows(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Daily net deposit/withdrawal flows from DefiLlama TVL deltas."""
        try:
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ).timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ).timestamp())
            return self._fetch_daily_flows_raw(start_ts, end_ts)
        except Exception as e:
            logger.error(f"fetch_daily_flows error: {e}")
            return []

    def fetch_collateral_breakdown(self) -> List[Dict[str, Any]]:
        """Per-token TVL distribution from DefiLlama tokensInUsd."""
        try:
            proto = self._get_protocol_data()
            return self._extract_collateral_breakdown(proto)
        except Exception as e:
            logger.error(f"fetch_collateral_breakdown error: {e}")
            return []

    def get_data_source_status(self) -> Dict[str, Any]:
        """Health check for each data source layer."""
        status: Dict[str, Any] = {
            "defillama": False,
            "subgraph": False,
            "alchemy": False,
            "has_alchemy_key": self._alchemy_key is not None,
            "has_thegraph_key": self._thegraph_key is not None,
        }

        # DefiLlama
        try:
            resp = self.client.get(
                f"{DEFILLAMA_BASE}/protocol/{DEFILLAMA_PROTOCOL_SLUG}",
                timeout=10.0,
            )
            status["defillama"] = resp.status_code == 200
        except Exception:
            pass

        # Subgraph
        try:
            test_query = '{ _meta { block { number } } }'
            result = self._query_subgraph(test_query, {})
            status["subgraph"] = "_meta" in result
        except Exception:
            pass

        # Alchemy
        if self._alchemy_key:
            try:
                resp = self.client.post(
                    f"https://eth-mainnet.g.alchemy.com/v2/{self._alchemy_key}",
                    json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                    timeout=10.0,
                )
                status["alchemy"] = resp.status_code == 200
            except Exception:
                pass

        return status

    # ------------------------------------------------------------------
    # Internal: DefiLlama
    # ------------------------------------------------------------------

    def _get_protocol_data(self, cache_seconds: int = 30) -> Dict[str, Any]:
        """Fetch full protocol data from DefiLlama (with short TTL cache)."""
        now = time.time()
        if (
            self._proto_cache is not None
            and (now - self._proto_cache_ts) < cache_seconds
        ):
            return self._proto_cache

        resp = self.client.get(
            f"{DEFILLAMA_BASE}/protocol/{DEFILLAMA_PROTOCOL_SLUG}"
        )
        resp.raise_for_status()
        self._proto_cache = resp.json()
        self._proto_cache_ts = now
        return self._proto_cache

    def _fetch_tvl_history_raw(
        self, start_ts: int, end_ts: int
    ) -> List[Dict[str, Any]]:
        """Extract daily TVL timeseries from DefiLlama protocol data."""
        proto = self._get_protocol_data()
        tvl_history = proto.get("tvl", [])

        rows = []
        for point in tvl_history:
            ts = point.get("date", 0)
            if start_ts <= ts <= end_ts:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                rows.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "timestamp": ts,
                    "tvl": round(point.get("totalLiquidityUSD", 0), 2),
                })
        return rows

    def _fetch_daily_flows_raw(
        self, start_ts: int, end_ts: int
    ) -> List[Dict[str, Any]]:
        """Calculate daily net flows from TVL deltas."""
        proto = self._get_protocol_data()
        tvl_history = proto.get("tvl", [])

        # Filter to range and compute deltas
        filtered = [
            p for p in tvl_history
            if start_ts <= p.get("date", 0) <= end_ts
        ]

        flows = []
        for i in range(1, len(filtered)):
            curr_tvl = filtered[i].get("totalLiquidityUSD", 0)
            prev_tvl = filtered[i - 1].get("totalLiquidityUSD", 0)
            net_flow = curr_tvl - prev_tvl
            ts = filtered[i].get("date", 0)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)

            flows.append({
                "date": dt.strftime("%Y-%m-%d"),
                "timestamp": ts,
                "net_flow": round(net_flow, 2),
                "tvl": round(curr_tvl, 2),
                "deposit": round(net_flow, 2) if net_flow > 0 else 0,
                "withdrawal": round(abs(net_flow), 2) if net_flow < 0 else 0,
            })
        return flows

    def _extract_collateral_breakdown(
        self, proto: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract per-token TVL breakdown from DefiLlama data."""
        tokens_in_usd = proto.get("currentChainTvls", {})

        # Try to get token-level breakdown from tokensInUsd
        tokens = proto.get("tokensInUsd", [])
        if tokens and isinstance(tokens, list) and len(tokens) > 0:
            # tokensInUsd is [{date, tokens: {symbol: value}}]
            latest = tokens[-1] if tokens else {}
            token_map = latest.get("tokens", {})
            total = sum(token_map.values()) if token_map else 1

            breakdown = []
            for symbol, value in sorted(
                token_map.items(), key=lambda x: x[1], reverse=True
            ):
                breakdown.append({
                    "token": symbol,
                    "tvl_usd": round(value, 2),
                    "share_pct": round((value / total) * 100, 2) if total > 0 else 0,
                })
            return breakdown

        # Fallback: use chain-level TVL as proxy
        total = sum(
            v for k, v in tokens_in_usd.items()
            if not k.startswith("staking") and not k.endswith("-staking")
        )
        breakdown = []
        for chain, value in sorted(
            tokens_in_usd.items(), key=lambda x: x[1], reverse=True
        ):
            if chain.startswith("staking") or chain.endswith("-staking"):
                continue
            breakdown.append({
                "token": chain,
                "tvl_usd": round(value, 2),
                "share_pct": round((value / total) * 100, 2) if total > 0 else 0,
            })
        return breakdown

    # ------------------------------------------------------------------
    # Internal: The Graph subgraph
    # ------------------------------------------------------------------

    def _get_subgraph_url(self) -> str:
        """Get the best available subgraph URL."""
        if self._thegraph_key:
            return SUBGRAPH_URL.format(api_key=self._thegraph_key)
        return SUBGRAPH_HOSTED_URL

    def _query_subgraph(
        self, query: str, variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against the Symbiotic subgraph."""
        url = self._get_subgraph_url()
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        resp = self.client.post(url, json=payload, timeout=15.0)
        resp.raise_for_status()
        result = resp.json()

        if "errors" in result:
            raise RuntimeError(f"Subgraph errors: {result['errors']}")

        return result.get("data", {})

    # ------------------------------------------------------------------
    # Internal: formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_vault(v: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw subgraph vault entity."""
        active_stake = int(v.get("activeStake", 0))
        created_ts = int(v.get("createdTimestamp", 0))

        return {
            "address": v.get("id", ""),
            "collateral": v.get("collateral", ""),
            "active_stake_raw": str(active_stake),
            "active_stake_eth": round(active_stake / 1e18, 4),
            "slasher": v.get("slasher", ""),
            "epoch_duration": int(v.get("epochDuration", 0)),
            "deposit_whitelist": v.get("depositWhitelist", False),
            "is_deposit_limit": v.get("isDepositLimit", False),
            "created_date": (
                datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                if created_ts > 0 else ""
            ),
            "created_block": int(v.get("createdBlockNumber", 0)),
        }

    @staticmethod
    def _format_operator(o: Dict[str, Any]) -> Dict[str, Any]:
        """Format a raw subgraph operator entity."""
        created_ts = int(o.get("createdTimestamp", 0))

        return {
            "address": o.get("id", ""),
            "network_opt_ins": int(o.get("networkOptInsCount", 0)),
            "vault_opt_ins": int(o.get("vaultOptInsCount", 0)),
            "created_date": (
                datetime.fromtimestamp(created_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                if created_ts > 0 else ""
            ),
            "created_block": int(o.get("createdBlockNumber", 0)),
        }

    @staticmethod
    def _format_usd(value: float) -> str:
        """Format a USD value with human-readable suffix."""
        if value >= 1e9:
            return f"${value / 1e9:.2f}B"
        if value >= 1e6:
            return f"${value / 1e6:.2f}M"
        if value >= 1e3:
            return f"${value / 1e3:.1f}K"
        return f"${value:.2f}"
