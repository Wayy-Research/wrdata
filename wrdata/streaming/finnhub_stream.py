"""
Finnhub WebSocket streaming provider.

Provides real-time stock quotes and trades via WebSocket.
FREE on Finnhub's free tier - this is awesome!

Docs: https://finnhub.io/docs/api/websocket-trades
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator
from datetime import datetime
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class FinnhubStreamProvider(BaseStreamProvider):
    """
    Finnhub WebSocket streaming provider.

    FREE real-time streaming included in free tier!

    Channels:
    - Trades: Real-time trade data
    - Quote updates automatically included
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="finnhub_stream", api_key=api_key)

        if not api_key:
            raise ValueError("Finnhub API key required for streaming")

        self.ws_url = f"wss://ws.finnhub.io?token={api_key}"
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

    async def connect(self) -> bool:
        """Establish WebSocket connection."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()

            self.websocket = await self.session.ws_connect(self.ws_url)
            self._connected = True
            self._reconnect_attempts = 0
            print(f"✓ Connected to Finnhub WebSocket")
            return True

        except Exception as e:
            print(f"Finnhub stream connection error: {e}")
            self._connected = False
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
        Subscribe to real-time trade data.

        Args:
            symbol: Stock ticker (e.g., "AAPL", "MSFT")
            callback: Optional callback for each message

        Yields:
            StreamMessage with trade data
        """
        symbol = symbol.upper()

        # Connect if not already connected
        if not self._connected:
            await self.connect()

        stream_id = f"ticker_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to symbol
        subscribe_msg = {
            "type": "subscribe",
            "symbol": symbol
        }

        try:
            await self.websocket.send_json(subscribe_msg)
            print(f"✓ Subscribed to {symbol} on Finnhub")

            # Listen for messages
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)

                        # Finnhub sends trade data
                        if data.get('type') == 'trade':
                            for trade in data.get('data', []):
                                stream_msg = StreamMessage(
                                    symbol=trade.get('s', symbol),
                                    timestamp=datetime.fromtimestamp(trade.get('t', 0) / 1000),
                                    price=float(trade.get('p', 0)),
                                    volume=float(trade.get('v', 0)),
                                    provider=self.name,
                                    stream_type="trade",
                                    raw_data=trade
                                )

                                await self._notify_callbacks(stream_id, stream_msg)
                                yield stream_msg

                        # Ping/pong for connection keep-alive
                        elif data.get('type') == 'ping':
                            await self.websocket.send_json({"type": "pong"})

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error parsing Finnhub message: {e}")
                        continue

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"WebSocket error: {self.websocket.exception()}")
                    break

        except asyncio.CancelledError:
            # Unsubscribe when cancelled
            unsubscribe_msg = {
                "type": "unsubscribe",
                "symbol": symbol
            }
            try:
                await self.websocket.send_json(unsubscribe_msg)
            except:
                pass
            raise

        except Exception as e:
            print(f"Finnhub stream error: {e}")
            self._connected = False

            # Attempt reconnection
            if self._reconnect_attempts < self._max_reconnect_attempts:
                wait_time = min(2 ** self._reconnect_attempts, 60)
                print(f"Reconnecting in {wait_time}s...")
                await asyncio.sleep(wait_time)
                self._reconnect_attempts += 1
                await self.reconnect()

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Finnhub doesn't provide native kline/candle streams.
        You'll need to aggregate trades yourself or use REST API.
        """
        raise NotImplementedError(
            "Finnhub WebSocket does not provide kline streams. "
            "Use subscribe_ticker and aggregate trades, or use REST API for candles."
        )

    async def subscribe_multiple(
        self,
        symbols: list[str],
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to multiple symbols at once.

        Finnhub allows multiple subscriptions on one WebSocket connection.
        """
        # Connect if not already connected
        if not self._connected:
            await self.connect()

        # Subscribe to all symbols
        for symbol in symbols:
            symbol = symbol.upper()
            subscribe_msg = {
                "type": "subscribe",
                "symbol": symbol
            }
            await self.websocket.send_json(subscribe_msg)
            print(f"✓ Subscribed to {symbol}")

        stream_id = f"multi_{len(symbols)}_symbols"
        if callback:
            self.add_callback(stream_id, callback)

        # Listen for messages from any symbol
        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)

                        if data.get('type') == 'trade':
                            for trade in data.get('data', []):
                                stream_msg = StreamMessage(
                                    symbol=trade.get('s'),
                                    timestamp=datetime.fromtimestamp(trade.get('t', 0) / 1000),
                                    price=float(trade.get('p', 0)),
                                    volume=float(trade.get('v', 0)),
                                    provider=self.name,
                                    stream_type="trade",
                                    raw_data=trade
                                )

                                await self._notify_callbacks(stream_id, stream_msg)
                                yield stream_msg

                        elif data.get('type') == 'ping':
                            await self.websocket.send_json({"type": "pong"})

                    except Exception as e:
                        print(f"Error parsing message: {e}")
                        continue

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"WebSocket error: {self.websocket.exception()}")
                    break

        except asyncio.CancelledError:
            # Unsubscribe all symbols
            for symbol in symbols:
                unsubscribe_msg = {
                    "type": "unsubscribe",
                    "symbol": symbol.upper()
                }
                try:
                    await self.websocket.send_json(unsubscribe_msg)
                except:
                    pass
            raise

    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self.websocket and not self.websocket.closed

    async def reconnect(self) -> bool:
        """Attempt to reconnect WebSocket."""
        await self.disconnect()
        return await self.connect()
