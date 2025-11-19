#!/usr/bin/env python3
"""Test CCXT specific symbol search."""

from wrdata import DataStream

def test_ccxt_specific():
    """Test searching for a symbol that's more common on CCXT exchanges."""
    stream = DataStream()

    print("=" * 70)
    print("Testing CCXT-Specific Symbol Search")
    print("=" * 70)

    # Test with higher limit
    print("\nSearching for 'DOGE' (limit=100)...")
    results = stream.search_symbol("DOGE", limit=100)

    # Group by provider
    by_provider = {}
    for r in results:
        provider = r['provider']
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(r)

    for provider, items in sorted(by_provider.items()):
        print(f"\n{provider.upper()} ({len(items)} results):")
        for item in items[:5]:  # Show first 5 from each
            print(f"  • {item['symbol']:25} - {item['name'][:30]}")

if __name__ == "__main__":
    test_ccxt_specific()
