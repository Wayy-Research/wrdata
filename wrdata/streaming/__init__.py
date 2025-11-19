"""
Streaming providers for real-time market data.

Providers are imported lazily to avoid dependency issues.
"""

from wrdata.streaming.base import BaseStreamProvider, StreamMessage
from wrdata.streaming.manager import StreamManager

__all__ = [
    "BaseStreamProvider",
    "StreamMessage",
    "StreamManager",
]
