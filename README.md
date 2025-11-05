# WRData - Universal Data Gathering Package

WRData is a unified data gathering package for financial and market data across multiple asset classes and providers.

## Features

- **Multi-Asset Support**: Stocks, crypto, forex, economic data, bonds, commodities
- **Multiple Providers**: Yahoo Finance, Binance, Kraken, FRED, AlphaVantage, TwelveData, CoinGecko, and more
- **Symbol Management**: Automated symbol discovery and caching
- **Unified API**: Consistent interface across all data providers
- **Database Integration**: Built-in SQLAlchemy models for symbol storage
- **Type Safety**: Full Pydantic v2 support

## Installation

```bash
pip install -e /path/to/wrdata
```

## Quick Start

```python
from wrdata import SymbolManager, DataFetcher

# Initialize symbol manager
manager = SymbolManager(db_session)

# Sync symbols from all providers
await manager.sync_all_providers()

# Fetch data
fetcher = DataFetcher()
data = fetcher.get_data(
    symbol="AAPL",
    asset_type="equity",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

## Supported Providers

- **Yahoo Finance**: Stocks, ETFs, indices, forex
- **Binance**: Crypto spot and futures
- **Kraken**: Crypto spot trading
- **FRED**: Economic indicators
- **AlphaVantage**: Stocks, forex, crypto
- **TwelveData**: Multi-asset financial data
- **CoinGecko**: Cryptocurrency market data
- **Polygon.io**: Real-time and historical market data

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

## License

MIT
