"""
Kraken WebSocket streaming provider.

FREE real-time cryptocurrency streaming from Kraken.
No API key required for public feeds!

WebSocket Docs: https://docs.kraken.com/websockets/
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator
from datetime import datetime
import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class KrakenStreamProvider(BaseStreamProvider):
    """
    Kraken WebSocket streaming provider.

    FREE real-time streaming for:
    - Trades
    - OHLC (candlesticks)
    - Ticker
    - Spread
    - Order book

    No API key required!
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="kraken_stream", api_key=api_key)

        self.ws_url = "wss://ws.kraken.com"
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> bool:
        """Establish WebSocket connection to Kraken."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            self.websocket = await self.session.ws_connect(self.ws_url)
            print(f"✓ Connected to Kraken WebSocket")
            return True

        except Exception as e:
            print(f"Kraken connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
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
        """Subscribe to real-time trades."""
        if not self.websocket:
            await self.connect()

        stream_id = f"trades_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        try:
            # Subscribe to trades
            subscribe_msg = {
                "event": "subscribe",
                "pair": [symbol],
                "subscription": {"name": "trade"}
            }
            await self.websocket.send_json(subscribe_msg)
            print(f"✓ Subscribed to {symbol} trades")

            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    # Skip system messages
                    if isinstance(data, dict):
                        continue

                    # Trade data format: [channelID, [trades], channelName, pair]
                    if len(data) >= 4 and data[2] == 'trade':
                        trades = data[1]
                        pair = data[3]

                        for trade in trades:
                            stream_msg = StreamMessage(
                                symbol=pair,
                                timestamp=datetime.fromtimestamp(float(trade[2])),
                                price=float(trade[0]),
                                volume=float(trade[1]),
                                provider=self.name,
                                stream_type="trade",
                                raw_data={'side': trade[3], 'type': trade[4]}
                            )

                            await self._notify_callbacks(stream_id, stream_msg)
                            yield stream_msg

        except asyncio.CancelledError:
            unsubscribe_msg = {
                "event": "unsubscribe",
                "pair": [symbol],
                "subscription": {"name": "trade"}
            }
            await self.websocket.send_json(unsubscribe_msg)
            raise

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """Subscribe to ticker updates."""
        if not self.websocket:
            await self.connect()

        stream_id = f"ticker_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        try:
            subscribe_msg = {
                "event": "subscribe",
                "pair": [symbol],
                "subscription": {"name": "ticker"}
            }
            await self.websocket.send_json(subscribe_msg)
            print(f"✓ Subscribed to {symbol} ticker")

            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    if isinstance(data, dict):
                        continue

                    if len(data) >= 4 and data[2] == 'ticker':
                        ticker = data[1]
                        pair = data[3]

                        stream_msg = StreamMessage(
                            symbol=pair,
                            timestamp=datetime.now(),
                            bid=float(ticker['b'][0]),
                            ask=float(ticker['a'][0]),
                            price=float(ticker['c'][0]),
                            volume=float(ticker['v'][1]),
                            provider=self.name,
                            stream_type="ticker",
                            raw_data=ticker
                        )

                        await self._notify_callbacks(stream_id, stream_msg)
                        yield stream_msg

        except asyncio.CancelledError:
            raise

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """Subscribe to OHLC (kline) data."""
        if not self.websocket:
            await self.connect()

        stream_id = f"ohlc_{symbol}_{interval}"
        if callback:
            self.add_callback(stream_id, callback)

        # Map intervals
        interval_map = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
        kraken_interval = interval_map.get(interval, 1)

        try:
            subscribe_msg = {
                "event": "subscribe",
                "pair": [symbol],
                "subscription": {"name": "ohlc", "interval": kraken_interval}
            }
            await self.websocket.send_json(subscribe_msg)
            print(f"✓ Subscribed to {symbol} {interval} candles")

            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    if isinstance(data, dict):
                        continue

                    if len(data) >= 4 and data[2].startswith('ohlc'):
                        ohlc = data[1]
                        pair = data[3]

                        stream_msg = StreamMessage(
                            symbol=pair,
                            timestamp=datetime.fromtimestamp(float(ohlc[1])),
                            open=float(ohlc[2]),
                            high=float(ohlc[3]),
                            low=float(ohlc[4]),
                            close=float(ohlc[5]),
                            volume=float(ohlc[7]),
                            provider=self.name,
                            stream_type="kline",
                            raw_data={'vwap': ohlc[6], 'count': ohlc[8]}
                        )

                        await self._notify_callbacks(stream_id, stream_msg)
                        yield stream_msg

        except asyncio.CancelledError:
            raise

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.websocket and not self.websocket.closed

    async def reconnect(self) -> bool:
        """Attempt to reconnect."""
        await self.disconnect()
        return await self.connect()
