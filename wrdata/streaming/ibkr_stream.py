"""
Interactive Brokers streaming provider.

Provides real-time market data via TWS API.
Requires TWS or IB Gateway running locally.

Note: Real-time data requires market data subscriptions from IBKR.
Delayed data is free.
"""

import asyncio
from typing import Optional, Callable, AsyncIterator
from datetime import datetime
from ib_insync import IB, Stock, util

from wrdata.streaming.base import BaseStreamProvider, StreamMessage


class IBKRStreamProvider(BaseStreamProvider):
    """
    Interactive Brokers streaming provider.

    Real-time streaming via TWS API.
    Supports stocks, options, futures, forex globally.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,  # 7497 = paper, 7496 = live
        client_id: int = 2,  # Different from provider client_id
    ):
        super().__init__(name="ibkr_stream")

        self.host = host
        self.port = port
        self.client_id = client_id

        self.ib = IB()
        self._connected = False

    async def connect(self) -> bool:
        """Establish connection to TWS/Gateway."""
        try:
            if not self._connected:
                await self.ib.connectAsync(
                    self.host,
                    self.port,
                    clientId=self.client_id
                )
                self._connected = True
                print(f"✓ Connected to IBKR stream on {self.host}:{self.port}")
            return True

        except Exception as e:
            print(f"IBKR stream connection error: {e}")
            print("Make sure TWS or IB Gateway is running")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close connection."""
        self._connected = False

        # Close all active streams
        for stream_id, task in list(self.active_streams.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self.ib.isConnected():
            self.ib.disconnect()

    async def subscribe_ticker(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time tick data.

        Args:
            symbol: Stock ticker
            exchange: Optional exchange (default: SMART)
            currency: Optional currency (default: USD)
            callback: Optional callback for each message

        Yields:
            StreamMessage with tick data
        """
        symbol = symbol.upper()
        exchange = kwargs.get('exchange', 'SMART')
        currency = kwargs.get('currency', 'USD')

        # Connect if not already connected
        if not self._connected:
            await self.connect()

        stream_id = f"ticker_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        try:
            # Create contract
            contract = Stock(symbol, exchange, currency)
            await self.ib.qualifyContractsAsync(contract)

            # Request real-time bars (5-second bars)
            bars = self.ib.reqRealTimeBars(
                contract,
                barSize=5,  # 5 seconds
                whatToShow='TRADES',
                useRTH=False  # Include extended hours
            )

            print(f"✓ Subscribed to {symbol} real-time bars")

            # Stream bars
            async for bar in bars:
                stream_msg = StreamMessage(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(bar.time),
                    open=float(bar.open_),
                    high=float(bar.high),
                    low=float(bar.low),
                    close=float(bar.close),
                    volume=float(bar.volume),
                    provider=self.name,
                    stream_type="bar",
                    raw_data={
                        'time': bar.time,
                        'open': bar.open_,
                        'high': bar.high,
                        'low': bar.low,
                        'close': bar.close,
                        'volume': bar.volume,
                        'wap': bar.wap,
                        'count': bar.count
                    }
                )

                await self._notify_callbacks(stream_id, stream_msg)
                yield stream_msg

        except asyncio.CancelledError:
            # Cancel subscription
            self.ib.cancelRealTimeBars(bars)
            raise

        except Exception as e:
            print(f"IBKR stream error: {e}")

    async def subscribe_market_data(
        self,
        symbol: str,
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time market data (tick-by-tick).

        Args:
            symbol: Stock ticker
            exchange: Optional exchange (default: SMART)
            currency: Optional currency (default: USD)
            callback: Optional callback for each message

        Yields:
            StreamMessage with market data updates
        """
        symbol = symbol.upper()
        exchange = kwargs.get('exchange', 'SMART')
        currency = kwargs.get('currency', 'USD')

        if not self._connected:
            await self.connect()

        stream_id = f"market_{symbol}"
        if callback:
            self.add_callback(stream_id, callback)

        try:
            # Create contract
            contract = Stock(symbol, exchange, currency)
            await self.ib.qualifyContractsAsync(contract)

            # Request market data
            ticker = self.ib.reqMktData(contract, '', False, False)

            print(f"✓ Subscribed to {symbol} market data")

            # Stream ticker updates
            while self._connected:
                await ticker.updateEvent

                # Only send if we have price data
                if ticker.last and ticker.last > 0:
                    stream_msg = StreamMessage(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        price=float(ticker.last),
                        bid=float(ticker.bid) if ticker.bid else None,
                        ask=float(ticker.ask) if ticker.ask else None,
                        volume=float(ticker.volume) if ticker.volume else 0,
                        provider=self.name,
                        stream_type="quote",
                        raw_data={
                            'last': ticker.last,
                            'bid': ticker.bid,
                            'ask': ticker.ask,
                            'bidSize': ticker.bidSize,
                            'askSize': ticker.askSize,
                            'volume': ticker.volume,
                            'high': ticker.high,
                            'low': ticker.low,
                            'close': ticker.close,
                        }
                    )

                    await self._notify_callbacks(stream_id, stream_msg)
                    yield stream_msg

        except asyncio.CancelledError:
            # Cancel market data
            self.ib.cancelMktData(contract)
            raise

        except Exception as e:
            print(f"IBKR market data error: {e}")

    async def subscribe_kline(
        self,
        symbol: str,
        interval: str = "1m",
        callback: Optional[Callable[[StreamMessage], None]] = None,
        **kwargs
    ) -> AsyncIterator[StreamMessage]:
        """
        Subscribe to real-time kline/bar data.

        IBKR provides 5-second bars. For other intervals, aggregate them.

        Args:
            symbol: Stock ticker
            interval: Time interval (IBKR supports 5-second bars)
            callback: Optional callback for each message

        Yields:
            StreamMessage with bar data
        """
        # IBKR only supports 5-second bars in real-time
        # For now, just use subscribe_ticker which provides bars
        async for msg in self.subscribe_ticker(symbol, callback, **kwargs):
            yield msg

    def is_connected(self) -> bool:
        """Check if connected to TWS/Gateway."""
        return self._connected and self.ib.isConnected()

    async def reconnect(self) -> bool:
        """Attempt to reconnect."""
        await self.disconnect()
        return await self.connect()
