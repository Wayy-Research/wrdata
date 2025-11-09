"""
Alpaca WebSocket streaming provider.

Provides real-time stock quotes and trades via WebSocket.
FREE with Alpaca account - IEX data feed included!

Docs: https://docs.alpaca.markets/docs/streaming-market-data
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator
from datetime import datetime
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class AlpacaStreamProvider(BaseStreamProvider):
    """
    Alpaca WebSocket streaming provider.

    FREE real-time streaming with Alpaca account!
    Uses IEX data feed on free tier.

    Channels:
    - Trades: Real-time trade data
    - Quotes: Real-time bid/ask quotes
    - Bars: Real-time minute bars
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper: bool = True
    ):
        super().__init__(name="alpaca_stream", api_key=api_key)

        if not api_key or not api_secret:
            raise ValueError("Alpaca API key and secret required for streaming")

        self.api_secret = api_secret
        self.paper = paper

        # WebSocket URL for market data (v2)
        self.ws_url = "wss://stream.data.alpaca.markets/v2/iex"

        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        self._authenticated = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

    async def connect(self) -> bool:
        """Establish WebSocket connection and authenticate."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            self.websocket = await self.session.ws_connect(self.ws_url)

            # Wait for welcome message
            welcome = await self.websocket.receive_json()
            if welcome[0].get('T') == 'success' and welcome[0].get('msg') == 'connected':
                print(f"✓ Connected to Alpaca WebSocket")

            # Authenticate
            auth_msg = {
                "action": "auth",
                "key": self.api_key,
                "secret": self.api_secret
            }
            await self.websocket.send_json(auth_msg)

            # Wait for auth response
            auth_response = await self.websocket.receive_json()
            if auth_response[0].get('T') == 'success' and auth_response[0].get('msg') == 'authenticated':
                print(f"✓ Authenticated with Alpaca")
                self._connected = True
                self._authenticated = True
                self._reconnect_attempts = 0
                return True
            else:
                print(f"❌ Authentication failed: {auth_response}")
                return False

        except Exception as e:
            print(f"Alpaca stream connection error: {e}")
            self._connected = False
            self._authenticated = False
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        self._connected = False
        self._authenticated = False

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
        Subscribe to real-time trade data.

        Args:
            symbol: Stock ticker (e.g., "AAPL", "MSFT")
            callback: Optional callback for each message

        Yields:
            StreamMessage with trade data
        """
        symbol = symbol.upper()

        # Connect if not already connected
        if not self._authenticated:
            await self.connect()

        stream_id = f"ticker_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to trades
        subscribe_msg = {
            "action": "subscribe",
            "trades": [symbol]
        }
        await self.websocket.send_json(subscribe_msg)

        # Wait for subscription confirmation
        confirm = await self.websocket.receive_json()
        if confirm[0].get('T') == 'subscription':
            print(f"✓ Subscribed to {symbol} trades")

        # Listen for messages
        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        messages = json.loads(msg.data)

                        for message in messages:
                            msg_type = message.get('T')

                            # Trade message
                            if msg_type == 't':
                                stream_msg = StreamMessage(
                                    symbol=message.get('S', symbol),
                                    timestamp=datetime.fromisoformat(message.get('t', '').replace('Z', '+00:00')),
                                    price=float(message.get('p', 0)),
                                    volume=float(message.get('s', 0)),
                                    provider=self.name,
                                    stream_type="trade",
                                    raw_data=message
                                )

                                await self._notify_callbacks(stream_id, stream_msg)
                                yield stream_msg

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error parsing Alpaca message: {e}")
                        continue

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"WebSocket error: {self.websocket.exception()}")
                    break

        except asyncio.CancelledError:
            # Unsubscribe when cancelled
            unsubscribe_msg = {
                "action": "unsubscribe",
                "trades": [symbol]
            }
            try:
                await self.websocket.send_json(unsubscribe_msg)
            except:
                pass
            raise

        except Exception as e:
            print(f"Alpaca stream error: {e}")
            self._connected = False

            # Attempt reconnection
            if self._reconnect_attempts < self._max_reconnect_attempts:
                wait_time = min(2 ** self._reconnect_attempts, 60)
                print(f"Reconnecting in {wait_time}s...")
                await asyncio.sleep(wait_time)
                self._reconnect_attempts += 1
                await self.reconnect()

    async def subscribe_quotes(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time quote data (bid/ask).

        Args:
            symbol: Stock ticker
            callback: Optional callback for each message

        Yields:
            StreamMessage with quote data
        """
        symbol = symbol.upper()

        if not self._authenticated:
            await self.connect()

        stream_id = f"quotes_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to quotes
        subscribe_msg = {
            "action": "subscribe",
            "quotes": [symbol]
        }
        await self.websocket.send_json(subscribe_msg)

        confirm = await self.websocket.receive_json()
        if confirm[0].get('T') == 'subscription':
            print(f"✓ Subscribed to {symbol} quotes")

        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        messages = json.loads(msg.data)

                        for message in messages:
                            if message.get('T') == 'q':  # Quote message
                                stream_msg = StreamMessage(
                                    symbol=message.get('S', symbol),
                                    timestamp=datetime.fromisoformat(message.get('t', '').replace('Z', '+00:00')),
                                    bid=float(message.get('bp', 0)),
                                    ask=float(message.get('ap', 0)),
                                    volume=float(message.get('bs', 0)) + float(message.get('as', 0)),
                                    provider=self.name,
                                    stream_type="quote",
                                    raw_data=message
                                )

                                await self._notify_callbacks(stream_id, stream_msg)
                                yield stream_msg

                    except Exception as e:
                        print(f"Error parsing quote: {e}")
                        continue

        except asyncio.CancelledError:
            unsubscribe_msg = {
                "action": "unsubscribe",
                "quotes": [symbol]
            }
            try:
                await self.websocket.send_json(unsubscribe_msg)
            except:
                pass
            raise

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time bar (candle) data.

        Note: Alpaca only provides 1-minute bars via WebSocket.
        For other intervals, aggregate the bars yourself.

        Args:
            symbol: Stock ticker
            interval: Only "1m" supported
            callback: Optional callback for each message

        Yields:
            StreamMessage with bar data
        """
        if interval != "1m":
            raise ValueError("Alpaca WebSocket only supports 1-minute bars. Use '1m' interval.")

        symbol = symbol.upper()

        if not self._authenticated:
            await self.connect()

        stream_id = f"bars_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to bars
        subscribe_msg = {
            "action": "subscribe",
            "bars": [symbol]
        }
        await self.websocket.send_json(subscribe_msg)

        confirm = await self.websocket.receive_json()
        if confirm[0].get('T') == 'subscription':
            print(f"✓ Subscribed to {symbol} 1-min bars")

        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        messages = json.loads(msg.data)

                        for message in messages:
                            if message.get('T') == 'b':  # Bar message
                                stream_msg = StreamMessage(
                                    symbol=message.get('S', symbol),
                                    timestamp=datetime.fromisoformat(message.get('t', '').replace('Z', '+00:00')),
                                    open=float(message.get('o', 0)),
                                    high=float(message.get('h', 0)),
                                    low=float(message.get('l', 0)),
                                    close=float(message.get('c', 0)),
                                    volume=float(message.get('v', 0)),
                                    provider=self.name,
                                    stream_type="kline",
                                    raw_data=message
                                )

                                await self._notify_callbacks(stream_id, stream_msg)
                                yield stream_msg

                    except Exception as e:
                        print(f"Error parsing bar: {e}")
                        continue

        except asyncio.CancelledError:
            unsubscribe_msg = {
                "action": "unsubscribe",
                "bars": [symbol]
            }
            try:
                await self.websocket.send_json(unsubscribe_msg)
            except:
                pass
            raise

    async def subscribe_multiple(
        self,
        symbols: list[str],
        data_type: str = "trades",
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to multiple symbols at once.

        Args:
            symbols: List of stock tickers
            data_type: "trades", "quotes", or "bars"
            callback: Optional callback for each message

        Yields:
            StreamMessage from any subscribed symbol
        """
        if not self._authenticated:
            await self.connect()

        symbols = [s.upper() for s in symbols]

        # Subscribe to all symbols
        subscribe_msg = {
            "action": "subscribe",
            data_type: symbols
        }
        await self.websocket.send_json(subscribe_msg)

        confirm = await self.websocket.receive_json()
        if confirm[0].get('T') == 'subscription':
            print(f"✓ Subscribed to {len(symbols)} symbols for {data_type}")

        stream_id = f"multi_{len(symbols)}_{data_type}"
        if callback:
            self.add_callback(stream_id, callback)

        # Message type mapping
        type_map = {
            'trades': 't',
            'quotes': 'q',
            'bars': 'b'
        }
        expected_type = type_map.get(data_type, 't')

        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        messages = json.loads(msg.data)

                        for message in messages:
                            if message.get('T') == expected_type:
                                if data_type == 'trades':
                                    stream_msg = StreamMessage(
                                        symbol=message.get('S'),
                                        timestamp=datetime.fromisoformat(message.get('t', '').replace('Z', '+00:00')),
                                        price=float(message.get('p', 0)),
                                        volume=float(message.get('s', 0)),
                                        provider=self.name,
                                        stream_type="trade",
                                        raw_data=message
                                    )
                                elif data_type == 'quotes':
                                    stream_msg = StreamMessage(
                                        symbol=message.get('S'),
                                        timestamp=datetime.fromisoformat(message.get('t', '').replace('Z', '+00:00')),
                                        bid=float(message.get('bp', 0)),
                                        ask=float(message.get('ap', 0)),
                                        provider=self.name,
                                        stream_type="quote",
                                        raw_data=message
                                    )
                                else:  # bars
                                    stream_msg = StreamMessage(
                                        symbol=message.get('S'),
                                        timestamp=datetime.fromisoformat(message.get('t', '').replace('Z', '+00:00')),
                                        open=float(message.get('o', 0)),
                                        high=float(message.get('h', 0)),
                                        low=float(message.get('l', 0)),
                                        close=float(message.get('c', 0)),
                                        volume=float(message.get('v', 0)),
                                        provider=self.name,
                                        stream_type="kline",
                                        raw_data=message
                                    )

                                await self._notify_callbacks(stream_id, stream_msg)
                                yield stream_msg

                    except Exception as e:
                        print(f"Error parsing message: {e}")
                        continue

        except asyncio.CancelledError:
            unsubscribe_msg = {
                "action": "unsubscribe",
                data_type: symbols
            }
            try:
                await self.websocket.send_json(unsubscribe_msg)
            except:
                pass
            raise

    def is_connected(self) -> bool:
        """Check if WebSocket is connected and authenticated."""
        return self._connected and self._authenticated and self.websocket and not self.websocket.closed

    async def reconnect(self) -> bool:
        """Attempt to reconnect WebSocket."""
        await self.disconnect()
        return await self.connect()
