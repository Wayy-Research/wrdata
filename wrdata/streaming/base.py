"""
Base classes for real-time streaming providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any, AsyncIterator
from datetime import datetime
from dataclasses import dataclass
import asyncio


@dataclass
class StreamMessage:
    """
    Standardized message format for real-time data.

    All providers normalize their data to this format.
    """
    symbol: str
    timestamp: datetime
    price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None

    # OHLCV for kline/candle streams
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None

    # Order book for depth streams
    bids: Optional[list] = None
    asks: Optional[list] = None

    # Additional metadata
    provider: Optional[str] = None
    stream_type: Optional[str] = None  # "trade", "ticker", "kline", "depth"
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'bid': self.bid,
            'ask': self.ask,
            'volume': self.volume,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'provider': self.provider,
            'stream_type': self.stream_type,
        }


class BaseStreamProvider(ABC):
    """
    Base class for all streaming data providers.

    Each provider (Binance, Polygon, etc.) implements this interface.
    """

    def __init__(self, name: str, api_key: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self.active_streams: Dict[str, asyncio.Task] = {}
        self._callbacks: Dict[str, list] = {}

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.

        Returns:
            True if connected successfully
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        pass

    @abstractmethod
    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time ticker/trade stream.

        Args:
            symbol: Trading symbol
            callback: Optional callback function

        Yields:
            StreamMessage objects
        """
        pass

    @abstractmethod
    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time kline/candlestick stream.

        Args:
            symbol: Trading symbol
            interval: Time interval (1m, 5m, 1h, etc.)
            callback: Optional callback function

        Yields:
            StreamMessage objects with OHLCV data
        """
        pass

    async def subscribe_depth(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to order book depth stream.

        Not all providers support this - default implementation raises NotImplementedError.

        Args:
            symbol: Trading symbol
            callback: Optional callback function

        Yields:
            StreamMessage objects with order book data
        """
        raise NotImplementedError(f"{self.name} does not support order book streaming")

    def add_callback(self, stream_id: str, callback: Callable):
        """Add a callback for a specific stream."""
        if stream_id not in self._callbacks:
            self._callbacks[stream_id] = []
        self._callbacks[stream_id].append(callback)

    def remove_callback(self, stream_id: str, callback: Callable):
        """Remove a callback for a specific stream."""
        if stream_id in self._callbacks:
            self._callbacks[stream_id].remove(callback)

    async def _notify_callbacks(self, stream_id: str, message: StreamMessage):
        """Notify all callbacks for a stream."""
        if stream_id in self._callbacks:
            for callback in self._callbacks[stream_id]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        pass

    @abstractmethod
    async def reconnect(self) -> bool:
        """Attempt to reconnect WebSocket."""
        pass
