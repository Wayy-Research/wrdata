# Symbol Discovery API - Quick Reference

Fast reference for the most common symbol discovery operations.

---

## Setup

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from wrdata.services import SymbolDiscoveryService

engine = create_engine('sqlite:///wrdata.db')
Session = sessionmaker(bind=engine)
db = Session()

discovery = SymbolDiscoveryService(db)
```

---

## Common Operations

### Get Symbol Coverage

```python
# Get all providers for a symbol
coverage = discovery.get_symbol_details_with_coverage('AAPL')

# Returns:
{
    'symbol': 'AAPL',
    'asset_type': 'stock',
    'coverage_count': 8,
    'providers': [
        {'provider_name': 'Alpaca', 'exchange': 'NASDAQ', ...},
        ...
    ],
    'best_name': 'Apple Inc.',
    'exchanges': ['NASDAQ']
}
```

### Search Symbols

```python
# Basic search
results = discovery.search_with_coverage('AAPL', limit=10)

# Search with filters
results = discovery.search_with_coverage(
    query='BTC',
    asset_type='crypto',
    min_providers=3,
    limit=50
)
```

### Find Popular Symbols

```python
# Top 100 stocks
popular_stocks = discovery.get_popular_symbols(
    asset_type='stock',
    limit=100
)

# Top crypto pairs
popular_crypto = discovery.get_popular_symbols(
    asset_type='crypto',
    limit=100
)
```

### Find by Coverage

```python
# Symbols on 5+ providers
high_coverage = discovery.find_symbols_by_coverage(
    min_providers=5,
    asset_type='stock'
)

# Provider-exclusive symbols
unique = discovery.find_symbols_by_coverage(
    min_providers=1,
    max_providers=1,
    asset_type='crypto_derivative'
)
```

### Get Statistics

```python
# Provider symbol counts
provider_counts = discovery.get_provider_symbol_count()
# {'binance': 1823, 'coingecko': 14532, ...}

# Asset distribution
asset_dist = discovery.get_asset_type_distribution()
# {'stock': 15234, 'crypto': 18432, ...}
```

### Export Data

```python
# Export to JSON
symbols = discovery.export_symbol_universe(output_format='json')

# Export to CSV
csv_data = discovery.export_symbol_universe(output_format='csv')

# Export to Parquet (requires pandas)
parquet_data = discovery.export_symbol_universe(output_format='parquet')
```

---

## Quick Patterns

### Symbol Autocomplete

```python
def autocomplete(query, limit=10):
    results = discovery.search_with_coverage(query, limit=limit)
    return [
        {
            'symbol': r['symbol'],
            'name': r['best_name'],
            'sources': r['coverage_count']
        }
        for r in results
    ]
```

### Best Provider Selection

```python
def get_best_provider(symbol, preferences=None):
    if not preferences:
        preferences = ['Alpaca', 'Polygon.io', 'Yahoo Finance']

    coverage = discovery.get_symbol_details_with_coverage(symbol)

    for pref in preferences:
        for p in coverage['providers']:
            if pref.lower() in p['provider_name'].lower():
                return p

    return coverage['providers'][0] if coverage['providers'] else None
```

### Multi-Source Data Fetcher

```python
def get_data_with_fallback(symbol, providers=None):
    coverage = discovery.get_symbol_details_with_coverage(symbol)

    if not providers:
        providers = [p['provider_name'] for p in coverage['providers']]

    for provider_name in providers:
        try:
            # Try to fetch from this provider
            data = fetch_from_provider(provider_name, symbol)
            if data:
                return data
        except Exception:
            continue

    raise Exception(f"No provider could fetch {symbol}")
```

### Market Scanner

```python
def scan_high_liquidity_crypto(min_exchanges=10):
    return discovery.find_symbols_by_coverage(
        min_providers=min_exchanges,
        asset_type='crypto',
        limit=100
    )

def scan_optionable_stocks():
    # Find stocks on providers with options support
    results = discovery.search_with_coverage(
        query='',
        asset_type='stock',
        min_providers=1
    )
    return [r for r in results if has_options_provider(r)]
```

---

## CLI Quick Reference

```bash
# Sync all providers
python scripts/sync_all_symbols.py

# Sync specific providers
python scripts/sync_all_symbols.py --providers binance,kraken

# Force re-sync
python scripts/sync_all_symbols.py --force

# Analyze coverage only
python scripts/sync_all_symbols.py --analyze-only

# Custom database
python scripts/sync_all_symbols.py --db custom.db
```

---

## Response Formats

### SymbolCoverage Response

```python
{
    'symbol': str,              # Symbol ticker
    'asset_type': str,          # stock, crypto, forex, etc.
    'coverage_count': int,      # Number of providers
    'providers': [              # List of supporting providers
        {
            'provider_name': str,
            'provider_id': int,
            'name': str,        # Symbol name from this provider
            'exchange': str,    # Exchange name
            'metadata': dict    # Provider-specific data
        },
        ...
    ],
    'common_names': [str],      # All names across providers
    'exchanges': [str],         # All exchanges
    'best_name': str            # Most descriptive name
}
```

### Search Results

```python
[
    {
        'symbol': str,
        'asset_type': str,
        'coverage_count': int,
        'providers': [...],
        'best_name': str,
        ...
    },
    ...
]
```

---

## Error Handling

```python
# Symbol not found
try:
    coverage = discovery.get_symbol_details_with_coverage('INVALID')
    if 'error' in coverage:
        print(f"Error: {coverage['error']}")
except Exception as e:
    print(f"Exception: {e}")

# No results
results = discovery.search_with_coverage('xyz123')
if not results:
    print("No symbols found")

# Handle missing providers
coverage = discovery.get_symbol_details_with_coverage('AAPL')
if coverage['coverage_count'] == 0:
    print("Symbol not available from any provider")
```

---

## Performance Tips

1. **Cache results**: Symbol coverage doesn't change often
2. **Use limits**: Don't fetch all 100K+ symbols at once
3. **Filter early**: Use min_providers to reduce result set
4. **Batch operations**: Group symbol lookups when possible
5. **Index database**: Ensure indexes on symbol, provider_id

---

## Integration Examples

### Flask API

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/symbols/search')
def search_symbols():
    query = request.args.get('q', '')
    asset_type = request.args.get('type')
    limit = int(request.args.get('limit', 20))

    results = discovery.search_with_coverage(
        query=query,
        asset_type=asset_type,
        limit=limit
    )
    return jsonify(results)

@app.route('/api/symbols/<symbol>/coverage')
def get_coverage(symbol):
    coverage = discovery.get_symbol_details_with_coverage(symbol)
    return jsonify(coverage)
```

### FastAPI

```python
from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/symbols/search")
async def search_symbols(
    q: str = Query(...),
    type: str = None,
    min_providers: int = 1,
    limit: int = 20
):
    return discovery.search_with_coverage(
        query=q,
        asset_type=type,
        min_providers=min_providers,
        limit=limit
    )

@app.get("/symbols/{symbol}")
async def get_symbol_info(symbol: str):
    return discovery.get_symbol_details_with_coverage(symbol)
```

---

## Testing

```python
# Test imports
from wrdata.services import SymbolDiscoveryService

# Test basic query
discovery = SymbolDiscoveryService(db)
result = discovery.get_symbol_details_with_coverage('AAPL')
assert result['coverage_count'] > 0

# Test search
results = discovery.search_with_coverage('AAP', limit=5)
assert len(results) <= 5

# Test statistics
counts = discovery.get_provider_symbol_count()
assert len(counts) > 0
```

---

## Troubleshooting

**No symbols found:**
- Run `python scripts/sync_all_symbols.py` first
- Check providers are active in database

**Slow queries:**
- Add database indexes (should be automatic)
- Use limits on queries
- Filter by asset_type early

**Import errors:**
- Ensure `pip install -e .` was run
- Check Python path includes wrdata

---

For complete documentation, see [SYMBOL_DISCOVERY.md](../SYMBOL_DISCOVERY.md)
