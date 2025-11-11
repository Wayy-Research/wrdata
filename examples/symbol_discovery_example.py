"""
Example: Symbol Discovery and Coverage Analysis

This example demonstrates how to:
1. Discover symbols across all providers
2. Analyze cross-provider coverage
3. Search for symbols with filtering
4. Find the best data sources for each symbol
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from wrdata.services.symbol_discovery import SymbolDiscoveryService
from wrdata.models.database import Base

# Setup database
engine = create_engine('sqlite:///wrdata.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

# Initialize discovery service
discovery = SymbolDiscoveryService(db)

# ========== Example 1: Get Symbol Coverage ==========
print("=" * 60)
print("Example 1: Analyze Symbol Coverage")
print("=" * 60)

# Find symbols available from multiple providers
popular_stocks = discovery.find_symbols_by_coverage(
    min_providers=3,  # At least 3 providers
    asset_type='stock',
    limit=10
)

print(f"\nTop 10 stocks with 3+ providers:")
for symbol_info in popular_stocks:
    print(f"\n{symbol_info['symbol']}")
    print(f"  Coverage: {symbol_info['coverage_count']} providers")
    print(f"  Providers: {', '.join([p['provider_name'] for p in symbol_info['providers']])}")
    print(f"  Name: {symbol_info['best_name']}")

# ========== Example 2: Get Detailed Symbol Information ==========
print("\n" + "=" * 60)
print("Example 2: Get Detailed Symbol Information")
print("=" * 60)

# Get all providers that support AAPL
aapl_details = discovery.get_symbol_details_with_coverage('AAPL')

print(f"\nSymbol: {aapl_details['symbol']}")
print(f"Asset Type: {aapl_details['asset_type']}")
print(f"Coverage: {aapl_details['coverage_count']} providers")
print(f"\nAvailable from:")
for provider in aapl_details['providers']:
    print(f"  - {provider['provider_name']}: {provider['name']} ({provider['exchange']})")

# ========== Example 3: Search Symbols with Coverage ==========
print("\n" + "=" * 60)
print("Example 3: Search Symbols with Coverage")
print("=" * 60)

# Search for Bitcoin across all providers
btc_results = discovery.search_with_coverage(
    query='BTC',
    asset_type='crypto',
    min_providers=2,  # Must be available from at least 2 providers
    limit=10
)

print(f"\nBitcoin symbols with 2+ providers:")
for result in btc_results:
    print(f"\n{result['symbol']}")
    print(f"  Coverage: {result['coverage_count']} providers")
    print(f"  Exchanges: {', '.join(result['exchanges'])}")

# ========== Example 4: Find Unique Symbols ==========
print("\n" + "=" * 60)
print("Example 4: Find Unique Symbols (Provider-Specific)")
print("=" * 60)

# Find symbols only available from Deribit (crypto options)
unique_symbols = discovery.get_unique_symbols(
    asset_type='crypto_derivative',
    limit=10
)

print(f"\nUnique crypto derivatives (only from one provider):")
for symbol_info in unique_symbols:
    if symbol_info['coverage_count'] == 1:
        provider = symbol_info['providers'][0]
        print(f"  {symbol_info['symbol']} - {provider['provider_name']}")

# ========== Example 5: Get Provider Statistics ==========
print("\n" + "=" * 60)
print("Example 5: Provider Statistics")
print("=" * 60)

# Get symbol counts per provider
provider_counts = discovery.get_provider_symbol_count()

print("\nSymbols per provider:")
for provider, count in sorted(provider_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {provider}: {count:,} symbols")

# Get asset type distribution
asset_dist = discovery.get_asset_type_distribution()

print("\nAsset type distribution:")
for asset_type, count in sorted(asset_dist.items(), key=lambda x: x[1], reverse=True):
    print(f"  {asset_type}: {count:,} symbols")

# ========== Example 6: Find Best Data Source for Symbol ==========
print("\n" + "=" * 60)
print("Example 6: Find Best Data Source for Symbol")
print("=" * 60)

def find_best_provider(symbol: str, preferences: list = None) -> dict:
    """
    Find the best provider for a symbol based on preferences.

    Args:
        symbol: Symbol to look up
        preferences: Ordered list of preferred provider names

    Returns:
        Best provider match with reasoning
    """
    details = discovery.get_symbol_details_with_coverage(symbol)

    if 'error' in details:
        return {'error': f'Symbol {symbol} not found'}

    if not preferences:
        # Default preferences: free > premium, real-time > delayed
        preferences = [
            'Alpaca',  # Free real-time US stocks
            'IEX Cloud',  # Free US stocks
            'Polygon.io',  # Premium quality
            'Yahoo Finance',  # Unlimited free
            'Binance',  # Crypto leader
            'CoinGecko',  # Free crypto, no key needed
        ]

    # Find first matching provider from preferences
    for pref in preferences:
        for provider in details['providers']:
            if pref.lower() in provider['provider_name'].lower():
                return {
                    'symbol': symbol,
                    'provider': provider['provider_name'],
                    'name': provider['name'],
                    'exchange': provider['exchange'],
                    'reason': f'Matches preference: {pref}',
                    'total_providers': details['coverage_count']
                }

    # If no preference match, return first provider
    if details['providers']:
        provider = details['providers'][0]
        return {
            'symbol': symbol,
            'provider': provider['provider_name'],
            'name': provider['name'],
            'exchange': provider['exchange'],
            'reason': 'No preference match, using first available',
            'total_providers': details['coverage_count']
        }

    return {'error': 'No providers found'}

# Test best provider selection
for symbol in ['AAPL', 'BTCUSDT', 'EUR/USD', 'GDP']:
    result = find_best_provider(symbol)
    if 'error' not in result:
        print(f"\n{result['symbol']}:")
        print(f"  Best Provider: {result['provider']}")
        print(f"  Reason: {result['reason']}")
        print(f"  Total Providers Available: {result['total_providers']}")

# ========== Example 7: Export Symbol Universe ==========
print("\n" + "=" * 60)
print("Example 7: Export Symbol Universe")
print("=" * 60)

# Export to JSON
all_symbols = discovery.export_symbol_universe(output_format='json')
print(f"\nTotal symbols in universe: {len(all_symbols):,}")

# Get coverage statistics
coverage_stats = {
    '1 provider': 0,
    '2-3 providers': 0,
    '4-5 providers': 0,
    '6+ providers': 0,
}

for symbol_info in all_symbols:
    count = symbol_info['coverage_count']
    if count == 1:
        coverage_stats['1 provider'] += 1
    elif count <= 3:
        coverage_stats['2-3 providers'] += 1
    elif count <= 5:
        coverage_stats['4-5 providers'] += 1
    else:
        coverage_stats['6+ providers'] += 1

print("\nCoverage distribution:")
for category, count in coverage_stats.items():
    percentage = (count / len(all_symbols)) * 100 if all_symbols else 0
    print(f"  {category}: {count:,} symbols ({percentage:.1f}%)")

# ========== Example 8: Find High-Coverage Crypto Pairs ==========
print("\n" + "=" * 60)
print("Example 8: Find High-Coverage Crypto Pairs")
print("=" * 60)

# Find crypto pairs available on 5+ exchanges
popular_crypto = discovery.find_symbols_by_coverage(
    min_providers=5,
    asset_type='crypto',
    limit=20
)

print(f"\nTop 20 crypto pairs with 5+ exchanges:")
for symbol_info in popular_crypto:
    exchanges = [p['exchange'] for p in symbol_info['providers'] if p.get('exchange')]
    print(f"\n{symbol_info['symbol']}")
    print(f"  Available on {len(exchanges)} exchanges: {', '.join(set(exchanges))}")

print("\n" + "=" * 60)
print("Symbol Discovery Examples Complete!")
print("=" * 60)

# Clean up
db.close()
