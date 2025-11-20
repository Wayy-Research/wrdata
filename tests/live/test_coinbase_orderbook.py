"""
Live test for Coinbase Level2 orderbook streaming.

This test connects to Coinbase WebSocket and streams orderbook data.
Run this to verify the Level2 implementation works correctly.

Usage:
    python -m pytest tests/live/test_coinbase_orderbook.py -v -s

Or run directly:
    python tests/live/test_coinbase_orderbook.py
"""

import asyncio
from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider


async def test_orderbook_stream():
    """Test Level2 orderbook streaming."""
    provider = CoinbaseStreamProvider()

    print("Connecting to Coinbase WebSocket...")
    await provider.connect()

    print("Subscribing to BTC-USD orderbook...")

    count = 0
    max_messages = 10

    async for message in provider.subscribe_depth("BTC-USD"):
        count += 1

        print(f"\n--- Update {count} ---")
        print(f"Timestamp: {message.timestamp}")
        print(f"Symbol: {message.symbol}")
        print(f"Mid Price: ${message.price:,.2f}" if message.price else "N/A")
        print(f"Best Bid: ${message.bid:,.2f}" if message.bid else "N/A")
        print(f"Best Ask: ${message.ask:,.2f}" if message.ask else "N/A")
        print(f"Spread: ${(message.ask - message.bid):.2f}" if (message.bid and message.ask) else "N/A")

        if message.bids:
            print(f"\nTop 5 Bids:")
            for i, (price, size) in enumerate(message.bids[:5]):
                print(f"  {i+1}. ${price:,.2f} x {size:.4f} BTC")

        if message.asks:
            print(f"\nTop 5 Asks:")
            for i, (price, size) in enumerate(message.asks[:5]):
                print(f"  {i+1}. ${price:,.2f} x {size:.4f} BTC")

        # Calculate total volume at each side
        if message.bids:
            total_bid_vol = sum(size for _, size in message.bids[:10])
            print(f"\nTotal bid volume (top 10): {total_bid_vol:.4f} BTC")

        if message.asks:
            total_ask_vol = sum(size for _, size in message.asks[:10])
            print(f"Total ask volume (top 10): {total_ask_vol:.4f} BTC")

        if count >= max_messages:
            print(f"\nReceived {count} messages, stopping...")
            break

    await provider.disconnect()
    print("\nDisconnected successfully")


async def test_orderbook_snapshot():
    """Test getting orderbook snapshot."""
    provider = CoinbaseStreamProvider()

    await provider.connect()

    print("Subscribing to ETH-USD orderbook...")

    # Collect a few updates
    count = 0
    async for message in provider.subscribe_depth("ETH-USD"):
        count += 1
        if count >= 3:
            break

    # Get snapshot
    print("\nRetrieving orderbook snapshot...")
    snapshot = provider.get_orderbook_snapshot("ETH-USD")

    if snapshot:
        print(f"Bids: {len(snapshot['bids'])} price levels")
        print(f"Asks: {len(snapshot['asks'])} price levels")

        if snapshot['bids']:
            best_bid = max(snapshot['bids'].keys())
            print(f"Best bid: ${best_bid:,.2f}")

        if snapshot['asks']:
            best_ask = min(snapshot['asks'].keys())
            print(f"Best ask: ${best_ask:,.2f}")
    else:
        print("No snapshot available")

    await provider.disconnect()


async def test_multiple_symbols():
    """Test streaming orderbooks for multiple symbols simultaneously."""
    provider = CoinbaseStreamProvider()

    await provider.connect()

    print("Testing multiple symbol subscriptions...")

    # Create tasks for multiple symbols
    async def monitor_symbol(symbol: str, num_updates: int = 5):
        print(f"\nStarting {symbol} monitor...")
        count = 0
        async for msg in provider.subscribe_depth(symbol):
            count += 1
            spread = (msg.ask - msg.bid) if (msg.bid and msg.ask) else None
            print(f"{symbol}: Bid ${msg.bid:,.2f} | Ask ${msg.ask:,.2f} | Spread ${spread:.2f}"
                  if spread else f"{symbol}: Waiting for data...")
            if count >= num_updates:
                break

    # Monitor BTC and ETH simultaneously
    await asyncio.gather(
        monitor_symbol("BTC-USD", 3),
        monitor_symbol("ETH-USD", 3)
    )

    await provider.disconnect()
    print("\nMultiple symbol test complete")


if __name__ == "__main__":
    print("=" * 60)
    print("Coinbase Level2 Orderbook Streaming Test")
    print("=" * 60)

    print("\n\n1. Testing basic orderbook stream...")
    asyncio.run(test_orderbook_stream())

    print("\n\n2. Testing orderbook snapshot...")
    asyncio.run(test_orderbook_snapshot())

    print("\n\n3. Testing multiple symbols...")
    asyncio.run(test_multiple_symbols())

    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)
