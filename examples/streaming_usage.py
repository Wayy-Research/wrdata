"""
Real-time streaming examples for wrdata.

Shows how to stream live market data using WebSockets.
"""

import asyncio
from wrdata import DataStream

# ============================================================================
# EXAMPLE 1: Basic price streaming (async iterator)
# ============================================================================
print("=" * 60)
print("EXAMPLE 1: Stream live Bitcoin prices")
print("=" * 60)


async def stream_btc_prices():
    """Stream live BTC prices for 10 seconds."""
    stream = DataStream()

    print("\nStreaming BTCUSDT prices...")
    count = 0
    max_ticks = 10

    async for tick in stream.stream("BTCUSDT", stream_type="ticker"):
        print(f"  BTC: ${tick.price:.2f} (Volume: {tick.volume:.4f})")
        count += 1
        if count >= max_ticks:
            break

    await stream.disconnect_streams()
    print("Stream closed.\n")


# Run example 1
asyncio.run(stream_btc_prices())


# ============================================================================
# EXAMPLE 2: Stream 1-minute candles
# ============================================================================
print("=" * 60)
print("EXAMPLE 2: Stream 1-minute candles")
print("=" * 60)


async def stream_eth_candles():
    """Stream live ETH 1-minute candles."""
    stream = DataStream()

    print("\nStreaming ETHUSDT 1-minute candles...")
    count = 0
    max_candles = 3

    async for candle in stream.stream("ETHUSDT", stream_type="kline", interval="1m"):
        print(f"  ETH Candle:")
        print(f"    Open:  ${candle.open:.2f}")
        print(f"    High:  ${candle.high:.2f}")
        print(f"    Low:   ${candle.low:.2f}")
        print(f"    Close: ${candle.close:.2f}")
        print(f"    Volume: {candle.volume:.2f}")
        print()
        count += 1
        if count >= max_candles:
            break

    await stream.disconnect_streams()
    print("Stream closed.\n")


# Run example 2
asyncio.run(stream_eth_candles())


# ============================================================================
# EXAMPLE 3: Callback-based streaming (simpler for some use cases)
# ============================================================================
print("=" * 60)
print("EXAMPLE 3: Callback-based streaming")
print("=" * 60)


async def callback_example():
    """Use callback function for streaming."""
    stream = DataStream()

    # Define callback
    tick_count = 0

    def on_price(msg):
        nonlocal tick_count
        print(f"  {msg.symbol}: ${msg.price:.2f}")
        tick_count += 1

    print("\nStreaming with callback...")

    # Start subscription
    task = stream.subscribe("BTCUSDT", callback=on_price)

    # Let it run for 5 seconds
    await asyncio.sleep(5)

    # Cancel subscription
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    await stream.disconnect_streams()
    print(f"\nReceived {tick_count} price updates.\n")


# Run example 3
asyncio.run(callback_example())


# ============================================================================
# EXAMPLE 4: Stream multiple symbols
# ============================================================================
print("=" * 60)
print("EXAMPLE 4: Stream multiple symbols simultaneously")
print("=" * 60)


async def stream_multiple_symbols():
    """Stream multiple crypto pairs at once."""
    stream = DataStream()

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    prices = {s: None for s in symbols}

    def on_tick(msg):
        prices[msg.symbol] = msg.price
        print(f"  Prices: ", end="")
        for sym, price in prices.items():
            if price:
                print(f"{sym}=${price:.2f}  ", end="")
        print()

    print(f"\nStreaming {len(symbols)} symbols...")

    # Stream all symbols
    task = asyncio.create_task(
        stream.stream_many(symbols, callback=on_tick)
    )

    # Let it run for 5 seconds
    await asyncio.sleep(5)

    # Cancel
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    await stream.disconnect_streams()
    print("\nStream closed.\n")


# Run example 4
asyncio.run(stream_multiple_symbols())


# ============================================================================
# EXAMPLE 5: Advanced - process and store data
# ============================================================================
print("=" * 60)
print("EXAMPLE 5: Process and aggregate streaming data")
print("=" * 60)


async def aggregate_trades():
    """Aggregate trade data over time."""
    stream = DataStream()

    # Track statistics
    stats = {
        'count': 0,
        'total_volume': 0,
        'min_price': float('inf'),
        'max_price': 0,
        'prices': []
    }

    async for tick in stream.stream("BTCUSDT", stream_type="ticker"):
        stats['count'] += 1
        stats['total_volume'] += tick.volume or 0
        stats['min_price'] = min(stats['min_price'], tick.price)
        stats['max_price'] = max(stats['max_price'], tick.price)
        stats['prices'].append(tick.price)

        # Print stats every 10 ticks
        if stats['count'] % 10 == 0:
            avg_price = sum(stats['prices']) / len(stats['prices'])
            print(f"\n  Trade Statistics (last {stats['count']} ticks):")
            print(f"    Avg Price:    ${avg_price:.2f}")
            print(f"    Min Price:    ${stats['min_price']:.2f}")
            print(f"    Max Price:    ${stats['max_price']:.2f}")
            print(f"    Total Volume: {stats['total_volume']:.4f} BTC")

        if stats['count'] >= 30:
            break

    await stream.disconnect_streams()
    print("\nAnalysis complete.\n")


# Run example 5
asyncio.run(aggregate_trades())


# ============================================================================
# EXAMPLE 6: Build a simple trading signal
# ============================================================================
print("=" * 60)
print("EXAMPLE 6: Simple momentum trading signal")
print("=" * 60)


async def momentum_signal():
    """Simple momentum signal from streaming prices."""
    stream = DataStream()

    prices = []
    window_size = 20

    async for tick in stream.stream("ETHUSDT", stream_type="ticker"):
        prices.append(tick.price)

        if len(prices) > window_size:
            prices.pop(0)

        if len(prices) == window_size:
            # Calculate simple momentum
            current = prices[-1]
            avg = sum(prices) / len(prices)
            momentum = ((current - avg) / avg) * 100

            if momentum > 0.1:
                signal = "🟢 BUY"
            elif momentum < -0.1:
                signal = "🔴 SELL"
            else:
                signal = "⚪ NEUTRAL"

            print(f"  ETH: ${current:.2f} | Momentum: {momentum:+.3f}% | Signal: {signal}")

        if len(prices) >= 50:  # Stop after 50 ticks
            break

    await stream.disconnect_streams()
    print("\nSignal generation complete.\n")


# Run example 6
asyncio.run(momentum_signal())


print("=" * 60)
print("All streaming examples completed!")
print("=" * 60)
