# WRData - Dead Simple Market Data

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Get **historical** and **real-time** stock, crypto, forex, and economic data with one simple API.

## Quick Start

```python
from wrdata import DataStream

stream = DataStream()

# Get historical data
df = stream.get("AAPL")

# Get crypto data (auto-detected!)
df = stream.get("BTCUSDT")

# Get options chain
chain = stream.options("SPY")
```

## Real-Time Streaming LIVE

Stream live market data from 7 providers via WebSockets:

```python
import asyncio
from wrdata import DataStream

async def main():
    stream = DataStream()

    # Stream live Bitcoin prices
    async for tick in stream.stream("BTCUSDT"):
        print(f"BTC: ${tick.price:.2f}")

    await stream.disconnect_streams()

asyncio.run(main())
```

**Live Streaming Providers:**
- **Binance** - Crypto (free, no key required)
- **Coinbase** - Crypto (free, no key required)
- **Finnhub** - Stocks (free tier, 60 req/min)
- **Alpaca** - US stocks (free with key)
- **Kraken** - Crypto (free, no key required)
- **Polygon** - Premium stocks (paid)
- **IBKR** - Global markets (requires TWS/Gateway)

**Stream Multiple Symbols:**

```python
async def track_portfolio():
    stream = DataStream()

    def on_price(msg):
        print(f"{msg.symbol}: ${msg.price:.2f}")

    # Track BTC, ETH, and stocks simultaneously
    await stream.stream_many(
        ["BTCUSDT", "ETHUSDT", "AAPL", "GOOGL"],
        callback=on_price
    )

asyncio.run(track_portfolio())
```

See `examples/streaming_usage.py` for 6 complete examples including trading signals.

## Installation

```bash
pip install wrdata
```

## Features

- ✅ **28 Data Providers** - Yahoo, Binance, Polygon, Alpaca, FRED, and 23 more
- ✅ **Real-Time Streaming** - Live WebSocket data from 7 providers
- ✅ **Multi-Asset Support** - Stocks, crypto, forex, options, economic data
- ✅ **Auto-Detection** - Automatically detects asset type from symbol
- ✅ **Smart Defaults** - Works immediately, configure only when needed
- ✅ **Options Data** - Full options chains with Greeks
- ✅ **Zero Dependencies** - No database required
- ✅ **Type Safety** - Full Pydantic v2 support

## Historical Data

### Get Data

```python
from wrdata import DataStream

stream = DataStream()

# Default: 1 year of daily data
df = stream.get("AAPL")

# Custom date range
df = stream.get("AAPL", start="2024-01-01", end="2024-12-31")

# Intraday data
df = stream.get("AAPL", interval="5m", start="2024-11-19")

# Crypto (auto-detected from symbol)
df = stream.get("BTCUSDT")

# Forex (auto-detected)
df = stream.get("EURUSD")
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

# Get full options chain
chain = stream.options("SPY")

# Filter options
calls = stream.options("SPY", option_type="call", strike_min=580, strike_max=600)
```

## API Keys (Optional)

Free providers work without keys. Add keys for premium providers:

**Via environment variables:**

```bash
# .env file
POLYGON_API_KEY=your_key_here
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here
FINNHUB_API_KEY=your_key_here
```

**Or pass directly:**

```python
stream = DataStream(
    polygon_key="your_key",
    binance_key="your_key",
    binance_secret="your_secret",
    alpaca_key="your_key",
    alpaca_secret="your_secret"
)
```

## Supported Providers (28 Total)

### Free - No API Key Required

- **Yahoo Finance** - Stocks, ETFs, crypto (delayed)
- **Binance** - Crypto market data + streaming
- **Coinbase** - Crypto market data + streaming
- **CoinGecko** - 10,000+ cryptocurrencies

### Free - API Key Required

- **Alpha Vantage** - Stocks, forex (5 calls/min)
- **FRED** - 800,000+ economic indicators
- **Finnhub** - Stocks + streaming (60 calls/min)
- **Alpaca** - Real-time US stocks + streaming
- **CoinGecko Pro** - Higher rate limits
- **CryptoCompare** - 100K calls/month
- **Kraken** - Crypto + streaming
- **TwelveData** - 800 calls/day

### Premium (Paid)

- **Polygon.io** - Professional US market data + streaming
- **Interactive Brokers** - Global markets + streaming
- **Tradier** - Options chains
- **IEX Cloud** - US stocks
- **TD Ameritrade** - US stocks + options
- **Marketstack** - 70+ global exchanges
- **Tiingo** - Stocks + news
- **15+ crypto exchanges** - Bybit, OKX, KuCoin, Gate.io, Bitfinex, Gemini, Huobi, Messari, Deribit

See [PROVIDER_SETUP_GUIDE.md](docs/PROVIDER_SETUP_GUIDE.md) for API key setup.

## Asset Type Auto-Detection

Asset types are automatically detected from symbol patterns:

```python
# All auto-detected - no need to specify asset_type!
stream.get("AAPL")       # -> equity
stream.get("BTCUSDT")    # -> crypto (USDT suffix)
stream.get("BTC-USD")    # -> crypto (dash pattern)
stream.get("EURUSD")     # -> forex (6-char)
stream.get("GDP")        # -> economic

# Override if needed
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

All data returned as Polars DataFrames (blazing fast!):

```python
df = stream.get("AAPL")
print(df.head())

# Columns: timestamp, open, high, low, close, volume
```

Convert to pandas if needed:

```python
pandas_df = df.to_pandas()
```

## Streaming Examples

See `examples/streaming_usage.py` for complete examples:

1. **Basic streaming** - Async iterator pattern
2. **Candle streaming** - 1-minute OHLCV candles
3. **Callback-based** - Simpler for some use cases
4. **Multiple symbols** - Track portfolio in real-time
5. **Data aggregation** - Calculate statistics on live data
6. **Trading signals** - Build momentum indicators from live streams

## Docker Support (IBKR)

Run Interactive Brokers Gateway in Docker:

```bash
cd docker/ibkr
./start.sh
```

See [IBKR_DOCKER_QUICKSTART.md](docs/IBKR_DOCKER_QUICKSTART.md) for details.

## Development

```bash
# Run tests
pytest tests/

# Format code
black wrdata/

# Type check
mypy wrdata/
```

## Examples

- `examples/basic_usage.py` - Simple historical data examples
- `examples/advanced_usage.py` - API keys and configuration
- `examples/options_chain_example.py` - Options data
- `examples/streaming_usage.py` - 6 real-time streaming examples

## License

MIT

## Contributing

Pull requests welcome! Please ensure tests pass and code is formatted with black.

---

**Simple. Fast. Powerful.**

28 providers. Historical + Real-time. One API.

© Wayy Research, 2025
