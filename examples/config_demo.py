"""
API Key Configuration Demo

Demonstrates the three ways to provide API keys in wrdata:
1. Environment variables (via .env file)
2. Constructor parameters
3. Direct provider instantiation

Run this to verify your configuration is working.
"""

import os
from wrdata.core.config import settings


def check_configuration():
    """Check which API keys are configured."""

    print("\n" + "=" * 80)
    print("🔑 WRDATA API KEY CONFIGURATION CHECK")
    print("=" * 80)

    print("\n📋 Configuration Status:")
    print("-" * 80)

    # Check each provider
    providers = [
        ("Alpha Vantage", settings.ALPHA_VANTAGE_API_KEY, "https://www.alphavantage.co/support/#api-key"),
        ("Twelve Data", settings.TWELVE_DATA_API_KEY, "https://twelvedata.com/apikey"),
        ("FRED", settings.FRED_API_KEY, "https://fred.stlouisfed.org/docs/api/api_key.html"),
        ("Finnhub", settings.FINNHUB_API_KEY, "https://finnhub.io/register"),
        ("Polygon", settings.POLYGON_API_KEY, "https://polygon.io/dashboard/api-keys"),
        ("Alpaca", settings.ALPACA_API_KEY, "https://app.alpaca.markets/"),
        ("Binance", settings.BINANCE_API_KEY, "https://www.binance.com/en/my/settings/api-management"),
        ("Coinbase", settings.COINBASE_API_KEY, "https://www.coinbase.com/settings/api"),
        ("Kraken", settings.KRAKEN_API_KEY, "https://www.kraken.com/u/security/api"),
        ("Whale Alert", settings.WHALE_ALERT_API_KEY, "https://whale-alert.io/"),
    ]

    configured_count = 0
    free_count = 0

    for name, key, url in providers:
        status = "✅ Configured" if key else "❌ Not configured"
        is_free = name in ["Alpha Vantage", "Twelve Data", "FRED", "Finnhub"]
        tier = "[FREE]" if is_free else "[PAID]"

        print(f"{name:20} {tier:8} {status}")

        if key:
            configured_count += 1
            if is_free:
                free_count += 1
            # Show masked key (first 4 chars only)
            masked = f"{key[:4]}{'*' * (len(key) - 4)}" if len(key) > 4 else "****"
            print(f"                     Key: {masked}")
        else:
            print(f"                     Get key: {url}")
        print()

    print("-" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total configured: {configured_count}/{len(providers)}")
    print(f"   Free tier: {free_count}")
    print(f"   Paid tier: {configured_count - free_count}")

    # Check helper properties
    print(f"\n🔍 Helper Property Checks:")
    print(f"   settings.has_alpha_vantage_key: {settings.has_alpha_vantage_key}")
    print(f"   settings.has_twelve_data_key: {settings.has_twelve_data_key}")
    print(f"   settings.has_binance_key: {settings.has_binance_key}")
    print(f"   settings.has_whale_alert_key: {settings.has_whale_alert_key}")

    print("\n" + "=" * 80)


def demo_three_configuration_methods():
    """Demonstrate the three ways to configure API keys."""

    print("\n" + "=" * 80)
    print("📚 THREE CONFIGURATION METHODS")
    print("=" * 80)

    print("\n1️⃣  METHOD 1: Environment Variables (Recommended)")
    print("-" * 80)
    print("""
    Step 1: Create .env file in project root

        cp .env.example .env

    Step 2: Edit .env and add your keys

        WHALE_ALERT_API_KEY=your_api_key_here
        ALPHA_VANTAGE_API_KEY=your_other_key

    Step 3: Import and use (keys auto-loaded)

        from wrdata import DataStream
        stream = DataStream()  # Keys loaded from .env automatically
    """)

    if settings.WHALE_ALERT_API_KEY:
        print("    ✅ Whale Alert key found in environment")
        print(f"       Key: {settings.WHALE_ALERT_API_KEY[:4]}****")
    else:
        print("    ❌ Whale Alert key NOT found in environment")
        print("       Set WHALE_ALERT_API_KEY in .env file")

    print("\n2️⃣  METHOD 2: Constructor Parameters")
    print("-" * 80)
    print("""
    Pass keys directly to DataStream constructor:

        from wrdata import DataStream

        stream = DataStream(
            whale_alert_key="your_whale_alert_key",
            polygon_key="your_polygon_key",
            alphavantage_key="your_alpha_vantage_key"
        )

    Note: Constructor params override environment variables
    """)

    print("\n3️⃣  METHOD 3: Direct Provider Instantiation")
    print("-" * 80)
    print("""
    Create providers directly with API keys:

        from wrdata.providers.whale_alert_provider import WhaleAlertProvider

        provider = WhaleAlertProvider(api_key="your_whale_alert_key")

        batch = provider.fetch_whale_transactions(
            start_date="2025-11-20",
            blockchain="bitcoin",
            min_value=1000000
        )

    Use case: When you don't need the full DataStream, just one provider
    """)

    print("\n" + "=" * 80)


def demo_fallback_pattern():
    """Show how the fallback pattern works."""

    print("\n" + "=" * 80)
    print("🔄 FALLBACK PATTERN DEMO")
    print("=" * 80)

    print("\nThe pattern used throughout wrdata:")
    print("""
    # In DataStream.__init__:
    whale_alert_key = whale_alert_key or settings.WHALE_ALERT_API_KEY

    Priority order:
    1. Constructor parameter (highest priority)
    2. Environment variable (from .env or system)
    3. None (provider not initialized)
    """)

    print("\nExample:")

    # Simulate the pattern
    constructor_key = None  # User didn't pass key to constructor
    env_key = settings.WHALE_ALERT_API_KEY  # From environment

    final_key = constructor_key or env_key

    if constructor_key:
        print(f"  ✅ Using constructor key: {constructor_key[:4]}****")
    elif env_key:
        print(f"  ✅ Using environment key: {env_key[:4]}****")
    else:
        print("  ❌ No key found - provider will not be initialized")

    print("\n" + "=" * 80)


def test_whale_alert_connection():
    """Test Whale Alert API connection if key is configured."""

    print("\n" + "=" * 80)
    print("🐋 WHALE ALERT CONNECTION TEST")
    print("=" * 80)

    if not settings.has_whale_alert_key:
        print("\n⚠️  Whale Alert API key not configured")
        print("\nTo test Whale Alert:")
        print("1. Get API key from https://whale-alert.io/")
        print("2. Add to .env file: WHALE_ALERT_API_KEY=your_key_here")
        print("3. Re-run this script")
        print("\n" + "=" * 80)
        return

    try:
        from wrdata.providers.whale_alert_provider import WhaleAlertProvider

        print("\n📡 Testing connection to Whale Alert API...")
        provider = WhaleAlertProvider(api_key=settings.WHALE_ALERT_API_KEY)

        if provider.validate_connection():
            print("✅ Successfully connected to Whale Alert API")

            status = provider.get_status()
            if status.get("success"):
                print("\n📊 API Status:")
                usage = status.get("usage", {})
                limits = status.get("limits", {})

                if usage:
                    print(f"   Usage: {usage}")
                if limits:
                    print(f"   Limits: {limits}")
            else:
                print("⚠️  Could not retrieve API status")
        else:
            print("❌ Failed to connect to Whale Alert API")
            print("   Check your API key is valid")

    except Exception as e:
        print(f"❌ Error connecting to Whale Alert: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🔑 wrdata API Key Configuration Demo\n")

    # Run all demos
    check_configuration()
    demo_three_configuration_methods()
    demo_fallback_pattern()
    test_whale_alert_connection()

    print("\n✅ Configuration demo complete!\n")

    # Recommendations
    print("💡 Recommendations:")
    print("   1. Use .env file for local development (add to .gitignore)")
    print("   2. Use environment variables in production")
    print("   3. Start with free providers, add paid keys as needed")
    print("   4. Never commit API keys to version control")
    print("\n📚 See docs/API_KEY_MANAGEMENT.md for full documentation\n")
