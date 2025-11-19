# Symbol Format Guide - wrdata

## TL;DR - Quick Reference

**For best results, use these formats:**

| Asset | Symbol Format | Example |
|-------|--------------|---------|
| Stocks | `TICKER` | `AAPL`, `GOOGL`, `MSFT` |
| Crypto | `XXX-USD` | `BTC-USD`, `ETH-USD`, `SOL-USD` |
| Forex | `XXXYYY` | `EURUSD`, `GBPJPY` |
| Economic | `CODE` | `GDP`, `CPI`, `UNRATE` |

## Why Symbol Formats Matter

Different data providers use different symbol conventions. wrdata tries to handle this automatically, but knowing the formats helps you get data faster.

## Crypto Symbol Formats by Provider

### Yahoo Finance (Free, Works in US)
**Format:** `XXX-USD`
- ✅ `BTC-USD`
- ✅ `ETH-USD`
- ✅ `SOL-USD`
- ✅ `DOGE-USD`
- ❌ `BTCUSDT` (won't work)
- ❌ `ETHUSDT` (won't work)

### Coinbase (Free, Works in US)
**Format:** `XXX-USD` or `XXXUSD`
- ✅ `BTC-USD`
- ✅ `ETH-USD`
- ✅ `BTCUSD`
- ✅ `ETHUSD`

### CoinGecko (Free, Works Everywhere)
**Format:** `XXX` or coin id
- ✅ `bitcoin`
- ✅ `ethereum`
- ✅ `solana`

## Stock Symbol Formats

### US Stocks (Most Providers)
**Format:** `TICKER`
- ✅ `AAPL` (Apple)
- ✅ `GOOGL` (Google)
- ✅ `MSFT` (Microsoft)
- ✅ `TSLA` (Tesla)

### International Stocks (YFinance)
**Format:** `TICKER.EXCHANGE`
- ✅ `7203.T` (Toyota - Tokyo)
- ✅ `VOD.L` (Vodafone - London)
- ✅ `BMW.DE` (BMW - Germany)

## Forex Symbol Formats

### Yahoo Finance
**Format:** `XXXYYY=X`
- ✅ `EURUSD=X`
- ✅ `GBPJPY=X`
- ✅ `USDJPY=X`

### Most Other Providers
**Format:** `XXXYYY` or `XXX/YYY`
- ✅ `EURUSD`
- ✅ `EUR/USD`
- ✅ `GBPJPY`

## Current Provider Priority

wrdata auto-selects providers based on asset type:

```python
# Crypto (US users)
1. YFinance → ✅ Primary (best for US)
2. CoinGecko → ✅ Fallback
3. Coinbase → ✅ Fallback

# Stocks
1. YFinance → ✅ Always works
2. Alpaca → ✅ If API key provided
3. Polygon → ✅ If API key provided
```

## Recommended Formats for US Users

Use these formats for best compatibility:

### Crypto (Use Yahoo Finance Format)
```python
from wrdata import DataStream

stream = DataStream()

# ✅ BEST - Direct to YFinance, no fallback needed
df = stream.get("BTC-USD")   # Bitcoin
df = stream.get("ETH-USD")   # Ethereum
df = stream.get("SOL-USD")   # Solana
df = stream.get("ADA-USD")   # Cardano
df = stream.get("DOGE-USD")  # Dogecoin
```

### Or Force Provider
```python
# Force YFinance for crypto
df = stream.get("BTC-USD", provider="yfinance")

# Force Coinbase
df = stream.get("BTCUSD", provider="coinbase")

# Force CoinGecko (uses coin IDs)
df = stream.get("bitcoin", provider="coingecko")
```

## Common Issues & Solutions

### Issue 1: "No data found for ETHUSDT"

**Problem:** YFinance doesn't recognize `ETHUSDT` format.

**Solution:** Use `ETH-USD` instead:
```python
# ❌ Won't work with YFinance
df = stream.get("ETHUSDT")  # Falls back to Coinbase (slower)

# ✅ Works directly with YFinance (faster)
df = stream.get("ETH-USD")
```

### Issue 2: Symbol Format Errors

**Problem:** Using the wrong symbol format for a provider.

**Solution:** Use YFinance format for best compatibility:
```python
# ✅ Recommended format
df = stream.get("BTC-USD")  # Works with YFinance

# Or force a specific provider
df = stream.get("BTCUSD", provider="coinbase")
```

### Issue 3: "possibly delisted; no timezone found"

**Problem:** YFinance warning when symbol format doesn't match.

**Solution:** Use correct format for the provider:
```python
# ❌ Wrong format for YFinance
df = stream.get("BTCUSDT")  # Causes warning

# ✅ Correct format for YFinance
df = stream.get("BTC-USD")  # No warning
```

## Symbol Conversion Table

| What You Want | YFinance | Coinbase | CoinGecko |
|---------------|----------|----------|-----------|
| Bitcoin | `BTC-USD` | `BTC-USD` or `BTCUSD` | `bitcoin` |
| Ethereum | `ETH-USD` | `ETH-USD` or `ETHUSD` | `ethereum` |
| Solana | `SOL-USD` | `SOL-USD` or `SOLUSD` | `solana` |
| Cardano | `ADA-USD` | `ADA-USD` or `ADAUSD` | `cardano` |
| Polygon | `MATIC-USD` | `MATIC-USD` | `matic-network` |
| Dogecoin | `DOGE-USD` | `DOGE-USD` | `dogecoin` |

## Auto-Normalization (Coming Soon)

We're working on automatic symbol normalization:

```python
# Future: These will all work
df = stream.get("ETH")      # → Auto-converts to ETH-USD
df = stream.get("ETHUSDT")  # → Auto-converts to ETH-USD for YFinance
df = stream.get("ETH-USD")  # → Already correct

# All return the same data!
```

## Best Practices

### 1. Use YFinance Format for Crypto (US Users)
```python
# ✅ Best
df = stream.get("BTC-USD")
df = stream.get("ETH-USD")
```

### 2. Check Available Providers
```python
stream = DataStream()
print(stream.providers.keys())  # See what's available
```

### 3. Force Provider When Needed
```python
# If you know which provider you want
df = stream.get("AAPL", provider="polygon")  # Premium data
df = stream.get("BTC-USD", provider="yfinance")  # Free crypto
```

### 4. Use Status to Verify
```python
status = stream.status()
for provider, info in status.items():
    print(f"{provider}: {info['connected']}")
```

## Quick Symbol Finder

Can't remember the format? Try these:

```python
from wrdata import DataStream

stream = DataStream()

# Stocks - just use the ticker
df = stream.get("AAPL")     # ✓ Works
df = stream.get("TSLA")     # ✓ Works

# Crypto - use dash format for best results
df = stream.get("BTC-USD")  # ✓ Works (YFinance)
df = stream.get("ETH-USD")  # ✓ Works (YFinance)

# Alternative formats (may require fallback)
df = stream.get("BTCUSD")   # ✓ Works (Coinbase)
df = stream.get("bitcoin")  # ✓ Works (CoinGecko)

# Forex
df = stream.get("EURUSD")   # ✓ Works
```

## Summary

**Best Practices:**
- ✅ Crypto: Use `XXX-USD` format (`BTC-USD`, `ETH-USD`)
- ✅ Stocks: Use ticker (`AAPL`, `GOOGL`)
- ✅ Forex: Use `XXXYYY` (`EURUSD`, `GBPJPY`)

**Using the right format ensures fast, reliable data fetching!**
