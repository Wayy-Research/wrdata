#!/usr/bin/env python3
"""
Test crypto-specific symbol search across providers.
"""

from wrdata import DataStream

def test_crypto_search():
    """Test crypto search across CoinGecko, Kraken, Coinbase."""
    stream = DataStream()

    print("=" * 70)
    print("Testing Crypto Symbol Search Across Multiple Providers")
    print("=" * 70)

    # Test 1: Bitcoin
    print("\n1. Searching for 'BTC'...")
    results = stream.search_symbol("BTC", limit=15)

    # Group by provider
    by_provider = {}
    for r in results:
        provider = r['provider']
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(r)

    for provider, items in by_provider.items():
        print(f"\n   {provider.upper()} ({len(items)} results):")
        for item in items[:5]:  # Show first 5 from each
            print(f"      • {item['symbol']:20} - {item['name'][:40]}")

    # Test 2: ETH
    print("\n\n2. Searching for 'ETH'...")
    results = stream.search_symbol("ETH", limit=15)

    # Group by provider
    by_provider = {}
    for r in results:
        provider = r['provider']
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(r)

    for provider, items in by_provider.items():
        print(f"\n   {provider.upper()} ({len(items)} results):")
        for item in items[:5]:
            print(f"      • {item['symbol']:20} - {item['name'][:40]}")

    # Test 3: SOL
    print("\n\n3. Searching for 'SOL' (Solana)...")
    results = stream.search_symbol("SOL", limit=15)

    # Group by provider
    by_provider = {}
    for r in results:
        provider = r['provider']
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(r)

    for provider, items in by_provider.items():
        print(f"\n   {provider.upper()} ({len(items)} results):")
        for item in items[:5]:
            print(f"      • {item['symbol']:20} - {item['name'][:40]}")

    print("\n" + "=" * 70)
    print("Provider Coverage Summary")
    print("=" * 70)

    providers = stream.providers
    print(f"\nTotal providers initialized: {len(providers)}")
    for name in sorted(providers.keys()):
        print(f"  ✓ {name}")

if __name__ == "__main__":
    test_crypto_search()
