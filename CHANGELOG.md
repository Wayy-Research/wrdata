# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2026-02-06

### Added
- Polymarket data provider (Gamma API, CLOB API, Data API)
  - Market discovery, search, and tag browsing
  - Historical price timeseries (YES/NO token joining)
  - Order book depth, midpoint, and last trade prices
  - Public trade history
- Polymarket WebSocket streaming
  - Real-time ticker, kline, and order book subscriptions
  - Auto-reconnection with exponential backoff
- Prediction market asset type routing (`prediction_market` -> `polymarket`)

### Fixed
- CI lint failures: ran `black` formatter across entire codebase (81 files)
- Made provider imports in `__init__.py` defensive with try/except
- Added `pytest-cov` and `pytest-asyncio` to dev dependencies

## [0.1.5] - 2026-01-12

### Fixed
- Added `httpx` to requirements.txt

## [0.1.4] - 2026-01-12

### Fixed
- Added `httpx` dependency to pyproject.toml

## [0.1.3] - 2026-01-12

### Added
- Alpaca options provider

## [0.1.2] - 2026-01-12

### Added
- Panoptic DeFi provider

## [0.1.1] - 2026-01-12

### Added
- Whale tracking, DEX providers, and enhanced streaming

## [0.1.0] - 2026-01-12

### Added
- Initial release
- DataStream unified API for market data
- YFinance, Binance, Coinbase, CoinGecko, Kraken providers
- CCXT multi-exchange support
- FRED economic data provider
- Finnhub, Alpaca, Interactive Brokers integrations
- Real-time WebSocket streaming (Coinbase, Finnhub, Alpaca, IBKR)
- Options chain data via YFinance
- Async parallel fetching for large data pulls
- Smart provider routing by asset type with automatic fallback
