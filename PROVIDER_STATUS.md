# Provider Status - November 2024

## Active Providers: 6

### REST API Providers

1. **YFinance** ✅
   - Status: Active
   - Cost: Free, unlimited
   - Coverage: Global stocks, ETFs, indices
   - Data: Historical OHLCV, delayed quotes
   - Limitations: 15-min delayed data

2. **Binance** ✅
   - Status: Active
   - Cost: Free (higher limits with API key)
   - Coverage: Cryptocurrency
   - Data: Real-time quotes, historical OHLCV
   - Limitations: Geo-restricted in some countries

3. **FRED** ✅
   - Status: Active
   - Cost: Free with API key
   - Coverage: 800,000+ economic indicators
   - Data: GDP, inflation, unemployment, etc.
   - Limitations: Economic data only

4. **Alpha Vantage** ✅
   - Status: Active
   - Cost: Free tier (5 calls/min)
   - Coverage: Stocks, forex, crypto
   - Data: Real-time quotes, historical OHLCV
   - Limitations: Rate limited (5/min)

5. **Coinbase** ✅
   - Status: Active
   - Cost: Free, no API key required
   - Coverage: 748 crypto trading pairs
   - Data: Real-time quotes, historical OHLCV
   - Limitations: Crypto only

6. **Finnhub** ✅ NEW!
   - Status: Active
   - Cost: Free tier (60 calls/min + WebSocket!)
   - Coverage: 60+ global exchanges, forex, crypto
   - Data: Real-time quotes, historical OHLCV, news, fundamentals
   - Limitations: 1 year historical per call
   - **Special: FREE WebSocket streaming!**

### Streaming Providers

1. **Binance WebSocket** ✅
   - Real-time crypto trades and klines
   - Free, no authentication required
   - Multiple symbols on one connection

2. **Coinbase WebSocket** ✅
   - Real-time crypto trades
   - Free, no authentication required
   - Clean JSON messages

3. **Finnhub WebSocket** ✅
   - Real-time stock trades
   - **FREE on free tier!**
   - Multi-symbol support
   - Global coverage

4. **IBKR TWS API** ✅
   - Real-time bars (5-second)
   - Tick-by-tick market data
   - Professional-grade streaming
   - Multi-asset support (stocks, options, futures, forex)

5. **Alpaca WebSocket** ✅ NEW!
   - Real-time IEX stock trades
   - Real-time quotes (bid/ask)
   - Real-time minute bars
   - FREE with Alpaca account

## Provider Priority by Asset Type

```python
{
    'stock':  ['alpaca', 'ibkr', 'finnhub', 'alphavantage', 'yfinance'],
    'equity': ['alpaca', 'ibkr', 'finnhub', 'alphavantage', 'yfinance'],
    'etf':    ['alpaca', 'ibkr', 'finnhub', 'yfinance'],
    'forex':  ['ibkr', 'alphavantage', 'yfinance'],
    'crypto': ['binance', 'coinbase', 'yfinance'],
    'economic': ['fred'],
    'options': ['ibkr'],
    'futures': ['ibkr'],
}
```

**Why Alpaca first for stocks?** Pure REST API, no local software required, free real-time IEX data, paper trading included!

## Recently Removed

### IEX Cloud ❌
- **Status**: Shut down August 31, 2024
- **Reason**: Service discontinued
- **Replacement**: Finnhub (BETTER alternative!)
- **Migration**: Change `iex_key` to `finnhub_key`

7. **Interactive Brokers (IBKR)** ✅
   - Status: Active
   - Cost: Free with IBKR account
   - Coverage: 150+ global exchanges, stocks, options, futures, forex
   - Data: Real-time & delayed quotes, historical OHLCV, options chains
   - Limitations: Requires TWS/IB Gateway running, account required
   - **Special: Professional-grade multi-asset platform!**

8. **Alpaca** ✅ NEW!
   - Status: Active
   - Cost: Free with account (paper trading included)
   - Coverage: US stocks (IEX feed)
   - Data: Real-time quotes, historical OHLCV, WebSocket streaming
   - Limitations: US markets only, no options
   - **Special: Pure REST API - no local software required!**

## Coming Soon

### Next 2 Providers to Implement:

1. **Kraken** 🔜
   - Major crypto exchange
   - WebSocket streaming
   - Historical data
   - Optional API key for higher limits

2. **Polygon.io** 🔜
   - Premium market data
   - High-quality REST API
   - Historical and real-time data
   - Free tier available

## Implementation Stats

- **Total Providers**: 8
- **REST APIs**: 8
- **WebSocket Streams**: 5
- **Free Tier**: 8 (100%!)
- **No API Key Required**: 2 (YFinance, Coinbase)
- **Free WebSocket**: 5 (Binance, Coinbase, Finnhub, IBKR, Alpaca)
- **Pure REST API (no local software)**: 7 (all except IBKR)

## Coverage Summary

### Asset Classes
- ✅ US Stocks (IBKR, Finnhub, Alpha Vantage, YFinance)
- ✅ Global Stocks (IBKR, Finnhub, YFinance)
- ✅ ETFs (IBKR, Finnhub, YFinance)
- ✅ Forex (IBKR, Alpha Vantage, YFinance)
- ✅ Cryptocurrency (Binance, Coinbase, YFinance)
- ✅ Economic Data (FRED)
- ✅ Options (IBKR)
- ✅ Futures (IBKR)
- ❌ Bonds (Coming: IBKR full implementation)

### Geographic Coverage
- ✅ United States
- ✅ Europe (IBKR, Finnhub, YFinance)
- ✅ Asia (IBKR, Finnhub, YFinance)
- ✅ Global Crypto Markets
- ✅ 150+ Exchanges (IBKR)

### Data Types
- ✅ Real-time Quotes
- ✅ Historical OHLCV
- ✅ Company Fundamentals
- ✅ News
- ✅ Economic Indicators
- ✅ Real-time Streaming (WebSocket)
- ✅ Options Chains (IBKR)
- ✅ Account Data (IBKR)
- ✅ Positions & Orders (IBKR)
- ❌ Level 2 Order Book (Coming)

## Rate Limits Summary

| Provider | REST API Limit | WebSocket | Cost |
|----------|---------------|-----------|------|
| YFinance | Unlimited | N/A | Free |
| Binance | Weight-based | Unlimited | Free |
| FRED | Unlimited | N/A | Free |
| Alpha Vantage | 5/min | N/A | Free |
| Coinbase | Burst-friendly | Unlimited | Free |
| Finnhub | 60/min | Unlimited | Free |
| IBKR | Unlimited | Unlimited | Free with account |
| **Alpaca** | **200/min** | **Unlimited** | **Free with account** |

## Best Providers for Each Use Case

### Real-time Stock Quotes
**Winner:** Alpaca (200/min + FREE WebSocket streaming + pure REST API)
- Alternative 1: Finnhub (60/min + WebSocket)
- Alternative 2: IBKR (unlimited but requires TWS/Gateway)

### Historical Stock Data
**Winner:** Finnhub (60/min, 1 year/call)
- Alternative: YFinance (unlimited, any timeframe)

### Crypto Real-time
**Winner:** Binance (fastest, most pairs)
- Alternative: Coinbase (US-friendly, no key required)

### Economic Data
**Winner:** FRED (only option, 800k+ series)

### News & Fundamentals
**Winner:** Finnhub (comprehensive coverage)

### WebSocket Streaming
**Winners:**
- Stocks: Alpaca (FREE, pure API, paper trading!)
- Stocks (global): Finnhub (FREE!)
- Crypto: Binance or Coinbase

## Testing Status

| Provider | REST API | WebSocket | Tested |
|----------|----------|-----------|--------|
| YFinance | ✅ | N/A | ✅ Yes |
| Binance | ✅ | ✅ | ✅ Yes |
| FRED | ✅ | N/A | ✅ Yes |
| Alpha Vantage | ✅ | ✅ | ✅ Yes |
| Coinbase | ✅ | ✅ | ✅ Yes |
| Finnhub | ✅ | ✅ | ⏳ Ready to test |
| IBKR | ✅ | ✅ | ⏳ Ready to test |
| Alpaca | ✅ | ✅ | ⏳ Ready to test |

## Get API Keys

### Required Keys:
- **FRED**: https://fred.stlouisfed.org/docs/api/api_key.html
- **Alpha Vantage**: https://www.alphavantage.co/support/#api-key
- **Finnhub**: https://finnhub.io/register
- **Alpaca**: https://app.alpaca.markets/signup (includes paper trading!)

### Optional Keys (higher limits):
- **Binance**: https://www.binance.com/en/my/settings/api-management

### No Key Required:
- **YFinance**: Just use it!
- **Coinbase**: Public endpoints work without key

## Quick Setup

```bash
# Set all API keys at once
cat >> .env << EOF
FRED_API_KEY=your_fred_key
ALPHA_VANTAGE_API_KEY=your_av_key
FINNHUB_API_KEY=your_finnhub_key
BINANCE_API_KEY=optional
BINANCE_API_SECRET=optional
EOF

# Test all providers
source .venv/bin/activate
python test_fred_live.py
python test_alphavantage_live.py
python test_coinbase_live.py
python test_finnhub_live.py  # NEW!
```

## Roadmap to 25+ Providers

**Current:** 8 providers ✅
**Target:** 25+ providers
**Progress:** 32% complete

**Next 4 priorities:**
1. Kraken (crypto)
2. Polygon.io (premium data)
3. Twelve Data (multi-asset)
4. Tradier (options)

See `PROVIDER_ROADMAP.md` for the full list of planned integrations.

---

**Last Updated:** November 8, 2024
**Latest Additions:** Interactive Brokers (IBKR) + Alpaca
**Next Up:** Kraken (crypto exchange)
