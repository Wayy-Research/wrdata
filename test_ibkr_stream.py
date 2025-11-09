#!/usr/bin/env python3
"""
Interactive Brokers streaming test.

Tests real-time data streaming via IBKR TWS API.

REQUIREMENTS:
1. TWS or IB Gateway must be running locally
2. API must be enabled in TWS settings
3. Socket port configured: 7497 (paper) or 7496 (live)
4. For real-time data: Active market data subscriptions
   (Delayed data is free)

Setup TWS/IB Gateway:
- Download: https://www.interactivebrokers.com/en/trading/tws.php
- Enable API: File → Global Configuration → API → Settings
- Check "Enable ActiveX and Socket Clients"
- Set socket port: 7497 for paper trading

Note: This test uses a different client_id (2) than the REST provider (1)
to allow both to connect simultaneously.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wrdata.streaming.ibkr_stream import IBKRStreamProvider


async def test_connection():
    """Test basic streaming connection."""
    print("\n" + "=" * 70)
    print("  Test 1: Streaming Connection")
    print("=" * 70)

    provider = IBKRStreamProvider(
        host="127.0.0.1",
        port=7497,  # Paper trading
        client_id=2  # Different from REST provider
    )

    try:
        connected = await provider.connect()

        if connected:
            print("✓ Successfully connected to IBKR streaming")
            await provider.disconnect()
            return True
        else:
            print("✗ Failed to connect")
            return False

    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False


async def test_realtime_bars():
    """Test real-time 5-second bar streaming."""
    print("\n" + "=" * 70)
    print("  Test 2: Real-time Bars (5-second)")
    print("=" * 70)

    provider = IBKRStreamProvider(port=7497, client_id=2)

    try:
        symbol = "AAPL"
        count = 0
        max_bars = 10  # Receive 10 bars then stop

        print(f"\nStreaming {symbol} real-time bars...")
        print("(This will take ~50 seconds for 10 bars)")
        print("\nPress Ctrl+C to stop early\n")

        async for msg in provider.subscribe_ticker(symbol):
            count += 1

            print(f"Bar {count}:")
            print(f"  Time: {msg.timestamp}")
            print(f"  OHLC: O=${msg.open:.2f} H=${msg.high:.2f} L=${msg.low:.2f} C=${msg.close:.2f}")
            print(f"  Volume: {msg.volume:,.0f}")
            print(f"  WAP: {msg.raw_data.get('wap', 'N/A')}")
            print(f"  Count: {msg.raw_data.get('count', 'N/A')}")
            print()

            if count >= max_bars:
                print(f"✓ Received {count} bars successfully")
                break

        await provider.disconnect()
        return True

    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
        await provider.disconnect()
        return True

    except Exception as e:
        print(f"\n✗ Streaming error: {e}")
        import traceback
        traceback.print_exc()
        await provider.disconnect()
        return False


async def test_market_data_stream():
    """Test tick-by-tick market data streaming."""
    print("\n" + "=" * 70)
    print("  Test 3: Market Data Stream (Tick-by-Tick)")
    print("=" * 70)

    provider = IBKRStreamProvider(port=7497, client_id=2)

    try:
        symbol = "AAPL"
        count = 0
        max_ticks = 20  # Receive 20 updates then stop

        print(f"\nStreaming {symbol} market data...")
        print("Press Ctrl+C to stop\n")

        async for msg in provider.subscribe_market_data(symbol):
            count += 1

            print(f"Tick {count} @ {msg.timestamp.strftime('%H:%M:%S')}:")
            print(f"  Last: ${msg.price:.2f}")
            if msg.bid and msg.ask:
                spread = msg.ask - msg.bid
                print(f"  Bid/Ask: ${msg.bid:.2f} / ${msg.ask:.2f} (spread: ${spread:.2f})")
            print(f"  Volume: {msg.volume:,.0f}")
            print()

            if count >= max_ticks:
                print(f"✓ Received {count} market data updates")
                break

        await provider.disconnect()
        return True

    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
        await provider.disconnect()
        return True

    except Exception as e:
        print(f"\n✗ Streaming error: {e}")
        import traceback
        traceback.print_exc()
        await provider.disconnect()
        return False


async def test_multi_symbol_stream():
    """Test streaming multiple symbols simultaneously."""
    print("\n" + "=" * 70)
    print("  Test 4: Multi-Symbol Streaming")
    print("=" * 70)

    provider = IBKRStreamProvider(port=7497, client_id=2)

    symbols = ["AAPL", "MSFT", "GOOGL"]
    tasks = []
    message_counts = {sym: 0 for sym in symbols}

    async def stream_symbol(symbol: str):
        """Stream a single symbol."""
        try:
            async for msg in provider.subscribe_market_data(symbol):
                message_counts[symbol] += 1

                if message_counts[symbol] == 1:
                    print(f"✓ {symbol}: First update received @ ${msg.price:.2f}")

                # Stop after 5 messages per symbol
                if message_counts[symbol] >= 5:
                    break

        except Exception as e:
            print(f"✗ {symbol} error: {e}")

    try:
        await provider.connect()

        print(f"\nStreaming {len(symbols)} symbols simultaneously...")
        print()

        # Create tasks for each symbol
        for symbol in symbols:
            task = asyncio.create_task(stream_symbol(symbol))
            tasks.append(task)

        # Wait for all to complete
        await asyncio.gather(*tasks)

        print(f"\n✓ Multi-symbol streaming complete")
        print(f"  Messages received:")
        for symbol, count in message_counts.items():
            print(f"    {symbol}: {count}")

        await provider.disconnect()
        return True

    except Exception as e:
        print(f"\n✗ Multi-symbol error: {e}")
        await provider.disconnect()
        return False


async def test_callback_handler():
    """Test streaming with callback handler."""
    print("\n" + "=" * 70)
    print("  Test 5: Callback Handler")
    print("=" * 70)

    provider = IBKRStreamProvider(port=7497, client_id=2)

    received_messages = []

    def on_message(msg):
        """Callback to handle messages."""
        received_messages.append(msg)
        print(f"📨 Callback: {msg.symbol} @ ${msg.price:.2f} ({msg.timestamp.strftime('%H:%M:%S')})")

    try:
        symbol = "AAPL"
        count = 0
        max_messages = 10

        print(f"\nStreaming {symbol} with callback handler...\n")

        async for msg in provider.subscribe_market_data(symbol, callback=on_message):
            count += 1

            if count >= max_messages:
                break

        print(f"\n✓ Callback received {len(received_messages)} messages")
        await provider.disconnect()
        return True

    except Exception as e:
        print(f"\n✗ Callback test error: {e}")
        await provider.disconnect()
        return False


async def test_reconnection():
    """Test reconnection capability."""
    print("\n" + "=" * 70)
    print("  Test 6: Reconnection")
    print("=" * 70)

    provider = IBKRStreamProvider(port=7497, client_id=2)

    try:
        # Connect
        print("\nConnecting...")
        connected = await provider.connect()
        print(f"✓ Connected: {provider.is_connected()}")

        # Disconnect
        print("\nDisconnecting...")
        await provider.disconnect()
        print(f"✓ Disconnected: {not provider.is_connected()}")

        # Reconnect
        print("\nReconnecting...")
        reconnected = await provider.reconnect()
        print(f"✓ Reconnected: {provider.is_connected()}")

        await provider.disconnect()
        return True

    except Exception as e:
        print(f"\n✗ Reconnection error: {e}")
        return False


async def run_all_tests():
    """Run all streaming tests."""
    print("\n" + "=" * 70)
    print("  IBKR Streaming Provider - Live Test Suite")
    print("=" * 70)
    print("\nNOTE: TWS or IB Gateway must be running on port 7497")
    print("      (Paper trading port)")
    print("\nWARNING: Some tests may take time due to real-time nature")

    tests = [
        ("Connection", test_connection),
        ("Real-time Bars", test_realtime_bars),
        ("Market Data Stream", test_market_data_stream),
        ("Multi-Symbol", test_multi_symbol_stream),
        ("Callback Handler", test_callback_handler),
        ("Reconnection", test_reconnection),
    ]

    results = {}

    for name, test_func in tests:
        try:
            results[name] = await test_func()
        except KeyboardInterrupt:
            print(f"\n⚠ Test '{name}' interrupted by user")
            results[name] = True  # Don't count as failure
            break
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Print summary
    print("\n" + "=" * 70)
    print("  Test Summary")
    print("=" * 70)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}  {name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All tests passed!")
    else:
        print(f"\n  ⚠ {total - passed} test(s) failed")

    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Test suite interrupted by user")
        sys.exit(0)
