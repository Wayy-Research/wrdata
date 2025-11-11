"""
Symbol Sync Script - Fetch and sync symbols from all 28 providers.

This script discovers all available symbols across providers and stores them
in the database with coverage tracking.

Usage:
    python scripts/sync_all_symbols.py [--force] [--providers PROVIDER1,PROVIDER2]
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from wrdata.models.database import Base, DataProvider, Symbol
from wrdata.services.symbol_manager import SymbolManager
from wrdata.services.symbol_discovery import SymbolDiscoveryService
from datetime import datetime


def init_providers(db):
    """Initialize all 28 providers in the database."""
    providers = [
        # Stock & Options
        {'name': 'alpaca', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock,options'},
        {'name': 'polygon', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock,options,forex,crypto'},
        {'name': 'tradier', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock,options'},
        {'name': 'twelvedata', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock,forex'},
        {'name': 'ibkr', 'provider_type': 'stock', 'api_key_required': False, 'supported_assets': 'stock,options,futures,forex'},
        {'name': 'finnhub', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock,forex,crypto'},
        {'name': 'alphavantage', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock,forex,crypto'},
        {'name': 'yfinance', 'provider_type': 'stock', 'api_key_required': False, 'supported_assets': 'stock,options,forex'},
        {'name': 'iexcloud', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock'},
        {'name': 'tdameritrade', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock,options'},
        {'name': 'marketstack', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock'},
        {'name': 'tiingo', 'provider_type': 'stock', 'api_key_required': True, 'supported_assets': 'stock'},

        # Cryptocurrency
        {'name': 'binance', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'coinbase', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'coinbase_advanced', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'kraken', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'kucoin', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'bybit', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'okx', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'gateio', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'bitfinex', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'gemini', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'huobi', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'coingecko', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'cryptocompare', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'messari', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto'},
        {'name': 'deribit', 'provider_type': 'crypto', 'api_key_required': False, 'supported_assets': 'crypto,options'},

        # Economic Data
        {'name': 'fred', 'provider_type': 'economic', 'api_key_required': True, 'supported_assets': 'economic'},
    ]

    for provider_data in providers:
        existing = db.query(DataProvider).filter(
            DataProvider.name == provider_data['name']
        ).first()

        if not existing:
            provider = DataProvider(**provider_data)
            db.add(provider)
            print(f"✅ Added provider: {provider_data['name']}")
        else:
            print(f"⏭️  Provider already exists: {provider_data['name']}")

    db.commit()
    print(f"\n✅ All {len(providers)} providers initialized!")


def sync_symbols(db, provider_names=None, force=False):
    """Sync symbols from specified providers or all providers."""
    manager = SymbolManager(db)
    discovery = SymbolDiscoveryService(db)

    # Get providers to sync
    query = db.query(DataProvider).filter(DataProvider.is_active == True)

    if provider_names:
        query = query.filter(DataProvider.name.in_(provider_names))

    providers = query.all()

    if not providers:
        print("❌ No providers found to sync")
        return

    print(f"\n🔄 Syncing symbols from {len(providers)} providers...")
    print("=" * 60)

    results = []
    for provider in providers:
        print(f"\nSyncing {provider.name}...")

        try:
            # Use existing manager methods or discovery service
            result = manager.sync_provider_symbols(provider.id, force=force)

            if result.get('success'):
                print(f"✅ {provider.name}: {result['created']} created, {result['updated']} updated")
                results.append(result)
            else:
                print(f"⚠️  {provider.name}: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"❌ {provider.name}: {str(e)}")

    print("\n" + "=" * 60)
    print("Sync Summary")
    print("=" * 60)

    total_created = sum(r.get('created', 0) for r in results)
    total_updated = sum(r.get('updated', 0) for r in results)
    total_symbols = sum(r.get('total_symbols', 0) for r in results)

    print(f"Providers synced: {len(results)}")
    print(f"Symbols created: {total_created:,}")
    print(f"Symbols updated: {total_updated:,}")
    print(f"Total symbols: {total_symbols:,}")


def analyze_coverage(db):
    """Analyze and display symbol coverage statistics."""
    discovery = SymbolDiscoveryService(db)

    print("\n" + "=" * 60)
    print("Coverage Analysis")
    print("=" * 60)

    # Provider statistics
    provider_counts = discovery.get_provider_symbol_count()
    print("\n📊 Symbols per provider:")
    for provider, count in sorted(provider_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {provider}: {count:,} symbols")

    # Asset type distribution
    asset_dist = discovery.get_asset_type_distribution()
    print("\n📊 Asset type distribution:")
    for asset_type, count in sorted(asset_dist.items(), key=lambda x: x[1], reverse=True):
        print(f"  {asset_type}: {count:,} symbols")

    # High-coverage symbols
    print("\n📊 Top 10 symbols with highest coverage:")
    popular = discovery.get_popular_symbols(limit=10)
    for symbol_info in popular:
        print(f"  {symbol_info['symbol']}: {symbol_info['coverage_count']} providers")

    # Coverage distribution
    coverage_ranges = {
        '1': 0,
        '2-3': 0,
        '4-5': 0,
        '6-9': 0,
        '10+': 0,
    }

    # Get coverage for all symbols
    all_symbols = discovery.find_symbols_by_coverage(min_providers=1, limit=100000)
    for symbol_info in all_symbols:
        count = symbol_info['coverage_count']
        if count == 1:
            coverage_ranges['1'] += 1
        elif count <= 3:
            coverage_ranges['2-3'] += 1
        elif count <= 5:
            coverage_ranges['4-5'] += 1
        elif count <= 9:
            coverage_ranges['6-9'] += 1
        else:
            coverage_ranges['10+'] += 1

    print("\n📊 Coverage distribution:")
    total = sum(coverage_ranges.values())
    for range_label, count in coverage_ranges.items():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {range_label} providers: {count:,} symbols ({percentage:.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Sync symbols from all providers')
    parser.add_argument('--force', action='store_true', help='Force re-sync even if recently synced')
    parser.add_argument('--providers', type=str, help='Comma-separated list of provider names to sync')
    parser.add_argument('--init-only', action='store_true', help='Only initialize providers, do not sync')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze coverage, do not sync')
    parser.add_argument('--db', type=str, default='wrdata.db', help='Database path (default: wrdata.db)')

    args = parser.parse_args()

    # Setup database
    db_path = args.db
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    print("=" * 60)
    print("WRData Symbol Sync - 28 Providers")
    print("=" * 60)

    try:
        # Initialize providers
        init_providers(db)

        if args.init_only:
            print("\n✅ Provider initialization complete!")
            return

        if args.analyze_only:
            analyze_coverage(db)
            return

        # Sync symbols
        provider_list = args.providers.split(',') if args.providers else None
        sync_symbols(db, provider_names=provider_list, force=args.force)

        # Analyze coverage
        analyze_coverage(db)

        print("\n✅ Symbol sync complete!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Sync interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    main()
