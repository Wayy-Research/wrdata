"""
Stream manager - coordinates multiple streaming providers.
"""

import asyncio
from typing import Optional, Callable, Dict, AsyncIterator, List
from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class StreamManager:
    """
    Manages multiple streaming providers and subscriptions.

    Handles:
    - Provider routing (which provider for which symbol)
    - Connection pooling
    - Automatic reconnection
    - Multi-symbol subscriptions
    """

    def __init__(self):
        self.providers: Dict[str, BaseStreamProvider] = {}
        self.active_subscriptions: Dict[str, asyncio.Task] = {}

    def add_provider(self, name: str, provider: BaseStreamProvider):
        """Add a streaming provider."""
        self.providers[name] = provider

    async def subscribe_ticker(
        self,
        symbol: str,
        provider: Optional[str] = None,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time ticker/trade stream.

        Args:
            symbol: Trading symbol
            provider: Provider name (auto-select if None)
            callback: Optional callback function

        Yields:
            StreamMessage objects
        """
        # Select provider
        provider_name = provider or self._select_provider(symbol)

        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available")

        stream_provider = self.providers[provider_name]

        # Ensure connected
        if not stream_provider.is_connected():
            await stream_provider.connect()

        # Subscribe
        async for message in stream_provider.subscribe_ticker(symbol, callback):
            yield message

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        provider: Optional[str] = None,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time kline/candlestick stream.

        Args:
            symbol: Trading symbol
            interval: Time interval
            provider: Provider name (auto-select if None)
            callback: Optional callback function

        Yields:
            StreamMessage objects with OHLCV data
        """
        # Select provider
        provider_name = provider or self._select_provider(symbol)

        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available")

        stream_provider = self.providers[provider_name]

        # Ensure connected
        if not stream_provider.is_connected():
            await stream_provider.connect()

        # Subscribe
        async for message in stream_provider.subscribe_kline(symbol, interval, callback):
            yield message

    async def subscribe_many(
        self,
        symbols: List[str],
        stream_type: str = "ticker",
        provider: Optional[str] = None,
        callback: Optional[Callable[[StreamMessage], None]] = None
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to multiple symbols simultaneously.

        Args:
            symbols: List of trading symbols
            stream_type: Type of stream ("ticker" or "kline")
            provider: Provider name (auto-select if None)
            callback: Optional callback function

        Yields:
            StreamMessage objects from all symbols
        """
        # Create tasks for each symbol
        tasks = []

        for symbol in symbols:
            if stream_type == "ticker":
                coro = self.subscribe_ticker(symbol, provider, callback)
            elif stream_type == "kline":
                coro = self.subscribe_kline(symbol, "1m", provider, callback)
            else:
                raise ValueError(f"Unknown stream type: {stream_type}")

            # Convert async generator to task
            task = asyncio.create_task(self._consume_stream(coro, callback))
            tasks.append(task)

        # Wait for all tasks
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            # Clean up tasks
            for task in tasks:
                task.cancel()

    async def _consume_stream(
        self,
        stream: AsyncIterator[StreamMessage],
        callback: Optional[Callable]
    ):
        """Helper to consume an async stream."""
        async for message in stream:
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)

    def _select_provider(self, symbol: str) -> str:
        """
        Auto-select best provider for a symbol.

        Logic:
        - Crypto pairs (USDT, BUSD, etc.) -> binance_stream
        - Otherwise -> first available provider
        """
        symbol_upper = symbol.upper()

        # Crypto detection
        if any(pair in symbol_upper for pair in ['USDT', 'BUSD', 'BTC', 'ETH', 'BNB']):
            if 'binance_stream' in self.providers:
                return 'binance_stream'

        # Fallback to first available
        if self.providers:
            return list(self.providers.keys())[0]

        raise ValueError("No streaming providers available")

    async def disconnect_all(self):
        """Disconnect all providers."""
        for provider in self.providers.values():
            await provider.disconnect()

    def get_active_streams(self) -> List[str]:
        """Get list of active stream IDs."""
        active = []
        for provider in self.providers.values():
            active.extend(provider.active_streams.keys())
        return active
