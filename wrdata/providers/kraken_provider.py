"""
Kraken provider for cryptocurrency data.

Kraken is a major European cryptocurrency exchange.
FREE API access - no key required for public market data!

Optional API keys for account/trading features.

API Docs: https://docs.kraken.com/rest/
"""

import requests
from typing import Optional, List
from datetime import datetime, date, timedelta
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class KrakenProvider(BaseProvider):
    """
    Kraken provider for cryptocurrency market data.

    FREE features (no API key needed):
    - Real-time prices for 200+ pairs
    - Historical OHLCV data
    - Order book data
    - Recent trades
    - Ticker information

    Optional API key for:
    - Account balances
    - Trading history
    - Order placement
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="kraken", api_key=api_key)

        self.base_url = "https://api.kraken.com/0"

        # Headers (API key optional for public endpoints)
        self.headers = {
            "User-Agent": "wrdata-kraken-client"
        }

        if api_key:
            self.headers["API-Key"] = api_key

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical cryptocurrency data from Kraken.

        Args:
            symbol: Trading pair (e.g., "BTCUSD", "ETHUSD", "XBTUSD")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval - "1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"

        Returns:
            DataResponse with OHLCV data
        """
        try:
            # Normalize symbol to Kraken format
            symbol = symbol.upper()

            # Kraken uses specific pair names
            # Try to normalize common symbols
            symbol = self._normalize_symbol(symbol)

            # Map interval to Kraken interval (in minutes)
            interval_map = {
                "1m": 1,
                "5m": 5,
                "15m": 15,
                "30m": 30,
                "1h": 60,
                "4h": 240,
                "1d": 1440,
                "1D": 1440,
                "1w": 10080,
            }

            if interval not in interval_map:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"Unsupported interval: {interval}. Use: {list(interval_map.keys())}"
                )

            kraken_interval = interval_map[interval]

            # Convert dates to timestamps
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            start_ts = int(start_dt.timestamp())

            # Build URL
            url = f"{self.base_url}/public/OHLC"

            # Parameters
            params = {
                "pair": symbol,
                "interval": kraken_interval,
                "since": start_ts,
            }

            # Make request
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for errors
            if 'error' in data and data['error']:
                error_msg = ', '.join(data['error'])
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"Kraken API error: {error_msg}"
                )

            # Get result data
            if 'result' not in data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error="No result data from Kraken"
                )

            result = data['result']

            # Find the pair key (Kraken returns dynamic keys)
            pair_key = None
            for key in result.keys():
                if key != 'last':  # 'last' is metadata
                    pair_key = key
                    break

            if not pair_key or pair_key not in result:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for pair {symbol}"
                )

            ohlc_data = result[pair_key]

            if not ohlc_data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No OHLC data for {symbol}"
                )

            # Convert to standard format
            # Kraken format: [time, open, high, low, close, vwap, volume, count]
            records = []
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

            for bar in ohlc_data:
                timestamp = int(bar[0])
                bar_dt = datetime.fromtimestamp(timestamp)

                # Filter by end date
                if bar_dt > end_dt:
                    break

                records.append({
                    'Date': bar_dt.strftime('%Y-%m-%d'),
                    'open': float(bar[1]),
                    'high': float(bar[2]),
                    'low': float(bar[3]),
                    'close': float(bar[4]),
                    'volume': float(bar[6]),
                })

            if not records:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data in date range for {symbol}"
                )

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'interval': interval,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(records),
                    'source': 'Kraken',
                    'pair_key': pair_key,
                },
                success=True
            )

        except requests.exceptions.HTTPError as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"HTTP error: {e.response.status_code}"
            )

        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Kraken API error: {str(e)}"
            )

    def get_ticker(self, symbol: str) -> dict:
        """
        Get ticker information for a trading pair.

        Args:
            symbol: Trading pair (e.g., "BTCUSD", "ETHUSD")

        Returns:
            Dictionary with ticker data
        """
        try:
            symbol = self._normalize_symbol(symbol.upper())

            url = f"{self.base_url}/public/Ticker"
            params = {"pair": symbol}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'error' in data and data['error']:
                return {}

            if 'result' not in data:
                return {}

            result = data['result']

            # Find pair key
            pair_key = None
            for key in result.keys():
                pair_key = key
                break

            if not pair_key:
                return {}

            ticker = result[pair_key]

            return {
                'symbol': symbol,
                'ask': float(ticker['a'][0]) if 'a' in ticker else None,
                'bid': float(ticker['b'][0]) if 'b' in ticker else None,
                'last': float(ticker['c'][0]) if 'c' in ticker else None,
                'volume': float(ticker['v'][1]) if 'v' in ticker else None,  # 24h volume
                'vwap': float(ticker['p'][1]) if 'p' in ticker else None,  # 24h vwap
                'trades': int(ticker['t'][1]) if 't' in ticker else None,  # 24h trades
                'low': float(ticker['l'][1]) if 'l' in ticker else None,  # 24h low
                'high': float(ticker['h'][1]) if 'h' in ticker else None,  # 24h high
                'open': float(ticker['o']) if 'o' in ticker else None,
            }

        except Exception as e:
            print(f"Failed to get ticker: {e}")
            return {}

    def get_asset_pairs(self) -> dict:
        """
        Get list of all tradable asset pairs.

        Returns:
            Dictionary of asset pairs
        """
        try:
            url = f"{self.base_url}/public/AssetPairs"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'error' in data and data['error']:
                return {}

            return data.get('result', {})

        except Exception as e:
            print(f"Failed to get asset pairs: {e}")
            return {}

    def get_recent_trades(self, symbol: str, count: int = 100) -> List[dict]:
        """
        Get recent trades for a trading pair.

        Args:
            symbol: Trading pair
            count: Number of trades to return

        Returns:
            List of recent trades
        """
        try:
            symbol = self._normalize_symbol(symbol.upper())

            url = f"{self.base_url}/public/Trades"
            params = {"pair": symbol}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if 'error' in data and data['error']:
                return []

            if 'result' not in data:
                return []

            result = data['result']

            # Find pair key
            pair_key = None
            for key in result.keys():
                if key != 'last':
                    pair_key = key
                    break

            if not pair_key:
                return []

            trades = result[pair_key][:count]

            # Format: [price, volume, time, buy/sell, market/limit, misc]
            return [
                {
                    'price': float(trade[0]),
                    'volume': float(trade[1]),
                    'time': datetime.fromtimestamp(trade[2]),
                    'side': 'buy' if trade[3] == 'b' else 'sell',
                    'type': 'market' if trade[4] == 'm' else 'limit',
                }
                for trade in trades
            ]

        except Exception as e:
            print(f"Failed to get trades: {e}")
            return []

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Kraken format.

        Args:
            symbol: Input symbol

        Returns:
            Normalized symbol for Kraken
        """
        # Common conversions
        conversions = {
            'BTCUSD': 'XBTUSD',
            'BTCUSDT': 'XBTUSDT',
            'BTCEUR': 'XBTEUR',
        }

        return conversions.get(symbol, symbol)

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """Kraken does not support options."""
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="Kraken does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Kraken does not support options."""
        return []

    def validate_connection(self) -> bool:
        """
        Validate Kraken API connection.

        Tests by fetching server time.
        """
        try:
            url = f"{self.base_url}/public/Time"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            return 'result' in data and 'unixtime' in data['result']

        except Exception:
            return False

    def supports_historical_options(self) -> bool:
        """Kraken does not support options."""
        return False


# Kraken popular trading pairs
KRAKEN_POPULAR_PAIRS = {
    'XBTUSD': 'Bitcoin / US Dollar',
    'ETHUSD': 'Ethereum / US Dollar',
    'XBTEUR': 'Bitcoin / Euro',
    'ETHEUR': 'Ethereum / Euro',
    'USDTUSD': 'Tether / US Dollar',
    'SOLUSD': 'Solana / US Dollar',
    'ADAUSD': 'Cardano / US Dollar',
    'DOTUSD': 'Polkadot / US Dollar',
}
