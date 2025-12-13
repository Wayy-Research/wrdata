"""
Coinbase Advanced Trade API provider.

The new Coinbase Advanced Trade API replaces the legacy Coinbase Pro API.
Supports both authenticated and unauthenticated access.

Authentication uses JWT tokens with ES256 (ECDSA) signing.
API key format: organizations/{org_id}/apiKeys/{key_id}
API secret: EC private key in PEM format

API Docs: https://docs.cdp.coinbase.com/advanced-trade/docs
"""

import requests
import time
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse

# Optional imports for JWT authentication
try:
    import jwt
    from cryptography.hazmat.primitives import serialization
    HAS_JWT = True
except ImportError:
    HAS_JWT = False


class CoinbaseAdvancedProvider(BaseProvider):
    """
    Coinbase Advanced Trade API provider.

    Supports authenticated access via JWT/ES256 for:
    - Higher rate limits
    - Account information
    - Trading operations
    - Portfolio data

    Also works without authentication for public market data.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize the Coinbase Advanced Trade provider.

        Args:
            api_key: CDP API key in format 'organizations/{org_id}/apiKeys/{key_id}'
            api_secret: EC private key in PEM format (can have escaped \\n)
        """
        super().__init__(name="coinbase_advanced", api_key=api_key)
        self.api_secret = self._normalize_private_key(api_secret) if api_secret else None
        self.base_url = "https://api.coinbase.com/api/v3/brokerage"
        self._authenticated = bool(api_key and self.api_secret and HAS_JWT)

    def _normalize_private_key(self, key: str) -> str:
        """Convert escaped newlines to actual newlines in PEM key."""
        if key and '\\n' in key:
            return key.replace('\\n', '\n')
        return key

    def _build_jwt(self, request_method: str, request_path: str) -> str:
        """
        Build a JWT token for authenticated requests.

        Args:
            request_method: HTTP method (GET, POST, etc.)
            request_path: API path (e.g., /api/v3/brokerage/accounts)

        Returns:
            JWT token string
        """
        if not HAS_JWT:
            raise ImportError("PyJWT and cryptography packages required for authentication. "
                            "Install with: pip install PyJWT cryptography")

        private_key_bytes = self.api_secret.encode('utf-8')
        private_key = serialization.load_pem_private_key(private_key_bytes, password=None)

        uri = f"{request_method} api.coinbase.com{request_path}"

        jwt_payload = {
            'sub': self.api_key,
            'iss': "coinbase-cloud",
            'nbf': int(time.time()),
            'exp': int(time.time()) + 120,  # 2 minute expiry
            'uri': uri,
        }

        jwt_token = jwt.encode(
            jwt_payload,
            private_key,
            algorithm='ES256',
            headers={'kid': self.api_key, 'nonce': secrets.token_hex()},
        )
        return jwt_token

    def _get_headers(self, method: str = "GET", path: str = "") -> Dict[str, str]:
        """Get request headers, with authentication if configured."""
        headers = {
            "Content-Type": "application/json",
        }
        if self._authenticated:
            jwt_token = self._build_jwt(method, path)
            headers["Authorization"] = f"Bearer {jwt_token}"
        return headers

    def _make_request(self, method: str, path: str, params: Optional[Dict] = None) -> requests.Response:
        """Make an authenticated or unauthenticated request."""
        url = f"https://api.coinbase.com{path}"
        headers = self._get_headers(method, path)
        return requests.request(method, url, headers=headers, params=params, timeout=30)

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to Coinbase format (BTC-USD)."""
        symbol = symbol.upper()
        if '-' in symbol:
            return symbol
        # Handle common patterns
        if '/' in symbol:
            return symbol.replace('/', '-')
        # Try to detect quote currency
        for quote in ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'BTC', 'ETH']:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-{quote}"
        return f"{symbol}-USD"

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical crypto data from Coinbase Advanced.

        Args:
            symbol: Trading pair (e.g., 'BTC-USD', 'BTCUSD', 'BTC/USD')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 2h, 6h, 1d)

        Returns:
            DataResponse with OHLCV data
        """
        try:
            symbol = self._normalize_symbol(symbol)

            # Map intervals to Coinbase granularity and seconds
            interval_map = {
                "1m": ("ONE_MINUTE", 60),
                "5m": ("FIVE_MINUTE", 300),
                "15m": ("FIFTEEN_MINUTE", 900),
                "30m": ("THIRTY_MINUTE", 1800),
                "1h": ("ONE_HOUR", 3600),
                "2h": ("TWO_HOUR", 7200),
                "6h": ("SIX_HOUR", 21600),
                "1d": ("ONE_DAY", 86400),
                "1D": ("ONE_DAY", 86400),
            }

            granularity, interval_seconds = interval_map.get(interval, ("ONE_DAY", 86400))

            # Parse dates
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # Include end date

            # Coinbase limits to 350 candles per request, paginate if needed
            max_candles = 350
            max_span_seconds = max_candles * interval_seconds

            all_records = []
            current_start = start_dt

            while current_start < end_dt:
                chunk_end = min(
                    current_start + timedelta(seconds=max_span_seconds),
                    end_dt
                )

                start_ts = int(current_start.timestamp())
                end_ts = int(chunk_end.timestamp())

                path = f"/api/v3/brokerage/products/{symbol}/candles"
                params = {
                    "start": start_ts,
                    "end": end_ts,
                    "granularity": granularity
                }

                response = self._make_request("GET", path, params)
                response.raise_for_status()
                data = response.json()

                candles = data.get('candles', [])

                for candle in candles:
                    timestamp = int(candle['start'])
                    dt = datetime.fromtimestamp(timestamp)

                    # Use appropriate date format based on interval
                    if interval in ['1m', '5m', '15m', '30m', '1h', '2h', '6h']:
                        date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        date_str = dt.strftime('%Y-%m-%d')

                    all_records.append({
                        'Date': date_str,
                        'open': float(candle['open']),
                        'high': float(candle['high']),
                        'low': float(candle['low']),
                        'close': float(candle['close']),
                        'volume': float(candle['volume']),
                    })

                current_start = chunk_end

            if not all_records:
                return DataResponse(
                    symbol=symbol, provider=self.name, data=[], success=False,
                    error=f"No data for {symbol}"
                )

            # Sort by date (oldest first) and deduplicate
            all_records.sort(key=lambda x: x['Date'])
            seen = set()
            unique_records = []
            for r in all_records:
                if r['Date'] not in seen:
                    seen.add(r['Date'])
                    unique_records.append(r)

            return DataResponse(
                symbol=symbol, provider=self.name, data=unique_records,
                metadata={
                    'interval': interval,
                    'records': len(unique_records),
                    'source': 'Coinbase Advanced',
                    'authenticated': self._authenticated
                },
                success=True
            )

        except requests.exceptions.HTTPError as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Coinbase API error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol, provider=self.name, data=[], success=False,
                error=f"Coinbase Advanced error: {str(e)}"
            )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        return OptionsChainResponse(
            symbol=request.symbol, provider=self.name,
            snapshot_timestamp=datetime.utcnow(), success=False,
            error="Coinbase Advanced does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        return []

    def validate_connection(self) -> bool:
        """Validate connection, using authentication if available."""
        try:
            path = "/api/v3/brokerage/products/BTC-USD"
            response = self._make_request("GET", path)
            return response.status_code == 200
        except:
            return False

    def supports_historical_options(self) -> bool:
        return False

    # =========================================================================
    # Authenticated Methods (require API key and secret)
    # =========================================================================

    def get_accounts(self) -> Dict[str, Any]:
        """
        Get all accounts (wallets) for the authenticated user.

        Returns:
            Dict with accounts data or error information
        """
        if not self._authenticated:
            return {"success": False, "error": "Authentication required. Provide api_key and api_secret."}

        try:
            path = "/api/v3/brokerage/accounts"
            response = self._make_request("GET", path)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_account(self, account_uuid: str) -> Dict[str, Any]:
        """
        Get a specific account by UUID.

        Args:
            account_uuid: The account UUID

        Returns:
            Dict with account data or error information
        """
        if not self._authenticated:
            return {"success": False, "error": "Authentication required."}

        try:
            path = f"/api/v3/brokerage/accounts/{account_uuid}"
            response = self._make_request("GET", path)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_products(self, product_type: str = None) -> Dict[str, Any]:
        """
        Get all available trading products.

        Args:
            product_type: Optional filter (SPOT, FUTURE)

        Returns:
            Dict with products data
        """
        try:
            path = "/api/v3/brokerage/products"
            params = {}
            if product_type:
                params["product_type"] = product_type

            response = self._make_request("GET", path, params)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_product(self, product_id: str) -> Dict[str, Any]:
        """
        Get details for a specific product.

        Args:
            product_id: Product ID (e.g., 'BTC-USD')

        Returns:
            Dict with product data
        """
        try:
            product_id = self._normalize_symbol(product_id)
            path = f"/api/v3/brokerage/products/{product_id}"
            response = self._make_request("GET", path)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_portfolios(self) -> Dict[str, Any]:
        """
        Get all portfolios for the authenticated user.

        Returns:
            Dict with portfolios data or error information
        """
        if not self._authenticated:
            return {"success": False, "error": "Authentication required."}

        try:
            path = "/api/v3/brokerage/portfolios"
            response = self._make_request("GET", path)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_best_bid_ask(self, product_ids: List[str] = None) -> Dict[str, Any]:
        """
        Get best bid/ask for products.

        Args:
            product_ids: List of product IDs (e.g., ['BTC-USD', 'ETH-USD'])

        Returns:
            Dict with bid/ask data
        """
        try:
            path = "/api/v3/brokerage/best_bid_ask"
            params = {}
            if product_ids:
                params["product_ids"] = ",".join([self._normalize_symbol(p) for p in product_ids])

            response = self._make_request("GET", path, params)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_product_book(self, product_id: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get order book for a product.

        Args:
            product_id: Product ID (e.g., 'BTC-USD')
            limit: Number of levels to return (default 100)

        Returns:
            Dict with order book data
        """
        try:
            product_id = self._normalize_symbol(product_id)
            path = f"/api/v3/brokerage/product_book"
            params = {"product_id": product_id, "limit": limit}
            response = self._make_request("GET", path, params)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @property
    def is_authenticated(self) -> bool:
        """Check if the provider is configured for authenticated access."""
        return self._authenticated

    def get_recent_trades(self, product_id: str) -> Dict[str, Any]:
        """
        Get recent trades (tick-level data) for a product.

        Works for both spot products (e.g., 'BTC-USD') and futures contracts
        (e.g., 'BIP-20DEC30-CDE' for BTC perp-style futures).

        Args:
            product_id: Product ID or futures contract symbol

        Returns:
            Dict with trades data including:
            - trades: List of recent trades with trade_id, price, size, time, side
            - best_bid: Current best bid price
            - best_ask: Current best ask price

        Example:
            >>> provider.get_recent_trades('BIP-20DEC30-CDE')
            {'success': True, 'data': {'trades': [...], 'best_bid': '90100', 'best_ask': '90110'}}
        """
        try:
            # Don't normalize futures symbols
            if '-CDE' not in product_id.upper():
                product_id = self._normalize_symbol(product_id)
            else:
                product_id = product_id.upper()

            path = f"/api/v3/brokerage/products/{product_id}/ticker"
            response = self._make_request("GET", path)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_futures_products(self) -> Dict[str, Any]:
        """
        Get all available futures products.

        Returns perp-style futures contracts like:
        - BIP-20DEC30-CDE (BTC nano perp)
        - ETP-20DEC30-CDE (ETH nano perp)
        - SLP-20DEC30-CDE (SOL nano perp)
        - XPP-20DEC30-CDE (XRP nano perp)

        Returns:
            Dict with futures products data
        """
        return self.get_products(product_type="FUTURE")
