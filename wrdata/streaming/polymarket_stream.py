"""
Polymarket CLOB WebSocket streaming provider.

Provides real-time market data from Polymarket's CLOB via WebSocket.
No API key required for public market data streams.

WebSocket URL: wss://ws-subscriptions-clob.polymarket.com/ws/market

Events:
- price_change: Price updates for a token
- last_trade_price: Last trade price updates
- book: Full order book snapshots
"""

import asyncio
import json
from typing import Optional, Callable, AsyncIterator, Dict, List
from datetime import datetime, timezone

import aiohttp

from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class PolymarketStreamProvider(BaseStreamProvider):
    """
    Polymarket CLOB WebSocket streaming provider.

    Streams real-time price changes, last trade prices, and order book
    snapshots for prediction market tokens.

    No authentication required.
    """

    WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    def __init__(self) -> None:
        super().__init__(name="polymarket_stream")
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

    async def connect(self) -> bool:
        """Establish aiohttp session (connection is per-subscription)."""
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession()
            return True
        except Exception as e:
            print(f"Polymarket stream connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Close WebSocket and session."""
        self._connected = False

        for task in list(self.active_streams.values()):
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
        callback: Optional[Callable[[StreamMessage], None]] = None,
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to price_change events for a token or market.

        Args:
            symbol: A condition_id or clob_token_id.
            callback: Optional callback for each message.

        Yields:
            StreamMessage with price updates.
        """
        stream_id = f"ticker_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        # Subscribe to price_change for this asset
        assets = [{"asset_id": symbol}]
        subscribe_msg = {
            "type": "market",
            "assets_ids": assets,
        }

        async for message in self._stream_ws(subscribe_msg):
            try:
                event_type = message.get("event_type")
                if event_type not in ("price_change", "last_trade_price"):
                    continue

                raw_price = message.get("price")
                price = float(raw_price) if raw_price is not None else None

                ts_str = message.get("timestamp")
                if ts_str:
                    try:
                        timestamp = datetime.fromtimestamp(
                            float(ts_str), tz=timezone.utc
                        )
                    except (ValueError, TypeError):
                        timestamp = datetime.now(timezone.utc)
                else:
                    timestamp = datetime.now(timezone.utc)

                stream_msg = StreamMessage(
                    symbol=message.get("asset_id", symbol),
                    timestamp=timestamp,
                    price=price,
                    provider=self.name,
                    stream_type="ticker",
                    raw_data=message,
                )

                await self._notify_callbacks(stream_id, stream_msg)
                yield stream_msg

            except Exception as e:
                print(f"Error parsing Polymarket ticker message: {e}")
                continue

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None,
    ) -> AsyncIterator[StreamMessage]:
        """
        Polymarket does not have native kline streams.

        Aggregates price_change events into candles.

        Args:
            symbol: Token or condition ID.
            interval: Candle interval (e.g., "1m").
            callback: Optional callback.

        Yields:
            StreamMessage with OHLCV data.
        """
        stream_id = f"kline_{symbol}_{interval}"
        if callback:
            self.add_callback(stream_id, callback)

        current_candle: Optional[Dict] = None
        interval_seconds = self._interval_to_seconds(interval)

        async for msg in self.subscribe_ticker(symbol):
            if msg.price is None:
                continue

            price = msg.price
            epoch = msg.timestamp.timestamp()
            candle_epoch = epoch - (epoch % interval_seconds)
            candle_start = datetime.fromtimestamp(candle_epoch, tz=timezone.utc)

            if current_candle is None or candle_start != current_candle["start"]:
                if current_candle:
                    stream_msg = StreamMessage(
                        symbol=symbol,
                        timestamp=current_candle["start"],
                        open=current_candle["open"],
                        high=current_candle["high"],
                        low=current_candle["low"],
                        close=current_candle["close"],
                        volume=current_candle["volume"],
                        provider=self.name,
                        stream_type="kline",
                    )
                    await self._notify_callbacks(stream_id, stream_msg)
                    yield stream_msg

                current_candle = {
                    "start": candle_start,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": 0.0,
                }
            else:
                current_candle["high"] = max(current_candle["high"], price)
                current_candle["low"] = min(current_candle["low"], price)
                current_candle["close"] = price

    async def subscribe_book(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to order book snapshots for a token.

        Args:
            symbol: clob_token_id.
            callback: Optional callback.

        Yields:
            StreamMessage with bids/asks.
        """
        stream_id = f"book_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        assets = [{"asset_id": symbol}]
        subscribe_msg = {
            "type": "market",
            "assets_ids": assets,
        }

        async for message in self._stream_ws(subscribe_msg):
            try:
                if message.get("event_type") != "book":
                    continue

                bids_raw = message.get("bids", [])
                asks_raw = message.get("asks", [])

                bids = [
                    [float(b.get("price", 0)), float(b.get("size", 0))]
                    for b in bids_raw
                ]
                asks = [
                    [float(a.get("price", 0)), float(a.get("size", 0))]
                    for a in asks_raw
                ]

                best_bid = bids[0][0] if bids else None
                best_ask = asks[0][0] if asks else None
                mid = (
                    (best_bid + best_ask) / 2
                    if (best_bid is not None and best_ask is not None)
                    else None
                )

                stream_msg = StreamMessage(
                    symbol=message.get("asset_id", symbol),
                    timestamp=datetime.now(timezone.utc),
                    price=mid,
                    bid=best_bid,
                    ask=best_ask,
                    bids=bids,
                    asks=asks,
                    provider=self.name,
                    stream_type="depth",
                    raw_data=message,
                )

                await self._notify_callbacks(stream_id, stream_msg)
                yield stream_msg

            except Exception as e:
                print(f"Error parsing Polymarket book message: {e}")
                continue

    def is_connected(self) -> bool:
        return self._connected

    async def reconnect(self) -> bool:
        await self.disconnect()
        return await self.connect()

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    @staticmethod
    def _interval_to_seconds(interval: str) -> int:
        interval_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }
        return interval_map.get(interval, 60)

    async def _stream_ws(self, subscribe_message: dict) -> AsyncIterator[dict]:
        """
        Connect to Polymarket WebSocket and yield parsed messages.

        Handles reconnection with exponential backoff.
        """
        while True:
            try:
                if self.session is None:
                    self.session = aiohttp.ClientSession()

                async with self.session.ws_connect(
                    self.WS_URL, max_msg_size=5 * 1024 * 1024
                ) as ws:
                    self.websocket = ws
                    self._connected = True
                    self._reconnect_attempts = 0

                    await ws.send_json(subscribe_message)
                    print(
                        f"Subscribed to Polymarket stream: "
                        f"{subscribe_message.get('assets_ids', [])}"
                    )

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            # Server may send arrays of events
                            if isinstance(data, list):
                                for item in data:
                                    yield item
                            else:
                                yield data

                        elif msg.type in (
                            aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR,
                        ):
                            print("Polymarket stream closed/error")
                            break

            except Exception as e:
                print(f"Polymarket stream error: {e}")
                self._connected = False

                if self._reconnect_attempts < self._max_reconnect_attempts:
                    wait = min(2**self._reconnect_attempts, 60)
                    print(f"Reconnecting in {wait}s...")
                    await asyncio.sleep(wait)
                    self._reconnect_attempts += 1
                else:
                    print("Max reconnection attempts reached")
                    break
