# CCXT Integration - 100+ Crypto Exchanges

## Overview

wrdata now includes **CCXT (CryptoCurrency eXchange Trading Library)** integration, giving you access to **100+ cryptocurrency exchanges** worldwide through a unified API.

## Quick Start

```python
from wrdata import DataStream

stream = DataStream()

# Search across CCXT exchanges
results = stream.search_symbol("DOGE", limit=50)

# Results from OKX, KuCoin, Gate.io, Bitfinex, and more
for r in results:
    print(f"{r['symbol']:25} from {r['provider']}")
```

## Pre-Configured Exchanges

wrdata automatically initializes these major exchanges (no API key required):

1. **OKX** - Global cryptocurrency exchange
   - 350+ trading pairs
   - High liquidity
   - Advanced trading features

2. **KuCoin** - "The People's Exchange"
   - 700+ cryptocurrencies
   - Wide altcoin selection
   - Low fees

3. **Gate.io** - Comprehensive crypto platform
   - 1,400+ trading pairs
   - Extensive crypto selection
   - DeFi tokens and NFTs

4. **Bitfinex** - Professional trading platform
   - Advanced trading tools
   - High liquidity pairs
   - Margin and derivatives

5. **Bybit** - Fast-growing derivatives exchange
   - Spot and derivatives
   - High-performance matching engine
   - Note: May be geo-blocked in some regions

## Real Test Results

### Search for "DOGE" (limit=100):

```
CCXT_GATEIO (43 results):
  • POLYDOGE/USDT
  • AIDOGE/USDT
  • DOGE2/USDT
  • DOGE5S/USDT
  • DOGE5L/USDT

CCXT_KUCOIN (7 results):
  • DOGE/BTC
  • DOGE/KCS
  • DOGE3L/USDT
  • DOGE3S/USDT
  • SHIB/DOGE

CCXT_OKX (8 results):
  • DOGE/EUR
  • DOGE/USD
  • BABYDOGE/USD
  • DOGE/USDT
  • BABYDOGE/USDT

CCXT_BITFINEX (2 results):
  • TESTDOGE/TESTUSD
  • TESTDOGE/TESTUSDT

COINGECKO (25 results):
  • dogecoin
  • binance-peg-dogecoin
  • baby-doge-coin

YFINANCE (5 results):
  • DOGE-USD
  • DOGE-EUR

COINBASE (3 results):
  • DOGE-BTC
  • DOGE-USDT

Total: 93 results from 7 providers!
```

## Using CCXT Exchanges for Data

After finding symbols, fetch historical data:

```python
# Search for Solana on different exchanges
results = stream.search_symbol("SOL", limit=20)

# Find OKX's Solana pair
okx_sol = next(r for r in results if r['provider'] == 'ccxt_okx' and 'SOL' in r['symbol'])

# Fetch historical data from OKX
df = stream.get(okx_sol['symbol'], provider='ccxt_okx', start="2024-01-01")
print(df.head())
```

## All 100+ Available Exchanges

CCXT supports these exchanges (add any via CCXTProvider):

### Tier 1 (High Volume)
- Binance, Coinbase, Kraken, OKX, Bybit
- KuCoin, Gate.io, Bitfinex, Gemini, Huobi
- Bitget, MEXC, Crypto.com

### Tier 2 (Medium Volume)
- BingX, BitMart, Bitrue, Poloniex
- HTX (Huobi), Bitstamp, Phemex
- BIT, Bitso, CoinEx, Lbank

### Tier 3 (Specialized)
- Deribit (Options & Futures)
- FTX (Derivatives)
- Kraken Futures
- Plus 70+ more exchanges

Full list: https://github.com/ccxt/ccxt#supported-cryptocurrency-exchange-markets

## Adding Custom Exchanges

```python
from wrdata.providers.ccxt_provider import CCXTProvider

# Add any CCXT exchange manually
gemini = CCXTProvider(exchange_id='gemini')
stream.providers['ccxt_gemini'] = gemini

# Now search will include Gemini
results = stream.search_symbol("BTC", limit=50)
```

## Exchange-Specific Features

Different exchanges offer different features:

| Exchange | Spot | Futures | Margin | Options | Staking |
|----------|------|---------|--------|---------|---------|
| OKX | ✓ | ✓ | ✓ | ✓ | ✓ |
| KuCoin | ✓ | ✓ | ✓ | ✗ | ✓ |
| Gate.io | ✓ | ✓ | ✓ | ✗ | ✓ |
| Bitfinex | ✓ | ✗ | ✓ | ✗ | ✓ |
| Bybit | ✓ | ✓ | ✓ | ✗ | ✗ |

## Symbol Format Differences

Each exchange uses slightly different formats:

| Asset | OKX | KuCoin | Gate.io | Standard |
|-------|-----|--------|---------|----------|
| Bitcoin | BTC/USDT | BTC/USDT | BTC/USDT | Same |
| Ethereum | ETH/USDT | ETH/USDT | ETH/USDT | Same |
| Solana | SOL/USDT | SOL/USDT | SOL/USDT | Same |

Most exchanges use the `/` separator: `BASE/QUOTE`

## Performance Tips

1. **Limit your searches** - Default is 10, increase only if needed
   ```python
   results = stream.search_symbol("BTC", limit=20)  # Faster
   ```

2. **CCXT searches last** - YFinance and CoinGecko are searched first
   - If you want CCXT results, increase limit to 30+

3. **Some exchanges are geo-blocked**
   - Bybit: Blocked in US, Canada, and some regions
   - Check your region's restrictions

4. **Use specific exchanges when possible**
   ```python
   # Faster - direct to exchange
   df = stream.get("BTC/USDT", provider="ccxt_okx")

   # Slower - searches all providers
   df = stream.get("BTC")
   ```

## Rate Limits

CCXT automatically handles rate limiting for each exchange:

- **OKX**: 20 requests/second
- **KuCoin**: 10 requests/second (public), 200/sec (private)
- **Gate.io**: 900 requests/minute
- **Bitfinex**: 90 requests/minute
- **Bybit**: 50 requests/second

wrdata enables `enableRateLimit: True` by default, so you don't need to worry about this.

## Geo-Restrictions

Some exchanges block certain countries:

### US-Blocked Exchanges
- Bybit
- Huobi (HTX)
- Several smaller exchanges

### US-Available Exchanges
- Coinbase
- Kraken
- Gemini
- Bitfinex (with restrictions)

### Global Exchanges
- OKX (some restrictions)
- Gate.io
- KuCoin

## Error Handling

CCXT errors are handled gracefully:

```python
# If an exchange fails, others continue
results = stream.search_symbol("ETH", limit=50)

# You'll see warnings like:
# Warning: CCXT bybit search failed: 403 Forbidden
# But other exchanges still return results
```

## Advanced: Using CCXT Directly

For advanced users who need exchange-specific features:

```python
from wrdata.providers.ccxt_provider import CCXTProvider

# Create OKX provider
okx = CCXTProvider(
    exchange_id='okx',
    api_key='your_key',  # Optional, for private endpoints
    api_secret='your_secret'
)

# Access the underlying CCXT exchange object
exchange = okx.exchange

# Use any CCXT method
tickers = exchange.fetch_tickers(['BTC/USDT', 'ETH/USDT'])
orderbook = exchange.fetch_order_book('BTC/USDT')
```

## Benefits Over Direct CCXT

wrdata's CCXT integration provides:

1. **Unified output format** - All exchanges return the same DataFrame structure
2. **Automatic error handling** - Failed exchanges don't crash your code
3. **Multi-provider search** - Search across all exchanges at once
4. **Consistent API** - Same `stream.get()` method for all exchanges
5. **Smart defaults** - Works immediately, no exchange-specific configuration

## Comparison: wrdata vs. Direct CCXT

### Direct CCXT
```python
import ccxt

# Manual setup for each exchange
okx = ccxt.okx({'enableRateLimit': True})
kucoin = ccxt.kucoin({'enableRateLimit': True})
gateio = ccxt.gateio({'enableRateLimit': True})

# Different method names
okx_data = okx.fetch_ohlcv('BTC/USDT', '1d')
kucoin_data = kucoin.fetch_ohlcv('BTC/USDT', '1d')

# Manual data conversion
import pandas as pd
df_okx = pd.DataFrame(okx_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
```

### wrdata with CCXT
```python
from wrdata import DataStream

stream = DataStream()  # All exchanges auto-initialized

# Unified API
df_okx = stream.get("BTC/USDT", provider="ccxt_okx")
df_kucoin = stream.get("BTC/USDT", provider="ccxt_kucoin")

# Already in Polars DataFrame format
print(df_okx.head())
```

## Conclusion

With CCXT integration, wrdata now provides access to:

- ✅ **100+ cryptocurrency exchanges**
- ✅ **Thousands of trading pairs**
- ✅ **Comprehensive altcoin coverage**
- ✅ **Unified API across all exchanges**
- ✅ **Automatic rate limiting**
- ✅ **Built-in error handling**

This makes wrdata the most comprehensive Python library for cryptocurrency market data.

## See Also

- [SYMBOL_SEARCH.md](SYMBOL_SEARCH.md) - Multi-provider symbol search guide
- [SYMBOL_FORMATS.md](SYMBOL_FORMATS.md) - Symbol format reference
- [README.md](README.md) - Main documentation
- [CCXT Documentation](https://docs.ccxt.com/) - Official CCXT docs
