# Symbol Search - Multi-Provider Discovery

## Overview

The `search_symbol()` method searches across multiple data providers to help you find the correct symbol format for any asset.

## Quick Start

```python
from wrdata import DataStream

stream = DataStream()

# Search for crypto
results = stream.search_symbol("bitcoin")
# Returns results from YFinance, CoinGecko, Kraken, Coinbase

# Search for stocks
results = stream.search_symbol("tesla")
# Returns TSLA, TL0.DE, TSLZ, etc.
```

## Providers Searched

### 1. **YFinance** (Always Available)
- Stocks, ETFs, major crypto
- Best for: US equities, futures, popular crypto pairs
- Format examples: `AAPL`, `BTC-USD`, `ETH-USD`

### 2. **CoinGecko** (Always Available, Free)
- **10,000+ cryptocurrencies**
- Best for: Altcoins, DeFi tokens, comprehensive crypto data
- Format examples: `bitcoin`, `ethereum`, `wrapped-bitcoin`
- No API key required!

### 3. **Kraken** (Always Available, Free)
- 200+ crypto trading pairs
- Best for: Major crypto with high liquidity
- Format examples: `XXBTZUSD`, `ETHEUR`
- No API key required for public data

### 4. **Coinbase** (Always Available, Free)
- Major crypto trading pairs
- Best for: US-available crypto
- Format examples: `BTC-USD`, `ETH-USD`, `SOL-USD`
- No API key required for market data

## Examples

### Search for Bitcoin

```python
results = stream.search_symbol("bitcoin", limit=10)

for r in results:
    print(f"{r['symbol']:20} from {r['provider']}")

# Output:
# BTC-USD              from yfinance
# bitcoin              from coingecko
# wrapped-bitcoin      from coingecko
# XXBTZUSD             from kraken
# BTC-USD              from coinbase
```

### Search for Ethereum

```python
results = stream.search_symbol("ethereum")

# Returns:
# ETH-USD (yfinance)
# ethereum (coingecko)
# ethereum-classic (coingecko)
# staked-ether (coingecko)
# wrapped-steth (coingecko)
# ...and more
```

### Group Results by Provider

```python
results = stream.search_symbol("SOL", limit=15)

by_provider = {}
for r in results:
    provider = r['provider']
    if provider not in by_provider:
        by_provider[provider] = []
    by_provider[provider].append(r)

for provider, items in by_provider.items():
    print(f"\n{provider.upper()}:")
    for item in items:
        print(f"  • {item['symbol']:20} - {item['name']}")
```

## Result Format

Each result is a dictionary with:

```python
{
    'symbol': 'BTC-USD',           # Trading symbol in provider's format
    'name': 'Bitcoin USD',         # Full name/description
    'type': 'cryptocurrency',      # Asset type
    'provider': 'yfinance',        # Where this result came from
    'exchange': 'CCC'              # Exchange/market
}
```

## Using Search Results

After finding the right symbol, use it to fetch data:

```python
# Search for Solana
results = stream.search_symbol("solana")

# Pick the YFinance result for historical data
symbol = next(r['symbol'] for r in results if r['provider'] == 'yfinance')

# Fetch data
df = stream.get(symbol)
print(df.head())
```

## Provider-Specific Symbol Formats

Different providers use different formats:

| Asset | YFinance | CoinGecko | Kraken | Coinbase |
|-------|----------|-----------|--------|----------|
| Bitcoin | `BTC-USD` | `bitcoin` | `XXBTZUSD` | `BTC-USD` |
| Ethereum | `ETH-USD` | `ethereum` | `XETHZUSD` | `ETH-USD` |
| Solana | `SOL-USD` | `solana` | `SOLUSD` | `SOL-USD` |
| Apple | `AAPL` | N/A | N/A | N/A |

## Performance Tips

1. **Limit results** - Default is 10, increase only if needed
   ```python
   results = stream.search_symbol("bitcoin", limit=5)  # Faster
   ```

2. **Search is sequential** - Results come from YFinance first, then CoinGecko, then others

3. **Duplicates are removed** - Each symbol appears only once

## Comprehensive Crypto Coverage

With CoinGecko integration, you can search for:

- **Major coins**: Bitcoin, Ethereum, Solana, Cardano
- **DeFi tokens**: Uniswap, Aave, Compound, Maker
- **Stablecoins**: USDT, USDC, DAI, FRAX
- **Wrapped assets**: WBTC, WETH, stETH
- **Layer 2s**: Polygon, Arbitrum, Optimism
- **Altcoins**: 10,000+ coins and tokens

## API Reference

```python
def search_symbol(
    query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for symbols across multiple providers.

    Args:
        query: Search query (e.g., "bitcoin", "apple", "ETH")
        limit: Maximum number of results (default: 10)

    Returns:
        List of dicts with symbol, name, type, provider, exchange
    """
```

## Common Searches

```python
# Find Ethereum
stream.search_symbol("ethereum")
stream.search_symbol("ETH")

# Find Solana
stream.search_symbol("solana")
stream.search_symbol("SOL")

# Find Cardano
stream.search_symbol("cardano")
stream.search_symbol("ADA")

# Find wrapped Bitcoin
stream.search_symbol("wrapped bitcoin")
stream.search_symbol("WBTC")

# Find DeFi tokens
stream.search_symbol("uniswap")
stream.search_symbol("aave")
```

## Why Multiple Providers?

Different providers have different:
- **Symbol formats** - `BTC-USD` vs `bitcoin`
- **Coverage** - Stocks vs crypto
- **Data quality** - Real-time vs delayed
- **Geographic availability** - US vs global

By searching across all providers, you can:
1. Find the correct format for your needs
2. Discover alternative symbols/exchanges
3. Compare what's available across providers
4. Pick the best provider for your use case

## See Also

- [SYMBOL_FORMATS.md](SYMBOL_FORMATS.md) - Symbol format reference
- [POLARS_VS_PANDAS.md](POLARS_VS_PANDAS.md) - Data format guide
- [README.md](README.md) - Main documentation
