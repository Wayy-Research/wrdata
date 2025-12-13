"""
Whale Alert WebSocket streaming provider for real-time whale alerts.

Whale Alert provides real-time notifications of large blockchain transactions.
API Key required - Get one at: https://whale-alert.io/

WebSocket Docs: https://docs.whale-alert.io/#websocket
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator
from datetime import datetime
from decimal import Decimal
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage
from wrdata.models.schemas import WhaleTransaction


class WhaleAlertStreamProvider(BaseStreamProvider):
    """
    Whale Alert WebSocket streaming provider.

    Streams:
    - Real-time whale transaction alerts
    - Customizable filters (min value, blockchain, currency)
    - Transaction attribution and classification

    Requires API key from https://whale-alert.io/
    """

    def __init__(self, api_key: str):
        """
        Initialize Whale Alert streaming provider.

        Args:
            api_key: Whale Alert API key (required)
        """
        if not api_key:
            raise ValueError("Whale Alert API key is required")

        super().__init__(name="whale_alert_stream", api_key=api_key)
        self.ws_url = "wss://socket.whale-alert.io"
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            return True  # Connection happens per-stream
        except Exception as e:
            print(f"Whale Alert stream connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._connected = False

        # Close all active streams
        for stream_id, task in list(self.active_streams.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self.websocket and not self.websocket.closed:
            await self.websocket.close()

        if self.session and not self.session.closed:
            await self.session.close()

        self.websocket = None
        self.session = None

    async def subscribe_whale_alerts(
        self,
        min_value: int = 500000,
        blockchain: Optional[str] = None,
        currency: Optional[str] = None,
        callback: Optional[Callable[[WhaleTransaction], None]] = None
    ) -> AsyncIterator[WhaleTransaction]:
        """
        Subscribe to real-time whale transaction alerts.

        Args:
            min_value: Minimum transaction value in USD (default: 500000)
            blockchain: Filter by blockchain (e.g., "bitcoin", "ethereum")
            currency: Filter by currency symbol (e.g., "btc", "eth")
            callback: Optional callback for whale transactions

        Yields:
            WhaleTransaction objects for each whale alert

        Note:
            Whale Alert WebSocket requires an active subscription plan.
            Free tier may have limitations.
        """
        stream_id = f"whale_alerts_{min_value}"
        if callback:
            self.add_callback(stream_id, None)  # Store for potential future use

        # Build subscription filters
        filters = {"min_value": min_value}
        if blockchain:
            filters["blockchain"] = blockchain.lower()
        if currency:
            filters["currency"] = currency.lower()

        async for transaction in self._stream_alerts(filters):
            # Notify callback if provided
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(transaction)
                else:
                    callback(transaction)

            yield transaction

    async def _stream_alerts(self, filters: dict) -> AsyncIterator[WhaleTransaction]:
        """
        Connect to Whale Alert WebSocket and stream whale alerts.

        Args:
            filters: Filter parameters for alerts

        Yields:
            WhaleTransaction objects
        """
        while True:
            try:
                if self.session is None:
                    self.session = aiohttp.ClientSession()

                # WebSocket URL with API key
                url = f"{self.ws_url}?api_key={self.api_key}"

                async with self.session.ws_connect(url) as ws:
                    self.websocket = ws
                    self._connected = True
                    self._reconnect_attempts = 0

                    # Send subscription message with filters
                    subscription = {
                        "method": "subscribe",
                        "params": filters
                    }
                    await ws.send_json(subscription)

                    print(f"Connected to Whale Alert stream (min value: ${filters['min_value']:,})")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)

                            # Handle different message types
                            if data.get("method") == "transaction":
                                # Parse whale transaction
                                tx_data = data.get("params", {})
                                whale_tx = self._parse_whale_alert_transaction(tx_data)
                                yield whale_tx

                            elif data.get("method") == "ping":
                                # Respond to ping
                                await ws.send_json({"method": "pong"})

                            elif data.get("error"):
                                print(f"Whale Alert error: {data.get('error')}")

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print("Whale Alert stream closed")
                            break

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print("Whale Alert stream error")
                            break

            except Exception as e:
                print(f"Whale Alert stream error: {e}")
                self._connected = False

                # Exponential backoff for reconnection
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    wait_time = min(2 ** self._reconnect_attempts, 60)
                    print(f"Reconnecting in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self._reconnect_attempts += 1
                else:
                    print("Max reconnection attempts reached")
                    break

    def _parse_whale_alert_transaction(self, tx_data: dict) -> WhaleTransaction:
        """
        Parse Whale Alert WebSocket transaction into WhaleTransaction model.

        Args:
            tx_data: Raw transaction data from WebSocket

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

        # Determine transaction type
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

        # Create symbol
        symbol = symbol_data.upper() if symbol_data else blockchain.upper()[:3]

        # Calculate price
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

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Not applicable for Whale Alert.
        Use subscribe_whale_alerts() instead.
        """
        raise NotImplementedError(
            "Whale Alert does not provide ticker streams. "
            "Use subscribe_whale_alerts() for whale transaction alerts."
        )

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Not applicable for Whale Alert.
        Use subscribe_whale_alerts() instead.
        """
        raise NotImplementedError(
            "Whale Alert does not provide kline streams. "
            "Use subscribe_whale_alerts() for whale transaction alerts."
        )

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected

    async def reconnect(self) -> bool:
        """Attempt to reconnect WebSocket."""
        await self.disconnect()
        return await self.connect()
