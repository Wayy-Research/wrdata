# Provider Setup Guide

Complete guide to setting up all 12 data providers in wrdata.

## Quick Overview

| Provider | Setup Time | API Key | Credit Card? | Best For |
|----------|------------|---------|--------------|----------|
| **YFinance** | 0 min | ❌ No | ❌ No | Global stocks (delayed) |
| **Coinbase** | 0 min | ❌ No | ❌ No | US crypto |
| **Binance** | 1 min | Optional | ❌ No | Global crypto |
| **Kraken** | 1 min | Optional | ❌ No | European crypto |
| **Alpaca** | 2 min | ✅ Yes | ❌ No | US stocks (real-time) |
| **FRED** | 2 min | ✅ Yes | ❌ No | Economic data |
| **Polygon.io** | 2 min | ✅ Yes | ❌ No | Premium US data |
| **Tradier** | 2 min | ✅ Yes | ❌ No | FREE options! |
| **TwelveData** | 2 min | ✅ Yes | ❌ No | Global stocks |
| **Alpha Vantage** | 2 min | ✅ Yes | ❌ No | Multi-asset |
| **Finnhub** | 2 min | ✅ Yes | ❌ No | Global stocks + news |
| **IBKR** | 5 min | ✅ Yes | ❌ No | Professional trading |

**Total providers: 12 active** (48% to goal of 25)

---

## No Setup Required (0 minutes)

### 1. YFinance - Just Use It!

```python
from wrdata.providers import YFinanceProvider

yf = YFinanceProvider()  # No API key needed!

response = yf.fetch_timeseries(
    symbol="AAPL",
    start_date="2024-01-01",
    end_date="2024-11-08"
)
```

**Features:**
- ✅ Completely free
- ✅ Unlimited requests
- ✅ Global stocks, ETFs, forex
- ⚠️ 15-minute delayed data

**When to use:** Quick testing, historical analysis, global coverage

---

### 2. Coinbase - No Key Needed!

```python
from wrdata.providers import CoinbaseProvider

coinbase = CoinbaseProvider()  # Public endpoints work without key!

response = coinbase.fetch_timeseries(
    symbol="BTC-USD",
    start_date="2024-01-01",
    end_date="2024-11-08"
)
```

**Features:**
- ✅ Free, no key needed
- ✅ 748 crypto pairs
- ✅ WebSocket streaming
- ✅ US-friendly

**When to use:** Crypto data, US-based users

---

## Free Tier Setup (2 minutes each)

### 3. Alpaca - Best for US Stocks

**Setup:**

1. **Sign up** (no credit card!):
   - Go to: https://app.alpaca.markets/signup
   - Create account
   - Verify email

2. **Get API keys:**
   - Click "Generate API Key"
   - Copy both Key and Secret
   - Choose "Paper Trading" (free!)

3. **Add to `.env`:**
   ```bash
   ALPACA_API_KEY=your_key_here
   ALPACA_API_SECRET=your_secret_here
   ```

4. **Use it:**
   ```python
   from wrdata.providers import AlpacaProvider
   import os

   alpaca = AlpacaProvider(
       api_key=os.getenv("ALPACA_API_KEY"),
       api_secret=os.getenv("ALPACA_API_SECRET"),
       paper=True  # Free paper trading!
   )

   response = alpaca.fetch_timeseries("AAPL", "2024-01-01", "2024-11-08")
   ```

**Free Tier:**
- ✅ Real-time IEX quotes
- ✅ 200 requests/minute
- ✅ WebSocket streaming
- ✅ Paper trading account

**When to use:** US stocks, real-time data, trading bots

---

### 4. Polygon.io - Premium US Data

**Setup:**

1. **Sign up**:
   - Go to: https://polygon.io/dashboard/signup
   - Create account (no credit card for free tier!)

2. **Get API key:**
   - Dashboard → API Keys
   - Copy your key

3. **Add to `.env`:**
   ```bash
   POLYGON_API_KEY=your_key_here
   ```

4. **Use it:**
   ```python
   from wrdata.providers import PolygonProvider
   import os

   polygon = PolygonProvider(api_key=os.getenv("POLYGON_API_KEY"))

   response = polygon.fetch_timeseries("AAPL", "2024-01-01", "2024-11-08")
   ```

**Free Tier:**
- ✅ 100 API calls/day
- ✅ 5 calls/minute
- ✅ Best-in-class data quality
- ⬆️ Upgrade: $99/mo for unlimited

**When to use:** Best US stock data, professional projects

---

### 5. Tradier - FREE Options Data! 🎁

**Setup:**

1. **Sign up**:
   - Go to: https://developer.tradier.com/getting_started
   - Click "Sign Up"
   - No credit card required!

2. **Create app:**
   - Dashboard → "Create Application"
   - Copy **Sandbox API Key** (for testing)

3. **Add to `.env`:**
   ```bash
   TRADIER_API_KEY=your_sandbox_key_here
   ```

4. **Use it:**
   ```python
   from wrdata.providers import TradierProvider
   import os

   tradier = TradierProvider(
       api_key=os.getenv("TRADIER_API_KEY"),
       sandbox=True  # Use sandbox for testing
   )

   # Get options chain (FREE!)
   expirations = tradier.get_available_expirations("AAPL")
   print(f"Found {len(expirations)} expirations")
   ```

**Free Tier:**
- ✅ **FREE options chains!** (unique!)
- ✅ Real-time quotes
- ✅ 120 requests/minute
- ✅ No credit card required

**When to use:** Options trading, free options data

---

### 6. FRED - Economic Data

**Setup:**

1. **Get API key**:
   - Go to: https://fred.stlouisfed.org/docs/api/api_key.html
   - Click "Request API Key"
   - Instant approval!

2. **Add to `.env`:**
   ```bash
   FRED_API_KEY=your_key_here
   ```

3. **Use it:**
   ```python
   from wrdata.providers import FREDProvider
   import os

   fred = FREDProvider(api_key=os.getenv("FRED_API_KEY"))

   # Get GDP data
   gdp = fred.fetch_timeseries("GDP", "2020-01-01", "2024-11-08")

   # Get unemployment rate
   unrate = fred.fetch_timeseries("UNRATE", "2020-01-01", "2024-11-08")
   ```

**Free Tier:**
- ✅ 800,000+ economic series
- ✅ Unlimited requests
- ✅ Federal Reserve data

**When to use:** Economic analysis, macro data

---

### 7. TwelveData - Global Stocks

**Setup:**

1. **Sign up**:
   - Go to: https://twelvedata.com/pricing
   - Choose "Basic (Free)"
   - No credit card!

2. **Get API key:**
   - Dashboard → API Key
   - Copy key

3. **Add to `.env`:**
   ```bash
   TWELVEDATA_API_KEY=your_key_here
   ```

4. **Use it:**
   ```python
   from wrdata.providers import TwelveDataProvider
   import os

   td = TwelveDataProvider(api_key=os.getenv("TWELVEDATA_API_KEY"))

   # Global stocks
   response = td.fetch_timeseries("AAPL", "2024-01-01", "2024-11-08")

   # Forex
   eurusd = td.fetch_timeseries("EUR/USD", "2024-01-01", "2024-11-08")
   ```

**Free Tier:**
- ✅ 800 API calls/day
- ✅ 8 calls/minute
- ✅ Global stocks, forex, crypto
- ✅ WebSocket (1 symbol)

**When to use:** Global stocks, forex, multi-asset portfolios

---

### 8. Kraken - European Crypto

**Setup:**

No API key needed for market data!

```python
from wrdata.providers import KrakenProvider

kraken = KrakenProvider()  # No key needed!

# Bitcoin
btc = kraken.fetch_timeseries("XBTUSD", "2024-01-01", "2024-11-08")

# Ethereum
eth = kraken.fetch_timeseries("ETHUSD", "2024-01-01", "2024-11-08")
```

**Optional:** Get API key for account features at https://www.kraken.com/

**Free Tier:**
- ✅ No API key needed
- ✅ 200+ crypto pairs
- ✅ WebSocket streaming
- ✅ Unlimited requests

**When to use:** European crypto, more pairs than Coinbase

---

### 9. Binance - Global Crypto Leader

**Setup:**

No API key needed for market data!

```python
from wrdata.providers import BinanceProvider

binance = BinanceProvider()  # No key needed!

# Bitcoin
btc = binance.fetch_timeseries("BTCUSDT", "2024-01-01", "2024-11-08")

# Ethereum
eth = binance.fetch_timeseries("ETHUSDT", "2024-01-01", "2024-11-08")
```

**Optional:** Get API key at https://www.binance.com/en/my/settings/api-management

**Free Tier:**
- ✅ No API key needed
- ✅ 1000+ crypto pairs
- ✅ WebSocket streaming
- ✅ Unlimited (with rate limits)

**When to use:** Global crypto, most pairs, fastest data

---

### 10. Alpha Vantage - Multi-Asset

**Setup:**

1. **Get API key**:
   - Go to: https://www.alphavantage.co/support/#api-key
   - Enter email
   - Instant key!

2. **Add to `.env`:**
   ```bash
   ALPHA_VANTAGE_API_KEY=your_key_here
   ```

3. **Use it:**
   ```python
   from wrdata.providers import AlphaVantageProvider
   import os

   av = AlphaVantageProvider(api_key=os.getenv("ALPHA_VANTAGE_API_KEY"))

   response = av.fetch_timeseries("AAPL", "2024-01-01", "2024-11-08")
   ```

**Free Tier:**
- ✅ 5 API calls/minute
- ✅ 500 calls/day
- ✅ Stocks, forex, crypto

**When to use:** Backup provider, multi-asset

---

### 11. Finnhub - Global Stocks + News

**Setup:**

1. **Sign up**:
   - Go to: https://finnhub.io/register
   - Create account

2. **Get API key:**
   - Dashboard → API Key
   - Copy key

3. **Add to `.env`:**
   ```bash
   FINNHUB_API_KEY=your_key_here
   ```

4. **Use it:**
   ```python
   from wrdata.providers import FinnhubProvider
   import os

   finnhub = FinnhubProvider(api_key=os.getenv("FINNHUB_API_KEY"))

   response = finnhub.fetch_timeseries("AAPL", "2024-01-01", "2024-11-08")
   ```

**Free Tier:**
- ✅ 60 API calls/minute
- ✅ WebSocket streaming
- ✅ Global coverage
- ✅ News + fundamentals

**When to use:** Global stocks, news data, WebSocket

---

### 12. Interactive Brokers (IBKR) - Professional

**Setup (with Docker):**

See [IBKR_DOCKER_QUICKSTART.md](IBKR_DOCKER_QUICKSTART.md) for details.

**Quick version:**

1. **Get IBKR account**: https://www.interactivebrokers.com/
2. **Enable API** in account settings
3. **Run Docker container:**
   ```bash
   cd docker/ibkr
   cp .env.example .env
   # Edit .env with your credentials
   ./start.sh
   ```

4. **Use it:**
   ```python
   from wrdata.providers import IBKRProvider

   ibkr = IBKRProvider(host="localhost", port=4002)
   ibkr.connect()

   response = ibkr.fetch_timeseries("AAPL", "2024-01-01", "2024-11-08")
   ```

**Free Tier:**
- ✅ Unlimited API calls
- ✅ Global markets (150+ exchanges)
- ✅ Options, futures, forex
- ⚠️ Requires Docker container

**When to use:** Options, futures, global markets, professional trading

---

## Complete `.env` File Example

```bash
# === Stock Providers ===
ALPACA_API_KEY=your_alpaca_key
ALPACA_API_SECRET=your_alpaca_secret
POLYGON_API_KEY=your_polygon_key
TRADIER_API_KEY=your_tradier_key
TWELVEDATA_API_KEY=your_twelvedata_key
ALPHA_VANTAGE_API_KEY=your_av_key
FINNHUB_API_KEY=your_finnhub_key

# === Economic Data ===
FRED_API_KEY=your_fred_key

# === IBKR (if using) ===
IBKR_USERNAME=your_ibkr_username
IBKR_PASSWORD=your_ibkr_password
IBKR_TRADING_MODE=paper  # or 'live'

# === Optional (public endpoints work without) ===
BINANCE_API_KEY=optional
KRAKEN_API_KEY=optional
COINBASE_API_KEY=optional
```

---

## Provider Decision Tree

```
What do you need?

├─ US Stocks?
│  ├─ Real-time? → Alpaca (free!) or Polygon ($99/mo)
│  ├─ Options? → Tradier (FREE!) or IBKR
│  └─ Historical? → YFinance (free, delayed)
│
├─ Global Stocks?
│  ├─ Premium quality? → IBKR or Polygon
│  ├─ Free? → TwelveData, Finnhub, YFinance
│  └─ News? → Finnhub
│
├─ Cryptocurrency?
│  ├─ Most pairs? → Binance
│  ├─ US-friendly? → Coinbase
│  └─ European? → Kraken
│
├─ Options?
│  ├─ FREE? → Tradier (unique!)
│  └─ Professional? → IBKR
│
├─ Economic Data?
│  └─ FRED (only choice, excellent!)
│
└─ Futures/Forex?
   └─ IBKR (best coverage)
```

---

## Testing Your Setup

After setting up, test each provider:

```bash
# Test individual providers
python test_alpaca_live.py
python test_polygon_live.py
python test_tradier_live.py
python test_twelvedata_live.py
python test_kraken_live.py

# Test IBKR (requires Docker running)
python test_ibkr_live.py

# Test streaming
python test_streaming.py
```

---

## Troubleshooting

### "API key not found"
```bash
# Make sure .env file exists
ls -la .env

# Source it if needed
export $(cat .env | xargs)
```

### "Rate limit exceeded"
Each provider has different limits:
- Alpha Vantage: 5/min (slowest)
- TwelveData: 8/min
- Polygon (free): 5/min
- Tradier: 120/min
- Alpaca: 200/min
- Others: Unlimited or very high

### "Invalid API key"
- Double-check key in .env
- Ensure no extra spaces
- Some keys expire - regenerate if needed

### "No data returned"
- Check symbol format (each provider differs)
- Verify date range
- Some providers limit historical data

---

## Cost Summary

| Provider | Free Tier | Paid Plans | Best Value |
|----------|-----------|------------|------------|
| YFinance | Unlimited | N/A | ⭐⭐⭐⭐⭐ Free |
| Coinbase | Unlimited | N/A | ⭐⭐⭐⭐⭐ Free |
| Binance | Unlimited | N/A | ⭐⭐⭐⭐⭐ Free |
| Kraken | Unlimited | N/A | ⭐⭐⭐⭐⭐ Free |
| FRED | Unlimited | N/A | ⭐⭐⭐⭐⭐ Free |
| Alpaca | 200/min | N/A | ⭐⭐⭐⭐⭐ Free |
| Tradier | 120/min | N/A | ⭐⭐⭐⭐⭐ Free |
| Alpha Vantage | 5/min | $50/mo | ⭐⭐⭐ Limited free |
| TwelveData | 800/day | $12/mo | ⭐⭐⭐⭐ Good free |
| Finnhub | 60/min | $60/mo | ⭐⭐⭐⭐ Good free |
| Polygon | 100/day | $99/mo | ⭐⭐⭐ Premium quality |
| IBKR | Unlimited | N/A | ⭐⭐⭐⭐ Free but complex |

**Recommendation:** Start with free unlimited providers, add paid ones as needed.

---

## Next Steps

1. **Choose 3-5 providers** that match your needs
2. **Get API keys** (takes 10 minutes total)
3. **Add to `.env`** file
4. **Run tests** to verify
5. **Start building!**

See [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) for usage examples.

---

**All 12 providers are ready to use!** 🎉
