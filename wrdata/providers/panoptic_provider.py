"""
Panoptic Subgraph Provider for wrdata.

Fetches real-time and historical data from the Panoptic protocol subgraph.
Panoptic is a permissionless DeFi perpetual options protocol built on Uniswap V3.

Data available:
- Live options chain (all active positions with decoded legs)
- Real-time trade feed (mints, burns, liquidations)
- Pool metrics and utilization
- Position data and collateral

Subgraph documentation: https://panoptic.xyz/docs/subgraph/schema

Note: Panoptic options are perpetual (no expiration) and use streamia-based pricing.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import httpx

from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
)

# Panoptic subgraph endpoints by network
# Note: Panoptic uses Goldsky for their subgraph hosting
SUBGRAPH_ENDPOINTS = {
    # Goldsky endpoints (primary)
    "sepolia": "https://api.goldsky.com/api/public/project_cl9gc21q105380hxuh8ks53k3/subgraphs/panoptic-subgraph-sepolia/prod/gn",
    "ethereum": "https://api.goldsky.com/api/public/project_cl9gc21q105380hxuh8ks53k3/subgraphs/panoptic-subgraph-mainnet/prod/gn",
    "base": "https://api.goldsky.com/api/public/project_cl9gc21q105380hxuh8ks53k3/subgraphs/panoptic-subgraph-base/prod/gn",
    # The Graph decentralized network (requires API key) - placeholder
    "ethereum_graph": "https://gateway.thegraph.com/api/{api_key}/subgraphs/id/{subgraph_id}",
}

# Tick spacing by fee tier (basis points)
TICK_SPACING = {
    100: 1,  # 0.01%
    500: 10,  # 0.05%
    3000: 60,  # 0.3%
    10000: 200,  # 1%
}


@dataclass
class OptionLeg:
    """Decoded option leg from a Panoptic position."""

    leg_index: int
    asset: int  # 0 = token0, 1 = token1
    option_ratio: int  # Contracts per leg
    is_long: bool  # True = bought (removed liquidity)
    token_type: str  # "put" or "call"
    strike_tick: int  # Tick at center of position
    width_ticks: int  # Width in ticks
    lower_tick: int  # Lower bound tick
    upper_tick: int  # Upper bound tick


def tick_to_price(tick: int, decimals0: int = 18, decimals1: int = 6) -> float:
    """Convert Uniswap V3 tick to price."""
    return (1.0001**tick) * (10 ** (decimals0 - decimals1))


def calculate_utilization(total_assets: str, in_amm: str) -> float:
    """Calculate utilization rate from collateral data."""
    try:
        total = float(total_assets or 0)
        used = float(in_amm or 0)
        return used / total if total > 0 else 0.0
    except (ValueError, TypeError):
        return 0.0


class PanopticProvider(BaseProvider):
    """
    Provider for Panoptic protocol data via The Graph subgraph.

    Fetches historical pool metrics, position data, and account activity
    from the Panoptic DeFi protocol.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        network: str = "ethereum",
        timeout: float = 30.0,
    ):
        """
        Initialize the Panoptic provider.

        Args:
            api_key: The Graph API key (optional - Goldsky endpoints are public)
            network: Network to query (ethereum, base, sepolia)
            timeout: Request timeout in seconds

        Note:
            Panoptic uses Goldsky for subgraph hosting. As of Jan 2025,
            V1 is disabled pending V2 launch - endpoints may be unavailable.
        """
        super().__init__(name="panoptic", api_key=api_key)
        self.network = network
        self.timeout = timeout

        # Select Goldsky endpoint (public, no API key required)
        self.endpoint = SUBGRAPH_ENDPOINTS.get(network)
        if not self.endpoint:
            self.endpoint = SUBGRAPH_ENDPOINTS.get("ethereum")
        self.headers = {}

        self._client = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout, headers=self.headers)
        return self._client

    async def _async_query(self, query: str, variables: Dict[str, Any] = None) -> Dict:
        """Execute async GraphQL query."""
        async with httpx.AsyncClient(
            timeout=self.timeout, headers=self.headers
        ) as client:
            response = await client.post(
                self.endpoint,
                json={"query": query, "variables": variables or {}},
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                raise Exception(f"GraphQL errors: {result['errors']}")

            return result.get("data", {})

    def _sync_query(self, query: str, variables: Dict[str, Any] = None) -> Dict:
        """Execute synchronous GraphQL query."""
        response = self.client.post(
            self.endpoint,
            json={"query": query, "variables": variables or {}},
        )
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result.get("data", {})

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs,
    ) -> DataResponse:
        """
        Fetch historical pool data for a Panoptic pool.

        Args:
            symbol: Pool address (e.g., "0x..." or "ETH-USDC-0.3%")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: "1d" for daily or "1h" for hourly
            **kwargs: Additional parameters
                - data_type: "pool" (default), "positions", or "collateral"

        Returns:
            DataResponse with pool metrics over time
        """
        data_type = kwargs.get("data_type", "pool")
        pool_address = self._resolve_pool_address(symbol)

        # Convert dates to timestamps
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

        try:
            if interval == "1h" and data_type == "pool":
                data = self._fetch_pool_hour_data(pool_address, start_ts, end_ts)
            elif data_type == "positions":
                data = self._fetch_position_events(pool_address, start_ts, end_ts)
            elif data_type == "collateral":
                data = self._fetch_collateral_data(pool_address, start_ts, end_ts)
            else:
                data = self._fetch_pool_day_data(pool_address, start_ts, end_ts)

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=data,
                metadata={
                    "network": self.network,
                    "data_type": data_type,
                    "pool_address": pool_address,
                    "interval": interval,
                },
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

    def _resolve_pool_address(self, symbol: str) -> str:
        """
        Resolve symbol to pool address.

        Accepts either a raw address or a human-readable format like "ETH-USDC-0.3%"
        """
        if symbol.startswith("0x") and len(symbol) == 42:
            return symbol.lower()

        # For human-readable format, would need to query pool registry
        # For now, assume it's an address
        return symbol.lower()

    def _fetch_pool_day_data(
        self, pool_address: str, start_ts: int, end_ts: int
    ) -> List[Dict[str, Any]]:
        """Fetch daily pool metrics."""
        query = """
        query GetPoolDayData($pool: String!, $start: Int!, $end: Int!) {
            panopticPoolDayDatas(
                where: {
                    panopticPool: $pool
                    date_gte: $start
                    date_lte: $end
                }
                orderBy: date
                orderDirection: asc
                first: 1000
            ) {
                id
                date
                panopticPool {
                    id
                }
                tvlUSD
                volumeUSD
                feesUSD
                txCount
            }
        }
        """

        result = self._sync_query(
            query,
            {
                "pool": pool_address,
                "start": start_ts,
                "end": end_ts,
            },
        )

        data = []
        for item in result.get("panopticPoolDayDatas", []):
            data.append(
                {
                    "timestamp": datetime.fromtimestamp(item["date"]).isoformat(),
                    "date": datetime.fromtimestamp(item["date"]).strftime("%Y-%m-%d"),
                    "tvl_usd": float(item.get("tvlUSD", 0)),
                    "volume_usd": float(item.get("volumeUSD", 0)),
                    "fees_usd": float(item.get("feesUSD", 0)),
                    "tx_count": int(item.get("txCount", 0)),
                }
            )

        return data

    def _fetch_pool_hour_data(
        self, pool_address: str, start_ts: int, end_ts: int
    ) -> List[Dict[str, Any]]:
        """Fetch hourly pool metrics."""
        query = """
        query GetPoolHourData($pool: String!, $start: Int!, $end: Int!) {
            poolHourDatas(
                where: {
                    pool: $pool
                    periodStartUnix_gte: $start
                    periodStartUnix_lte: $end
                }
                orderBy: periodStartUnix
                orderDirection: asc
                first: 1000
            ) {
                id
                periodStartUnix
                pool {
                    id
                }
                liquidity
                sqrtPrice
                token0Price
                token1Price
                tick
                feeGrowthGlobal0X128
                feeGrowthGlobal1X128
                tvlUSD
                volumeToken0
                volumeToken1
                volumeUSD
                feesUSD
                txCount
                open
                high
                low
                close
            }
        }
        """

        result = self._sync_query(
            query,
            {
                "pool": pool_address,
                "start": start_ts,
                "end": end_ts,
            },
        )

        data = []
        for item in result.get("poolHourDatas", []):
            data.append(
                {
                    "timestamp": datetime.fromtimestamp(
                        item["periodStartUnix"]
                    ).isoformat(),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "close": float(item.get("close", 0)),
                    "volume_usd": float(item.get("volumeUSD", 0)),
                    "volume_token0": float(item.get("volumeToken0", 0)),
                    "volume_token1": float(item.get("volumeToken1", 0)),
                    "fees_usd": float(item.get("feesUSD", 0)),
                    "tvl_usd": float(item.get("tvlUSD", 0)),
                    "liquidity": item.get("liquidity"),
                    "tick": int(item.get("tick", 0)),
                    "tx_count": int(item.get("txCount", 0)),
                }
            )

        return data

    def _fetch_position_events(
        self, pool_address: str, start_ts: int, end_ts: int
    ) -> List[Dict[str, Any]]:
        """Fetch option mint/burn events for a pool."""
        query = """
        query GetPositionEvents($pool: String!, $start: Int!, $end: Int!) {
            optionMints(
                where: {
                    panopticPool: $pool
                    blockTimestamp_gte: $start
                    blockTimestamp_lte: $end
                }
                orderBy: blockTimestamp
                orderDirection: asc
                first: 1000
            ) {
                id
                blockTimestamp
                transactionHash
                account {
                    id
                }
                tokenId {
                    id
                }
                positionSize
                poolUtilizations
            }
            optionBurns(
                where: {
                    panopticPool: $pool
                    blockTimestamp_gte: $start
                    blockTimestamp_lte: $end
                }
                orderBy: blockTimestamp
                orderDirection: asc
                first: 1000
            ) {
                id
                blockTimestamp
                transactionHash
                account {
                    id
                }
                tokenId {
                    id
                }
                positionSize
                premium0
                premium1
            }
        }
        """

        result = self._sync_query(
            query,
            {
                "pool": pool_address,
                "start": start_ts,
                "end": end_ts,
            },
        )

        data = []

        # Process mints
        for item in result.get("optionMints", []):
            data.append(
                {
                    "timestamp": datetime.fromtimestamp(
                        int(item["blockTimestamp"])
                    ).isoformat(),
                    "event_type": "mint",
                    "tx_hash": item.get("transactionHash"),
                    "account": item.get("account", {}).get("id"),
                    "token_id": item.get("tokenId", {}).get("id"),
                    "position_size": item.get("positionSize"),
                    "pool_utilizations": item.get("poolUtilizations"),
                }
            )

        # Process burns
        for item in result.get("optionBurns", []):
            data.append(
                {
                    "timestamp": datetime.fromtimestamp(
                        int(item["blockTimestamp"])
                    ).isoformat(),
                    "event_type": "burn",
                    "tx_hash": item.get("transactionHash"),
                    "account": item.get("account", {}).get("id"),
                    "token_id": item.get("tokenId", {}).get("id"),
                    "position_size": item.get("positionSize"),
                    "premium0": item.get("premium0"),
                    "premium1": item.get("premium1"),
                }
            )

        # Sort by timestamp
        data.sort(key=lambda x: x["timestamp"])

        return data

    def _fetch_collateral_data(
        self, pool_address: str, start_ts: int, end_ts: int
    ) -> List[Dict[str, Any]]:
        """Fetch collateral tracker day data."""
        query = """
        query GetCollateralData($pool: String!, $start: Int!, $end: Int!) {
            collateralDayDatas(
                where: {
                    panopticPool: $pool
                    date_gte: $start
                    date_lte: $end
                }
                orderBy: date
                orderDirection: asc
                first: 1000
            ) {
                id
                date
                collateral {
                    id
                    token {
                        symbol
                        decimals
                    }
                }
                totalAssets
                totalShares
                inAMM
                utilizationRate
            }
        }
        """

        result = self._sync_query(
            query,
            {
                "pool": pool_address,
                "start": start_ts,
                "end": end_ts,
            },
        )

        data = []
        for item in result.get("collateralDayDatas", []):
            collateral = item.get("collateral", {})
            token = collateral.get("token", {})
            data.append(
                {
                    "timestamp": datetime.fromtimestamp(item["date"]).isoformat(),
                    "date": datetime.fromtimestamp(item["date"]).strftime("%Y-%m-%d"),
                    "collateral_address": collateral.get("id"),
                    "token_symbol": token.get("symbol"),
                    "token_decimals": token.get("decimals"),
                    "total_assets": item.get("totalAssets"),
                    "total_shares": item.get("totalShares"),
                    "in_amm": item.get("inAMM"),
                    "utilization_rate": float(item.get("utilizationRate", 0)),
                }
            )

        return data

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """
        Not applicable for Panoptic perpetual options.

        Panoptic uses perpetual options with no expiration,
        so traditional options chain format doesn't apply.
        Use fetch_timeseries with data_type="positions" instead.
        """
        raise NotImplementedError(
            "Panoptic uses perpetual options without expiration. "
            "Use fetch_timeseries with data_type='positions' for position data."
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """
        Not applicable for Panoptic perpetual options.

        Panoptic options are perpetual and have no expiration dates.
        """
        return []  # No expirations for perpetual options

    def validate_connection(self) -> bool:
        """Validate connection to the subgraph."""
        try:
            # Simple query to test connection
            query = """
            query {
                panopticPools(first: 1) {
                    id
                }
            }
            """
            result = self._sync_query(query)
            return "panopticPools" in result
        except Exception:
            return False

    def get_pools(self, first: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of available Panoptic pools.

        Returns:
            List of pool information dictionaries
        """
        query = """
        query GetPools($first: Int!) {
            panopticPools(
                first: $first
                orderBy: txCount
                orderDirection: desc
            ) {
                id
                txCount
                underlyingPool {
                    id
                    token0 {
                        symbol
                        decimals
                    }
                    token1 {
                        symbol
                        decimals
                    }
                    feeTier
                }
                collateral0 {
                    id
                }
                collateral1 {
                    id
                }
            }
        }
        """

        result = self._sync_query(query, {"first": first})

        pools = []
        for item in result.get("panopticPools", []):
            underlying = item.get("underlyingPool", {})
            token0 = underlying.get("token0", {})
            token1 = underlying.get("token1", {})
            fee_tier = underlying.get("feeTier", 0)

            pools.append(
                {
                    "pool_address": item.get("id"),
                    "underlying_pool": underlying.get("id"),
                    "token0_symbol": token0.get("symbol"),
                    "token1_symbol": token1.get("symbol"),
                    "token0_decimals": token0.get("decimals"),
                    "token1_decimals": token1.get("decimals"),
                    "fee_tier": (
                        int(fee_tier) / 10000 if fee_tier else None
                    ),  # Convert to percentage
                    "tx_count": int(item.get("txCount", 0)),
                    "collateral0_address": item.get("collateral0", {}).get("id"),
                    "collateral1_address": item.get("collateral1", {}).get("id"),
                }
            )

        return pools

    def get_account_positions(
        self, account_address: str, pool_address: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get open positions for an account.

        Args:
            account_address: The account address to query
            pool_address: Optional pool address to filter by

        Returns:
            List of position information
        """
        where_clause = f'account: "{account_address.lower()}"'
        if pool_address:
            where_clause += f', panopticPool: "{pool_address.lower()}"'

        query = f"""
        query GetAccountPositions {{
            accountBalances(
                where: {{ {where_clause}, isOpen: true }}
                first: 100
            ) {{
                id
                tokenId {{
                    id
                }}
                panopticPool {{
                    id
                }}
                positionSize
                createdTimestamp
                createdBlockNumber
            }}
        }}
        """

        result = self._sync_query(query)

        positions = []
        for item in result.get("accountBalances", []):
            positions.append(
                {
                    "id": item.get("id"),
                    "token_id": item.get("tokenId", {}).get("id"),
                    "pool_address": item.get("panopticPool", {}).get("id"),
                    "position_size": item.get("positionSize"),
                    "created_timestamp": datetime.fromtimestamp(
                        int(item.get("createdTimestamp", 0))
                    ).isoformat(),
                    "created_block": int(item.get("createdBlockNumber", 0)),
                }
            )

        return positions

    # =========================================================================
    # Live Options Chain
    # =========================================================================

    def get_options_chain(
        self, pool_address: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get live options chain - all active positions for a pool.

        Returns positions with decoded legs showing strike, width, type (put/call),
        and direction (long/short).

        Args:
            pool_address: Panoptic pool address
            limit: Maximum positions to return

        Returns:
            List of positions with decoded leg information
        """
        query = """
        query GetOptionsChain($pool: String!, $first: Int!) {
            accountBalances(
                where: {
                    panopticPoolAccount_: { panopticPool: $pool }
                    tokenCount_gt: 0
                }
                orderBy: positionSize
                orderDirection: desc
                first: $first
            ) {
                id
                owner {
                    id
                }
                tokenId {
                    id
                    idHexString
                    legs {
                        id
                        index
                        asset
                        optionRatio
                        isLong
                        tokenType
                        riskPartner
                        strike
                        width
                    }
                }
                panopticPoolAccount {
                    panopticPool {
                        id
                        underlyingPool {
                            id
                            tick
                            token0 {
                                symbol
                                decimals
                            }
                            token1 {
                                symbol
                                decimals
                            }
                            feeTier
                        }
                    }
                }
                positionSize
                tokenCount
            }
        }
        """

        result = self._sync_query(query, {"pool": pool_address.lower(), "first": limit})

        positions = []
        for item in result.get("accountBalances", []):
            token_id_data = item.get("tokenId", {})
            ppa = item.get("panopticPoolAccount", {})
            pool_data = ppa.get("panopticPool", {})
            underlying = pool_data.get("underlyingPool", {})

            # Get tick spacing for this pool
            fee_tier = int(underlying.get("feeTier", 3000))
            tick_spacing = TICK_SPACING.get(fee_tier, 60)
            current_tick = int(underlying.get("tick", 0))

            # Decode legs
            legs_data = token_id_data.get("legs", [])
            legs = []
            for leg in legs_data:
                strike_tick = int(leg.get("strike", 0)) * tick_spacing
                width_ticks = int(leg.get("width", 0)) * tick_spacing
                # isLong is BigInt, need to convert
                is_long = int(leg.get("isLong", 0)) == 1
                token_type = "call" if int(leg.get("tokenType", 0)) == 1 else "put"

                # Calculate ITM status
                if token_type == "put":
                    is_itm = current_tick < strike_tick
                else:
                    is_itm = current_tick > strike_tick

                legs.append(
                    {
                        "leg_index": leg.get("index"),
                        "asset": int(leg.get("asset", 0)),
                        "option_ratio": int(leg.get("optionRatio", 1)),
                        "is_long": is_long,
                        "position": "long" if is_long else "short",
                        "token_type": token_type,
                        "strike_tick": strike_tick,
                        "width_ticks": width_ticks,
                        "lower_tick": strike_tick - width_ticks,
                        "upper_tick": strike_tick + width_ticks,
                        "is_itm": is_itm,
                    }
                )

            positions.append(
                {
                    "id": item.get("id"),
                    "account": item.get("owner", {}).get("id"),
                    "token_id": token_id_data.get("id"),
                    "token_id_hex": token_id_data.get("idHexString"),
                    "pool_address": pool_data.get("id"),
                    "underlying_pool": underlying.get("id"),
                    "token0_symbol": underlying.get("token0", {}).get("symbol"),
                    "token1_symbol": underlying.get("token1", {}).get("symbol"),
                    "fee_tier": fee_tier / 10000,
                    "current_tick": current_tick,
                    "position_size": item.get("positionSize"),
                    "token_count": item.get("tokenCount"),
                    "legs": legs,
                    "num_legs": len(legs),
                }
            )

        return positions

    # =========================================================================
    # Live Trade Feed
    # =========================================================================

    def get_live_trades(
        self, pool_address: Optional[str] = None, limit: int = 50, hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades (mints, burns, liquidations).

        Args:
            pool_address: Optional pool to filter by (None = all pools)
            limit: Maximum trades per type to return
            hours_back: How far back to look (default 24, Panoptic markets are sparse)

        Returns:
            List of trades sorted by timestamp descending
        """
        start_ts = int((datetime.now() - timedelta(hours=hours_back)).timestamp())

        pool_filter = f'panopticPool: "{pool_address.lower()}",' if pool_address else ""

        query = f"""
        query GetLiveTrades($start: Int!, $first: Int!) {{
            optionMints(
                where: {{
                    {pool_filter}
                    timestamp_gte: $start
                }}
                orderBy: timestamp
                orderDirection: desc
                first: $first
            ) {{
                id
                timestamp
                blockNumber
                hash
                recipient {{ id }}
                tokenId {{
                    id
                    idHexString
                    legs {{
                        index
                        isLong
                        tokenType
                        strike
                        width
                    }}
                }}
                panopticPool {{
                    id
                    underlyingPool {{
                        token0 {{ symbol }}
                        token1 {{ symbol }}
                        feeTier
                    }}
                }}
                positionSize
                poolUtilization0
                poolUtilization1
                commissions0
                commissions1
            }}

            optionBurns(
                where: {{
                    {pool_filter}
                    timestamp_gte: $start
                }}
                orderBy: timestamp
                orderDirection: desc
                first: $first
            ) {{
                id
                timestamp
                blockNumber
                hash
                recipient {{ id }}
                tokenId {{
                    id
                    idHexString
                    legs {{
                        index
                        isLong
                        tokenType
                        strike
                        width
                    }}
                }}
                panopticPool {{
                    id
                    underlyingPool {{
                        token0 {{ symbol }}
                        token1 {{ symbol }}
                        feeTier
                    }}
                }}
                positionSize
                premium0
                premium1
            }}

            accountLiquidateds(
                where: {{
                    {pool_filter}
                    timestamp_gte: $start
                }}
                orderBy: timestamp
                orderDirection: desc
                first: $first
            ) {{
                id
                timestamp
                blockNumber
                hash
                liquidatee
                liquidator
                panopticPool {{
                    id
                    underlyingPool {{
                        token0 {{ symbol }}
                        token1 {{ symbol }}
                    }}
                }}
                bonusAmounts
                liquidationBonusUSD
            }}
        }}
        """

        result = self._sync_query(query, {"start": start_ts, "first": limit})

        trades = []

        # Process mints
        for item in result.get("optionMints", []):
            pool_data = item.get("panopticPool", {})
            underlying = pool_data.get("underlyingPool", {})
            token_id_data = item.get("tokenId", {})
            legs = token_id_data.get("legs", [])
            fee_tier = int(underlying.get("feeTier", 3000))
            tick_spacing = TICK_SPACING.get(fee_tier, 60)

            # Determine if buying or selling (isLong is BigInt)
            is_buying = any(int(leg.get("isLong", 0)) == 1 for leg in legs)

            trades.append(
                {
                    "type": "MINT",
                    "action": "BUY" if is_buying else "SELL",
                    "timestamp": datetime.fromtimestamp(int(item["timestamp"])),
                    "block": int(item.get("blockNumber", 0)),
                    "tx_hash": item.get("hash"),
                    "account": item.get("recipient", {}).get("id"),
                    "pool": f"{underlying.get('token0', {}).get('symbol')}/{underlying.get('token1', {}).get('symbol')}",
                    "pool_address": pool_data.get("id"),
                    "token_id": token_id_data.get("id"),
                    "position_size": item.get("positionSize"),
                    "num_legs": len(legs),
                    "legs": [
                        {
                            "type": (
                                "call" if int(leg.get("tokenType", 0)) == 1 else "put"
                            ),
                            "position": (
                                "long" if int(leg.get("isLong", 0)) == 1 else "short"
                            ),
                            "strike": int(leg.get("strike", 0)) * tick_spacing,
                            "width": int(leg.get("width", 0)) * tick_spacing,
                        }
                        for leg in legs
                    ],
                    "utilizations": {
                        "token0": item.get("poolUtilization0"),
                        "token1": item.get("poolUtilization1"),
                    },
                    "commissions": {
                        "token0": item.get("commissions0"),
                        "token1": item.get("commissions1"),
                    },
                }
            )

        # Process burns
        for item in result.get("optionBurns", []):
            pool_data = item.get("panopticPool", {})
            underlying = pool_data.get("underlyingPool", {})
            token_id_data = item.get("tokenId", {})
            legs = token_id_data.get("legs", [])
            fee_tier = int(underlying.get("feeTier", 3000))
            tick_spacing = TICK_SPACING.get(fee_tier, 60)

            trades.append(
                {
                    "type": "BURN",
                    "action": "CLOSE",
                    "timestamp": datetime.fromtimestamp(int(item["timestamp"])),
                    "block": int(item.get("blockNumber", 0)),
                    "tx_hash": item.get("hash"),
                    "account": item.get("recipient", {}).get("id"),
                    "pool": f"{underlying.get('token0', {}).get('symbol')}/{underlying.get('token1', {}).get('symbol')}",
                    "pool_address": pool_data.get("id"),
                    "token_id": token_id_data.get("id"),
                    "position_size": item.get("positionSize"),
                    "num_legs": len(legs),
                    "legs": [
                        {
                            "type": (
                                "call" if int(leg.get("tokenType", 0)) == 1 else "put"
                            ),
                            "position": (
                                "long" if int(leg.get("isLong", 0)) == 1 else "short"
                            ),
                            "strike": int(leg.get("strike", 0)) * tick_spacing,
                            "width": int(leg.get("width", 0)) * tick_spacing,
                        }
                        for leg in legs
                    ],
                    "premium": {
                        "token0": item.get("premium0"),
                        "token1": item.get("premium1"),
                    },
                }
            )

        # Process liquidations
        for item in result.get("accountLiquidateds", []):
            pool_data = item.get("panopticPool", {})
            underlying = pool_data.get("underlyingPool", {})

            trades.append(
                {
                    "type": "LIQUIDATION",
                    "action": "LIQUIDATE",
                    "timestamp": datetime.fromtimestamp(int(item["timestamp"])),
                    "block": int(item.get("blockNumber", 0)),
                    "tx_hash": item.get("hash"),
                    "account": item.get("liquidatee"),
                    "liquidator": item.get("liquidator"),
                    "pool": f"{underlying.get('token0', {}).get('symbol')}/{underlying.get('token1', {}).get('symbol')}",
                    "pool_address": pool_data.get("id"),
                    "bonus_amounts": item.get("bonusAmounts"),
                    "bonus_usd": item.get("liquidationBonusUSD"),
                }
            )

        # Sort by timestamp descending
        trades.sort(key=lambda x: x["timestamp"], reverse=True)

        return trades

    # =========================================================================
    # Pool Statistics
    # =========================================================================

    def get_pool_stats(self, pool_address: str) -> Dict[str, Any]:
        """
        Get comprehensive stats for a Panoptic pool.

        Includes current price, tick, liquidity, collateral utilization.
        """
        query = """
        query GetPoolStats($pool: String!) {
            panopticPool(id: $pool) {
                id
                txCount
                underlyingPool {
                    id
                    tick
                    sqrtPrice
                    liquidity
                    token0 {
                        symbol
                        decimals
                    }
                    token1 {
                        symbol
                        decimals
                    }
                    feeTier
                    token0Price
                    token1Price
                }
                collateral0 {
                    id
                    totalAssets
                    totalShares
                    inAMM
                }
                collateral1 {
                    id
                    totalAssets
                    totalShares
                    inAMM
                }
            }
        }
        """

        result = self._sync_query(query, {"pool": pool_address.lower()})
        pool = result.get("panopticPool", {})

        if not pool:
            return {}

        underlying = pool.get("underlyingPool", {})
        collateral0 = pool.get("collateral0", {})
        collateral1 = pool.get("collateral1", {})

        # Calculate price from sqrtPrice
        sqrt_price = int(underlying.get("sqrtPrice", 0) or 0)
        if sqrt_price > 0:
            price = (sqrt_price / (2**96)) ** 2
        else:
            price = 0

        # Calculate utilization from inAMM / totalAssets
        util0 = calculate_utilization(
            collateral0.get("totalAssets"), collateral0.get("inAMM")
        )
        util1 = calculate_utilization(
            collateral1.get("totalAssets"), collateral1.get("inAMM")
        )

        return {
            "pool_address": pool.get("id"),
            "underlying_pool": underlying.get("id"),
            "token0_symbol": underlying.get("token0", {}).get("symbol"),
            "token1_symbol": underlying.get("token1", {}).get("symbol"),
            "token0_decimals": underlying.get("token0", {}).get("decimals"),
            "token1_decimals": underlying.get("token1", {}).get("decimals"),
            "fee_tier": int(underlying.get("feeTier", 0)) / 10000,
            "current_tick": int(underlying.get("tick", 0)),
            "current_price": price,
            "token0_price": float(underlying.get("token0Price", 0) or 0),
            "token1_price": float(underlying.get("token1Price", 0) or 0),
            "liquidity": underlying.get("liquidity"),
            "tx_count": int(pool.get("txCount", 0)),
            "collateral0": {
                "total_assets": collateral0.get("totalAssets"),
                "total_shares": collateral0.get("totalShares"),
                "in_amm": collateral0.get("inAMM"),
                "utilization": util0,
            },
            "collateral1": {
                "total_assets": collateral1.get("totalAssets"),
                "total_shares": collateral1.get("totalShares"),
                "in_amm": collateral1.get("inAMM"),
                "utilization": util1,
            },
        }

    def get_all_pools_with_stats(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Get all Panoptic pools with current stats.

        Returns pools sorted by transaction count (most active first).
        """
        query = """
        query GetAllPoolsWithStats($first: Int!) {
            panopticPools(
                first: $first
                orderBy: txCount
                orderDirection: desc
            ) {
                id
                txCount
                underlyingPool {
                    id
                    tick
                    sqrtPrice
                    liquidity
                    token0 {
                        symbol
                        decimals
                    }
                    token1 {
                        symbol
                        decimals
                    }
                    feeTier
                }
                collateral0 {
                    id
                    totalAssets
                    totalShares
                    inAMM
                }
                collateral1 {
                    id
                    totalAssets
                    totalShares
                    inAMM
                }
            }
        }
        """

        result = self._sync_query(query, {"first": limit})

        pools = []
        for item in result.get("panopticPools", []):
            underlying = item.get("underlyingPool", {})
            collateral0 = item.get("collateral0", {})
            collateral1 = item.get("collateral1", {})

            util0 = calculate_utilization(
                collateral0.get("totalAssets") if collateral0 else None,
                collateral0.get("inAMM") if collateral0 else None,
            )
            util1 = calculate_utilization(
                collateral1.get("totalAssets") if collateral1 else None,
                collateral1.get("inAMM") if collateral1 else None,
            )

            pools.append(
                {
                    "pool_address": item.get("id"),
                    "pair": f"{underlying.get('token0', {}).get('symbol')}/{underlying.get('token1', {}).get('symbol')}",
                    "fee_tier": int(underlying.get("feeTier", 0)) / 10000,
                    "tx_count": int(item.get("txCount", 0)),
                    "liquidity": underlying.get("liquidity"),
                    "current_tick": int(underlying.get("tick", 0)),
                    "util_token0": util0,
                    "util_token1": util1,
                }
            )

        return pools
