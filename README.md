# WRData - Universal Data Gathering Package

![Tests](https://github.com/YOUR_USERNAME/wrdata/workflows/Tests/badge.svg)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/YOUR_USERNAME/GIST_ID/raw/wrdata-coverage.json)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

WRData is a unified data gathering package for financial and market data across multiple asset classes and providers.

## Features

- **Multi-Asset Support**: Stocks, crypto, forex, economic data, bonds, commodities
- **28 Data Providers**: Yahoo Finance, Binance, Kraken, FRED, Polygon, Alpaca, and 22 more
- **Symbol Discovery**: Cross-provider symbol search with coverage tracking (100,000+ symbols)
- **Coverage Analysis**: Find symbols available from multiple providers
- **Unified API**: Consistent interface across all data providers
- **Database Integration**: Built-in SQLAlchemy models for symbol storage
- **Type Safety**: Full Pydantic v2 support
- **Options Data**: Support for equity and crypto options chains

## Installation

```bash
pip install -e /path/to/wrdata
```

## Quick Start

### Symbol Discovery & Coverage

```bash
# Sync symbols from all 28 providers
python scripts/sync_all_symbols.py

# Analyze coverage
python scripts/sync_all_symbols.py --analyze-only
```

```python
from wrdata.services import SymbolDiscoveryService

# Find symbols with coverage info
discovery = SymbolDiscoveryService(db_session)

# Get all providers supporting a symbol
aapl_coverage = discovery.get_symbol_details_with_coverage('AAPL')
print(f"AAPL available from {aapl_coverage['coverage_count']} providers")

# Search with coverage filtering
btc_results = discovery.search_with_coverage(
    query='BTC',
    asset_type='crypto',
    min_providers=3  # Must be on 3+ exchanges
)

# Find most popular symbols
popular = discovery.get_popular_symbols(asset_type='stock', limit=100)
```

### Data Fetching

```python
from wrdata import DataFetcher

# Fetch data
fetcher = DataFetcher()
data = fetcher.get_data(
    symbol="AAPL",
    asset_type="equity",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

**See [SYMBOL_DISCOVERY.md](SYMBOL_DISCOVERY.md) for complete documentation.**

## Active Providers: 28

### GOAL EXCEEDED: 28 Providers (112% of goal)

**Stock & Options (12 providers):**
1. **Alpaca** - US stocks, free real-time IEX data, paper trading
2. **Polygon.io** - Premium US data (best quality)
3. **Tradier** - FREE options chains (unique)
4. **TwelveData** - Global stocks, 800 calls/day
5. **IBKR** - Global markets, options, futures (with Docker support)
6. **Finnhub** - Global stocks + WebSocket + news
7. **Alpha Vantage** - Multi-asset
8. **Yahoo Finance** - Unlimited free (delayed)
9. **IEX Cloud** - US stocks, 500K calls/month free
10. **TD Ameritrade** - US stocks + OPTIONS
11. **Marketstack** - 70+ global exchanges
12. **Tiingo** - Stocks + news sentiment

**Cryptocurrency (15 providers):**
13. **Binance** - Global leader, 1000+ pairs
14. **Coinbase** - US-friendly, 748 pairs (legacy)
15. **Coinbase Advanced** - New Coinbase API
16. **Kraken** - European exchange, 200+ pairs
17. **KuCoin** - 700+ trading pairs
18. **Bybit** - Derivatives specialist
19. **OKX** - Global exchange
20. **Gate.io** - 1,400+ trading pairs
21. **Bitfinex** - Established exchange
22. **Gemini** - US-regulated (Winklevoss)
23. **Huobi (HTX)** - 600+ pairs
24. **CoinGecko** - NO API KEY, 10K+ cryptos
25. **CryptoCompare** - 100K calls/month free
26. **Messari** - Research + metrics
27. **Deribit** - CRYPTO OPTIONS (unique)

**Economic Data (1 provider):**
28. **FRED** - 800,000+ economic indicators

**Progress: 112% COMPLETE**

See [PROVIDER_SETUP_GUIDE.md](PROVIDER_SETUP_GUIDE.md) for setup instructions.

### Docker Support

**IBKR with Docker** - Run IB Gateway in a container (no local installation):
```bash
cd docker/ibkr
./start.sh
```
See [IBKR_DOCKER_QUICKSTART.md](IBKR_DOCKER_QUICKSTART.md) for details.

## Architecture

```
wrdata/
├── providers/          # Data provider adapters
│   ├── base.py        # Base provider interface
│   ├── yfinance.py    # Yahoo Finance adapter
│   ├── binance.py     # Binance adapter
│   └── ...
├── models/            # Database and Pydantic models
├── services/          # Business logic services
└── utils/             # Utility functions
```

## Development

### Running Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=wrdata --cov-report=term-missing

# Run integration tests (may hit external APIs)
pytest tests/integration/ -v -m integration

# Run specific test file
pytest tests/unit/test_providers.py -v
```

### Code Quality

```bash
# Format code with black
black wrdata/ tests/

# Lint with ruff
ruff check wrdata/ tests/

# Type check with mypy
mypy wrdata/ --ignore-missing-imports
```

### Test Coverage

Current test coverage: **50%+**

We use pytest with coverage reporting. All pull requests should:
- Include tests for new features
- Maintain or improve overall coverage
- Pass all existing tests

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT
