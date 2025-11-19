# IBKR vs Alpaca: Which Should You Use?

## Quick Answer

**Use Alpaca** if you want:
- ✅ Pure REST API (no local software)
- ✅ Easy setup (just API keys)
- ✅ US stocks only
- ✅ Free paper trading
- ✅ Fast development

**Use IBKR** if you need:
- ✅ Options trading
- ✅ Futures
- ✅ Global markets (150+ exchanges)
- ✅ Professional-grade platform
- ✅ Multi-asset trading

---

## The IBKR "Problem"

### Interactive Brokers Requires Local Software

IBKR's API architecture **requires** either TWS (Trader Workstation) or IB Gateway to be running locally. This is **by design** and cannot be bypassed.

**Why?**
- Security: Your credentials never leave your machine
- Control: You maintain full control over connections
- Reliability: Direct connection to IBKR servers

**The Trade-off:**
```
More Security + Control = More Setup Complexity
```

### Deployment Challenges with IBKR

If you need to deploy your application to production:

❌ **Bad for:**
- Serverless functions (Lambda, Cloud Functions)
- Simple cloud deployments
- Quick prototypes
- CI/CD pipelines

✅ **Good for:**
- Dedicated trading servers
- VPS deployments
- Docker containers (can run IB Gateway)
- Local development

### IBKR Workarounds

1. **🐳 Use Docker (RECOMMENDED!)**
   - We provide a ready-to-use Docker setup
   - No local installation needed
   - Easy deployment to cloud
   - See `docker/ibkr/README.md`

   ```bash
   cd docker/ibkr
   cp .env.example .env
   # Edit .env with your IBKR credentials
   ./start.sh
   ```

2. **Use IB Gateway (headless version)**
   - Lighter than TWS
   - Can run as background service
   - Still requires local installation

3. **VPS/Cloud Server**
   - Deploy Docker container on a VPS
   - Your app connects to VPS
   - Fully automated

4. **Just use Alpaca instead!** 😊

---

## Alpaca: The REST-Only Alternative

### Pure REST API - No Local Software Required

Alpaca was built as a **API-first broker** with modern developers in mind:

```python
# IBKR - requires TWS/Gateway running
ibkr = IBKRProvider(host="127.0.0.1", port=7497)  # Must have TWS running!

# Alpaca - just API keys
alpaca = AlpacaProvider(
    api_key="YOUR_KEY",
    api_secret="YOUR_SECRET",
    paper=True  # Free paper trading!
)
```

### Alpaca Benefits

✅ **Easy Deployment**
- Works on Lambda
- Works on Cloud Run
- Works anywhere with internet

✅ **Free Tier Includes:**
- Real-time IEX stock data
- Historical data (6 years)
- WebSocket streaming
- Paper trading account
- 200 requests/minute

✅ **Zero Setup**
- No local software
- No port configuration
- Just API keys

### Alpaca Limitations

❌ **US Markets Only**
- No international stocks
- No European/Asian exchanges

❌ **No Options**
- Stocks and ETFs only
- Use IBKR for options

❌ **IEX Data Feed**
- Real-time but IEX only
- Not consolidated tape
- (Upgrade to SIP for full market)

---

## Feature Comparison

| Feature | Alpaca | IBKR |
|---------|--------|------|
| **Setup** | API keys only | Requires TWS/Gateway |
| **Deployment** | Anywhere | Requires local/VPS |
| **Cost** | Free | Free with account |
| **US Stocks** | ✅ Real-time IEX | ✅ Real-time |
| **Global Stocks** | ❌ | ✅ 150+ exchanges |
| **Options** | ❌ | ✅ Full support |
| **Futures** | ❌ | ✅ Full support |
| **Forex** | ❌ | ✅ Full support |
| **Crypto** | ✅ (coming) | ✅ CFDs |
| **Paper Trading** | ✅ Free | ✅ Free |
| **WebSocket** | ✅ Free | ✅ Free |
| **REST API Limit** | 200/min | Unlimited |
| **Historical Data** | 6 years | Unlimited |

---

## Recommended Usage

### For Most Use Cases → Use Alpaca

```python
from wrdata.providers import AlpacaProvider

# Get free API keys: https://app.alpaca.markets/signup
alpaca = AlpacaProvider(
    api_key=os.getenv("ALPACA_API_KEY"),
    api_secret=os.getenv("ALPACA_API_SECRET"),
    paper=True  # Free paper trading!
)

# Fetch historical data
response = alpaca.fetch_timeseries(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2024-11-08",
    interval="1d"
)

# Real-time quote
quote = alpaca.get_latest_quote("AAPL")

# Account info
account = alpaca.get_account()
positions = alpaca.get_positions()
```

**Perfect for:**
- US stock trading bots
- Paper trading / backtesting
- Cloud deployments
- Quick prototypes
- Learning algorithmic trading

### For Advanced Traders → Use IBKR

```python
from wrdata.providers import IBKRProvider

# Requires TWS or IB Gateway running on localhost:7497
ibkr = IBKRProvider(
    host="127.0.0.1",
    port=7497,  # 7497=paper, 7496=live
    client_id=1,
    readonly=True
)

ibkr.connect()

# Options chains
expirations = ibkr.get_available_expirations("AAPL")

# Global stocks
response = ibkr.fetch_timeseries(
    symbol="TSLA",
    start_date="2024-01-01",
    end_date="2024-11-08",
    interval="1d",
    exchange="NASDAQ"  # Or "LSE", "TSE", etc.
)

# Futures, forex, etc.
```

**Perfect for:**
- Options trading
- Global markets
- Multi-asset strategies
- Professional trading
- Dedicated trading servers

---

## Our Implementation Status

### ✅ Both Fully Implemented!

**Alpaca Provider:**
- ✅ REST API (`wrdata/providers/alpaca_provider.py`)
- ✅ WebSocket streaming (`wrdata/streaming/alpaca_stream.py`)
- ✅ Test file (`test_alpaca_live.py`)
- ✅ Exported and documented

**IBKR Provider:**
- ✅ REST API (`wrdata/providers/ibkr_provider.py`)
- ✅ WebSocket streaming (`wrdata/streaming/ibkr_stream.py`)
- ✅ Test files (`test_ibkr_live.py`, `test_ibkr_stream.py`)
- ✅ Exported and documented

### Provider Priority for Stocks

We now recommend **Alpaca first** for US stocks:

```python
{
    'stock':  ['alpaca', 'ibkr', 'finnhub', 'alphavantage', 'yfinance'],
    'options': ['ibkr'],  # Only IBKR supports options
}
```

**Why Alpaca first?**
1. Pure REST API - no setup required
2. Free real-time data
3. Paper trading included
4. Easy cloud deployment
5. 200 requests/minute

---

## Summary

### The Bottom Line

**IBKR requires TWS/IB Gateway to run locally.** This is not a bug - it's their architecture. You cannot bypass it.

**For most developers:** Use Alpaca
- Easier setup
- Pure REST API
- Free tier is generous
- Perfect for US stocks

**For professional traders:** Use IBKR
- Worth the setup complexity
- Best for options/futures
- Global market access
- Industry-standard platform

**For crypto:** Use Binance or Coinbase
- Both have pure REST APIs
- Free WebSocket streaming
- No local software required

### Next Steps

1. **Try Alpaca first** (easiest)
   ```bash
   # Get free keys: https://app.alpaca.markets/signup
   python test_alpaca_live.py
   ```

2. **If you need options/futures** → Set up IBKR
   - Download IB Gateway
   - Enable API
   - Run tests

3. **Pick the right provider for your use case!**

---

**Quick Reference:**
- 🎯 US Stocks → **Alpaca**
- 📊 Options → **IBKR**
- 🌍 Global Markets → **IBKR**
- 🚀 Cloud Deployment → **Alpaca**
- 💰 Crypto → **Binance/Coinbase**
- 📈 Economic Data → **FRED**

**All 8 providers are fully implemented and ready to use!**
