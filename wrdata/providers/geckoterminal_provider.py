"""
GeckoTerminal / CoinGecko Onchain API provider.

Provides historical OHLCV data and pool information for DEX trading pairs.
Uses CoinGecko's onchain endpoints (powered by GeckoTerminal).

FREE tier available with rate limits.
Paid plans available for higher rate limits and more data.

API Docs: https://docs.coingecko.com/reference/onchain-simple-networks-list
GeckoTerminal: https://www.geckoterminal.com

Covers 200+ blockchain networks and 1,500+ DEXes including:
Uniswap, SushiSwap, PancakeSwap, Curve, Balancer, Raydium, Orca, etc.
"""

import requests
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class GeckoTerminalProvider(BaseProvider):
    """
    GeckoTerminal/CoinGecko Onchain API provider for DEX data.

    Features:
    - Historical OHLCV data for DEX pools
    - Pool/pair discovery across 200+ chains
    - Trending pools and new pools
    - Token price by contract address

    Rate Limits (free tier):
    - 30 calls/minute
    - Use CoinGecko API key for higher limits (500 calls/min)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GeckoTerminal provider.

        Args:
            api_key: Optional CoinGecko API key for higher rate limits
        """
        super().__init__(name="geckoterminal", api_key=api_key)
        self.base_url = "https://api.geckoterminal.com/api/v2"
        self._last_request_time = 0
        self._min_request_interval = 2.0  # 30 requests/min = 2 sec between requests

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> requests.Response:
        """Make a rate-limited request."""
        self._rate_limit()

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-cg-pro-api-key"] = self.api_key

        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=headers, params=params, timeout=30)
        return response

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical OHLCV data for a DEX pool.

        Args:
            symbol: Pool address in format 'network:pool_address'
                   (e.g., 'eth:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)

        Returns:
            DataResponse with OHLCV data
        """
        try:
            # Parse network:pool_address format
            if ':' not in symbol:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="Symbol must be in format 'network:pool_address' "
                          "(e.g., 'eth:0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640')"
                )

            network, pool_address = symbol.split(':', 1)

            # Map interval to GeckoTerminal timeframe
            interval_map = {
                "1m": ("minute", 1),
                "5m": ("minute", 5),
                "15m": ("minute", 15),
                "1h": ("hour", 1),
                "4h": ("hour", 4),
                "1d": ("day", 1),
                "1D": ("day", 1),
            }

            if interval not in interval_map:
                interval = "1d"

            timeframe, aggregate = interval_map[interval]

            # Parse dates
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            # GeckoTerminal limits to 1000 candles per request
            # and max 6 months per request for paid plans
            endpoint = f"networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
            params = {
                "aggregate": aggregate,
                "limit": 1000,
            }

            # Add currency parameter if provided
            if kwargs.get('currency'):
                params['currency'] = kwargs['currency']

            response = self._make_request(endpoint, params)
            response.raise_for_status()
            data = response.json()

            ohlcv_list = data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])

            if not ohlcv_list:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No OHLCV data found for pool {pool_address} on {network}"
                )

            records = []
            for candle in ohlcv_list:
                # GeckoTerminal format: [timestamp, open, high, low, close, volume]
                timestamp = candle[0]
                dt = datetime.fromtimestamp(timestamp)

                # Filter by date range
                if start_dt <= dt <= end_dt + timedelta(days=1):
                    if interval in ['1m', '5m', '15m', '1h', '4h']:
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = dt.strftime('%Y-%m-%d')

                    records.append({
                        'Date': date_str,
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5]),
                    })

            # Sort by date (oldest first)
            records.sort(key=lambda x: x['Date'])

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'interval': interval,
                    'records': len(records),
                    'network': network,
                    'pool_address': pool_address,
                    'source': 'GeckoTerminal'
                },
                success=True
            )

        except requests.exceptions.HTTPError as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"GeckoTerminal API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"GeckoTerminal error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="GeckoTerminal does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        """Validate connection to GeckoTerminal API."""
        try:
            response = self._make_request("networks")
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False

    # =========================================================================
    # Network & DEX Discovery
    # =========================================================================

    def get_networks(self) -> Dict[str, Any]:
        """
        Get list of all supported blockchain networks.

        Returns:
            Dict with list of networks and their metadata
        """
        try:
            response = self._make_request("networks")
            response.raise_for_status()
            data = response.json()

            networks = []
            for item in data.get('data', []):
                attrs = item.get('attributes', {})
                networks.append({
                    'id': item.get('id', ''),
                    'name': attrs.get('name', ''),
                    'coingecko_asset_platform_id': attrs.get('coingecko_asset_platform_id', ''),
                })

            return {
                'success': True,
                'count': len(networks),
                'networks': networks
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_dexes(self, network: str) -> Dict[str, Any]:
        """
        Get list of DEXes on a specific network.

        Args:
            network: Network identifier (e.g., 'eth', 'bsc', 'solana')

        Returns:
            Dict with list of DEXes
        """
        try:
            response = self._make_request(f"networks/{network}/dexes")
            response.raise_for_status()
            data = response.json()

            dexes = []
            for item in data.get('data', []):
                attrs = item.get('attributes', {})
                dexes.append({
                    'id': item.get('id', ''),
                    'name': attrs.get('name', ''),
                })

            return {
                'success': True,
                'count': len(dexes),
                'dexes': dexes
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Pool Discovery
    # =========================================================================

    def get_trending_pools(self, network: Optional[str] = None) -> Dict[str, Any]:
        """
        Get trending pools, optionally filtered by network.

        Args:
            network: Optional network filter (e.g., 'eth', 'solana')

        Returns:
            Dict with trending pools
        """
        try:
            if network:
                endpoint = f"networks/{network}/trending_pools"
            else:
                endpoint = "networks/trending_pools"

            response = self._make_request(endpoint)
            response.raise_for_status()
            data = response.json()

            pools = self._parse_pools(data.get('data', []))
            return {
                'success': True,
                'count': len(pools),
                'pools': pools
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_new_pools(self, network: Optional[str] = None) -> Dict[str, Any]:
        """
        Get newly created pools.

        Args:
            network: Optional network filter

        Returns:
            Dict with new pools
        """
        try:
            if network:
                endpoint = f"networks/{network}/new_pools"
            else:
                endpoint = "networks/new_pools"

            response = self._make_request(endpoint)
            response.raise_for_status()
            data = response.json()

            pools = self._parse_pools(data.get('data', []))
            return {
                'success': True,
                'count': len(pools),
                'pools': pools
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_pool(self, network: str, pool_address: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific pool.

        Args:
            network: Network identifier
            pool_address: Pool contract address

        Returns:
            Dict with pool details
        """
        try:
            response = self._make_request(f"networks/{network}/pools/{pool_address}")
            response.raise_for_status()
            data = response.json()

            pool_data = data.get('data', {})
            attrs = pool_data.get('attributes', {})

            return {
                'success': True,
                'pool': {
                    'address': pool_data.get('id', '').split('_')[-1] if '_' in pool_data.get('id', '') else pool_address,
                    'name': attrs.get('name', ''),
                    'base_token': attrs.get('base_token_price_usd', ''),
                    'quote_token': attrs.get('quote_token_price_usd', ''),
                    'price_usd': attrs.get('base_token_price_usd', ''),
                    'volume_24h': attrs.get('volume_usd', {}).get('h24', 0),
                    'reserve_usd': attrs.get('reserve_in_usd', 0),
                    'fdv_usd': attrs.get('fdv_usd', 0),
                    'market_cap_usd': attrs.get('market_cap_usd', 0),
                    'price_change_24h': attrs.get('price_change_percentage', {}).get('h24', 0),
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_top_pools(self, network: str, page: int = 1) -> Dict[str, Any]:
        """
        Get top pools on a network by volume.

        Args:
            network: Network identifier
            page: Page number for pagination

        Returns:
            Dict with top pools
        """
        try:
            response = self._make_request(
                f"networks/{network}/pools",
                params={"page": page}
            )
            response.raise_for_status()
            data = response.json()

            pools = self._parse_pools(data.get('data', []))
            return {
                'success': True,
                'count': len(pools),
                'pools': pools
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def search_pools(self, query: str, network: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for pools by token name/symbol.

        Args:
            query: Search query
            network: Optional network filter

        Returns:
            Dict with matching pools
        """
        try:
            params = {"query": query}
            if network:
                params["network"] = network

            response = self._make_request("search/pools", params)
            response.raise_for_status()
            data = response.json()

            pools = self._parse_pools(data.get('data', []))
            return {
                'success': True,
                'count': len(pools),
                'pools': pools
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_token_pools(self, network: str, token_address: str) -> Dict[str, Any]:
        """
        Get all pools for a specific token.

        Args:
            network: Network identifier
            token_address: Token contract address

        Returns:
            Dict with all pools trading this token
        """
        try:
            response = self._make_request(
                f"networks/{network}/tokens/{token_address}/pools"
            )
            response.raise_for_status()
            data = response.json()

            pools = self._parse_pools(data.get('data', []))
            return {
                'success': True,
                'count': len(pools),
                'pools': pools
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Token Data
    # =========================================================================

    def get_token_price(self, network: str, token_address: str) -> Dict[str, Any]:
        """
        Get current price for a token by contract address.

        Args:
            network: Network identifier (e.g., 'eth', 'bsc')
            token_address: Token contract address

        Returns:
            Dict with token price data
        """
        try:
            response = self._make_request(
                f"networks/{network}/tokens/{token_address}"
            )
            response.raise_for_status()
            data = response.json()

            attrs = data.get('data', {}).get('attributes', {})

            return {
                'success': True,
                'token': {
                    'address': token_address,
                    'name': attrs.get('name', ''),
                    'symbol': attrs.get('symbol', ''),
                    'price_usd': float(attrs.get('price_usd', 0) or 0),
                    'volume_24h': float(attrs.get('volume_usd', {}).get('h24', 0) or 0),
                    'market_cap_usd': float(attrs.get('market_cap_usd', 0) or 0),
                    'fdv_usd': float(attrs.get('fdv_usd', 0) or 0),
                    'total_supply': attrs.get('total_supply', ''),
                    'price_change_24h': float(attrs.get('price_change_percentage', {}).get('h24', 0) or 0),
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_token_info(self, network: str, token_address: str) -> Dict[str, Any]:
        """
        Get detailed token information.

        Args:
            network: Network identifier
            token_address: Token contract address

        Returns:
            Dict with token info
        """
        try:
            response = self._make_request(
                f"networks/{network}/tokens/{token_address}/info"
            )
            response.raise_for_status()
            data = response.json()

            attrs = data.get('data', {}).get('attributes', {})

            return {
                'success': True,
                'info': {
                    'address': token_address,
                    'name': attrs.get('name', ''),
                    'symbol': attrs.get('symbol', ''),
                    'description': attrs.get('description', ''),
                    'website': attrs.get('websites', []),
                    'discord': attrs.get('discord_url', ''),
                    'telegram': attrs.get('telegram_handle', ''),
                    'twitter': attrs.get('twitter_handle', ''),
                    'coingecko_id': attrs.get('coingecko_coin_id', ''),
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_pools(self, pools_data: List[Dict]) -> List[Dict]:
        """Parse pool data from API response."""
        pools = []
        for item in pools_data:
            attrs = item.get('attributes', {})
            pool_id = item.get('id', '')

            # Extract network and address from ID (format: network_address)
            parts = pool_id.split('_', 1)
            network = parts[0] if len(parts) > 1 else ''
            address = parts[1] if len(parts) > 1 else pool_id

            pools.append({
                'id': pool_id,
                'network': network,
                'address': address,
                'name': attrs.get('name', ''),
                'dex': attrs.get('dex_id', ''),
                'price_usd': attrs.get('base_token_price_usd', ''),
                'volume_24h': attrs.get('volume_usd', {}).get('h24', 0) if isinstance(attrs.get('volume_usd'), dict) else 0,
                'reserve_usd': attrs.get('reserve_in_usd', 0),
                'price_change_24h': attrs.get('price_change_percentage', {}).get('h24', 0) if isinstance(attrs.get('price_change_percentage'), dict) else 0,
            })

        return pools
