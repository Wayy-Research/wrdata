# WRData Quick Start Guide

Choose your provider and get started in 5 minutes!

## 🎯 Which Provider Should I Use?

```
Need US stocks only?              → Alpaca (easiest!)
Need options/futures?             → IBKR with Docker
Need global markets?              → IBKR with Docker
Need cryptocurrency?              → Binance or Coinbase
Need economic data?               → FRED
```

---

## 🚀 Alpaca - Easiest Option (Recommended)

**Perfect for:** US stocks, quick projects, cloud deployment

### Setup (2 minutes)

1. Get free API keys: https://app.alpaca.markets/signup
2. Add to `.env`:
   ```bash
   ALPACA_API_KEY=your_key
   ALPACA_API_SECRET=your_secret
   ```

### Use

```python
from wrdata.providers import AlpacaProvider
import os

alpaca = AlpacaProvider(
    api_key=os.getenv("ALPACA_API_KEY"),
    api_secret=os.getenv("ALPACA_API_SECRET"),
    paper=True  # Free paper trading!
)

# Historical data
response = alpaca.fetch_timeseries(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2024-11-08",
    interval="1d"
)
print(f"Got {len(response.data)} records")

# Real-time quote
quote = alpaca.get_latest_quote("AAPL")
print(f"AAPL: ${quote}")

# Account info
account = alpaca.get_account()
positions = alpaca.get_positions()
```

### Test

```bash
python test_alpaca_live.py
```

**Pros:**
- ✅ Pure REST API (no local software)
- ✅ Free real-time data
- ✅ Paper trading included
- ✅ Cloud-friendly

**Cons:**
- ❌ US markets only
- ❌ No options

---

## 📊 IBKR with Docker - Professional Option

**Perfect for:** Options, futures, global markets, professional trading

### Setup (5 minutes)

1. Get IBKR account: https://www.interactivebrokers.com/
2. Enable API in account settings
3. Configure Docker:

```bash
cd docker/ibkr
cp .env.example .env
nano .env  # Add your IBKR credentials

# Start IB Gateway
./start.sh

# Test connection
python test-connection.py
```

### Use

```python
from wrdata.providers import IBKRProvider

ibkr = IBKRProvider(
    host="localhost",  # or your cloud server IP
    port=4002,         # 4002=paper, 4001=live
    client_id=1,
    readonly=True
)

if ibkr.connect():
    # Historical data
    response = ibkr.fetch_timeseries(
        symbol="AAPL",
        start_date="2024-01-01",
        end_date="2024-11-08",
        interval="1d"
    )

    # Options
    expirations = ibkr.get_available_expirations("AAPL")

    # Account info
    account = ibkr.get_account_summary()
    positions = ibkr.get_positions()
```

### Test

```bash
python test_ibkr_live.py
```

**Pros:**
- ✅ Global markets (150+ exchanges)
- ✅ Options & futures
- ✅ Professional platform
- ✅ Unlimited API calls

**Cons:**
- ⚠️ Requires Docker container
- ⚠️ More complex setup

**See:** [IBKR_DOCKER_QUICKSTART.md](IBKR_DOCKER_QUICKSTART.md) for detailed guide

---

## 🪙 Crypto - Binance or Coinbase

### Binance (More Pairs)

```python
from wrdata.providers import BinanceProvider

binance = BinanceProvider()  # No API key needed for basic use

# Get BTC price
response = binance.fetch_timeseries(
    symbol="BTCUSDT",
    start_date="2024-01-01",
    end_date="2024-11-08",
    interval="1d"
)
```

### Coinbase (US-Friendly)

```python
from wrdata.providers import CoinbaseProvider

coinbase = CoinbaseProvider()  # No API key needed

# Get ETH price
response = coinbase.fetch_timeseries(
    symbol="ETH-USD",
    start_date="2024-01-01",
    end_date="2024-11-08",
    interval="1d"
)
```

**Test:**
```bash
python test_binance_live.py
python test_coinbase_live.py
```

---

## 📈 Economic Data - FRED

```python
from wrdata.providers import FREDProvider
import os

fred = FREDProvider(api_key=os.getenv("FRED_API_KEY"))

# Get GDP data
response = fred.fetch_timeseries(
    symbol="GDP",
    start_date="2020-01-01",
    end_date="2024-11-08"
)

# Get unemployment rate
response = fred.fetch_timeseries(
    symbol="UNRATE",
    start_date="2020-01-01",
    end_date="2024-11-08"
)
```

**Get API key:** https://fred.stlouisfed.org/docs/api/api_key.html

**Test:**
```bash
python test_fred_live.py
```

---

## 🔄 Real-time Streaming

### Alpaca WebSocket

```python
from wrdata.streaming import AlpacaStreamProvider
import asyncio

async def stream_quotes():
    stream = AlpacaStreamProvider(
        api_key=os.getenv("ALPACA_API_KEY"),
        api_secret=os.getenv("ALPACA_API_SECRET")
    )

    async for msg in stream.subscribe_trades("AAPL"):
        print(f"AAPL: ${msg.price} @ {msg.timestamp}")

asyncio.run(stream_quotes())
```

### Binance WebSocket

```python
from wrdata.streaming import BinanceStreamProvider
import asyncio

async def stream_crypto():
    stream = BinanceStreamProvider()

    async for msg in stream.subscribe_kline("BTCUSDT", "1m"):
        print(f"BTC: ${msg.close}")

asyncio.run(stream_crypto())
```

**Test:**
```bash
python test_streaming.py
```

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/your-repo/wrdata.git
cd wrdata

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .

# Set up environment variables
cp .env.example .env
nano .env  # Add your API keys
```

---

## 🗂️ Environment Variables

Create `.env` file:

```bash
# Alpaca (recommended for stocks)
ALPACA_API_KEY=your_alpaca_key
ALPACA_API_SECRET=your_alpaca_secret

# IBKR (for Docker setup)
IBKR_USERNAME=your_ibkr_username
IBKR_PASSWORD=your_ibkr_password

# Economic data
FRED_API_KEY=your_fred_key

# Optional: Alpha Vantage
ALPHA_VANTAGE_API_KEY=your_av_key

# Optional: Finnhub
FINNHUB_API_KEY=your_finnhub_key
```

---

## 🧪 Testing

```bash
# Test individual providers
python test_alpaca_live.py
python test_ibkr_live.py
python test_binance_live.py
python test_coinbase_live.py
python test_fred_live.py

# Test streaming
python test_streaming.py
python test_ibkr_stream.py

# Run all tests
pytest tests/ -v
```

---

## 🎓 Examples

### Multi-Provider Data Fetching

```python
from wrdata.providers import AlpacaProvider, BinanceProvider
from datetime import datetime, timedelta

# Get stock data from Alpaca
alpaca = AlpacaProvider(api_key=key, api_secret=secret)
stocks = alpaca.fetch_timeseries("AAPL", "2024-01-01", "2024-11-08")

# Get crypto data from Binance
binance = BinanceProvider()
crypto = binance.fetch_timeseries("BTCUSDT", "2024-01-01", "2024-11-08")

# Compare performance
print(f"AAPL records: {len(stocks.data)}")
print(f"BTC records: {len(crypto.data)}")
```

### Building a Trading Strategy

```python
from wrdata.providers import AlpacaProvider
import pandas as pd

alpaca = AlpacaProvider(api_key=key, api_secret=secret, paper=True)

# Get historical data
response = alpaca.fetch_timeseries(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2024-11-08",
    interval="1d"
)

# Convert to DataFrame
df = pd.DataFrame(response.data)
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)

# Calculate moving averages
df['SMA_20'] = df['close'].rolling(window=20).mean()
df['SMA_50'] = df['close'].rolling(window=50).mean()

# Simple strategy: buy when SMA_20 > SMA_50
df['signal'] = (df['SMA_20'] > df['SMA_50']).astype(int)

print(df.tail())
```

---

## 📚 Documentation

- **Provider comparison:** [PROVIDER_STATUS.md](PROVIDER_STATUS.md)
- **IBKR vs Alpaca:** [IBKR_VS_ALPACA.md](IBKR_VS_ALPACA.md)
- **Docker setup:** [IBKR_DOCKER_QUICKSTART.md](IBKR_DOCKER_QUICKSTART.md)
- **Full Docker docs:** [docker/ibkr/README.md](docker/ibkr/README.md)

---

## 🆘 Common Issues

### "API key not found"
```bash
# Make sure .env file exists and is loaded
cp .env.example .env
nano .env  # Add your keys
```

### "Connection refused" (IBKR)
```bash
# Check if Docker container is running
cd docker/ibkr
docker-compose ps

# Restart if needed
./start.sh
```

### "Rate limit exceeded"
```python
# Use a different provider or wait
# Alpha Vantage: 5 calls/min
# Alpaca: 200 calls/min
# IBKR: Unlimited
```

---

## 🚀 Next Steps

1. **Choose your provider** (Alpaca recommended for beginners)
2. **Get API keys** (links above)
3. **Set up `.env`** file
4. **Run test file** to verify
5. **Start building** your application!

---

## 📊 Quick Reference

| Provider | Best For | API Keys | Setup Time |
|----------|----------|----------|------------|
| **Alpaca** ⭐ | US stocks | Required | 2 min |
| **IBKR** | Options/Global | Required + Docker | 5 min |
| **Binance** | Crypto | Optional | 1 min |
| **Coinbase** | Crypto | Not needed | 1 min |
| **FRED** | Economic data | Required | 2 min |
| **Finnhub** | Global stocks | Required | 2 min |

**Total providers:** 8 (all free tier!)

---

**Ready to start?** Pick a provider above and follow the setup! 🎉

For questions or issues, check the documentation or file an issue on GitHub.
