"""
Whale Alert API provider for historical whale transaction data.

Whale Alert tracks large blockchain transactions across multiple cryptocurrencies.
API Key required - Get one at: https://whale-alert.io/

API Docs: https://docs.whale-alert.io/
Pricing: https://whale-alert.io/#pricing
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    WhaleTransaction,
    WhaleTransactionBatch
)


class WhaleAlertProvider(BaseProvider):
    """
    Whale Alert API provider for blockchain whale transactions.

    Features:
    - Historical whale transaction data
    - Multiple blockchain support (BTC, ETH, etc.)
    - Transaction attribution (exchanges, wallets)
    - USD value at transaction time
    - Transaction type classification

    Requires API key from https://whale-alert.io/
    """

    def __init__(self, api_key: str):
        """
        Initialize Whale Alert provider.

        Args:
            api_key: Whale Alert API key (required)
        """
        if not api_key:
            raise ValueError("Whale Alert API key is required")

        super().__init__(name="whale_alert", api_key=api_key)
        self.base_url = "https://api.whale-alert.io/v1"

    def fetch_whale_transactions(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        min_value: int = 500000,
        blockchain: Optional[str] = None,
        currency: Optional[str] = None,
        limit: int = 100
    ) -> WhaleTransactionBatch:
        """
        Fetch historical whale transactions from Whale Alert.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (defaults to start_date)
            min_value: Minimum transaction value in USD (default: 500000)
            blockchain: Filter by blockchain (e.g., "bitcoin", "ethereum")
            currency: Filter by currency symbol (e.g., "btc", "eth")
            limit: Maximum number of transactions to return (max 100)

        Returns:
            WhaleTransactionBatch with whale transactions

        Note:
            Whale Alert API has rate limits (typically 1000 calls/minute).
            Free tier may have reduced limits.
        """
        try:
            if end_date is None:
                end_date = start_date

            # Convert dates to Unix timestamps
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp()) + 86399  # End of day

            # Whale Alert API endpoint
            url = f"{self.base_url}/transactions"

            params = {
                "api_key": self.api_key,
                "start": start_ts,
                "end": end_ts,
                "min_value": min_value,
                "limit": min(limit, 100)  # API max is 100
            }

            # Add optional filters
            if blockchain:
                params["blockchain"] = blockchain.lower()
            if currency:
                params["currency"] = currency.lower()

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("result") != "success":
                raise Exception(f"Whale Alert API error: {data.get('message', 'Unknown error')}")

            transactions_data = data.get("transactions", [])
            count = data.get("count", 0)

            # Convert to WhaleTransaction objects
            whale_transactions = []
            for tx_data in transactions_data:
                whale_tx = self._parse_whale_alert_transaction(tx_data)
                whale_transactions.append(whale_tx)

            return WhaleTransactionBatch(
                transactions=whale_transactions,
                count=count,
                start_time=datetime.fromtimestamp(start_ts),
                end_time=datetime.fromtimestamp(end_ts),
                filters_applied={
                    "min_value": min_value,
                    "blockchain": blockchain,
                    "currency": currency
                },
                provider=self.name
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise Exception("Whale Alert API rate limit exceeded. Please wait before retrying.")
            elif e.response.status_code == 401:
                raise Exception("Invalid Whale Alert API key")
            else:
                raise Exception(f"Whale Alert API HTTP error: {e}")
        except Exception as e:
            raise Exception(f"Error fetching whale transactions: {e}")

    def _parse_whale_alert_transaction(self, tx_data: Dict[str, Any]) -> WhaleTransaction:
        """
        Parse Whale Alert transaction data into WhaleTransaction model.

        Args:
            tx_data: Raw transaction data from Whale Alert API

        Returns:
            WhaleTransaction object
        """
        # Extract basic info
        blockchain = tx_data.get("blockchain", "unknown")
        symbol_data = tx_data.get("symbol", "")
        amount = Decimal(str(tx_data.get("amount", 0)))
        amount_usd = Decimal(str(tx_data.get("amount_usd", 0)))
        timestamp = datetime.fromtimestamp(tx_data.get("timestamp", 0))
        tx_hash = tx_data.get("hash", "")

        # Extract addresses
        from_data = tx_data.get("from", {})
        to_data = tx_data.get("to", {})

        from_address = from_data.get("address", "")
        to_address = to_data.get("address", "")

        # Determine transaction type based on addresses
        from_owner = from_data.get("owner", "")
        to_owner = to_data.get("owner", "")
        from_owner_type = from_data.get("owner_type", "")
        to_owner_type = to_data.get("owner_type", "")

        # Classify transaction type
        transaction_type = "transfer"
        if from_owner_type == "exchange" and to_owner_type != "exchange":
            transaction_type = "withdrawal"
        elif to_owner_type == "exchange" and from_owner_type != "exchange":
            transaction_type = "deposit"
        elif from_owner_type == "exchange" and to_owner_type == "exchange":
            transaction_type = "exchange_transfer"

        # Determine exchange
        exchange = None
        if from_owner_type == "exchange":
            exchange = from_owner
        elif to_owner_type == "exchange":
            exchange = to_owner

        # Create symbol (e.g., "BTC", "ETH")
        symbol = symbol_data.upper() if symbol_data else blockchain.upper()[:3]

        # Calculate price from amount and USD value
        price = Decimal(str(amount_usd)) / amount if amount > 0 else Decimal(0)

        return WhaleTransaction(
            symbol=symbol,
            timestamp=timestamp,
            exchange=exchange,
            transaction_id=tx_hash,
            size=amount,
            price=price,
            usd_value=amount_usd,
            transaction_type=transaction_type,
            from_address=from_address,
            to_address=to_address,
            blockchain=blockchain,
            tx_hash=tx_hash,
            provider=self.name,
            raw_data=tx_data
        )

    def get_status(self) -> Dict[str, Any]:
        """
        Get Whale Alert API status and usage information.

        Returns:
            Dictionary with API status and usage limits
        """
        try:
            url = f"{self.base_url}/status"
            params = {"api_key": self.api_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return {
                "success": data.get("result") == "success",
                "usage": data.get("usage", {}),
                "limits": data.get("limits", {})
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # BaseProvider abstract methods (not applicable for whale data)

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Not applicable for Whale Alert.
        Use fetch_whale_transactions() instead.
        """
        raise NotImplementedError(
            "Whale Alert does not provide OHLCV timeseries data. "
            "Use fetch_whale_transactions() to get whale transaction data."
        )

    def fetch_options_chain(self, request: OptionsChainRequest) -> OptionsChainResponse:
        """Not applicable for Whale Alert."""
        raise NotImplementedError("Whale Alert does not provide options data")

    def get_available_expirations(self, symbol: str) -> List[date]:
        """Not applicable for Whale Alert."""
        raise NotImplementedError("Whale Alert does not provide options data")

    def validate_connection(self) -> bool:
        """
        Validate API key and connection to Whale Alert.

        Returns:
            True if connection is valid
        """
        try:
            status = self.get_status()
            return status.get("success", False)
        except:
            return False
