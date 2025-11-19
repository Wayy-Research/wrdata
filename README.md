# WRData - Dead Simple Market Data

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Get stock, crypto, forex, and economic data with one simple API. No database required.

## Installation

```bash
pip install wrdata
```

## Quick Start

```python
from wrdata import DataStream

stream = DataStream()

# Get stock data
df = stream.get("AAPL")

# Get crypto data (auto-detected!)
df = stream.get("BTCUSDT")

# Get options chain
chain = stream.options("SPY")

# That's it!
```

## Usage

### Get Historical Data

```python
from wrdata import DataStream

stream = DataStream()

# Default: 1 year of daily data
df = stream.get("AAPL")

# Custom date range
df = stream.get("AAPL", start="2024-01-01", end="2024-12-31")

# Intraday data
df = stream.get("AAPL", interval="5m", start="2024-11-19")
```

### Get Multiple Symbols

```python
data = stream.get_many(["AAPL", "GOOGL", "MSFT"])

for symbol, df in data.items():
    print(f"{symbol}: {len(df)} rows")
```

### Get Options Data

```python
# Get available expiration dates
expirations = stream.get_expirations("SPY")

# Get options chain
chain = stream.options("SPY")

# Filter options
calls = stream.options("SPY", option_type="call", strike_min=580, strike_max=600)
```

### Use Your API Keys

Add your API keys via environment variables or `.env` file:

```bash
# .env file
POLYGON_API_KEY=your_key_here
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here
```

Or pass them directly:

```python
stream = DataStream(
    polygon_key="your_key",
    binance_key="your_key",
    binance_secret="your_secret"
)
```

## Supported Providers

**Free (No API Key Required):**
- Yahoo Finance - Stocks, ETFs, crypto (delayed)
- Binance - Crypto market data
- Coinbase - Crypto market data
- CoinGecko - 10,000+ cryptocurrencies

**Free (API Key Required):**
- Alpha Vantage - Stocks, forex (5 calls/min)
- FRED - 800,000+ economic indicators
- Finnhub - Stocks + WebSocket (60 calls/min)
- Alpaca - Real-time US stocks + paper trading
- CoinGecko Pro - Higher rate limits
- CryptoCompare - 100K calls/month

**Premium:**
- Polygon.io - High-quality US market data
- Interactive Brokers - Global markets + options + futures
- TwelveData - Global stocks (800 calls/day free)
- Tradier - FREE options chains
- And 15+ more crypto exchanges

**Total: 28 data providers**

See [PROVIDER_SETUP_GUIDE.md](PROVIDER_SETUP_GUIDE.md) for API key setup instructions.

## Asset Types

Asset types are **auto-detected** from the symbol:

```python
# Stocks (auto-detected)
stream.get("AAPL")

# Crypto (auto-detected from USDT suffix)
stream.get("BTCUSDT")

# Forex (auto-detected from 6-char pattern)
stream.get("EURUSD")

# Economic data (auto-detected)
stream.get("GDP")

# Or specify explicitly if needed
stream.get("AAPL", asset_type="equity")
```

## Advanced Features

### Check Provider Status

```python
status = stream.status()
print(status)
```

### Force Specific Provider

```python
df = stream.get("AAPL", provider="polygon")
```

### Get Provider Info

```python
print(stream)  # Shows available providers
```

## Output Format

All data is returned as Polars DataFrames:

```python
df = stream.get("AAPL")
print(df.head())

# Columns: timestamp, open, high, low, close, volume
```

Convert to pandas if needed:

```python
pandas_df = df.to_pandas()
```

## Real-Time Streaming (Coming Soon)

```python
# Stream live prices
async for tick in stream.stream("BTCUSDT"):
    print(f"BTC: ${tick.price}")
```

## Examples

See the [examples/](examples/) directory:
- `basic_usage.py` - Simple examples
- `advanced_usage.py` - API keys and configuration
- `options_chain_example.py` - Options data
- `streaming_usage.py` - Real-time streaming

## Development

```bash
# Run tests
pytest tests/

# Format code
black wrdata/

# Type check
mypy wrdata/
```

## License

MIT

## Contributing

Pull requests welcome! Please ensure tests pass and code is formatted with black.
