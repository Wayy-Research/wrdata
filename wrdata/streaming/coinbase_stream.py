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
from decimal import Decimal
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage
from wrdata.models.schemas import WhaleTransaction
from wrdata.utils.whale_detection import WhaleDetector


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

        # Use Advanced Trade API (supports level2 without authentication)
        self.ws_url = "wss://advanced-trade-ws.coinbase.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

        # Orderbook state management for Level2
        self._orderbooks: Dict[str, Dict] = {}

        # Whale detection
        self.whale_detector: Optional[WhaleDetector] = None

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

        # Subscribe to level2 channel (Advanced Trade API format)
        subscribe_message = {
            "type": "subscribe",
            "product_ids": [symbol],
            "channel": "level2"  # Singular for Advanced Trade API
        }

        async for message in self._stream_channel(subscribe_message):
            try:
                # Advanced Trade API format
                channel = message.get('channel')
                if channel != 'l2_data':
                    continue

                events = message.get('events', [])
                for event in events:
                    event_type = event.get('type')

                    if event_type == 'snapshot':
                        # Full orderbook snapshot
                        self._process_advanced_snapshot(symbol, event)

                        stream_msg = self._create_orderbook_message(symbol)
                        await self._notify_callbacks(stream_id, stream_msg)
                        yield stream_msg

                    elif event_type == 'update':
                        # Incremental update
                        self._process_advanced_update(symbol, event)

                        stream_msg = self._create_orderbook_message(symbol)
                        await self._notify_callbacks(stream_id, stream_msg)
                        yield stream_msg

            except Exception as e:
                print(f"Error processing Coinbase orderbook update: {e}")
                import traceback
                traceback.print_exc()
                continue

    async def subscribe_matches(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        whale_callback: Optional[Callable[[WhaleTransaction], None]] = None,
        enable_whale_detection: bool = False,
        percentile_threshold: float = 99.0,
        min_usd_value: Optional[float] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to trade matches stream for whale detection.

        Coinbase matches channel provides real-time trade execution data,
        perfect for identifying large whale transactions on the exchange.

        Args:
            symbol: Trading pair (e.g., "BTC-USD")
            callback: Optional callback for all trades
            whale_callback: Optional callback for whale transactions only
            enable_whale_detection: Enable percentile-based whale filtering
            percentile_threshold: Volume percentile threshold (default: 99.0 = top 1%)
            min_usd_value: Minimum USD value to qualify as whale

        Yields:
            StreamMessage objects for trade matches
        """
        # Initialize whale detector if needed
        if enable_whale_detection and self.whale_detector is None:
            self.whale_detector = WhaleDetector(
                default_percentile=percentile_threshold,
                min_usd_value=min_usd_value,
                window_size=1000,
                time_window_seconds=3600
            )

        # Normalize symbol
        symbol = self._normalize_symbol(symbol)

        stream_id = f"matches_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to matches channel (trades)
        subscribe_message = {
            "type": "subscribe",
            "product_ids": [symbol],
            "channels": ["matches"]
        }

        async for message in self._stream_channel(subscribe_message):
            try:
                if message.get('type') != 'match':
                    continue

                # Parse Coinbase match message
                # Message format:
                # {
                #   "type": "match",
                #   "trade_id": 12345,
                #   "maker_order_id": "...",
                #   "taker_order_id": "...",
                #   "side": "buy" or "sell",
                #   "size": "0.5",
                #   "price": "50000.00",
                #   "product_id": "BTC-USD",
                #   "time": "2024-01-01T12:00:00.123456Z",
                #   "sequence": 1234567890
                # }

                timestamp = datetime.fromisoformat(message['time'].replace('Z', '+00:00'))
                price = float(message['price'])
                size = float(message['size'])
                side = message.get('side', 'unknown')

                stream_msg = StreamMessage(
                    symbol=symbol,
                    timestamp=timestamp,
                    price=price,
                    volume=size,
                    provider=self.name,
                    stream_type="match",
                    raw_data=message
                )

                # Whale detection
                if enable_whale_detection and self.whale_detector:
                    is_whale, metadata = self.whale_detector.process_transaction(
                        symbol=symbol,
                        volume=size,
                        price=price,
                        exchange="coinbase",
                        timestamp=timestamp,
                        percentile_threshold=percentile_threshold
                    )

                    if is_whale:
                        # Create WhaleTransaction object
                        whale_tx = WhaleTransaction(
                            symbol=symbol,
                            timestamp=timestamp,
                            exchange="coinbase",
                            transaction_id=str(message.get('trade_id')),
                            size=Decimal(str(size)),
                            price=Decimal(str(price)),
                            usd_value=Decimal(str(metadata['usd_value'])),
                            percentile=metadata['percentile'],
                            volume_rank=metadata['rank'],
                            transaction_type="trade",
                            side=side,
                            provider=self.name,
                            raw_data=message
                        )

                        # Notify whale callback
                        if whale_callback:
                            if asyncio.iscoroutinefunction(whale_callback):
                                await whale_callback(whale_tx)
                            else:
                                whale_callback(whale_tx)

                        # Add whale metadata to stream message
                        if stream_msg.raw_data is None:
                            stream_msg.raw_data = {}
                        stream_msg.raw_data['whale_metadata'] = metadata

                # Notify callbacks
                await self._notify_callbacks(stream_id, stream_msg)

                yield stream_msg

            except Exception as e:
                print(f"Error parsing Coinbase match message: {e}")
                continue

    async def subscribe_market_trades(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to market trades stream (Advanced Trade API).

        This channel works for BOTH spot AND futures products (including perp-style futures).
        Use this method for streaming tick-level trade data from futures contracts like:
        - BIP-20DEC30-CDE (BTC perp-style)
        - ETP-20DEC30-CDE (ETH perp-style)
        - SLP-20DEC30-CDE (SOL perp-style)
        - XPP-20DEC30-CDE (XRP perp-style)

        Args:
            symbol: Trading pair or futures contract (e.g., "BTC-USD" or "BIP-20DEC30-CDE")
            callback: Optional callback for each trade

        Yields:
            StreamMessage objects for each trade
        """
        # Don't normalize futures symbols (they have special format)
        if '-CDE' not in symbol.upper():
            symbol = self._normalize_symbol(symbol)
        else:
            symbol = symbol.upper()

        stream_id = f"market_trades_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to market_trades channel (Advanced Trade API format)
        subscribe_message = {
            "type": "subscribe",
            "product_ids": [symbol],
            "channel": "market_trades"
        }

        async for message in self._stream_channel(subscribe_message):
            try:
                channel = message.get('channel')
                if channel != 'market_trades':
                    continue

                events = message.get('events', [])
                for event in events:
                    event_type = event.get('type')

                    # Process both snapshot and update events
                    trades = event.get('trades', [])
                    for trade in trades:
                        # Handle various timestamp formats from Coinbase
                        time_str = trade['time']
                        try:
                            # Remove timezone suffix for consistent parsing
                            if time_str.endswith('Z'):
                                time_str = time_str[:-1]
                            elif '+' in time_str:
                                time_str = time_str.split('+')[0]
                            # Normalize microseconds to 6 digits
                            if '.' in time_str:
                                main, micro = time_str.rsplit('.', 1)
                                micro = micro[:6].ljust(6, '0')
                                time_str = f"{main}.{micro}"
                            timestamp = datetime.fromisoformat(time_str)
                        except (ValueError, AttributeError):
                            timestamp = datetime.utcnow()
                        price = float(trade['price'])
                        size = float(trade['size'])
                        side = trade.get('side', 'unknown').lower()

                        stream_msg = StreamMessage(
                            symbol=symbol,
                            timestamp=timestamp,
                            price=price,
                            volume=size,
                            provider=self.name,
                            stream_type="trade",
                            raw_data={
                                'trade_id': trade.get('trade_id'),
                                'side': side,
                                'product_id': trade.get('product_id'),
                                'event_type': event_type
                            }
                        )

                        await self._notify_callbacks(stream_id, stream_msg)
                        yield stream_msg

            except Exception as e:
                print(f"Error processing market trade: {e}")
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
        """Process incremental orderbook update (Legacy Exchange API)."""
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

    def _process_advanced_snapshot(self, symbol: str, event: dict):
        """Process full orderbook snapshot (Advanced Trade API)."""
        orderbook = self._orderbooks[symbol]

        # Reset orderbook
        orderbook['bids'] = {}
        orderbook['asks'] = {}

        # updates format: [{"side": "bid"/"ask", "price_level": "123.45", "new_quantity": "1.23"}, ...]
        for update in event.get('updates', []):
            side = update.get('side')
            price = float(update.get('price_level'))
            size = float(update.get('new_quantity'))

            book = orderbook['bids'] if side == 'bid' else orderbook['asks']
            if size > 0:
                book[price] = size

    def _process_advanced_update(self, symbol: str, event: dict):
        """Process incremental orderbook update (Advanced Trade API)."""
        orderbook = self._orderbooks[symbol]

        # updates format: [{"side": "bid"/"ask", "price_level": "123.45", "new_quantity": "1.23"}, ...]
        for update in event.get('updates', []):
            side = update.get('side')
            price = float(update.get('price_level'))
            size = float(update.get('new_quantity'))

            book = orderbook['bids'] if side == 'bid' else orderbook['asks']

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

                # Increase max_msg_size to handle large orderbook snapshots (~5MB)
                async with self.session.ws_connect(self.ws_url, max_msg_size=10*1024*1024) as ws:
                    self.websocket = ws
                    self._connected = True
                    self._reconnect_attempts = 0

                    # Send subscription
                    await ws.send_json(subscribe_message)
                    # Handle both old (channels) and new (channel) format
                    channels = subscribe_message.get('channels') or [subscribe_message.get('channel')]
                    print(f"Subscribed to Coinbase: {channels} for {subscribe_message['product_ids']}")

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
