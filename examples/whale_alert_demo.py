"""
Whale Alert API Integration Demo

This demo shows how to:
1. Fetch historical whale transactions from Whale Alert API
2. Fetch corresponding price data from Binance
3. Analyze price impact of whale transactions

Requirements:
- Whale Alert API key (get one at https://whale-alert.io/)
- Set environment variable: export WHALE_ALERT_API_KEY=your_key_here
"""

import os
from datetime import datetime, timedelta
from wrdata.providers.whale_alert_provider import WhaleAlertProvider


def demo_whale_alert_api():
    """Demonstrate Whale Alert API integration."""

    # Check for API key
    api_key = os.getenv("WHALE_ALERT_API_KEY")

    if not api_key:
        print("\n" + "=" * 80)
        print("⚠️  WHALE ALERT API KEY NOT FOUND")
        print("=" * 80)
        print("\nTo use Whale Alert API:")
        print("1. Sign up at: https://whale-alert.io/")
        print("2. Get an API key from: https://whale-alert.io/api")
        print("3. Set environment variable:")
        print("   export WHALE_ALERT_API_KEY=your_api_key_here")
        print("\n" + "=" * 80)
        print("\n💡 For now, showing demo with mock data structure...\n")
        demo_mock_whale_data()
        return

    # Initialize provider
    whale_provider = WhaleAlertProvider(api_key=api_key)

    print("\n" + "=" * 80)
    print("🐋 WHALE ALERT API DEMO")
    print("=" * 80)

    # Test API connection
    print("\n📡 Testing API connection...")
    if whale_provider.validate_connection():
        print("   ✅ Successfully connected to Whale Alert API")

        # Get status
        status = whale_provider.get_status()
        if status.get("success"):
            usage = status.get("usage", {})
            limits = status.get("limits", {})
            print("\n📊 API Status:")
            print(f"   Usage: {usage}")
            print(f"   Limits: {limits}")
    else:
        print("   ❌ Failed to connect - check your API key")
        return

    # Fetch whale transactions
    print("\n🔍 Fetching whale transactions...")
    print("   Period: Last 24 hours")
    print("   Blockchain: Bitcoin")
    print("   Min Value: $1,000,000")

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        batch = whale_provider.fetch_whale_transactions(
            start_date=yesterday,
            end_date=yesterday,
            blockchain="bitcoin",
            min_value=1000000,
            limit=20,
        )

        print(f"\n✅ Found {batch.count} whale transactions")

        if batch.transactions:
            print("\n" + "-" * 80)
            print("RECENT WHALE TRANSACTIONS:")
            print("-" * 80)

            for i, whale_tx in enumerate(batch.transactions[:5], 1):
                print(f"\n{i}. {whale_tx.symbol} Whale Transaction")
                print(f"   Time: {whale_tx.timestamp}")
                print(f"   Size: {whale_tx.size:,.2f} {whale_tx.symbol}")
                print(f"   USD Value: ${whale_tx.usd_value:,.0f}")
                print(f"   Type: {whale_tx.transaction_type}")
                print(f"   Exchange: {whale_tx.exchange or 'N/A'}")
                print(f"   From: {whale_tx.from_address[:20]}...")
                print(f"   To: {whale_tx.to_address[:20]}...")
                print(f"   Blockchain: {whale_tx.blockchain}")

            if batch.count > 5:
                print(f"\n... and {batch.count - 5} more whale transactions")

        else:
            print("\n⚠️  No whale transactions found for this period")
            print("   This is normal - whale transactions are relatively rare")

    except Exception as e:
        print(f"\n❌ Error fetching whale transactions: {e}")
        return

    print("\n" + "=" * 80)


def demo_mock_whale_data():
    """Show what whale transaction data looks like (mock data)."""

    print("=" * 80)
    print("📋 WHALE TRANSACTION DATA STRUCTURE (Mock Example)")
    print("=" * 80)

    print("\nExample Whale Transaction:")
    print("""{
    "symbol": "BTC",
    "timestamp": "2025-11-23 10:45:32",
    "exchange": "Binance",
    "transaction_id": "a3b8c9d7e2f1...",
    "size": 125.5,
    "price": 95000.00,
    "usd_value": 11922500.00,
    "percentile": 99.8,
    "volume_rank": 3,
    "transaction_type": "withdrawal",
    "side": "N/A",
    "from_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "to_address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "blockchain": "bitcoin",
    "tx_hash": "a3b8c9d7e2f1...",
    "provider": "whale_alert"
}""")

    print("\n" + "=" * 80)
    print("\n🎯 Key Fields:")
    print("   • size: Amount of cryptocurrency transferred")
    print("   • usd_value: USD value at time of transaction")
    print("   • transaction_type: withdrawal, deposit, transfer, exchange_transfer")
    print("   • from_address/to_address: Blockchain addresses")
    print("   • exchange: Exchange name if applicable")
    print("   • blockchain: Which blockchain (bitcoin, ethereum, etc.)")

    print("\n" + "=" * 80)


def demo_price_impact_analysis():
    """Demonstrate how price impact analysis works (requires API key)."""

    api_key = os.getenv("WHALE_ALERT_API_KEY")

    if not api_key:
        print("\n" + "=" * 80)
        print("💡 PRICE IMPACT ANALYSIS WORKFLOW")
        print("=" * 80)
        print("\nWith a Whale Alert API key, you can:")
        print("\n1. Fetch whale transactions for a specific period")
        print("2. Fetch corresponding minute-level price data")
        print("3. Analyze price movement before/after each whale transaction")
        print("4. Calculate metrics like:")
        print("   • Average price change (5m, 10m, 15m)")
        print("   • Volume surge percentage")
        print("   • Volatility increase")
        print("   • Impact by transaction type (deposit vs withdrawal)")
        print("\nSee examples/whale_tracking.py for real-time whale detection")
        print("See tests/integration/test_whale_price_impact.py for full analysis")
        print("\n" + "=" * 80)
        return

    print("\n" + "=" * 80)
    print("📊 PRICE IMPACT ANALYSIS DEMO")
    print("=" * 80)
    print("\nThis would:")
    print("1. Fetch whale transactions from Whale Alert")
    print("2. Fetch BTC price data from Binance (minute-level)")
    print("3. Analyze price changes around each whale transaction")
    print("4. Generate statistical report")

    print("\n💡 To run full analysis:")
    print("   cd /home/rcgalbo/wayy-research/wayy-fin/wf/wrdata")
    print("   export WHALE_ALERT_API_KEY=your_key_here")
    print("   python3 -m pytest tests/integration/test_whale_price_impact.py -v -s")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🐋 Whale Alert Integration Demo\n")

    # Run demos
    demo_whale_alert_api()
    print()
    demo_price_impact_analysis()

    print("\n✅ Demo complete!")
    print("\nNext steps:")
    print("1. Get API key from https://whale-alert.io/")
    print("2. Run: export WHALE_ALERT_API_KEY=your_key")
    print("3. Re-run this demo to see real whale data")
    print("4. Try examples/whale_tracking.py for real-time detection")
    print("5. Run integration test for price impact analysis\n")
