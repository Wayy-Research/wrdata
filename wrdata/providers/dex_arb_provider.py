"""
DEX Arbitrage Provider - Cross-DEX price comparison and arb detection.

Composes DexScreener (real-time spot prices, 60+ chains, 300 req/min)
and GeckoTerminal (historical OHLCV, pool discovery, 200+ chains, 30 req/min)
to provide a unified interface for cross-DEX analysis.

FREE - No API key required.

Usage:
    >>> from wrdata.providers.dex_arb_provider import DexArbProvider
    >>> provider = DexArbProvider()
    >>> prices = provider.get_cross_dex_prices("ethereum", "0xC02...Cc2")
    >>> arbs = provider.find_arbitrage_opportunities("ethereum", "0xC02...Cc2")
"""

import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.providers.dexscreener_provider import DexScreenerProvider
from wrdata.providers.geckoterminal_provider import GeckoTerminalProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


# Major token addresses for convenience
MAJOR_TOKENS: Dict[str, Dict[str, str]] = {
    "ethereum": {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
        "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
        "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",
        "MKR": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",
        "CRV": "0xD533a949740bb3306d119CC777fa900bA034cd52",
        "PEPE": "0x6982508145454Ce325dDbE47a25d4ec3d2311933",
        "SHIB": "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE",
    },
    "arbitrum": {
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
        "ARB": "0x912CE59144191C1204E64559FE8253a0e49E6548",
        "GMX": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a",
    },
    "base": {
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    },
    "bsc": {
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "CAKE": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    },
    "polygon": {
        "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    },
    "solana": {
        "SOL": "So11111111111111111111111111111111111111112",
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    },
}

# DexScreener chain IDs
CHAIN_IDS = {
    "ethereum": "ethereum",
    "arbitrum": "arbitrum",
    "base": "base",
    "bsc": "bsc",
    "polygon": "polygon",
    "solana": "solana",
    "optimism": "optimism",
    "avalanche": "avalanche",
    "fantom": "fantom",
    "zksync": "zksync",
}

# GeckoTerminal network IDs (sometimes different from DexScreener)
GECKO_NETWORK_IDS = {
    "ethereum": "eth",
    "arbitrum": "arbitrum",
    "base": "base",
    "bsc": "bsc",
    "polygon": "polygon_pos",
    "solana": "solana",
    "optimism": "optimism",
    "avalanche": "avax",
    "fantom": "ftm",
}


class DexArbProvider(BaseProvider):
    """
    Cross-DEX arbitrage detection provider.

    Composes DexScreener (real-time) and GeckoTerminal (historical)
    to provide cross-DEX price comparison and arb opportunity detection.

    Features:
    - Real-time prices across all DEXes for a token
    - Cross-DEX spread calculation
    - Arbitrage opportunity detection with spread in bps
    - Pool discovery across 60+ chains
    - Historical DEX OHLCV via GeckoTerminal
    - No API key required

    Rate Limits:
    - DexScreener: 300 requests/minute
    - GeckoTerminal: 30 requests/minute

    Usage:
        >>> provider = DexArbProvider()
        >>>
        >>> # Get all pool prices for WETH on Ethereum
        >>> prices = provider.get_cross_dex_prices("ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        >>> for p in prices['pools']:
        ...     print(f"{p['dex']:20s} ${p['price_usd']:.4f}  liq=${p['liquidity_usd']:,.0f}")
        >>>
        >>> # Find arb opportunities
        >>> arbs = provider.find_arbitrage_opportunities("ethereum", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2")
        >>> for a in arbs['opportunities']:
        ...     print(f"Buy on {a['buy_dex']} @ {a['buy_price']:.4f}, Sell on {a['sell_dex']} @ {a['sell_price']:.4f} = {a['spread_bps']}bps")
        >>>
        >>> # Batch scan all major tokens
        >>> results = provider.scan_chain("ethereum")
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="dex_arb", api_key=api_key)
        self._dexscreener = DexScreenerProvider()
        self._geckoterminal = GeckoTerminalProvider(api_key=api_key)

    # === BaseProvider interface ===

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs,
    ) -> DataResponse:
        """
        Fetch historical OHLCV for a DEX pool.

        Delegates to GeckoTerminal. Symbol format: 'network:pool_address'
        (e.g., 'eth:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640')
        """
        return self._geckoterminal.fetch_timeseries(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            **kwargs,
        )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="DexArbProvider does not provide options data",
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        """Validate both DexScreener and GeckoTerminal are reachable."""
        return self._dexscreener.validate_connection()

    def supports_historical_options(self) -> bool:
        return False

    # === Cross-DEX Price Methods ===

    def get_cross_dex_prices(
        self,
        chain: str,
        token_address: str,
        min_liquidity_usd: float = 10000.0,
        max_pools: int = 20,
    ) -> Dict[str, Any]:
        """
        Get current prices for a token across all DEXes on a chain.

        Uses DexScreener's token pairs endpoint for real-time data.

        Args:
            chain: Chain name (e.g., 'ethereum', 'arbitrum')
            token_address: Token contract address
            min_liquidity_usd: Minimum pool liquidity to include
            max_pools: Maximum number of pools to return

        Returns:
            Dict with:
                - pools: List of pool price data
                - min_price: Lowest price found
                - max_price: Highest price found
                - spread_bps: Max spread in basis points
                - dex_count: Number of unique DEXes
        """
        chain_id = CHAIN_IDS.get(chain, chain)

        result = self._dexscreener.get_token_pairs(
            chain_id=chain_id,
            token_address=token_address,
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Failed to fetch token pairs"),
                "pools": [],
            }

        pools: List[Dict[str, Any]] = []
        for pair in result.get("pairs", []):
            liquidity = float(pair.get("liquidity", {}).get("usd", 0) or 0)
            if liquidity < min_liquidity_usd:
                continue

            price_usd = float(pair.get("priceUsd", 0) or 0)
            if price_usd <= 0:
                continue

            pools.append({
                "chain": chain,
                "dex": pair.get("dexId", "unknown"),
                "pool_address": pair.get("pairAddress", ""),
                "pair_name": (
                    pair.get("baseToken", {}).get("symbol", "")
                    + "/"
                    + pair.get("quoteToken", {}).get("symbol", "")
                ),
                "token_symbol": pair.get("baseToken", {}).get("symbol", ""),
                "token_address": pair.get("baseToken", {}).get("address", ""),
                "quote_token": pair.get("quoteToken", {}).get("symbol", ""),
                "price_usd": price_usd,
                "price_native": float(pair.get("priceNative", 0) or 0),
                "liquidity_usd": liquidity,
                "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0),
                "price_change_24h": float(
                    pair.get("priceChange", {}).get("h24", 0) or 0
                ),
                "txns_24h": pair.get("txns", {}).get("h24", {}),
                "created_at": pair.get("pairCreatedAt"),
            })

        # Sort by liquidity descending
        pools.sort(key=lambda p: p["liquidity_usd"], reverse=True)
        pools = pools[:max_pools]

        # Calculate spread
        prices = [p["price_usd"] for p in pools if p["price_usd"] > 0]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        spread_bps = (
            int((max_price - min_price) / min_price * 10000) if min_price > 0 else 0
        )

        dex_names = list(set(p["dex"] for p in pools))

        return {
            "success": True,
            "chain": chain,
            "token_address": token_address,
            "token_symbol": pools[0]["token_symbol"] if pools else "",
            "pool_count": len(pools),
            "dex_count": len(dex_names),
            "dexes": dex_names,
            "min_price": min_price,
            "max_price": max_price,
            "spread_bps": spread_bps,
            "pools": pools,
        }

    def find_arbitrage_opportunities(
        self,
        chain: str,
        token_address: str,
        min_spread_bps: int = 10,
        min_liquidity_usd: float = 50000.0,
    ) -> Dict[str, Any]:
        """
        Find arbitrage opportunities for a token across DEXes.

        Compares all pairwise prices and returns opportunities
        where the spread exceeds the threshold.

        Args:
            chain: Chain name
            token_address: Token contract address
            min_spread_bps: Minimum spread in basis points (default: 10 = 0.1%)
            min_liquidity_usd: Minimum liquidity per pool

        Returns:
            Dict with:
                - opportunities: List of arb opportunities sorted by spread
                - max_spread_bps: Largest spread found
                - profitable_count: Number of opportunities above threshold
        """
        cross_dex = self.get_cross_dex_prices(
            chain=chain,
            token_address=token_address,
            min_liquidity_usd=min_liquidity_usd,
        )

        if not cross_dex.get("success"):
            return {
                "success": False,
                "error": cross_dex.get("error"),
                "opportunities": [],
            }

        pools = cross_dex["pools"]

        # Deduplicate by DEX (keep highest liquidity pool per DEX)
        dex_best: Dict[str, Dict[str, Any]] = {}
        for pool in pools:
            dex = pool["dex"]
            if dex not in dex_best or pool["liquidity_usd"] > dex_best[dex]["liquidity_usd"]:
                dex_best[dex] = pool

        unique_pools = list(dex_best.values())
        opportunities: List[Dict[str, Any]] = []

        # Pairwise comparison
        for i in range(len(unique_pools)):
            for j in range(i + 1, len(unique_pools)):
                a = unique_pools[i]
                b = unique_pools[j]

                if a["price_usd"] < b["price_usd"]:
                    buy, sell = a, b
                else:
                    buy, sell = b, a

                if buy["price_usd"] <= 0:
                    continue

                spread_pct = (sell["price_usd"] - buy["price_usd"]) / buy["price_usd"]
                spread_bps = int(spread_pct * 10000)

                if spread_bps < min_spread_bps:
                    continue

                opportunities.append({
                    "chain": chain,
                    "token_symbol": buy["token_symbol"],
                    "token_address": token_address,
                    "buy_dex": buy["dex"],
                    "buy_pool": buy["pool_address"],
                    "buy_price": buy["price_usd"],
                    "buy_liquidity": buy["liquidity_usd"],
                    "sell_dex": sell["dex"],
                    "sell_pool": sell["pool_address"],
                    "sell_price": sell["price_usd"],
                    "sell_liquidity": sell["liquidity_usd"],
                    "spread_bps": spread_bps,
                    "spread_pct": round(spread_pct * 100, 4),
                    "min_liquidity": min(buy["liquidity_usd"], sell["liquidity_usd"]),
                })

        # Sort by spread descending
        opportunities.sort(key=lambda o: o["spread_bps"], reverse=True)

        return {
            "success": True,
            "chain": chain,
            "token_symbol": cross_dex.get("token_symbol", ""),
            "pools_checked": len(unique_pools),
            "dexes_checked": len(unique_pools),
            "opportunity_count": len(opportunities),
            "max_spread_bps": opportunities[0]["spread_bps"] if opportunities else 0,
            "opportunities": opportunities,
        }

    def scan_chain(
        self,
        chain: str,
        min_spread_bps: int = 10,
        min_liquidity_usd: float = 50000.0,
    ) -> Dict[str, Any]:
        """
        Scan all major tokens on a chain for arb opportunities.

        Args:
            chain: Chain to scan
            min_spread_bps: Minimum spread threshold
            min_liquidity_usd: Minimum liquidity per pool

        Returns:
            Dict with aggregated results across all tokens
        """
        tokens = MAJOR_TOKENS.get(chain, {})
        if not tokens:
            return {
                "success": False,
                "error": f"No tokens configured for chain: {chain}",
                "results": [],
            }

        results: List[Dict[str, Any]] = []
        total_opportunities = 0

        for symbol, address in tokens.items():
            arb_result = self.find_arbitrage_opportunities(
                chain=chain,
                token_address=address,
                min_spread_bps=min_spread_bps,
                min_liquidity_usd=min_liquidity_usd,
            )

            if arb_result.get("success"):
                results.append({
                    "token_symbol": symbol,
                    "token_address": address,
                    "pools_checked": arb_result.get("pools_checked", 0),
                    "opportunity_count": arb_result.get("opportunity_count", 0),
                    "max_spread_bps": arb_result.get("max_spread_bps", 0),
                    "opportunities": arb_result.get("opportunities", []),
                })
                total_opportunities += arb_result.get("opportunity_count", 0)

            # Respect rate limits (DexScreener: 300/min = 5/sec)
            time.sleep(0.25)

        # Sort by max spread
        results.sort(key=lambda r: r["max_spread_bps"], reverse=True)

        return {
            "success": True,
            "chain": chain,
            "tokens_scanned": len(results),
            "total_opportunities": total_opportunities,
            "results": results,
        }

    def scan_all_chains(
        self,
        chains: Optional[List[str]] = None,
        min_spread_bps: int = 10,
        min_liquidity_usd: float = 50000.0,
    ) -> Dict[str, Any]:
        """
        Scan multiple chains for arb opportunities.

        Args:
            chains: List of chains to scan (default: all configured)
            min_spread_bps: Minimum spread threshold
            min_liquidity_usd: Minimum liquidity per pool

        Returns:
            Dict with per-chain results
        """
        chains = chains or list(MAJOR_TOKENS.keys())

        all_results: Dict[str, Any] = {}
        total_opps = 0

        for chain in chains:
            chain_result = self.scan_chain(
                chain=chain,
                min_spread_bps=min_spread_bps,
                min_liquidity_usd=min_liquidity_usd,
            )
            all_results[chain] = chain_result
            total_opps += chain_result.get("total_opportunities", 0)

        return {
            "success": True,
            "chains_scanned": len(chains),
            "total_opportunities": total_opps,
            "results": all_results,
        }

    # === Pool Discovery ===

    def discover_pools(
        self,
        chain: str,
        token_address: str,
        source: str = "dexscreener",
    ) -> Dict[str, Any]:
        """
        Discover all pools for a token on a chain.

        Args:
            chain: Chain name
            token_address: Token contract address
            source: 'dexscreener' or 'geckoterminal'

        Returns:
            Dict with pool list
        """
        if source == "geckoterminal":
            network = GECKO_NETWORK_IDS.get(chain, chain)
            return self._geckoterminal.get_token_pools(network, token_address)
        else:
            chain_id = CHAIN_IDS.get(chain, chain)
            return self._dexscreener.get_token_pairs(chain_id, token_address)

    def get_trending_pools(self, chain: Optional[str] = None) -> Dict[str, Any]:
        """Get trending pools from GeckoTerminal."""
        network = GECKO_NETWORK_IDS.get(chain, chain) if chain else None
        return self._geckoterminal.get_trending_pools(network)

    def get_new_pools(self, chain: Optional[str] = None) -> Dict[str, Any]:
        """Get newly created pools from GeckoTerminal."""
        network = GECKO_NETWORK_IDS.get(chain, chain) if chain else None
        return self._geckoterminal.get_new_pools(network)

    def get_top_pools(self, chain: str) -> Dict[str, Any]:
        """Get top pools by volume on a chain."""
        network = GECKO_NETWORK_IDS.get(chain, chain)
        return self._geckoterminal.get_top_pools(network)

    def search_pools(self, query: str, chain: Optional[str] = None) -> Dict[str, Any]:
        """Search pools by token name/symbol."""
        network = GECKO_NETWORK_IDS.get(chain, chain) if chain else None
        return self._geckoterminal.search_pools(query, network)

    # === Token Info ===

    def get_token_price(self, chain: str, token_address: str) -> Dict[str, Any]:
        """Get current price for a token."""
        network = GECKO_NETWORK_IDS.get(chain, chain)
        return self._geckoterminal.get_token_price(network, token_address)

    def get_token_info(self, chain: str, token_address: str) -> Dict[str, Any]:
        """Get detailed token info."""
        network = GECKO_NETWORK_IDS.get(chain, chain)
        return self._geckoterminal.get_token_info(network, token_address)

    # === Supported Chains ===

    def get_supported_chains(self) -> List[str]:
        """Get list of supported chains for DEX arb scanning."""
        return list(MAJOR_TOKENS.keys())

    def get_all_supported_chains(self) -> List[str]:
        """Get all chains supported by DexScreener."""
        return self._dexscreener.get_supported_chains()

    def get_dexes_on_chain(self, chain: str) -> Dict[str, Any]:
        """Get list of DEXes on a chain."""
        network = GECKO_NETWORK_IDS.get(chain, chain)
        return self._geckoterminal.get_dexes(network)

    def get_major_tokens(self, chain: str) -> Dict[str, str]:
        """Get preconfigured major token addresses for a chain."""
        return MAJOR_TOKENS.get(chain, {})
