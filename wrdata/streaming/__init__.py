"""
Real-time streaming infrastructure for wrdata.

Provides WebSocket-based real-time data streaming from multiple providers.
"""

from wrdata.streaming.base import BaseStreamProvider, StreamMessage
from wrdata.streaming.manager import StreamManager
from wrdata.streaming.ibkr_stream import IBKRStreamProvider
from wrdata.streaming.alpaca_stream import AlpacaStreamProvider
from wrdata.streaming.polygon_stream import PolygonStreamProvider
from wrdata.streaming.kraken_stream import KrakenStreamProvider

__all__ = [
    "BaseStreamProvider",
    "StreamMessage",
    "StreamManager",
    "IBKRStreamProvider",
    "AlpacaStreamProvider",
    "PolygonStreamProvider",
    "KrakenStreamProvider",
]
