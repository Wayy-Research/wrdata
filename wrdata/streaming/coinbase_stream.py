"""
Coinbase WebSocket streaming provider.

Provides real-time market data from Coinbase via WebSocket.
No API key required for public market data streams.

WebSocket Docs: https://docs.cloud.coinbase.com/exchange/docs/websocket-overview
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator, Dict
from datetime import datetime
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class CoinbaseStreamProvider(BaseStreamProvider):
    """
    Coinbase WebSocket streaming provider.

    Streams:
    - Ticker: Real-time price updates
    - Matches: Trade execution data
    - Level2: Order book updates

    No authentication required for public market data.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="coinbase_stream", api_key=api_key)

        self.ws_url = "wss://ws-feed.exchange.coinbase.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

        # Orderbook state management for Level2
        self._orderbooks: Dict[str, Dict] = {}

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            return True  # Coinbase uses per-subscription connections
        except Exception as e:
            print(f"Coinbase stream connection error: {e}")
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

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time ticker stream.

        Coinbase provides best bid/ask updates.
        """
        # Normalize symbol (BTC-USD format)
        symbol = self._normalize_symbol(symbol)

        stream_id = f"ticker_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to ticker channel
        subscribe_message = {
            "type": "subscribe",
            "product_ids": [symbol],
            "channels": ["ticker"]
        }

        async for message in self._stream_channel(subscribe_message):
            try:
                if message.get('type') != 'ticker':
                    continue

                # Parse Coinbase ticker message
                stream_msg = StreamMessage(
                    symbol=message['product_id'],
                    timestamp=datetime.fromisoformat(message['time'].replace('Z', '+00:00')),
                    price=float(message.get('price', 0)),
                    bid=float(message.get('best_bid', 0)),
                    ask=float(message.get('best_ask', 0)),
                    volume=float(message.get('last_size', 0)),
                    provider=self.name,
                    stream_type="ticker",
                    raw_data=message
                )

                # Notify callbacks
                await self._notify_callbacks(stream_id, stream_msg)

                yield stream_msg

            except Exception as e:
                print(f"Error parsing Coinbase ticker message: {e}")
                continue

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time trade matches (simulates kline data).

        Note: Coinbase doesn't have native kline WebSocket.
        We aggregate trades to create candles.
        """
        # Normalize symbol
        symbol = self._normalize_symbol(symbol)

        stream_id = f"matches_{symbol}_{interval}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to matches channel (trades)
        subscribe_message = {
            "type": "subscribe",
            "product_ids": [symbol],
            "channels": ["matches"]
        }

        # Aggregate trades into candles
        current_candle = None
        interval_seconds = self._interval_to_seconds(interval)

        async for message in self._stream_channel(subscribe_message):
            try:
                if message.get('type') != 'match':
                    continue

                timestamp = datetime.fromisoformat(message['time'].replace('Z', '+00:00'))
                price = float(message['price'])
                volume = float(message['size'])

                # Get candle start time
                candle_start = timestamp.replace(
                    second=0,
                    microsecond=0
                )

                # Create new candle or update existing
                if current_candle is None or candle_start != current_candle['start']:
                    # Emit previous candle if exists
                    if current_candle:
                        stream_msg = StreamMessage(
                            symbol=symbol,
                            timestamp=current_candle['start'],
                            open=current_candle['open'],
                            high=current_candle['high'],
                            low=current_candle['low'],
                            close=current_candle['close'],
                            volume=current_candle['volume'],
                            provider=self.name,
                            stream_type="kline"
                        )

                        await self._notify_callbacks(stream_id, stream_msg)
                        yield stream_msg

                    # Start new candle
                    current_candle = {
                        'start': candle_start,
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': volume
                    }
                else:
                    # Update current candle
                    current_candle['high'] = max(current_candle['high'], price)
                    current_candle['low'] = min(current_candle['low'], price)
                    current_candle['close'] = price
                    current_candle['volume'] += volume

            except Exception as e:
                print(f"Error processing Coinbase match: {e}")
                continue

    async def subscribe_depth(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to Level2 orderbook updates.

        Provides:
        - Initial full orderbook snapshot
        - Incremental updates (l2update channel)

        Args:
            symbol: Trading pair (e.g., "BTC-USD")
            callback: Optional callback for each update

        Yields:
            StreamMessage with bids/asks orderbook data
        """
        symbol = self._normalize_symbol(symbol)
        stream_id = f"depth_{symbol}"

        if callback:
            self.add_callback(stream_id, callback)

        # Initialize orderbook state
        self._orderbooks[symbol] = {
            'bids': {},  # price -> size
            'asks': {},  # price -> size
        }

        # Subscribe to level2 channel
        subscribe_message = {
            "type": "subscribe",
            "product_ids": [symbol],
            "channels": ["level2"]
        }

        async for message in self._stream_channel(subscribe_message):
            try:
                msg_type = message.get('type')

                if msg_type == 'snapshot':
                    # Full orderbook snapshot
                    self._process_snapshot(symbol, message)

                    stream_msg = self._create_orderbook_message(symbol)
                    await self._notify_callbacks(stream_id, stream_msg)
                    yield stream_msg

                elif msg_type == 'l2update':
                    # Incremental update
                    self._process_l2update(symbol, message)

                    stream_msg = self._create_orderbook_message(symbol)
                    await self._notify_callbacks(stream_id, stream_msg)
                    yield stream_msg

            except Exception as e:
                print(f"Error processing Coinbase orderbook update: {e}")
                continue

    def _process_snapshot(self, symbol: str, message: dict):
        """Process full orderbook snapshot."""
        orderbook = self._orderbooks[symbol]

        # Reset orderbook
        orderbook['bids'] = {}
        orderbook['asks'] = {}

        # Add all bids [price, size]
        for price, size in message.get('bids', []):
            orderbook['bids'][float(price)] = float(size)

        # Add all asks [price, size]
        for price, size in message.get('asks', []):
            orderbook['asks'][float(price)] = float(size)

    def _process_l2update(self, symbol: str, message: dict):
        """Process incremental orderbook update."""
        orderbook = self._orderbooks[symbol]

        # changes format: [side, price, size]
        for change in message.get('changes', []):
            side, price, size = change
            price = float(price)
            size = float(size)

            book = orderbook['bids'] if side == 'buy' else orderbook['asks']

            if size == 0:
                # Remove price level
                book.pop(price, None)
            else:
                # Update price level
                book[price] = size

    def _create_orderbook_message(self, symbol: str) -> StreamMessage:
        """Create StreamMessage from current orderbook state."""
        orderbook = self._orderbooks[symbol]

        # Sort and convert to list of [price, size]
        # Bids: highest to lowest
        bids = sorted(
            [[p, s] for p, s in orderbook['bids'].items()],
            key=lambda x: x[0],
            reverse=True
        )[:20]  # Top 20 levels

        # Asks: lowest to highest
        asks = sorted(
            [[p, s] for p, s in orderbook['asks'].items()],
            key=lambda x: x[0]
        )[:20]  # Top 20 levels

        # Calculate best bid/ask
        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None
        mid_price = (best_bid + best_ask) / 2 if (best_bid and best_ask) else None

        return StreamMessage(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            price=mid_price,
            bid=best_bid,
            ask=best_ask,
            bids=bids,
            asks=asks,
            provider=self.name,
            stream_type="depth"
        )

    def get_orderbook_snapshot(self, symbol: str) -> Optional[Dict]:
        """
        Get current orderbook state for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC-USD")

        Returns:
            Dict with 'bids' and 'asks' or None if not available
        """
        symbol = self._normalize_symbol(symbol)
        return self._orderbooks.get(symbol)

    def _interval_to_seconds(self, interval: str) -> int:
        """Convert interval string to seconds."""
        interval_map = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '4h': 14400,
            '1d': 86400,
        }
        return interval_map.get(interval, 60)

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol to Coinbase format (BTC-USD).
        """
        symbol = symbol.upper()

        if '-' in symbol:
            return symbol

        # Common quote currencies
        quote_currencies = ['USD', 'USDT', 'EUR', 'GBP', 'BTC', 'ETH']

        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}-{quote}"

        # Default to USD
        return f"{symbol}-USD"

    async def _stream_channel(self, subscribe_message: dict) -> AsyncIterator[dict]:
        """
        Connect to Coinbase WebSocket and stream messages.

        Args:
            subscribe_message: Subscription message to send

        Yields:
            Parsed JSON messages
        """
        while True:
            try:
                if self.session is None:
                    self.session = aiohttp.ClientSession()

                async with self.session.ws_connect(self.ws_url) as ws:
                    self.websocket = ws
                    self._connected = True
                    self._reconnect_attempts = 0

                    # Send subscription
                    await ws.send_json(subscribe_message)
                    print(f"Subscribed to Coinbase: {subscribe_message['channels']} for {subscribe_message['product_ids']}")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            yield data

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print("Coinbase stream closed")
                            break

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print("Coinbase stream error")
                            break

            except Exception as e:
                print(f"Coinbase stream error: {e}")
                self._connected = False

                # Exponential backoff
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    wait_time = min(2 ** self._reconnect_attempts, 60)
                    print(f"Reconnecting in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self._reconnect_attempts += 1
                else:
                    print("Max reconnection attempts reached")
                    break

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected

    async def reconnect(self) -> bool:
        """Attempt to reconnect WebSocket."""
        await self.disconnect()
        return await self.connect()
