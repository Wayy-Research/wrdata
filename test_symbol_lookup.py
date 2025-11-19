#!/usr/bin/env python3
"""
Test script for the new symbol lookup feature.
"""

from wrdata import DataStream

def test_symbol_search():
    """Test the search_symbol functionality."""
    stream = DataStream()

    print("=" * 60)
    print("Testing Symbol Lookup Feature")
    print("=" * 60)

    # Test 1: Search for Bitcoin
    print("\n1. Searching for 'bitcoin'...")
    results = stream.search_symbol("bitcoin", limit=5)
    if results:
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['symbol']:15} - {result['name']}")
            print(f"      Type: {result['type']:15} Provider: {result['provider']}")
    else:
        print("   No results found")

    # Test 2: Search for Ethereum (show multiple providers)
    print("\n2. Searching for 'ethereum' (showing multi-provider results)...")
    results = stream.search_symbol("ethereum", limit=10)
    if results:
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['symbol']:20} - {result['name'][:40]:40}")
            print(f"      Provider: {result['provider']:15} Exchange: {result['exchange']}")
    else:
        print("   No results found")

    # Test 3: Search for Apple
    print("\n3. Searching for 'apple'...")
    results = stream.search_symbol("apple", limit=5)
    if results:
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['symbol']:15} - {result['name']}")
            print(f"      Type: {result['type']:15} Provider: {result['provider']}")
    else:
        print("   No results found")

    # Test 4: Search for Tesla
    print("\n4. Searching for 'tesla'...")
    results = stream.search_symbol("tesla", limit=3)
    if results:
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['symbol']:15} - {result['name']}")
            print(f"      Type: {result['type']:15} Provider: {result['provider']}")
    else:
        print("   No results found")

    # Test 5: Search for ETH (should find Ethereum)
    print("\n5. Searching for 'ETH'...")
    results = stream.search_symbol("ETH", limit=5)
    if results:
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['symbol']:15} - {result['name']}")
            print(f"      Type: {result['type']:15} Provider: {result['provider']}")
    else:
        print("   No results found")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_symbol_search()
