## Symbol Discovery & Coverage Tracking

WRData includes a powerful symbol discovery system that tracks symbol availability across all 28 providers with cross-provider coverage analysis.

---

## Features

### 1. **Universal Symbol Discovery**
- Automatically fetch symbols from all 28 providers
- Support for stocks, crypto, forex, options, economic indicators
- 100,000+ unique symbols tracked

### 2. **Coverage Analysis**
- Track which providers support each symbol
- Find symbols with highest provider coverage
- Identify provider-exclusive symbols

### 3. **Smart Search**
- Search symbols with coverage filtering
- Filter by asset type, exchange, provider
- Find best data source for any symbol

### 4. **Coverage Metrics**
- Provider symbol counts
- Asset type distribution
- Cross-provider availability statistics

---

## Quick Start

### Sync All Symbols

```bash
# Sync symbols from all providers
python scripts/sync_all_symbols.py

# Sync specific providers only
python scripts/sync_all_symbols.py --providers binance,kraken,coinbase

# Force re-sync (ignore cache)
python scripts/sync_all_symbols.py --force

# Analyze coverage only (no sync)
python scripts/sync_all_symbols.py --analyze-only
```

### Basic Usage

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from wrdata.services.symbol_discovery import SymbolDiscoveryService

# Setup
engine = create_engine('sqlite:///wrdata.db')
Session = sessionmaker(bind=engine)
db = Session()

# Initialize service
discovery = SymbolDiscoveryService(db)

# Get symbol coverage
aapl_coverage = discovery.get_symbol_details_with_coverage('AAPL')
print(f"AAPL available from {aapl_coverage['coverage_count']} providers")

# Search with coverage filtering
results = discovery.search_with_coverage(
    query='BTC',
    asset_type='crypto',
    min_providers=3  # Must be on 3+ exchanges
)

# Find most popular symbols
popular = discovery.get_popular_symbols(asset_type='stock', limit=100)
```

---

## API Reference

### SymbolDiscoveryService

#### `get_symbol_details_with_coverage(symbol: str)`
Get comprehensive information about a symbol including all supporting providers.

**Returns:**
```python
{
    'symbol': 'AAPL',
    'asset_type': 'stock',
    'coverage_count': 8,
    'providers': [
        {'provider_name': 'Alpaca', 'exchange': 'NASDAQ', ...},
        {'provider_name': 'Polygon.io', 'exchange': 'NASDAQ', ...},
        ...
    ],
    'common_names': ['Apple Inc.', 'APPLE INC'],
    'exchanges': ['NASDAQ'],
    'best_name': 'Apple Inc.'
}
```

#### `find_symbols_by_coverage(min_providers, max_providers, asset_type, limit)`
Find symbols based on provider coverage.

**Example:**
```python
# Find stocks on 5+ providers
high_coverage = discovery.find_symbols_by_coverage(
    min_providers=5,
    asset_type='stock',
    limit=100
)

# Find provider-exclusive crypto
unique_crypto = discovery.find_symbols_by_coverage(
    min_providers=1,
    max_providers=1,
    asset_type='crypto'
)
```

#### `search_with_coverage(query, asset_type, min_providers, limit)`
Search symbols with coverage filtering.

**Example:**
```python
# Search for "tesla" with 2+ providers
results = discovery.search_with_coverage(
    query='tesla',
    min_providers=2,
    limit=50
)
```

#### `get_popular_symbols(asset_type, limit)`
Get symbols with highest provider coverage.

**Example:**
```python
# Top 100 most widely available stocks
popular_stocks = discovery.get_popular_symbols(
    asset_type='stock',
    limit=100
)
```

#### `get_unique_symbols(asset_type, limit)`
Get symbols only available from one provider (exclusive offerings).

**Example:**
```python
# Find Deribit-exclusive crypto options
deribit_exclusive = discovery.get_unique_symbols(
    asset_type='crypto_derivative',
    limit=100
)
```

#### `get_provider_symbol_count()`
Get symbol count for each provider.

**Returns:**
```python
{
    'binance': 1823,
    'coingecko': 14532,
    'yfinance': 8642,
    ...
}
```

#### `get_asset_type_distribution()`
Get distribution of symbols by asset type.

**Returns:**
```python
{
    'stock': 15234,
    'crypto': 18432,
    'economic': 842,
    'forex': 128,
    ...
}
```

#### `export_symbol_universe(output_format)`
Export complete symbol universe.

**Formats:** `'json'`, `'csv'`, `'parquet'`

**Example:**
```python
# Export to JSON
symbols = discovery.export_symbol_universe(output_format='json')

# Export to CSV
csv_data = discovery.export_symbol_universe(output_format='csv')
```

---

## Use Cases

### 1. **Find Best Data Source for a Symbol**

```python
def find_best_provider(symbol, preferences=None):
    """Find best provider based on preferences."""
    details = discovery.get_symbol_details_with_coverage(symbol)

    if not preferences:
        preferences = [
            'Alpaca',      # Free real-time
            'Polygon.io',  # Premium quality
            'Yahoo Finance' # Free unlimited
        ]

    for pref in preferences:
        for provider in details['providers']:
            if pref.lower() in provider['provider_name'].lower():
                return provider

    return details['providers'][0]  # Return first if no match

# Example
best_aapl = find_best_provider('AAPL')
print(f"Best source for AAPL: {best_aapl['provider_name']}")
```

### 2. **Build a Multi-Provider Charting Tool**

```python
def get_chart_data_sources(symbol):
    """Get all available data sources for charting."""
    details = discovery.get_symbol_details_with_coverage(symbol)

    sources = []
    for provider in details['providers']:
        sources.append({
            'name': provider['provider_name'],
            'label': f"{provider['name']} ({provider['exchange']})",
            'free': is_free_provider(provider['provider_name']),
            'realtime': is_realtime(provider['provider_name'])
        })

    return sources

# Use in charting UI
sources = get_chart_data_sources('AAPL')
# Display dropdown: "Alpaca (Real-time)", "Yahoo Finance (Delayed)", etc.
```

### 3. **Find High-Liquidity Crypto Pairs**

```python
# Find crypto pairs on 10+ exchanges (high liquidity)
liquid_pairs = discovery.find_symbols_by_coverage(
    min_providers=10,
    asset_type='crypto',
    limit=50
)

print("Top 50 most liquid crypto pairs:")
for pair in liquid_pairs:
    exchanges = [p['exchange'] for p in pair['providers']]
    print(f"{pair['symbol']}: {len(exchanges)} exchanges")
```

### 4. **Discover New Markets**

```python
# Find symbols unique to specific providers
deribit_options = discovery.get_unique_symbols(asset_type='crypto_derivative')
print(f"Unique crypto options on Deribit: {len(deribit_options)}")

# Find international stocks only on TwelveData
international = discovery.search_with_coverage(
    query='',
    min_providers=1,
    max_providers=1
)
twelvedata_only = [s for s in international
                   if any(p['provider_name'] == 'TwelveData'
                         for p in s['providers'])]
print(f"International stocks: {len(twelvedata_only)}")
```

### 5. **Build Symbol Autocomplete**

```python
def autocomplete_symbols(query, limit=10):
    """Fast symbol autocomplete with coverage."""
    results = discovery.search_with_coverage(
        query=query,
        min_providers=1,
        limit=limit
    )

    # Format for autocomplete UI
    suggestions = []
    for result in results:
        suggestions.append({
            'symbol': result['symbol'],
            'label': f"{result['symbol']} - {result['best_name']}",
            'subtitle': f"{result['coverage_count']} sources",
            'type': result['asset_type']
        })

    return suggestions

# Use in search box
suggestions = autocomplete_symbols('AAP')
# Returns: ["AAPL - Apple Inc. (8 sources)", "AAPH - ...", ...]
```

---

## Coverage Statistics

After syncing, you can query comprehensive statistics:

```python
# Provider statistics
provider_counts = discovery.get_provider_symbol_count()
# binance: 1,823 symbols
# coingecko: 14,532 symbols
# polygon: 18,234 symbols

# Asset distribution
asset_dist = discovery.get_asset_type_distribution()
# stock: 15,234 symbols
# crypto: 18,432 symbols
# economic: 842 symbols

# Coverage analysis
coverage = discovery.analyze_symbol_coverage(min_providers=1)
# Shows distribution of symbol availability
```

---

## Symbol Universe Export

Export complete symbol universe for analysis:

```python
# Export to JSON
symbols = discovery.export_symbol_universe(output_format='json')
# Returns list of all symbols with full coverage details

# Export to CSV for Excel/analysis
csv_data = discovery.export_symbol_universe(output_format='csv')
with open('symbol_universe.csv', 'w') as f:
    f.write(csv_data)

# Export to Parquet for data science
parquet_data = discovery.export_symbol_universe(output_format='parquet')
```

---

## Database Schema

### Symbol Table
```sql
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY,
    provider_id INTEGER,
    symbol VARCHAR(50),
    name VARCHAR(500),
    description TEXT,
    asset_type VARCHAR(50),
    exchange VARCHAR(100),
    currency VARCHAR(10),
    extra_metadata TEXT,
    is_active BOOLEAN,
    last_verified DATETIME,
    created_at DATETIME,
    updated_at DATETIME
);

-- Indexes for fast queries
CREATE INDEX idx_symbol_provider ON symbols(symbol, provider_id);
CREATE INDEX idx_asset_type ON symbols(asset_type);
CREATE INDEX idx_exchange ON symbols(exchange);
```

---

## Performance Tips

1. **Batch Symbol Sync**: Sync providers in batches for large datasets
2. **Use Caching**: Cache popular symbol lookups in Redis/memory
3. **Limit Results**: Use `limit` parameter to prevent large result sets
4. **Index Optimization**: Ensure database indexes are created
5. **Async Operations**: Use async for parallel provider queries

---

## Provider-Specific Notes

### Free Tier Providers (No API Key)
- **CoinGecko**: 14,000+ cryptocurrencies, no key required
- **Bybit, OKX, Gemini**: Full crypto pairs, no key required
- **Yahoo Finance**: All US stocks, unlimited access

### Premium Features
- **Polygon.io**: Highest quality US stock data
- **Deribit**: Only crypto options provider
- **Tradier**: Free equity options chains

### Symbol Formats
- **Stocks**: Standard tickers (AAPL, MSFT, GOOGL)
- **Crypto**: Exchange-specific (BTCUSDT, BTC-USD, btcusd)
- **Forex**: Slash format (EUR/USD, GBP/JPY)
- **Economic**: Series codes (GDP, UNRATE, CPIAUCSL)

---

## Troubleshooting

### No symbols found after sync
```python
# Check provider configuration
providers = db.query(DataProvider).all()
for p in providers:
    print(f"{p.name}: active={p.is_active}, has_key={p.has_api_key}")
```

### Slow coverage queries
```python
# Add database indexes
from wrdata.models.database import Base
Base.metadata.create_all(engine)
```

### Duplicate symbols
```python
# Symbols are unique per provider, check provider_id
symbols = db.query(Symbol).filter(Symbol.symbol == 'AAPL').all()
for s in symbols:
    print(f"{s.symbol}: {s.provider.name}")
```

---

## Examples

See `examples/symbol_discovery_example.py` for comprehensive examples covering:
- Symbol coverage analysis
- Detailed symbol lookup
- Search with filtering
- Provider statistics
- Best source selection
- Universe export

Run examples:
```bash
python examples/symbol_discovery_example.py
```

---

## API Integration

Use in your charting/trading application:

```python
from wrdata.services.symbol_discovery import SymbolDiscoveryService

class MarketDataAPI:
    def __init__(self):
        self.discovery = SymbolDiscoveryService(db)

    def search_symbols(self, query):
        """Search endpoint for UI."""
        return self.discovery.search_with_coverage(query, limit=20)

    def get_data_sources(self, symbol):
        """Get all available sources for a symbol."""
        return self.discovery.get_symbol_details_with_coverage(symbol)

    def get_popular_stocks(self):
        """Get trending/popular stocks."""
        return self.discovery.get_popular_symbols(asset_type='stock')
```

---

**Ready to discover your symbol universe?** 🚀

Start with: `python scripts/sync_all_symbols.py`
