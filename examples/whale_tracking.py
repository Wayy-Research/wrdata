"""
Whale Transaction Tracking Examples for wrdata.

Demonstrates how to detect and monitor large volume cryptocurrency transactions
(whale transactions) using percentile-based detection across Binance and Coinbase.
"""

import asyncio
from datetime import datetime
from wrdata.streaming.binance_stream import BinanceStreamProvider
from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider

# ============================================================================
# EXAMPLE 1: Basic Whale Detection on Binance
# ============================================================================
print("=" * 80)
print("EXAMPLE 1: Whale Detection on Binance (Top 1% Transactions)")
print("=" * 80)


async def binance_whale_detection():
    """
    Monitor BTCUSDT on Binance and detect whale transactions.

    Detects transactions in the top 1% by volume using a rolling window
    of the last 1000 trades.
    """
    provider = BinanceStreamProvider()
    await provider.connect()

    print("\nMonitoring BTCUSDT for whale transactions...")
    print("Whale threshold: Top 1% by volume (99th percentile)")
    print("-" * 80)

    whale_count = 0
    total_count = 0
    max_messages = 100  # Monitor first 100 trades

    def whale_alert(whale_tx):
        """Callback for whale transactions."""
        nonlocal whale_count
        whale_count += 1
        print(f"\n🐋 WHALE ALERT #{whale_count}!")
        print(f"  Symbol:     {whale_tx.symbol}")
        print(f"  Size:       {whale_tx.size} BTC")
        print(f"  Price:      ${whale_tx.price:,.2f}")
        print(f"  Value:      ${whale_tx.usd_value:,.2f}")
        print(f"  Percentile: {whale_tx.percentile:.2f}% (Rank: {whale_tx.volume_rank})")
        print(f"  Side:       {whale_tx.side}")
        print(f"  Time:       {whale_tx.timestamp}")
        print("-" * 80)

    async for msg in provider.subscribe_aggregate_trades(
        symbol="BTCUSDT",
        enable_whale_detection=True,
        percentile_threshold=99.0,  # Top 1%
        whale_callback=whale_alert
    ):
        total_count += 1

        # Print regular trade info (only non-whale trades)
        if 'whale_metadata' not in (msg.raw_data or {}):
            if total_count % 10 == 0:  # Print every 10th trade to avoid spam
                print(f"Regular trade: {msg.volume:.4f} BTC @ ${msg.price:,.2f}")

        if total_count >= max_messages:
            break

    await provider.disconnect()

    print(f"\n📊 Summary:")
    print(f"  Total trades processed: {total_count}")
    print(f"  Whale transactions detected: {whale_count}")
    print(f"  Whale percentage: {(whale_count/total_count)*100:.2f}%\n")


# Run example 1
asyncio.run(binance_whale_detection())


# ============================================================================
# EXAMPLE 2: Multi-Symbol Whale Monitoring
# ============================================================================
print("=" * 80)
print("EXAMPLE 2: Multi-Symbol Whale Monitoring (Binance)")
print("=" * 80)


async def multi_symbol_whale_tracking():
    """
    Monitor multiple cryptocurrencies simultaneously for whale activity.
    """
    provider = BinanceStreamProvider()
    await provider.connect()

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    whale_counts = {sym: 0 for sym in symbols}

    print(f"\nMonitoring {len(symbols)} symbols for whale activity...")
    print("Whale threshold: Top 5% by volume")
    print("-" * 80)

    def whale_alert(whale_tx):
        """Callback for whale transactions."""
        whale_counts[whale_tx.symbol] += 1
        print(f"🐋 {whale_tx.symbol}: {whale_tx.size} @ ${whale_tx.price:,.2f} "
              f"(${whale_tx.usd_value:,.0f}) - Percentile: {whale_tx.percentile:.1f}%")

    # Create tasks for each symbol
    tasks = []
    for symbol in symbols:
        async def monitor_symbol(sym):
            count = 0
            async for msg in provider.subscribe_aggregate_trades(
                symbol=sym,
                enable_whale_detection=True,
                percentile_threshold=95.0,  # Top 5%
                whale_callback=whale_alert
            ):
                count += 1
                if count >= 50:  # Monitor 50 trades per symbol
                    break

        tasks.append(asyncio.create_task(monitor_symbol(symbol)))

    # Run all monitoring tasks concurrently
    await asyncio.gather(*tasks)
    await provider.disconnect()

    print("\n📊 Whale Summary by Symbol:")
    for symbol, count in whale_counts.items():
        print(f"  {symbol}: {count} whale transactions")
    print()


# Run example 2
asyncio.run(multi_symbol_whale_tracking())


# ============================================================================
# EXAMPLE 3: Coinbase Whale Detection with USD Threshold
# ============================================================================
print("=" * 80)
print("EXAMPLE 3: Coinbase Whale Detection (USD Value Threshold)")
print("=" * 80)


async def coinbase_whale_detection_usd():
    """
    Monitor Coinbase for whale transactions above a specific USD value.

    Combines percentile-based detection with absolute USD value threshold.
    """
    provider = CoinbaseStreamProvider()
    await provider.connect()

    min_usd = 100000  # $100k minimum

    print(f"\nMonitoring BTC-USD on Coinbase...")
    print(f"Whale criteria: Top 1% AND minimum ${min_usd:,}")
    print("-" * 80)

    whale_count = 0
    total_count = 0
    max_messages = 100

    def whale_alert(whale_tx):
        """Callback for whale transactions."""
        nonlocal whale_count
        whale_count += 1
        print(f"\n🐋 MAJOR WHALE DETECTED!")
        print(f"  Exchange:   Coinbase")
        print(f"  Symbol:     {whale_tx.symbol}")
        print(f"  Size:       {whale_tx.size} BTC")
        print(f"  Price:      ${whale_tx.price:,.2f}")
        print(f"  Value:      ${whale_tx.usd_value:,.2f}")
        print(f"  Percentile: {whale_tx.percentile:.2f}%")
        print(f"  Rank:       #{whale_tx.volume_rank} (largest recent trades)")
        print(f"  Side:       {whale_tx.side.upper()}")
        print(f"  Trade ID:   {whale_tx.transaction_id}")
        print("-" * 80)

    async for msg in provider.subscribe_matches(
        symbol="BTC-USD",
        enable_whale_detection=True,
        percentile_threshold=99.0,  # Top 1%
        min_usd_value=min_usd,  # Minimum $100k
        whale_callback=whale_alert
    ):
        total_count += 1

        if total_count % 20 == 0:
            print(f"Processed {total_count} trades, {whale_count} whales detected...")

        if total_count >= max_messages:
            break

    await provider.disconnect()

    print(f"\n📊 Summary:")
    print(f"  Total trades: {total_count}")
    print(f"  Whale transactions (>{min_usd:,} USD + Top 1%): {whale_count}\n")


# Run example 3
asyncio.run(coinbase_whale_detection_usd())


# ============================================================================
# EXAMPLE 4: Real-time Whale Analytics Dashboard
# ============================================================================
print("=" * 80)
print("EXAMPLE 4: Real-time Whale Analytics Dashboard")
print("=" * 80)


async def whale_analytics_dashboard():
    """
    Advanced example: Track whale activity with real-time statistics.
    """
    provider = BinanceStreamProvider()
    await provider.connect()

    # Analytics tracking
    whale_stats = {
        'total_whales': 0,
        'total_volume_usd': 0.0,
        'largest_whale': None,
        'buy_whales': 0,
        'sell_whales': 0,
    }

    print("\n📊 Real-time Whale Analytics Dashboard")
    print("Symbol: ETHUSDT | Threshold: Top 2% by volume")
    print("=" * 80)

    def analyze_whale(whale_tx):
        """Analyze and track whale transaction."""
        whale_stats['total_whales'] += 1
        whale_stats['total_volume_usd'] += float(whale_tx.usd_value)

        # Track largest whale
        if (whale_stats['largest_whale'] is None or
            float(whale_tx.usd_value) > float(whale_stats['largest_whale'].usd_value)):
            whale_stats['largest_whale'] = whale_tx

        # Track buy/sell
        if whale_tx.side == 'buy':
            whale_stats['buy_whales'] += 1
        elif whale_tx.side == 'sell':
            whale_stats['sell_whales'] += 1

        # Print update every 5 whales
        if whale_stats['total_whales'] % 5 == 0:
            print(f"\n📈 Dashboard Update (After {whale_stats['total_whales']} whales):")
            print(f"  Total Whale Volume: ${whale_stats['total_volume_usd']:,.0f}")
            print(f"  Buy Whales:  {whale_stats['buy_whales']}")
            print(f"  Sell Whales: {whale_stats['sell_whales']}")
            if whale_stats['largest_whale']:
                lw = whale_stats['largest_whale']
                print(f"  Largest Whale: {lw.size} ETH @ ${lw.price:,.2f} "
                      f"(${lw.usd_value:,.0f})")
            print("-" * 80)

    count = 0
    async for msg in provider.subscribe_aggregate_trades(
        symbol="ETHUSDT",
        enable_whale_detection=True,
        percentile_threshold=98.0,  # Top 2%
        whale_callback=analyze_whale
    ):
        count += 1
        if count >= 200:  # Process 200 trades
            break

    await provider.disconnect()

    # Final dashboard
    print("\n" + "=" * 80)
    print("📊 FINAL WHALE ANALYTICS REPORT")
    print("=" * 80)
    print(f"Total Whale Transactions: {whale_stats['total_whales']}")
    print(f"Total Whale Volume: ${whale_stats['total_volume_usd']:,.2f}")
    print(f"Average Whale Size: ${whale_stats['total_volume_usd']/max(whale_stats['total_whales'], 1):,.2f}")
    print(f"Buy Whales: {whale_stats['buy_whales']} ({whale_stats['buy_whales']/max(whale_stats['total_whales'], 1)*100:.1f}%)")
    print(f"Sell Whales: {whale_stats['sell_whales']} ({whale_stats['sell_whales']/max(whale_stats['total_whales'], 1)*100:.1f}%)")

    if whale_stats['largest_whale']:
        lw = whale_stats['largest_whale']
        print(f"\n🏆 Largest Whale Transaction:")
        print(f"  Size:  {lw.size} ETH")
        print(f"  Price: ${lw.price:,.2f}")
        print(f"  Value: ${lw.usd_value:,.2f}")
        print(f"  Side:  {lw.side.upper()}")
        print(f"  Time:  {lw.timestamp}")
    print("=" * 80)
    print()


# Run example 4
asyncio.run(whale_analytics_dashboard())


# ============================================================================
# EXAMPLE 5: Custom Percentile Thresholds
# ============================================================================
print("=" * 80)
print("EXAMPLE 5: Comparing Different Whale Thresholds")
print("=" * 80)


async def compare_thresholds():
    """
    Compare whale detection at different percentile thresholds.
    """
    provider = BinanceStreamProvider()
    await provider.connect()

    thresholds = {
        'Ultra Whales (Top 0.1%)': 99.9,
        'Major Whales (Top 1%)': 99.0,
        'Minor Whales (Top 5%)': 95.0,
    }

    print("\nComparing whale detection thresholds on BTCUSDT...")
    print("This will take ~30 seconds to collect data\n")

    for label, threshold in thresholds.items():
        whale_count = 0
        total_count = 0
        total_whale_value = 0.0

        def track_whale(whale_tx):
            nonlocal whale_count, total_whale_value
            whale_count += 1
            total_whale_value += float(whale_tx.usd_value)

        async for msg in provider.subscribe_aggregate_trades(
            symbol="BTCUSDT",
            enable_whale_detection=True,
            percentile_threshold=threshold,
            whale_callback=track_whale
        ):
            total_count += 1
            if total_count >= 100:
                break

        print(f"{label} (≥{threshold}th percentile):")
        print(f"  Whale count: {whale_count}/{total_count} trades ({whale_count/total_count*100:.2f}%)")
        print(f"  Total value: ${total_whale_value:,.0f}")
        print(f"  Avg per whale: ${total_whale_value/max(whale_count, 1):,.0f}\n")

    await provider.disconnect()
    print()


# Run example 5
asyncio.run(compare_thresholds())


print("=" * 80)
print("All whale tracking examples completed!")
print("=" * 80)
print("\nKey Takeaways:")
print("1. Percentile-based detection adapts to market conditions")
print("2. Combine with USD thresholds for more precise whale identification")
print("3. Monitor multiple symbols to track whale activity across markets")
print("4. Use callbacks for efficient real-time processing")
print("5. Binance aggregate trades provide excellent whale detection data")
print("6. Coinbase matches channel works great for spot whale tracking")
print("\nHappy whale watching! 🐋\n")
