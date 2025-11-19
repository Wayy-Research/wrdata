#!/usr/bin/env python3
"""Test CCXT provider integration."""

from wrdata import DataStream

def test_ccxt():
    """Test CCXT providers."""
    print("=" * 70)
    print("Testing CCXT Integration")
    print("=" * 70)

    stream = DataStream()

    print(f"\nTotal providers initialized: {len(stream.providers)}")
    print("\nAll providers:")
    for name in sorted(stream.providers.keys()):
        print(f"  • {name}")

    # Count CCXT providers
    ccxt_providers = [n for n in stream.providers.keys() if n.startswith('ccxt_')]
    print(f"\nCCXT providers found: {len(ccxt_providers)}")
    for name in ccxt_providers:
        print(f"  • {name}")

    # Test search with more results
    print("\n" + "=" * 70)
    print("Searching for 'BTC' (limit=50)")
    print("=" * 70)

    results = stream.search_symbol("BTC", limit=50)

    # Group by provider
    by_provider = {}
    for r in results:
        provider = r['provider']
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(r)

    for provider, items in sorted(by_provider.items()):
        print(f"\n{provider.upper()} ({len(items)} results):")
        for item in items[:3]:  # Show first 3 from each
            print(f"  • {item['symbol']:20} - {item['name'][:40]}")

if __name__ == "__main__":
    test_ccxt()
