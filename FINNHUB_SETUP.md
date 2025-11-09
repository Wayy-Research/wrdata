# Finnhub Setup & Testing Guide 🚀

## Why Finnhub is AMAZING for Free Tier

**Finnhub beats IEX Cloud in every way:**
- ✅ **FREE WebSocket streaming** (real-time trades!)
- ✅ **60 API calls per minute** (vs IEX's monthly quota)
- ✅ **Still active in 2024** (IEX Cloud shut down)
- ✅ **Global coverage** - 60+ stock exchanges
- ✅ **Comprehensive data** - stocks, forex, crypto, news, fundamentals

## Get Your Free API Key

1. Go to: **https://finnhub.io/register**
2. Sign up with email (no credit card required)
3. Verify your email
4. Go to dashboard and copy your API key

**Free Tier Benefits:**
- 60 API calls per minute
- WebSocket streaming (unlimited!)
- 1 year of historical data per call
- Company fundamentals
- News and earnings data
- Global market coverage

## Set Up Your API Key

```bash
# Add to your .env file
echo "FINNHUB_API_KEY=your_key_here" >> .env

# Or export directly
export FINNHUB_API_KEY="your_key_here"
```

## Test Finnhub

Run the live test:

```bash
cd /home/rcgalbo/wayy-research/wayy-fin/wf/wrdata
source .venv/bin/activate
python test_finnhub_live.py
```

## What Gets Tested

The test will verify:

1. ✅ API connection validation
2. ✅ Real-time quote for AAPL
3. ✅ Historical data (Oct 1 - Nov 7, 2024)
4. ✅ Company profile information
5. ✅ Symbol search
6. ✅ Company news
7. ✅ DataStream integration
8. ✅ **WebSocket streaming** (real-time trades!)

## Expected Output

```
============================================================
Finnhub Available Endpoints
============================================================
  quote           - Real-time quote
  candle          - Historical OHLCV
  profile2        - Company profile
  company-news    - Company news
  search          - Symbol search
  recommendation  - Analyst recommendations
  ...

============================================================
Testing Finnhub Provider
============================================================

✓ Finnhub API key found
✓ Testing connection...
  ✓ Connection successful!

✓ Fetching real-time quote for AAPL...
  ✓ AAPL: $226.50
    Open: $225.00
    High: $227.10
    Low: $224.80
    Previous Close: $225.90

✓ Fetching historical data for AAPL...
  ✓ Got 27 data points
  First point: {'Date': '2024-10-01', 'open': 226.37, ...}
  Last point: {'Date': '2024-11-07', 'open': 221.98, ...}

✓ Fetching company profile for AAPL...
  Company: Apple Inc.
  Industry: Technology
  Country: US
  Market Cap: $3,500B
  IPO: 1980-12-12

============================================================
Testing Finnhub WebSocket Streaming
============================================================

✓ Starting Finnhub WebSocket stream...
  Streaming live trades for AAPL and MSFT

  AAPL: $226.50 @ 14:32:15 (vol: 100)
  MSFT: $378.25 @ 14:32:15 (vol: 50)
  AAPL: $226.51 @ 14:32:16 (vol: 200)
  ...

  ✓ Received 20 real-time trade messages!
```

## Troubleshooting

**Error: "FINNHUB_API_KEY not set"**
- Make sure you've exported the key or added it to .env

**Error: "401 Unauthorized"**
- Your API key is invalid - check it at https://finnhub.io/dashboard
- Make sure you copied the full key

**Error: "429 Too Many Requests"**
- You're making more than 60 calls/minute
- Add delays between calls or use WebSocket streaming instead

**WebSocket disconnects:**
- Finnhub sends ping messages every 30 seconds
- Our provider auto-responds with pong
- Check your internet connection

## Quick Test Commands

### Test 1: Direct Provider Usage
```bash
source .venv/bin/activate
export FINNHUB_API_KEY="your_key"
python -c "
from wrdata.providers.finnhub_provider import FinnhubProvider
provider = FinnhubProvider(api_key='$FINNHUB_API_KEY')
print('✓ Connected:', provider.validate_connection())
quote = provider.get_quote('AAPL')
print(f'✓ AAPL: \${quote.get(\"c\", \"N/A\")}')
"
```

### Test 2: DataStream Integration
```bash
source .venv/bin/activate
export FINNHUB_API_KEY="your_key"
python -c "
from wrdata import DataStream
stream = DataStream(finnhub_key='$FINNHUB_API_KEY')
df = stream.get('AAPL', start='2024-10-01', end='2024-11-07')
print(f'✓ Got {len(df)} rows of AAPL data')
print(df.tail(3))
"
```

### Test 3: WebSocket Streaming
```bash
source .venv/bin/activate
export FINNHUB_API_KEY="your_key"
python test_finnhub_live.py
# Then press 'y' when prompted for streaming test
```

## Provider Priority for Stocks

With Finnhub integrated, stock data routing is now:

**1st choice:** Finnhub (60 calls/min + WebSocket streaming)
**2nd choice:** Alpha Vantage (5 calls/min)
**3rd choice:** YFinance (unlimited, delayed)

```python
stream = DataStream(finnhub_key="...", alphavantage_key="...")
df = stream.get("AAPL", asset_type="stock")  # Auto-uses Finnhub first!
```

## Integration in Your Code

### Basic Usage

```python
from wrdata import DataStream

# Initialize with Finnhub
stream = DataStream(finnhub_key="your_key")

# Get Apple stock data
df = stream.get("AAPL", start="2024-01-01", end="2024-11-07")
print(df)
```

### Direct Provider Access

```python
from wrdata.providers.finnhub_provider import FinnhubProvider

provider = FinnhubProvider(api_key="your_key")

# Get real-time quote
quote = provider.get_quote("AAPL")
print(f"AAPL: ${quote['c']}")  # current price

# Get historical data
response = provider.fetch_timeseries(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2024-11-07",
    interval="1d"
)

if response.success:
    print(f"Got {len(response.data)} days of data")

# Search for symbols
results = provider.search_symbols("Apple")
for result in results[:5]:
    print(f"{result['description']} ({result['symbol']})")

# Get company news
news = provider.get_company_news("AAPL", "2024-11-01", "2024-11-07")
for article in news[:3]:
    print(article['headline'])
```

### WebSocket Streaming

```python
import asyncio
from wrdata.streaming.finnhub_stream import FinnhubStreamProvider

async def stream_trades():
    stream = FinnhubStreamProvider(api_key="your_key")
    await stream.connect()

    # Stream single symbol
    async for msg in stream.subscribe_ticker("AAPL"):
        print(f"{msg.symbol}: ${msg.price} @ {msg.timestamp}")

    await stream.disconnect()

asyncio.run(stream_trades())
```

### Stream Multiple Symbols

```python
async def stream_multiple():
    stream = FinnhubStreamProvider(api_key="your_key")
    await stream.connect()

    # Stream multiple symbols on one connection
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]
    async for msg in stream.subscribe_multiple(symbols):
        print(f"{msg.symbol}: ${msg.price:.2f}")

    await stream.disconnect()

asyncio.run(stream_multiple())
```

## Finnhub vs IEX Cloud

| Feature | Finnhub (FREE) | IEX Cloud |
|---------|----------------|-----------|
| **Status** | ✅ Active 2024 | ❌ Shut down Aug 2024 |
| **WebSocket** | ✅ FREE | ❌ Paid only |
| **Rate Limit** | 60/min | 50k/month |
| **Coverage** | 60+ exchanges | US only |
| **Historical** | 1 year/call | Up to 5 years |
| **Cost** | $0 | $9+/month |

**Winner:** Finnhub by a landslide! 🏆

## What's Next?

Once Finnhub is tested and working, we'll move on to:

1. **Alpaca** - Free real-time stock data + paper trading API
2. **Kraken** - Crypto exchange with WebSocket streaming
3. **Interactive Brokers** - Professional trading platform with TWS API

## Available Endpoints (Free Tier)

- **quote** - Real-time stock quotes
- **candle** - Historical OHLCV data
- **profile2** - Company profile
- **company-news** - Latest company news
- **search** - Symbol search
- **recommendation** - Analyst recommendations
- **price-target** - Price targets
- **earnings** - Earnings data
- **financials** - Financial statements
- **metrics** - Financial metrics
- **peers** - Peer companies
- **split** - Stock splits
- **dividend** - Dividends

## Data Coverage

- **US Stocks** - NYSE, NASDAQ, AMEX
- **Global Stocks** - 60+ exchanges worldwide
- **Forex** - Major currency pairs
- **Crypto** - Major cryptocurrencies
- **Update Frequency** - Real-time via WebSocket
- **Historical Data** - Up to 1 year per call

## Rate Limits

- **Free Tier**: 60 calls/minute REST API
- **WebSocket**: Unlimited streaming (FREE!)
- **Premium Plans**: Higher rate limits + more data history

## Finnhub Advantages

1. **Free WebSocket Streaming** - Most providers charge for this!
2. **Global Coverage** - Not just US markets
3. **High Rate Limits** - 60/min is very generous
4. **No Credit Card** - Truly free tier
5. **Active Development** - Regular updates and improvements
6. **Great Documentation** - Easy to integrate

## Links

- Finnhub Homepage: https://finnhub.io/
- Sign Up (Free): https://finnhub.io/register
- API Documentation: https://finnhub.io/docs/api/
- Dashboard: https://finnhub.io/dashboard
- WebSocket Docs: https://finnhub.io/docs/api/websocket-trades
