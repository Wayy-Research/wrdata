"""
Binance WebSocket streaming provider.

Provides real-time market data from Binance via WebSocket.
No API key required for public market data streams.
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator
from datetime import datetime
from decimal import Decimal
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage
from wrdata.models.schemas import WhaleTransaction
from wrdata.utils.whale_detection import WhaleDetector


class BinanceStreamProvider(BaseStreamProvider):
    """
    Binance WebSocket streaming provider.

    Streams:
    - Ticker/Trade: Real-time price updates
    - Kline: Real-time candlestick data
    - Depth: Order book updates

    No authentication required for market data.
    """

    def __init__(self, api_key: Optional[str] = None, testnet: bool = False):
        super().__init__(name="binance_stream", api_key=api_key)

        # WebSocket URLs
        if testnet:
            self.ws_url = "wss://testnet.binance.vision/ws"
        else:
            self.ws_url = "wss://stream.binance.com:9443/ws"

        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

        # Whale detection
        self.whale_detector: Optional[WhaleDetector] = None

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            return True  # Binance uses per-stream connections
        except Exception as e:
            print(f"Binance stream connection error: {e}")
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
        Subscribe to real-time ticker/trade stream.

        Binance provides tick-by-tick trade data.
        """
        # Normalize symbol (BTCUSDT)
        symbol = symbol.upper().replace('/', '').replace('-', '')
        stream_name = f"{symbol.lower()}@trade"

        stream_id = f"ticker_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        async for message in self._stream_endpoint(stream_name):
            try:
                # Parse Binance trade message
                stream_msg = StreamMessage(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(message['T'] / 1000),
                    price=float(message['p']),
                    volume=float(message['q']),
                    provider=self.name,
                    stream_type="trade",
                    raw_data=message
                )

                # Notify callbacks
                await self._notify_callbacks(stream_id, stream_msg)

                yield stream_msg

            except Exception as e:
                print(f"Error parsing Binance trade message: {e}")
                continue

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time kline/candlestick stream.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d)
        """
        # Normalize symbol
        symbol = symbol.upper().replace('/', '').replace('-', '')

        # Map interval to Binance format
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d',
        }
        binance_interval = interval_map.get(interval, '1m')

        stream_name = f"{symbol.lower()}@kline_{binance_interval}"

        stream_id = f"kline_{symbol}_{interval}"
        if callback:
            self.add_callback(stream_id, callback)

        async for message in self._stream_endpoint(stream_name):
            try:
                # Parse Binance kline message
                kline = message['k']

                stream_msg = StreamMessage(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(kline['t'] / 1000),
                    open=float(kline['o']),
                    high=float(kline['h']),
                    low=float(kline['l']),
                    close=float(kline['c']),
                    volume=float(kline['v']),
                    provider=self.name,
                    stream_type="kline",
                    raw_data=message
                )

                # Notify callbacks
                await self._notify_callbacks(stream_id, stream_msg)

                yield stream_msg

            except Exception as e:
                print(f"Error parsing Binance kline message: {e}")
                continue

    async def subscribe_depth(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to order book depth stream.

        Provides top 20 bids/asks with updates.
        """
        # Normalize symbol
        symbol = symbol.upper().replace('/', '').replace('-', '')
        stream_name = f"{symbol.lower()}@depth20@100ms"

        stream_id = f"depth_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        async for message in self._stream_endpoint(stream_name):
            try:
                stream_msg = StreamMessage(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    bids=[[float(p), float(q)] for p, q in message['bids'][:5]],
                    asks=[[float(p), float(q)] for p, q in message['asks'][:5]],
                    provider=self.name,
                    stream_type="depth",
                    raw_data=message
                )

                # Notify callbacks
                await self._notify_callbacks(stream_id, stream_msg)

                yield stream_msg

            except Exception as e:
                print(f"Error parsing Binance depth message: {e}")
                continue

    async def subscribe_aggregate_trades(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        whale_callback: Optional[Callable[[WhaleTransaction], None]] = None,
        enable_whale_detection: bool = False,
        percentile_threshold: float = 99.0,
        min_usd_value: Optional[float] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to aggregate trade stream for whale detection.

        Binance aggregate trades combine individual trades that are filled at the same
        time, from the same taker order, against multiple maker orders. This is ideal
        for whale detection as large orders are often filled in multiple smaller trades.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            callback: Optional callback for all trades
            whale_callback: Optional callback for whale transactions only
            enable_whale_detection: Enable percentile-based whale filtering
            percentile_threshold: Volume percentile threshold (default: 99.0 = top 1%)
            min_usd_value: Minimum USD value to qualify as whale

        Yields:
            StreamMessage objects for aggregate trades
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
        symbol = symbol.upper().replace('/', '').replace('-', '')
        stream_name = f"{symbol.lower()}@aggTrade"

        stream_id = f"aggtrade_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        async for message in self._stream_endpoint(stream_name):
            try:
                # Parse Binance aggregate trade message
                # Message format:
                # {
                #   "e": "aggTrade",
                #   "E": 1234567890,  # Event time
                #   "s": "BTCUSDT",   # Symbol
                #   "a": 12345,       # Aggregate trade ID
                #   "p": "50000.00",  # Price
                #   "q": "0.5",       # Quantity
                #   "f": 100,         # First trade ID
                #   "l": 105,         # Last trade ID
                #   "T": 1234567890,  # Trade time
                #   "m": true,        # Is the buyer the market maker?
                # }

                price = float(message['p'])
                quantity = float(message['q'])
                timestamp = datetime.fromtimestamp(message['T'] / 1000)
                is_buyer_maker = message['m']

                stream_msg = StreamMessage(
                    symbol=symbol,
                    timestamp=timestamp,
                    price=price,
                    volume=quantity,
                    provider=self.name,
                    stream_type="aggtrade",
                    raw_data=message
                )

                # Whale detection
                if enable_whale_detection and self.whale_detector:
                    is_whale, metadata = self.whale_detector.process_transaction(
                        symbol=symbol,
                        volume=quantity,
                        price=price,
                        exchange="binance",
                        timestamp=timestamp,
                        percentile_threshold=percentile_threshold
                    )

                    if is_whale:
                        # Create WhaleTransaction object
                        whale_tx = WhaleTransaction(
                            symbol=symbol,
                            timestamp=timestamp,
                            exchange="binance",
                            transaction_id=str(message['a']),
                            size=Decimal(str(quantity)),
                            price=Decimal(str(price)),
                            usd_value=Decimal(str(metadata['usd_value'])),
                            percentile=metadata['percentile'],
                            volume_rank=metadata['rank'],
                            transaction_type="trade",
                            side="sell" if is_buyer_maker else "buy",
                            is_maker=is_buyer_maker,
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
                print(f"Error parsing Binance aggregate trade message: {e}")
                continue

    async def _stream_endpoint(self, stream_name: str) -> AsyncIterator[dict]:
        """
        Connect to specific Binance stream endpoint.

        Args:
            stream_name: Binance stream name (e.g., "btcusdt@trade")

        Yields:
            Parsed JSON messages
        """
        url = f"{self.ws_url}/{stream_name}"

        while True:
            try:
                if self.session is None:
                    self.session = aiohttp.ClientSession()

                async with self.session.ws_connect(url) as ws:
                    self._connected = True
                    self._reconnect_attempts = 0

                    print(f"Connected to Binance stream: {stream_name}")

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            yield data

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print(f"Binance stream closed: {stream_name}")
                            break

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"Binance stream error: {stream_name}")
                            break

            except Exception as e:
                print(f"Binance stream error: {e}")
                self._connected = False

                # Exponential backoff for reconnection
                if self._reconnect_attempts < self._max_reconnect_attempts:
                    wait_time = min(2 ** self._reconnect_attempts, 60)
                    print(f"Reconnecting in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self._reconnect_attempts += 1
                else:
                    print(f"Max reconnection attempts reached for {stream_name}")
                    break

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected

    async def reconnect(self) -> bool:
        """Attempt to reconnect WebSocket."""
        await self.disconnect()
        return await self.connect()
