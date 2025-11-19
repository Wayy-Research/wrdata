"""Quick test of real-time streaming API."""

import asyncio
from wrdata import DataStream


async def test_streaming():
    """Test basic streaming functionality."""
    print("Testing wrdata Real-Time Streaming...")
    print("=" * 60)

    stream = DataStream()

    # Test 1: Stream a few BTC ticks
    print("\nTest 1: Streaming BTCUSDT ticks...")
    count = 0
    async for tick in stream.stream("BTCUSDT", stream_type="ticker"):
        print(f"  ✓ Received tick: BTC=${tick.price:.2f}, Volume={tick.volume:.4f}")
        count += 1
        if count >= 3:
            break

    # Test 2: Stream a candle
    print("\nTest 2: Streaming ETHUSDT 1m candles...")
    count = 0
    async for candle in stream.stream("ETHUSDT", stream_type="kline", interval="1m"):
        print(f"  ✓ Received candle: O=${candle.open:.2f} H=${candle.high:.2f} L=${candle.low:.2f} C=${candle.close:.2f}")
        count += 1
        if count >= 1:
            break

    # Clean up
    await stream.disconnect_streams()

    print("\n" + "=" * 60)
    print("Streaming tests passed! 🎉")


if __name__ == "__main__":
    asyncio.run(test_streaming())
