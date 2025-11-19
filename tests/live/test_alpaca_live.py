"""
Live test of Alpaca broker provider.

Get your free API keys: https://app.alpaca.markets/signup
Free tier: Real-time IEX data + paper trading account!

Set them as:
export ALPACA_API_KEY="your_key_here"
export ALPACA_API_SECRET="your_secret_here"
"""

import os
import asyncio
from wrdata import DataStream
from wrdata.providers.alpaca_provider import AlpacaProvider


def test_alpaca_provider():
    """Test Alpaca provider directly."""
    print("=" * 60)
    print("Testing Alpaca Provider")
    print("=" * 60)

    # Get API keys from environment
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')

    if not api_key or not api_secret:
        print("\n❌ ALPACA_API_KEY or ALPACA_API_SECRET not set!")
        print("Get free API keys at: https://app.alpaca.markets/signup")
        print("Then set them:")
        print("  export ALPACA_API_KEY='your_key_here'")
        print("  export ALPACA_API_SECRET='your_secret_here'")
        return

    # Create provider (use paper trading)
    print(f"\n✓ Alpaca API keys found")
    provider = AlpacaProvider(api_key=api_key, api_secret=api_secret, paper=True)

    # Test connection
    print("✓ Testing connection...")
    if provider.validate_connection():
        print("  ✓ Connection successful!")
    else:
        print("  ❌ Connection failed!")
        return

    # Get account info
    print("\n✓ Fetching account information...")
    account = provider.get_account()
    if account:
        print(f"  Account Number: {account.get('account_number', 'N/A')}")
        print(f"  Status: {account.get('status', 'N/A')}")
        print(f"  Cash: ${float(account.get('cash', 0)):,.2f}")
        print(f"  Portfolio Value: ${float(account.get('portfolio_value', 0)):,.2f}")
        print(f"  Buying Power: ${float(account.get('buying_power', 0)):,.2f}")
        print(f"  Paper Trading: {account.get('account_number', '').startswith('P')}")
    else:
        print("  ❌ Failed to get account info")

    # Get latest trade
    print("\n✓ Fetching latest trade for AAPL...")
    trade = provider.get_latest_trade("AAPL")
    if trade:
        print(f"  ✓ AAPL latest trade: ${trade.get('p', 'N/A')}")
        print(f"    Size: {trade.get('s', 'N/A')} shares")
        print(f"    Time: {trade.get('t', 'N/A')}")
    else:
        print("  ❌ Failed to get latest trade")

    # Get latest quote
    print("\n✓ Fetching latest quote for AAPL...")
    quote = provider.get_latest_quote("AAPL")
    if quote:
        print(f"  ✓ AAPL quote:")
        print(f"    Bid: ${quote.get('bp', 'N/A')} x {quote.get('bs', 'N/A')}")
        print(f"    Ask: ${quote.get('ap', 'N/A')} x {quote.get('as', 'N/A')}")
        print(f"    Time: {quote.get('t', 'N/A')}")
    else:
        print("  ❌ Failed to get latest quote")

    # Get market snapshot
    print("\n✓ Fetching market snapshot for AAPL...")
    snapshot = provider.get_snapshot("AAPL")
    if snapshot:
        latest_trade = snapshot.get('latestTrade', {})
        latest_quote = snapshot.get('latestQuote', {})
        print(f"  ✓ Latest Trade: ${latest_trade.get('p', 'N/A')} @ {latest_trade.get('t', 'N/A')}")
        print(f"  ✓ Latest Quote: ${latest_quote.get('bp', 'N/A')} / ${latest_quote.get('ap', 'N/A')}")
    else:
        print("  ⚠️ Could not get snapshot")

    # Get historical data
    print("\n✓ Fetching historical data for AAPL...")
    response = provider.fetch_timeseries(
        symbol="AAPL",
        start_date="2024-10-01",
        end_date="2024-11-07",
        interval="1d"
    )

    if response.success:
        print(f"  ✓ Got {len(response.data)} data points")
        if response.data:
            print(f"  First point: {response.data[0]}")
            print(f"  Last point: {response.data[-1]}")
    else:
        print(f"  ❌ Failed: {response.error}")

    # Get positions
    print("\n✓ Checking current positions...")
    positions = provider.get_positions()
    if positions:
        print(f"  ✓ You have {len(positions)} open position(s)")
        for pos in positions[:5]:  # Show first 5
            print(f"    {pos.get('symbol')}: {pos.get('qty')} shares @ ${pos.get('avg_entry_price')}")
    else:
        print("  No open positions")

    # Get open orders
    print("\n✓ Checking open orders...")
    orders = provider.get_orders(status="open")
    if orders:
        print(f"  ✓ You have {len(orders)} open order(s)")
        for order in orders[:5]:
            print(f"    {order.get('symbol')}: {order.get('side')} {order.get('qty')} @ {order.get('type')}")
    else:
        print("  No open orders")

    print("\n" + "=" * 60)
    print("Alpaca Provider Test Complete!")
    print("=" * 60)


def test_datastream_with_alpaca():
    """Test Alpaca via DataStream API."""
    print("\n" + "=" * 60)
    print("Testing Alpaca via DataStream")
    print("=" * 60)

    # Get API keys
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')

    if not api_key or not api_secret:
        print("\n❌ Skipping DataStream test - no API keys")
        return

    # Create DataStream with Alpaca
    stream = DataStream(alpaca_key=api_key, alpaca_secret=api_secret, alpaca_paper=True)

    # Check provider status
    status = stream.status()
    print(f"\n✓ Available providers: {list(stream.providers.keys())}")
    if 'alpaca' in status:
        print(f"  Alpaca connected: {status['alpaca'].get('connected', False)}")

    # Fetch Apple stock data
    print("\n✓ Fetching Apple (AAPL) stock data...")
    df = stream.get(
        "AAPL",
        start="2024-10-01",
        end="2024-11-07",
        asset_type="stock"
    )

    print(f"  ✓ Got {len(df)} rows of AAPL data")
    if len(df) > 0:
        print("\n  Latest AAPL prices:")
        print(df.tail(5))

    # Fetch Microsoft data
    print("\n✓ Fetching Microsoft (MSFT)...")
    df = stream.get(
        "MSFT",
        start="2024-11-01",
        end="2024-11-07",
        asset_type="stock"
    )

    print(f"  ✓ Got {len(df)} rows")
    if len(df) > 0:
        print("\n  Recent MSFT prices:")
        print(df.tail(5))

    # Test provider priority (Alpaca should be first for stocks)
    print("\n✓ Testing provider auto-selection...")
    print("  For stocks, priority is: alpaca → finnhub → alphavantage → yfinance")

    print("\n" + "=" * 60)
    print("DataStream Alpaca Test Complete!")
    print("=" * 60)


async def test_alpaca_streaming():
    """Test Alpaca WebSocket streaming."""
    print("\n" + "=" * 60)
    print("Testing Alpaca WebSocket Streaming")
    print("=" * 60)

    # Get API keys
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')

    if not api_key or not api_secret:
        print("\n❌ Skipping streaming test - no API keys")
        return

    print("\n✓ Starting Alpaca WebSocket stream...")
    print("  Streaming live trades for AAPL and MSFT")
    print("  Press Ctrl+C to stop\n")

    from wrdata.streaming.alpaca_stream import AlpacaStreamProvider

    stream = AlpacaStreamProvider(api_key=api_key, api_secret=api_secret, paper=True)

    try:
        await stream.connect()

        # Stream multiple symbols
        count = 0
        max_messages = 20  # Just show first 20 messages

        async for msg in stream.subscribe_multiple(['AAPL', 'MSFT'], data_type='trades'):
            print(f"  {msg.symbol}: ${msg.price:.2f} @ {msg.timestamp.strftime('%H:%M:%S')} (vol: {msg.volume:.0f})")

            count += 1
            if count >= max_messages:
                print(f"\n  ✓ Received {count} real-time trade messages!")
                break

    except KeyboardInterrupt:
        print("\n  Stream stopped by user")
    finally:
        await stream.disconnect()

    print("\n" + "=" * 60)
    print("Alpaca Streaming Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    # Test Alpaca provider
    test_alpaca_provider()

    # Test via DataStream
    test_datastream_with_alpaca()

    # Test WebSocket streaming
    print("\n✅ REST API tests completed!")
    print("\nReady to test WebSocket streaming? (y/n): ", end='')
    try:
        response = input()
        if response.lower() == 'y':
            asyncio.run(test_alpaca_streaming())
    except:
        print("\nSkipping streaming test")

    print("\n✅ All Alpaca tests completed!")
    print("\nNote: Alpaca free tier includes:")
    print("  - Real-time IEX stock data")
    print("  - FREE WebSocket streaming")
    print("  - Paper trading account ($100k virtual cash)")
    print("  - Up to 200 API calls/minute")
    print("  - Historical data (up to 6 years)")
