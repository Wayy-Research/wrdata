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

Stream live market data from 8 providers via WebSockets:

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
- **Binance** - Crypto (free, no key required) + Whale detection
- **Coinbase** - Crypto (free, no key required) + Whale detection
- **Finnhub** - Stocks (free tier, 60 req/min)
- **Alpaca** - US stocks (free with key)
- **Kraken** - Crypto (free, no key required)
- **Polygon** - Premium stocks (paid)
- **Polymarket** - Prediction markets (free, no key required)
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

## Orderbook Streaming (Level2)

Stream real-time orderbook data from Coinbase with full depth-of-market updates:

```python
import asyncio
from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider

async def stream_orderbook():
    provider = CoinbaseStreamProvider()
    await provider.connect()

    # Stream Level2 orderbook updates
    async for msg in provider.subscribe_depth("BTC-USD"):
        print(f"Mid Price: ${msg.price:,.2f}")
        print(f"Best Bid: ${msg.bid:,.2f} | Best Ask: ${msg.ask:,.2f}")
        print(f"Spread: ${msg.ask - msg.bid:.2f}")

        # Access top 20 bid/ask levels
        print(f"\nTop 5 Bids: {msg.bids[:5]}")  # [[price, size], ...]
        print(f"Top 5 Asks: {msg.asks[:5]}")

        # Calculate order imbalance
        bid_vol = sum(size for _, size in msg.bids[:10])
        ask_vol = sum(size for _, size in msg.asks[:10])
        print(f"Bid/Ask Volume Ratio: {bid_vol/ask_vol:.2f}")

    await provider.disconnect()

asyncio.run(stream_orderbook())
```

**Get Orderbook Snapshot:**

```python
# Stream a few updates first to build orderbook state
count = 0
async for msg in provider.subscribe_depth("ETH-USD"):
    count += 1
    if count >= 3:
        break

# Get current orderbook state
snapshot = provider.get_orderbook_snapshot("ETH-USD")
print(f"Total price levels - Bids: {len(snapshot['bids'])}, Asks: {len(snapshot['asks'])}")
```

**Track Multiple Orderbooks:**

```python
async def monitor_books():
    provider = CoinbaseStreamProvider()
    await provider.connect()

    async def track(symbol):
        async for msg in provider.subscribe_depth(symbol):
            spread = msg.ask - msg.bid
            print(f"{symbol}: ${msg.price:,.2f} | Spread: ${spread:.2f}")

    # Monitor BTC and ETH simultaneously
    await asyncio.gather(
        track("BTC-USD"),
        track("ETH-USD")
    )

asyncio.run(monitor_books())
```

Features:
- Real-time Level2 orderbook updates via WebSocket
- Full snapshot on connection + incremental updates
- Top 20 bid/ask levels maintained automatically
- No API key required
- Track multiple symbols concurrently

## Whale Transaction Tracking 🐋

Detect and monitor large volume cryptocurrency transactions (whale transactions) in real-time using percentile-based detection:

```python
import asyncio
from wrdata.streaming.binance_stream import BinanceStreamProvider

async def track_whales():
    provider = BinanceStreamProvider()
    await provider.connect()

    def whale_alert(whale_tx):
        print(f"🐋 WHALE ALERT!")
        print(f"  Symbol: {whale_tx.symbol}")
        print(f"  Size: {whale_tx.size} BTC")
        print(f"  Value: ${whale_tx.usd_value:,.2f}")
        print(f"  Percentile: {whale_tx.percentile:.2f}% (Rank: {whale_tx.volume_rank})")

    # Monitor for top 1% transactions by volume
    async for msg in provider.subscribe_aggregate_trades(
        symbol="BTCUSDT",
        enable_whale_detection=True,
        percentile_threshold=99.0,  # Top 1%
        whale_callback=whale_alert
    ):
        pass  # Process messages

    await provider.disconnect()

asyncio.run(track_whales())
```

**Coinbase Whale Detection with USD Threshold:**

```python
from wrdata.streaming.coinbase_stream import CoinbaseStreamProvider

async def coinbase_whales():
    provider = CoinbaseStreamProvider()
    await provider.connect()

    def whale_alert(whale_tx):
        print(f"🐋 {whale_tx.symbol}: ${whale_tx.usd_value:,.0f} - {whale_tx.side.upper()}")

    # Detect whales: Top 1% AND minimum $100k
    async for msg in provider.subscribe_matches(
        symbol="BTC-USD",
        enable_whale_detection=True,
        percentile_threshold=99.0,
        min_usd_value=100000,  # $100k minimum
        whale_callback=whale_alert
    ):
        pass

    await provider.disconnect()

asyncio.run(coinbase_whales())
```

**Key Features:**
- 📊 **Percentile-based detection** - Adapts to market conditions using rolling window analysis
- 💰 **USD value thresholds** - Combine percentile with absolute dollar amounts
- 🔄 **Real-time streaming** - WebSocket-based for instant whale alerts
- 📈 **Volume statistics** - Track mean, median, percentiles (p50, p75, p90, p95, p99, p99.9)
- 🎯 **Multi-symbol support** - Monitor whale activity across multiple cryptocurrencies
- ⚡ **Exchange-specific tracking** - Separate detection per exchange (Binance, Coinbase)
- 🏆 **Transaction ranking** - See where each whale ranks among recent trades

**How It Works:**

The whale detector maintains a rolling window of recent transactions (default: last 1000 trades or 1 hour) and calculates volume percentiles in real-time. Transactions exceeding your threshold (e.g., 99th percentile = top 1%) are classified as whale transactions.

**Supported Data Sources:**
- **Binance** - Aggregate trade streams (perfect for whale detection)
- **Coinbase** - Trade matches channel with full execution data
- **Whale Alert** - Historical + real-time blockchain whale transactions (API key required)

**Whale Alert Integration:**

Whale Alert provides purpose-built whale transaction tracking across all major blockchains. Requires API key from [whale-alert.io](https://whale-alert.io/).

```python
from wrdata.providers.whale_alert_provider import WhaleAlertProvider

# Historical whale transactions
provider = WhaleAlertProvider(api_key="your_api_key")

batch = provider.fetch_whale_transactions(
    start_date="2025-11-20",
    end_date="2025-11-23",
    blockchain="bitcoin",
    min_value=1000000  # $1M minimum
)

for whale_tx in batch.transactions:
    print(f"Whale: {whale_tx.size} {whale_tx.symbol} = ${whale_tx.usd_value:,.0f}")
    print(f"Type: {whale_tx.transaction_type} via {whale_tx.exchange}")
```

**Real-time Whale Alert Stream:**

```python
from wrdata.streaming.whale_alert_stream import WhaleAlertStreamProvider

provider = WhaleAlertStreamProvider(api_key="your_api_key")
await provider.connect()

async for whale_tx in provider.subscribe_whale_alerts(min_value=2000000):
    print(f"🐋 ALERT: ${whale_tx.usd_value:,.0f} {whale_tx.transaction_type}")
```

**Historical Price Impact Analysis:**

Analyze how whale transactions affect price:

```python
from tests.integration.test_whale_price_impact import WhalePriceImpactAnalyzer

analyzer = WhalePriceImpactAnalyzer(whale_provider, price_provider)

# Fetch whale transactions
whales = analyzer.fetch_whale_transactions(
    start_date="2025-11-20",
    end_date="2025-11-20",
    blockchain="bitcoin"
)

# Fetch corresponding price data
prices = analyzer.fetch_price_data(
    symbol="BTCUSDT",
    start_date="2025-11-20",
    interval="1m"
)

# Analyze impact
analysis = analyzer.analyze_price_impact(whales, prices)
analyzer.print_analysis_report(analysis)

# Outputs:
# - Average price change (5m, 10m, 15m after whale transaction)
# - Volume surge percentage
# - Volatility increase
# - Impact by transaction type (deposit vs withdrawal)
```

See `examples/whale_tracking.py` for 5 complete examples including multi-symbol monitoring and analytics dashboard.

See `examples/whale_alert_demo.py` for Whale Alert API integration demo.

See `tests/integration/test_whale_price_impact.py` for full price impact analysis.

## Installation

```bash
pip install wrdata
```

## Features

- ✅ **32+ Data Providers** - Yahoo, Polygon, Alpaca, FRED, Polymarket, and more
- ✅ **Real-Time Streaming** - Live WebSocket data from 8 providers (including Polymarket)
- ✅ **Whale Transaction Tracking** 🐋 - Real-time detection of large volume crypto transactions
- ✅ **Prediction Markets** - Polymarket events, price history, order books, and live streaming
- ✅ **Symbol Operations** - Search, validate, resolve, and get metadata for any symbol
- ✅ **Multi-Asset Support** - Stocks, crypto, forex, options, economic data, prediction markets
- ✅ **Multi-Provider Search** - Search across 9+ providers simultaneously
- ✅ **100+ Crypto Exchanges** - CCXT integration (Bybit, OKX, KuCoin, Gate.io, Bitfinex)
- ✅ **Comprehensive Crypto** - 10,000+ cryptocurrencies via CoinGecko integration
- ✅ **Auto-Detection** - Automatically detects asset type from symbol
- ✅ **Smart Defaults** - Works immediately, configure only when needed
- ✅ **Options Data** - Full options chains with Greeks (YFinance + Polygon.io)
- ✅ **Economic Data** - 800,000+ FRED series with search + economic calendar
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

### Search for Symbols

```python
# Search across 9+ providers (YFinance, CoinGecko, CCXT exchanges, etc.)
results = stream.search_symbol("DOGE", limit=50)

# Results from multiple exchanges
for r in results[:5]:
    print(f"{r['symbol']:25} from {r['provider']}")

# Output:
# DOGE/USDT                 from ccxt_okx
# DOGE/BTC                  from ccxt_kucoin
# POLYDOGE/USDT             from ccxt_gateio
# DOGE-USD                  from yfinance
# dogecoin                  from coingecko

# Group by provider to see coverage
from collections import defaultdict
by_provider = defaultdict(list)
for r in results:
    by_provider[r['provider']].append(r['symbol'])

for provider, symbols in by_provider.items():
    print(f"{provider}: {len(symbols)} results")

# Output:
# ccxt_okx: 8 results
# ccxt_kucoin: 7 results
# ccxt_gateio: 43 results
# yfinance: 5 results
# coingecko: 25 results
```

## Symbol Operations (v0.1.6)

Standalone functions for searching, validating, and resolving symbols. Available as both sync and async, exported at the top level.

```python
from wrdata.symbol_ops import search, validate, resolve, get_metadata

# Search for symbols via yfinance
results = search("NVIDIA", limit=5)
for r in results:
    print(f"{r['symbol']:10} {r['name']:30} ({r['exchange']})")

# Validate a symbol exists
assert validate("AAPL") == True
assert validate("FAKESYMBOL123") == False

# Resolve a canonical symbol to provider-specific format
resolve("BTC", "binance")     # -> "BTCUSDT"
resolve("BTC", "coinbase")    # -> "BTC-USD"
resolve("BTC", "coingecko")   # -> "bitcoin"
resolve("BTC", "kraken")      # -> "XXBTZUSD"
resolve("EURUSD", "yfinance") # -> "EURUSD=X"
resolve("EURUSD", "twelvedata") # -> "EUR/USD"

# Get rich metadata for any symbol
meta = get_metadata("AAPL")
print(meta)
# {'symbol': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology',
#  'industry': 'Consumer Electronics', 'market_cap': 3500000000000,
#  'currency': 'USD', 'exchange': 'NMS', ...}
```

**Async versions** (for use in async code / FastAPI / notebooks):

```python
import asyncio
from wrdata import search_async, validate_async, resolve_async, get_metadata_async

async def main():
    results = await search_async("Tesla", limit=3)
    is_valid = await validate_async("TSLA")
    symbol = await resolve_async("ETH", provider="binance")  # -> "ETHUSDT"
    meta = await get_metadata_async("MSFT")
    print(meta["sector"])  # "Technology"

asyncio.run(main())
```

**Economic Calendar** (requires Alpha Vantage API key):

```python
from wrdata.symbol_ops import get_economic_calendar

events = get_economic_calendar(horizon="3month")
for event in events[:3]:
    print(f"{event['date']} - {event['event']} ({event['country']})")
```

## Prediction Markets (Polymarket)

Access Polymarket prediction markets -- no API key required. Search events, fetch historical prices, stream live updates.

### Market Discovery

```python
from wrdata import DataStream

stream = DataStream()

# Or use the provider directly for full API access
from wrdata.providers.polymarket_provider import PolymarketProvider

poly = PolymarketProvider()

# Search for markets
markets = poly.search_markets("bitcoin", limit=5)
for m in markets:
    print(f"  {m.get('question', '?')}")

# Browse active events by category
events = poly.fetch_events(active=True, tag_slug="crypto", limit=10)
for e in events:
    print(f"{e['title']} ({len(e.get('markets', []))} markets)")

# Fetch all available tags
tags = poly.fetch_tags()
for t in tags[:5]:
    print(t.get("label"))
```

### Historical Price Data

Prices are probabilities in [0.0, 1.0]:

```python
# Fetch YES/NO price history for a market (by slug or condition_id)
df = poly.fetch_market_history(
    "will-bitcoin-hit-100k-in-2026",
    start_date="2026-01-01",
    end_date="2026-02-12",
    fidelity=poly.FIDELITY_1HR,  # 1min, 5min, 15min, 1hr, 6hr, 1day
)
print(df.head())
# timestamp | yes_price | no_price
# 2026-01-01 00:00:00 | 0.72 | 0.28

# Or use via DataStream (auto-detected asset type)
df = stream.get("will-bitcoin-hit-100k-in-2026", interval="1h")
```

### Order Books & Live Pricing

```python
# Fetch order book for a specific token
market = poly.fetch_market("will-bitcoin-hit-100k-in-2026")
token_id = market["clobTokenIds"][0]  # YES token

book = poly.fetch_orderbook(token_id)
print(f"Best bid: {book['bids'][0]}, Best ask: {book['asks'][0]}")

# Midpoint and last trade
mid = poly.fetch_midpoint(token_id)
last = poly.fetch_last_trade_price(token_id)
print(f"Mid: {mid:.4f}, Last: {last:.4f}")
```

### Real-Time Streaming

```python
import asyncio
from wrdata.streaming.polymarket_stream import PolymarketStreamProvider

async def stream_predictions():
    provider = PolymarketStreamProvider()
    await provider.connect()

    # Stream price changes (pass a condition_id or clob_token_id)
    async for msg in provider.subscribe_ticker(token_id):
        print(f"Price: {msg.price:.4f} at {msg.timestamp}")

    # Stream order book snapshots
    async for msg in provider.subscribe_book(token_id):
        print(f"Mid: {msg.price:.4f} | Bid: {msg.bid} | Ask: {msg.ask}")

    await provider.disconnect()

asyncio.run(stream_predictions())
```

## Polygon.io Options (v0.1.6)

Dedicated options data via Polygon.io for historical options chains and timeseries. Requires a paid Polygon.io API key.

```python
stream = DataStream(polygon_key="your_polygon_key")

# Get options chain (auto-routes to Polygon when key is configured)
chain = stream.options("SPY")

# Or use the provider directly for advanced queries
from wrdata.providers.polygon_options_provider import PolygonOptionsProvider

poly_opts = PolygonOptionsProvider(api_key="your_polygon_key")

# Get available expirations
expirations = poly_opts.get_available_expirations("AAPL")
print(expirations[:5])

# Fetch historical OHLCV for a specific options contract
from wrdata.models.schemas import OptionsTimeseriesRequest

request = OptionsTimeseriesRequest(
    contract_symbol="O:SPY260220C00600000",
    underlying_symbol="SPY",
    start_date="2026-01-01",
    end_date="2026-02-12",
)
result = poly_opts.fetch_options_timeseries(request)
for bar in result.data[:3]:
    print(f"{bar['timestamp']} | C: {bar['close']} | V: {bar['volume']}")
```

## FRED Economic Data

Access 800,000+ economic indicators from the Federal Reserve (requires free API key from [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)).

```python
stream = DataStream(fred_key="your_fred_key")

# Fetch economic time series
df = stream.get("FEDFUNDS", asset_type="economic")  # Federal Funds Rate
df = stream.get("GDP")       # GDP (auto-detected as economic)
df = stream.get("UNRATE")    # Unemployment rate
df = stream.get("DGS10")     # 10-Year Treasury yield

# Search for series
from wrdata.providers.fred_provider import FredProvider

fred = FredProvider(api_key="your_fred_key")
results = fred.search_series("consumer price index")
for r in results[:5]:
    print(f"{r['symbol']:15} {r['name'][:50]}  ({r['frequency']})")
```

## API Keys (Optional)

Free providers work without keys. Add keys for premium providers:

**Via environment variables:**

```bash
# .env file
POLYGON_API_KEY=your_key_here        # Options + premium equity data
ALPACA_API_KEY=your_key_here         # US stocks + streaming
ALPACA_API_SECRET=your_secret_here
FINNHUB_API_KEY=your_key_here        # Stocks + streaming
FRED_API_KEY=your_key_here           # 800K+ economic indicators
ALPHA_VANTAGE_API_KEY=your_key_here  # Stocks, forex, economic calendar
```

**Or pass directly:**

```python
stream = DataStream(
    polygon_key="your_key",
    alpaca_key="your_key",
    alpaca_secret="your_secret"
)
```

## Supported Providers (32+ Total)

### Free - No API Key Required

- **Yahoo Finance** - Stocks, ETFs, crypto (delayed)
- **Coinbase** - Crypto market data + streaming
- **CoinGecko** - 10,000+ cryptocurrencies
- **Polymarket** - Prediction markets (events, prices, order books, streaming)
- **CCXT Exchanges** (5 pre-configured):
  - **OKX** - Global crypto exchange
  - **KuCoin** - 700+ altcoins
  - **Gate.io** - Extensive crypto selection
  - **Bitfinex** - Professional trading platform
  - **Bybit** - Derivatives and spot trading
  - *Plus 95+ more exchanges available via CCXT!*

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

- **Polygon.io** - Professional US market data + streaming + **options chains/timeseries**
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

32+ providers. 100+ crypto exchanges. Prediction markets. Historical + Real-time. One API.

© Wayy Research, 2026
