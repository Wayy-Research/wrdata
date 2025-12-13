"""
DEX Screener API provider.

Provides real-time DEX trading pair data across multiple chains.
FREE API - No key required!

Supported chains include: ethereum, bsc, polygon, arbitrum, optimism,
avalanche, fantom, solana, base, and many more.

API Docs: https://docs.dexscreener.com/api/reference
Rate Limits: 300 requests/minute for pair data, 60 requests/minute for other endpoints
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


# Supported chains on DEX Screener
SUPPORTED_CHAINS = [
    'ethereum', 'bsc', 'polygon', 'arbitrum', 'optimism', 'avalanche',
    'fantom', 'solana', 'base', 'zksync', 'linea', 'mantle', 'scroll',
    'blast', 'manta', 'mode', 'metis', 'celo', 'moonbeam', 'moonriver',
    'harmony', 'cronos', 'aurora', 'gnosis', 'klaytn', 'kava', 'canto',
    'evmos', 'oasis', 'telos', 'fuse', 'boba', 'velas', 'syscoin',
    'milkomeda', 'astar', 'shiden', 'iotex', 'elastos', 'kardia',
    'thundercore', 'palm', 'cube', 'findora', 'godwoken', 'wanchain',
    'conflux', 'smartbch', 'dogechain', 'flare', 'songbird', 'redlight',
    'core', 'pulsechain', 'sui', 'aptos', 'sei', 'injective', 'osmosis',
    'ton', 'tron', 'near', 'starknet', 'hedera',
]


class DexScreenerProvider(BaseProvider):
    """
    DEX Screener API provider for real-time DEX data.

    Features:
    - Real-time trading pair prices across 60+ chains
    - Search for pairs by token name/symbol
    - Get all pools for a specific token
    - No API key required

    Note: DEX Screener does not provide historical OHLCV data.
    Use GeckoTerminalProvider for historical DEX data.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="dexscreener", api_key=api_key)
        self.base_url = "https://api.dexscreener.com"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        DEX Screener does not provide historical OHLCV data.
        Use GeckoTerminalProvider for historical DEX data.
        """
        return DataResponse(
            symbol=symbol,
            provider=self.name,
            data=[],
            success=False,
            error="DEX Screener does not provide historical OHLCV data. "
                  "Use GeckoTerminalProvider or CoinGecko onchain endpoints for historical DEX data."
        )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="DEX Screener does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        """Validate connection to DEX Screener API."""
        try:
            response = requests.get(
                f"{self.base_url}/latest/dex/search?q=ETH",
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False

    # =========================================================================
    # DEX-Specific Methods
    # =========================================================================

    def search_pairs(self, query: str) -> Dict[str, Any]:
        """
        Search for trading pairs by token name, symbol, or address.

        Args:
            query: Search query (token name, symbol, or contract address)

        Returns:
            Dict with matching pairs data
        """
        try:
            url = f"{self.base_url}/latest/dex/search"
            params = {"q": query}

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            pairs = data.get('pairs', [])
            return {
                'success': True,
                'count': len(pairs),
                'pairs': pairs
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_pair(self, chain_id: str, pair_address: str) -> Dict[str, Any]:
        """
        Get detailed data for a specific trading pair.

        Args:
            chain_id: Chain identifier (e.g., 'ethereum', 'bsc', 'solana')
            pair_address: The pair/pool contract address

        Returns:
            Dict with pair data including price, volume, liquidity
        """
        try:
            url = f"{self.base_url}/latest/dex/pairs/{chain_id}/{pair_address}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'pair': data.get('pair') or data.get('pairs', [{}])[0]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_token_pairs(self, chain_id: str, token_address: str) -> Dict[str, Any]:
        """
        Get all trading pairs for a specific token.

        Args:
            chain_id: Chain identifier (e.g., 'ethereum', 'bsc', 'solana')
            token_address: The token contract address

        Returns:
            Dict with all pairs trading this token
        """
        try:
            url = f"{self.base_url}/token-pairs/v1/{chain_id}/{token_address}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            pairs = data if isinstance(data, list) else data.get('pairs', [])
            return {
                'success': True,
                'count': len(pairs),
                'pairs': pairs
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_tokens(self, chain_id: str, token_addresses: List[str]) -> Dict[str, Any]:
        """
        Get data for multiple tokens at once (max 30).

        Args:
            chain_id: Chain identifier
            token_addresses: List of token contract addresses (max 30)

        Returns:
            Dict with token pair data
        """
        try:
            if len(token_addresses) > 30:
                token_addresses = token_addresses[:30]

            addresses = ",".join(token_addresses)
            url = f"{self.base_url}/tokens/v1/{chain_id}/{addresses}"

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'data': data
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_latest_boosts(self) -> Dict[str, Any]:
        """Get latest boosted tokens."""
        try:
            url = f"{self.base_url}/token-boosts/latest/v1"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_top_boosts(self) -> Dict[str, Any]:
        """Get top boosted tokens."""
        try:
            url = f"{self.base_url}/token-boosts/top/v1"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return {'success': True, 'data': response.json()}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_supported_chains(self) -> List[str]:
        """Get list of supported chain identifiers."""
        return SUPPORTED_CHAINS.copy()

    def get_pair_price(self, chain_id: str, pair_address: str) -> Dict[str, Any]:
        """
        Get current price for a trading pair.

        Args:
            chain_id: Chain identifier
            pair_address: Pair contract address

        Returns:
            Dict with current price data
        """
        result = self.get_pair(chain_id, pair_address)
        if not result.get('success'):
            return result

        pair = result.get('pair', {})
        return {
            'success': True,
            'symbol': pair.get('baseToken', {}).get('symbol', ''),
            'price_usd': float(pair.get('priceUsd', 0) or 0),
            'price_native': float(pair.get('priceNative', 0) or 0),
            'volume_24h': float(pair.get('volume', {}).get('h24', 0) or 0),
            'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0) or 0),
            'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0) or 0),
            'dex': pair.get('dexId', ''),
            'chain': chain_id,
            'pair_address': pair_address,
        }
