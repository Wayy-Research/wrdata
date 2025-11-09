"""
Polygon.io WebSocket streaming provider.

Real-time market data streaming from Polygon.io.
Requires paid plan for WebSocket access.

WebSocket Docs: https://polygon.io/docs/stocks/ws_getting-started
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator
from datetime import datetime
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class PolygonStreamProvider(BaseStreamProvider):
    """
    Polygon.io WebSocket streaming provider.

    Real-time streaming for:
    - Stock trades
    - Stock quotes (bid/ask)
    - Stock aggregates (bars)
    - Options trades
    - Forex quotes
    - Crypto trades

    Note: WebSocket requires paid Polygon.io plan
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="polygon_stream", api_key=api_key)

        if not api_key:
            raise ValueError("Polygon.io API key required for streaming")

        # WebSocket endpoints
        self.ws_url = "wss://socket.polygon.io/stocks"
        self.ws_crypto_url = "wss://socket.polygon.io/crypto"
        self.ws_forex_url = "wss://socket.polygon.io/forex"

        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False

    async def connect(self) -> bool:
        """Establish WebSocket connection to Polygon.io."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Connect to stocks WebSocket
            self.websocket = await self.session.ws_connect(self.ws_url)

            print(f"✓ Connected to Polygon.io WebSocket")

            # Authenticate
            auth_message = {
                "action": "auth",
                "params": self.api_key
            }
            await self.websocket.send_json(auth_message)

            # Wait for auth response
            response = await self.websocket.receive_json()

            if response[0].get('status') == 'auth_success':
                self._authenticated = True
                print("✓ Authenticated with Polygon.io")
                return True
            else:
                error = response[0].get('message', 'Authentication failed')
                print(f"✗ Polygon authentication failed: {error}")
                return False

        except Exception as e:
            print(f"Polygon connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
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

        if self.session:
            await self.session.close()
            self.session = None

    async def subscribe_trades(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time trades.

        Args:
            symbol: Stock ticker (e.g., "AAPL")
            callback: Optional callback for each message

        Yields:
            StreamMessage with trade data
        """
        symbol = symbol.upper()

        if not self._authenticated:
            await self.connect()

        stream_id = f"trades_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        try:
            # Subscribe to trades
            subscribe_msg = {
                "action": "subscribe",
                "params": f"T.{symbol}"  # T = Trades
            }
            await self.websocket.send_json(subscribe_msg)

            print(f"✓ Subscribed to {symbol} trades")

            # Stream messages
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    for event in data:
                        # Check if it's a trade event
                        if event.get('ev') == 'T':
                            stream_msg = StreamMessage(
                                symbol=event.get('sym'),
                                timestamp=datetime.fromtimestamp(event.get('t', 0) / 1000),
                                price=float(event.get('p', 0)),
                                volume=float(event.get('s', 0)),  # Size
                                provider=self.name,
                                stream_type="trade",
                                raw_data={
                                    'exchange': event.get('x'),
                                    'conditions': event.get('c', []),
                                    'id': event.get('i'),
                                    'tape': event.get('z'),
                                }
                            )

                            await self._notify_callbacks(stream_id, stream_msg)
                            yield stream_msg

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"WebSocket error: {msg.data}")
                    break

        except asyncio.CancelledError:
            # Unsubscribe
            unsubscribe_msg = {
                "action": "unsubscribe",
                "params": f"T.{symbol}"
            }
            await self.websocket.send_json(unsubscribe_msg)
            raise

        except Exception as e:
            print(f"Polygon stream error: {e}")

    async def subscribe_quotes(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time quotes (bid/ask).

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

        try:
            # Subscribe to quotes
            subscribe_msg = {
                "action": "subscribe",
                "params": f"Q.{symbol}"  # Q = Quotes
            }
            await self.websocket.send_json(subscribe_msg)

            print(f"✓ Subscribed to {symbol} quotes")

            # Stream messages
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    for event in data:
                        # Check if it's a quote event
                        if event.get('ev') == 'Q':
                            stream_msg = StreamMessage(
                                symbol=event.get('sym'),
                                timestamp=datetime.fromtimestamp(event.get('t', 0) / 1000),
                                bid=float(event.get('bp', 0)),  # Bid price
                                ask=float(event.get('ap', 0)),  # Ask price
                                provider=self.name,
                                stream_type="quote",
                                raw_data={
                                    'bid_size': event.get('bs'),
                                    'ask_size': event.get('as'),
                                    'bid_exchange': event.get('bx'),
                                    'ask_exchange': event.get('ax'),
                                    'conditions': event.get('c', []),
                                }
                            )

                            await self._notify_callbacks(stream_id, stream_msg)
                            yield stream_msg

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"WebSocket error: {msg.data}")
                    break

        except asyncio.CancelledError:
            # Unsubscribe
            unsubscribe_msg = {
                "action": "unsubscribe",
                "params": f"Q.{symbol}"
            }
            await self.websocket.send_json(unsubscribe_msg)
            raise

        except Exception as e:
            print(f"Polygon stream error: {e}")

    async def subscribe_aggregates(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time aggregates (bars).

        Args:
            symbol: Stock ticker
            interval: Time interval - "1s" (second) or "1m" (minute)
            callback: Optional callback for each message

        Yields:
            StreamMessage with aggregate data
        """
        symbol = symbol.upper()

        if not self._authenticated:
            await self.connect()

        stream_id = f"aggregates_{symbol}_{interval}"
        if callback:
            self.add_callback(stream_id, callback)

        # Map interval to Polygon channel
        interval_map = {
            "1s": "A",   # Second aggregates
            "1m": "AM",  # Minute aggregates
        }

        channel = interval_map.get(interval, "AM")

        try:
            # Subscribe to aggregates
            subscribe_msg = {
                "action": "subscribe",
                "params": f"{channel}.{symbol}"
            }
            await self.websocket.send_json(subscribe_msg)

            print(f"✓ Subscribed to {symbol} {interval} aggregates")

            # Stream messages
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    for event in data:
                        # Check if it's an aggregate event
                        if event.get('ev') in ['A', 'AM']:
                            stream_msg = StreamMessage(
                                symbol=event.get('sym'),
                                timestamp=datetime.fromtimestamp(event.get('s', 0) / 1000),
                                open=float(event.get('o', 0)),
                                high=float(event.get('h', 0)),
                                low=float(event.get('l', 0)),
                                close=float(event.get('c', 0)),
                                volume=float(event.get('v', 0)),
                                provider=self.name,
                                stream_type="bar",
                                raw_data={
                                    'vwap': event.get('vw'),  # Volume weighted average
                                    'avg_price': event.get('a'),
                                    'start_time': event.get('s'),
                                    'end_time': event.get('e'),
                                }
                            )

                            await self._notify_callbacks(stream_id, stream_msg)
                            yield stream_msg

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"WebSocket error: {msg.data}")
                    break

        except asyncio.CancelledError:
            # Unsubscribe
            unsubscribe_msg = {
                "action": "unsubscribe",
                "params": f"{channel}.{symbol}"
            }
            await self.websocket.send_json(unsubscribe_msg)
            raise

        except Exception as e:
            print(f"Polygon stream error: {e}")

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to ticker updates (aggregates).

        This is an alias for subscribe_aggregates for consistency with other providers.
        """
        async for msg in self.subscribe_aggregates(symbol, "1m", callback, **kwargs):
            yield msg

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to kline/candlestick data.

        This is an alias for subscribe_aggregates for consistency with other providers.
        """
        async for msg in self.subscribe_aggregates(symbol, interval, callback, **kwargs):
            yield msg

    def is_connected(self) -> bool:
        """Check if connected and authenticated."""
        return self._authenticated and self.websocket and not self.websocket.closed

    async def reconnect(self) -> bool:
        """Attempt to reconnect."""
        await self.disconnect()
        return await self.connect()
