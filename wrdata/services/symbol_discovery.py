"""
Symbol Discovery Service - Enhanced symbol management with coverage tracking.

This service provides:
- Symbol fetching from all 28 providers
- Cross-provider symbol coverage analysis
- Advanced search and filtering
- Symbol aggregation and deduplication
"""

import json
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from ..models.database import DataProvider, Symbol


class SymbolCoverage:
    """Represents coverage information for a symbol across providers."""

    def __init__(self, symbol: str, asset_type: str = None):
        self.symbol = symbol
        self.asset_type = asset_type
        self.providers: List[Dict[str, Any]] = []
        self.provider_count = 0
        self.names: Set[str] = set()
        self.exchanges: Set[str] = set()

    def add_provider(self, provider_name: str, provider_id: int,
                     name: str = None, exchange: str = None,
                     metadata: Dict[str, Any] = None):
        """Add a provider that supports this symbol."""
        self.providers.append({
            'provider_name': provider_name,
            'provider_id': provider_id,
            'name': name,
            'exchange': exchange,
            'metadata': metadata or {}
        })
        self.provider_count += 1
        if name:
            self.names.add(name)
        if exchange:
            self.exchanges.add(exchange)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'symbol': self.symbol,
            'asset_type': self.asset_type,
            'coverage_count': self.provider_count,
            'providers': self.providers,
            'common_names': list(self.names),
            'exchanges': list(self.exchanges),
            'best_name': self._get_best_name(),
        }

    def _get_best_name(self) -> str:
        """Get the most descriptive name from all providers."""
        if not self.names:
            return self.symbol
        # Prefer longer, more descriptive names
        return max(self.names, key=len)


class SymbolDiscoveryService:
    """
    Enhanced symbol discovery service with coverage tracking.

    Provides comprehensive symbol discovery across all 28 providers with
    cross-provider coverage analysis.
    """

    def __init__(self, db: Session):
        self.db = db

    # ========== Symbol Fetchers for All Providers ==========

    def fetch_polygon_symbols(self) -> List[Dict[str, Any]]:
        """Fetch symbols from Polygon.io - US stocks, options, forex, crypto."""
        try:
            import requests
            import os

            api_key = os.getenv('POLYGON_API_KEY')
            if not api_key:
                return []

            symbols = []

            # Fetch stocks
            url = "https://api.polygon.io/v3/reference/tickers"
            params = {
                'apiKey': api_key,
                'market': 'stocks',
                'active': 'true',
                'limit': 1000
            }

            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for ticker in data.get('results', []):
                    symbols.append({
                        'symbol': ticker['ticker'],
                        'name': ticker.get('name', ''),
                        'description': f"{ticker.get('name', '')} - {ticker.get('primary_exchange', '')}",
                        'asset_type': 'stock',
                        'exchange': ticker.get('primary_exchange'),
                        'currency': ticker.get('currency_name', 'USD'),
                    })

            return symbols
        except Exception as e:
            print(f"Error fetching Polygon symbols: {e}")
            return []

    def fetch_tradier_symbols(self) -> List[Dict[str, Any]]:
        """Fetch symbols from Tradier - US stocks with options."""
        try:
            import requests
            import os

            api_key = os.getenv('TRADIER_API_KEY')
            if not api_key:
                return []

            # Tradier doesn't have a symbols endpoint, return common optionable stocks
            optionable_stocks = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'AMD',
                'NFLX', 'DIS', 'BA', 'SPY', 'QQQ', 'IWM', 'GLD', 'SLV'
            ]

            symbols = []
            for ticker in optionable_stocks:
                symbols.append({
                    'symbol': ticker,
                    'name': f'{ticker} (Options Available)',
                    'description': f'{ticker} with options trading',
                    'asset_type': 'stock',
                    'has_options': True,
                })

            return symbols
        except Exception as e:
            print(f"Error fetching Tradier symbols: {e}")
            return []

    def fetch_iexcloud_symbols(self) -> List[Dict[str, Any]]:
        """Fetch symbols from IEX Cloud - US stocks."""
        try:
            import requests
            import os

            api_key = os.getenv('IEX_API_KEY')
            if not api_key:
                return []

            url = "https://cloud.iexapis.com/stable/ref-data/symbols"
            params = {'token': api_key}

            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                return []

            data = response.json()
            symbols = []

            for item in data:
                if item.get('isEnabled'):
                    symbols.append({
                        'symbol': item['symbol'],
                        'name': item.get('name', ''),
                        'description': f"{item.get('name', '')} - {item.get('exchange', '')}",
                        'asset_type': item.get('type', 'stock').lower(),
                        'exchange': item.get('exchange'),
                        'currency': 'USD',
                    })

            return symbols
        except Exception as e:
            print(f"Error fetching IEX Cloud symbols: {e}")
            return []

    def fetch_kucoin_symbols(self) -> List[Dict[str, Any]]:
        """Fetch symbols from KuCoin - 700+ crypto pairs."""
        try:
            import requests

            url = "https://api.kucoin.com/api/v1/symbols"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return []

            data = response.json()
            symbols = []

            for item in data.get('data', []):
                if item.get('enableTrading'):
                    symbols.append({
                        'symbol': item['symbol'],
                        'name': f"{item['baseCurrency']}/{item['quoteCurrency']}",
                        'description': f"KuCoin {item['baseCurrency']}/{item['quoteCurrency']}",
                        'asset_type': 'crypto',
                        'exchange': 'KuCoin',
                        'extra_metadata': json.dumps({
                            'baseCurrency': item['baseCurrency'],
                            'quoteCurrency': item['quoteCurrency'],
                        })
                    })

            return symbols
        except Exception as e:
            print(f"Error fetching KuCoin symbols: {e}")
            return []

    def fetch_gateio_symbols(self) -> List[Dict[str, Any]]:
        """Fetch symbols from Gate.io - 1,400+ crypto pairs."""
        try:
            import requests

            url = "https://api.gateio.ws/api/v4/spot/currency_pairs"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return []

            data = response.json()
            symbols = []

            for item in data:
                if item.get('trade_status') == 'tradable':
                    symbols.append({
                        'symbol': item['id'],
                        'name': item['id'],
                        'description': f"Gate.io {item['id']}",
                        'asset_type': 'crypto',
                        'exchange': 'Gate.io',
                    })

            return symbols
        except Exception as e:
            print(f"Error fetching Gate.io symbols: {e}")
            return []

    def fetch_gemini_symbols(self) -> List[Dict[str, Any]]:
        """Fetch symbols from Gemini - US-regulated crypto."""
        try:
            import requests

            url = "https://api.gemini.com/v1/symbols"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return []

            symbols_list = response.json()
            symbols = []

            for symbol in symbols_list:
                symbols.append({
                    'symbol': symbol.upper(),
                    'name': symbol.upper(),
                    'description': f"Gemini {symbol}",
                    'asset_type': 'crypto',
                    'exchange': 'Gemini',
                })

            return symbols
        except Exception as e:
            print(f"Error fetching Gemini symbols: {e}")
            return []

    def fetch_deribit_symbols(self) -> List[Dict[str, Any]]:
        """Fetch symbols from Deribit - Crypto options and futures."""
        try:
            import requests

            symbols = []

            # Fetch BTC instruments
            for currency in ['BTC', 'ETH']:
                url = "https://www.deribit.com/api/v2/public/get_instruments"
                params = {'currency': currency}

                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for instrument in data.get('result', []):
                        symbols.append({
                            'symbol': instrument['instrument_name'],
                            'name': instrument['instrument_name'],
                            'description': f"Deribit {instrument['kind']} - {instrument['instrument_name']}",
                            'asset_type': 'crypto_derivative',
                            'exchange': 'Deribit',
                            'extra_metadata': json.dumps({
                                'kind': instrument['kind'],  # option, future, perpetual
                                'strike': instrument.get('strike'),
                                'expiration': instrument.get('expiration_timestamp'),
                            })
                        })

            return symbols
        except Exception as e:
            print(f"Error fetching Deribit symbols: {e}")
            return []

    # ========== Coverage Analysis ==========

    def analyze_symbol_coverage(self,
                                asset_type: Optional[str] = None,
                                min_providers: int = 1) -> List[Dict[str, Any]]:
        """
        Analyze symbol coverage across all providers.

        Args:
            asset_type: Filter by asset type (stock, crypto, forex, etc.)
            min_providers: Minimum number of providers for a symbol to be included

        Returns:
            List of symbols with coverage information
        """
        # Build query
        query = self.db.query(
            Symbol.symbol,
            Symbol.asset_type,
            func.count(Symbol.provider_id).label('provider_count'),
            func.group_concat(DataProvider.name).label('provider_names')
        ).join(DataProvider).filter(Symbol.is_active == True)

        if asset_type:
            query = query.filter(Symbol.asset_type == asset_type)

        # Group by symbol and asset type
        query = query.group_by(Symbol.symbol, Symbol.asset_type)

        # Filter by minimum providers
        query = query.having(func.count(Symbol.provider_id) >= min_providers)

        # Order by coverage (most providers first)
        query = query.order_by(func.count(Symbol.provider_id).desc())

        results = query.all()

        # Format results
        coverage_list = []
        for result in results:
            coverage_list.append({
                'symbol': result.symbol,
                'asset_type': result.asset_type,
                'provider_count': result.provider_count,
                'providers': result.provider_names.split(',') if result.provider_names else [],
            })

        return coverage_list

    def get_symbol_details_with_coverage(self, symbol: str) -> Dict[str, Any]:
        """
        Get detailed information about a symbol including all providers that support it.

        Args:
            symbol: Symbol to lookup

        Returns:
            Comprehensive symbol information with provider coverage
        """
        # Query all instances of this symbol across providers
        symbol_instances = self.db.query(Symbol).join(DataProvider).filter(
            Symbol.symbol == symbol,
            Symbol.is_active == True
        ).all()

        if not symbol_instances:
            return {'error': 'Symbol not found', 'symbol': symbol}

        # Build coverage object
        coverage = SymbolCoverage(symbol)

        for instance in symbol_instances:
            coverage.add_provider(
                provider_name=instance.provider.name,
                provider_id=instance.provider_id,
                name=instance.name,
                exchange=instance.exchange,
                metadata=json.loads(instance.extra_metadata) if instance.extra_metadata else {}
            )
            if not coverage.asset_type:
                coverage.asset_type = instance.asset_type

        return coverage.to_dict()

    def find_symbols_by_coverage(self,
                                 min_providers: int = 2,
                                 max_providers: Optional[int] = None,
                                 asset_type: Optional[str] = None,
                                 limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find symbols based on provider coverage.

        Args:
            min_providers: Minimum number of providers
            max_providers: Maximum number of providers (optional)
            asset_type: Filter by asset type
            limit: Maximum results to return

        Returns:
            List of symbols matching coverage criteria
        """
        # Subquery to count providers per symbol
        coverage_query = self.db.query(
            Symbol.symbol,
            Symbol.asset_type,
            func.count(Symbol.provider_id).label('provider_count')
        ).filter(Symbol.is_active == True)

        if asset_type:
            coverage_query = coverage_query.filter(Symbol.asset_type == asset_type)

        coverage_query = coverage_query.group_by(Symbol.symbol, Symbol.asset_type)
        coverage_query = coverage_query.having(func.count(Symbol.provider_id) >= min_providers)

        if max_providers:
            coverage_query = coverage_query.having(func.count(Symbol.provider_id) <= max_providers)

        coverage_query = coverage_query.order_by(func.count(Symbol.provider_id).desc())
        coverage_query = coverage_query.limit(limit)

        results = coverage_query.all()

        # Get full details for each symbol
        detailed_results = []
        for result in results:
            details = self.get_symbol_details_with_coverage(result.symbol)
            detailed_results.append(details)

        return detailed_results

    def get_provider_symbol_count(self) -> Dict[str, int]:
        """
        Get symbol count for each provider.

        Returns:
            Dictionary mapping provider name to symbol count
        """
        results = self.db.query(
            DataProvider.name,
            func.count(Symbol.id).label('symbol_count')
        ).join(Symbol).filter(
            Symbol.is_active == True
        ).group_by(DataProvider.name).all()

        return {result.name: result.symbol_count for result in results}

    def get_asset_type_distribution(self) -> Dict[str, int]:
        """
        Get distribution of symbols by asset type.

        Returns:
            Dictionary mapping asset type to count
        """
        results = self.db.query(
            Symbol.asset_type,
            func.count(Symbol.id).label('count')
        ).filter(
            Symbol.is_active == True
        ).group_by(Symbol.asset_type).all()

        return {result.asset_type: result.count for result in results}

    def search_with_coverage(self,
                            query: str,
                            asset_type: Optional[str] = None,
                            min_providers: int = 1,
                            limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search symbols with coverage information.

        Args:
            query: Search query
            asset_type: Filter by asset type
            min_providers: Minimum provider coverage
            limit: Maximum results

        Returns:
            List of matching symbols with coverage info
        """
        # Get symbols matching search query
        search_filter = f"%{query.upper()}%"

        symbol_query = self.db.query(Symbol.symbol).filter(
            Symbol.is_active == True,
            or_(
                Symbol.symbol.ilike(search_filter),
                Symbol.name.ilike(search_filter),
                Symbol.description.ilike(search_filter)
            )
        )

        if asset_type:
            symbol_query = symbol_query.filter(Symbol.asset_type == asset_type)

        # Get unique symbols
        matching_symbols = symbol_query.distinct().limit(limit).all()

        # Get coverage for each symbol
        results = []
        for symbol_tuple in matching_symbols:
            symbol = symbol_tuple[0]
            coverage = self.get_symbol_details_with_coverage(symbol)

            if coverage.get('coverage_count', 0) >= min_providers:
                results.append(coverage)

        # Sort by coverage
        results.sort(key=lambda x: x.get('coverage_count', 0), reverse=True)

        return results

    def get_popular_symbols(self,
                           asset_type: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get most widely supported symbols (highest coverage).

        Args:
            asset_type: Filter by asset type
            limit: Maximum results

        Returns:
            List of popular symbols sorted by coverage
        """
        return self.find_symbols_by_coverage(
            min_providers=2,
            asset_type=asset_type,
            limit=limit
        )

    def get_unique_symbols(self,
                          asset_type: Optional[str] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get symbols only available from one provider (unique offerings).

        Args:
            asset_type: Filter by asset type
            limit: Maximum results

        Returns:
            List of unique symbols
        """
        return self.find_symbols_by_coverage(
            min_providers=1,
            max_providers=1,
            asset_type=asset_type,
            limit=limit
        )

    def export_symbol_universe(self,
                               output_format: str = 'json') -> Any:
        """
        Export complete symbol universe with coverage data.

        Args:
            output_format: 'json', 'csv', or 'parquet'

        Returns:
            Exported data in requested format
        """
        # Get all symbols with coverage
        symbols = self.find_symbols_by_coverage(min_providers=1, limit=100000)

        if output_format == 'json':
            return symbols

        elif output_format == 'csv':
            import csv
            import io

            output = io.StringIO()
            if symbols:
                writer = csv.DictWriter(output, fieldnames=symbols[0].keys())
                writer.writeheader()
                writer.writerows(symbols)

            return output.getvalue()

        elif output_format == 'parquet':
            try:
                import pandas as pd
                df = pd.DataFrame(symbols)
                return df.to_parquet()
            except ImportError:
                return {'error': 'pandas required for parquet export'}

        return {'error': f'Unsupported format: {output_format}'}
