# Whale Transaction Tracking - Complete Implementation Guide

## Overview

The wrdata package now includes comprehensive whale transaction tracking capabilities with three levels of integration:

1. **Real-time Exchange Monitoring** (Binance, Coinbase) - Free, no API key required
2. **Blockchain Transaction Tracking** (Whale Alert) - Requires API key ($30/mo+)
3. **Historical Price Impact Analysis** - Correlate whale activity with price movements

## Architecture

### Core Components

```
wrdata/
├── models/schemas.py
│   ├── WhaleTransaction      # Standardized whale transaction model
│   ├── WhaleAlert             # Alert configuration
│   └── WhaleTransactionBatch  # Batch processing with metadata
│
├── utils/whale_detection.py
│   ├── VolumeTracker          # Rolling window percentile calculator
│   └── WhaleDetector          # Multi-exchange coordinator
│
├── streaming/
│   ├── binance_stream.py      # Binance aggregate trades + whale detection
│   ├── coinbase_stream.py     # Coinbase matches + whale detection
│   └── whale_alert_stream.py  # Whale Alert WebSocket (real-time)
│
└── providers/
    └── whale_alert_provider.py # Whale Alert REST API (historical)
```

## Features

### 1. Percentile-Based Detection

Adapts to market conditions using rolling window analysis:

- **Rolling Window**: Last 1000 trades or 1 hour (configurable)
- **Real-time Percentiles**: p50, p75, p90, p95, p99, p99.9
- **Volume Statistics**: Mean, median, std, min, max
- **Transaction Ranking**: See where each whale ranks

```python
from wrdata.streaming.binance_stream import BinanceStreamProvider

provider = BinanceStreamProvider()
await provider.connect()

async for msg in provider.subscribe_aggregate_trades(
    symbol="BTCUSDT",
    enable_whale_detection=True,
    percentile_threshold=99.0  # Top 1%
):
    if 'whale_metadata' in msg.raw_data:
        print(f"Whale detected: {msg.raw_data['whale_metadata']}")
```

### 2. Blockchain Transaction Tracking

Track actual on-chain transfers with Whale Alert:

**REST API - Historical Data:**

```python
from wrdata.providers.whale_alert_provider import WhaleAlertProvider

provider = WhaleAlertProvider(api_key="your_key")

# Fetch whale transactions
batch = provider.fetch_whale_transactions(
    start_date="2025-11-20",
    end_date="2025-11-23",
    blockchain="bitcoin",
    min_value=1000000,  # $1M minimum
    limit=100
)

print(f"Found {batch.count} whale transactions")

for whale_tx in batch.transactions:
    print(f"{whale_tx.symbol}: {whale_tx.size} = ${whale_tx.usd_value:,.0f}")
    print(f"  Type: {whale_tx.transaction_type}")
    print(f"  From: {whale_tx.from_address}")
    print(f"  To: {whale_tx.to_address}")
    print(f"  Exchange: {whale_tx.exchange}")
```

**WebSocket - Real-time Alerts:**

```python
from wrdata.streaming.whale_alert_stream import WhaleAlertStreamProvider

provider = WhaleAlertStreamProvider(api_key="your_key")
await provider.connect()

async for whale_tx in provider.subscribe_whale_alerts(
    min_value=2000000,  # $2M minimum
    blockchain="ethereum"
):
    print(f"🐋 WHALE ALERT!")
    print(f"   ${whale_tx.usd_value:,.0f} {whale_tx.symbol}")
    print(f"   Type: {whale_tx.transaction_type}")
```

### 3. Historical Price Impact Analysis

Analyze correlation between whale transactions and price movements:

```python
from tests.integration.test_whale_price_impact import WhalePriceImpactAnalyzer
from wrdata.providers.whale_alert_provider import WhaleAlertProvider
from wrdata.providers.binance_provider import BinanceProvider

# Initialize
whale_provider = WhaleAlertProvider(api_key="your_key")
price_provider = BinanceProvider()
analyzer = WhalePriceImpactAnalyzer(whale_provider, price_provider)

# Fetch whale transactions
whales = analyzer.fetch_whale_transactions(
    start_date="2025-11-20",
    end_date="2025-11-20",
    blockchain="bitcoin",
    min_value=2000000
)

# Fetch corresponding price data (minute-level)
prices = analyzer.fetch_price_data(
    symbol="BTCUSDT",
    start_date="2025-11-20",
    interval="1m"
)

# Analyze price impact
analysis = analyzer.analyze_price_impact(
    whale_txs=whales,
    price_df=prices,
    window_before=5,   # 5 minutes before
    window_after=15    # 15 minutes after
)

# Print report
analyzer.print_analysis_report(analysis)
```

**Output Example:**

```
================================================================================
🐋 WHALE TRANSACTION PRICE IMPACT ANALYSIS REPORT
================================================================================

📊 Overall Statistics:
   Total Whale Transactions Analyzed: 47
   Average Whale Size: $3,450,000
   Median Whale Size: $2,100,000
   Total Whale Volume: $162,150,000

📈 Price Impact:
   Average Price Change (5m):  +0.087%
   Average Price Change (10m): +0.142%
   Average Price Change (15m): +0.089%
   Median Price Change (5m):   +0.034%

📊 Directional Impact (5 minutes):
   Positive Impact: 28 transactions
   Negative Impact: 19 transactions

💹 Market Response:
   Average Volume Surge: +45.3%
   Average Volatility Increase: 0.125%

🔍 By Transaction Type:
   WITHDRAWAL:
      Count: 23
      Avg Value: $3,200,000
      Avg 5m Impact: +0.154%
   DEPOSIT:
      Count: 18
      Avg Value: $3,800,000
      Avg 5m Impact: -0.089%
   TRANSFER:
      Count: 6
      Avg Value: $3,100,000
      Avg 5m Impact: +0.045%

================================================================================
```

## Data Sources Comparison

| Source | Type | Cost | Real-time | Historical | Blockchain | Exchange |
|--------|------|------|-----------|------------|------------|----------|
| **Binance** | Exchange trades | Free | ✅ WebSocket | ❌ | ❌ | ✅ |
| **Coinbase** | Exchange trades | Free | ✅ WebSocket | ❌ | ❌ | ✅ |
| **Whale Alert** | Blockchain txs | Paid | ✅ WebSocket | ✅ REST API | ✅ | Partial |

### When to Use Each

**Binance/Coinbase (Free):**
- Real-time exchange trading activity
- Percentile-based whale detection
- Multi-symbol monitoring
- No API key required
- Best for: Tracking whale trades on exchanges

**Whale Alert (Paid ~$30/mo):**
- Actual blockchain transactions
- Wallet attribution (exchanges, DeFi, etc.)
- Historical data for backtesting
- Cross-chain support
- Transaction classification
- Best for: On-chain whale tracking, research, compliance

## Examples

### Example 1: Multi-Symbol Real-time Monitoring

```python
import asyncio
from wrdata.streaming.binance_stream import BinanceStreamProvider

async def monitor_whales():
    provider = BinanceStreamProvider()
    await provider.connect()

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    def whale_alert(whale_tx):
        print(f"🐋 {whale_tx.symbol}: ${whale_tx.usd_value:,.0f}")
        print(f"   Percentile: {whale_tx.percentile:.1f}%")
        print(f"   Side: {whale_tx.side}")

    # Monitor all symbols concurrently
    tasks = []
    for symbol in symbols:
        async def track(sym):
            async for msg in provider.subscribe_aggregate_trades(
                symbol=sym,
                enable_whale_detection=True,
                percentile_threshold=95.0,  # Top 5%
                whale_callback=whale_alert
            ):
                pass  # Callback handles output

        tasks.append(asyncio.create_task(track(symbol)))

    await asyncio.gather(*tasks)

asyncio.run(monitor_whales())
```

### Example 2: Whale Alert Historical Analysis

```python
from wrdata.providers.whale_alert_provider import WhaleAlertProvider
from datetime import datetime, timedelta

provider = WhaleAlertProvider(api_key="your_key")

# Last 7 days
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

batch = provider.fetch_whale_transactions(
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    blockchain="ethereum",
    min_value=5000000,  # $5M minimum
    limit=100
)

# Analyze by exchange
exchange_stats = {}
for tx in batch.transactions:
    if tx.exchange:
        if tx.exchange not in exchange_stats:
            exchange_stats[tx.exchange] = {'count': 0, 'volume': 0}
        exchange_stats[tx.exchange]['count'] += 1
        exchange_stats[tx.exchange]['volume'] += float(tx.usd_value)

# Print top exchanges by whale activity
sorted_exchanges = sorted(
    exchange_stats.items(),
    key=lambda x: x[1]['volume'],
    reverse=True
)

print("Top Exchanges by Whale Volume (7 days):")
for exchange, stats in sorted_exchanges[:10]:
    print(f"{exchange:15} {stats['count']:3} whales  ${stats['volume']:,.0f}")
```

### Example 3: Price Impact by Transaction Type

```python
from tests.integration.test_whale_price_impact import WhalePriceImpactAnalyzer

# ... initialize analyzer ...

analysis = analyzer.analyze_price_impact(whales, prices)
df = analysis['dataframe']

# Group by transaction type
for tx_type in df['transaction_type'].unique():
    subset = df[df['transaction_type'] == tx_type]

    print(f"\n{tx_type.upper()} Transactions:")
    print(f"  Count: {len(subset)}")
    print(f"  Avg Size: ${subset['whale_usd_value'].mean():,.0f}")
    print(f"  Avg 5m Impact: {subset['change_5m_pct'].mean():+.3f}%")
    print(f"  Avg 15m Impact: {subset['change_15m_pct'].mean():+.3f}%")
```

## Testing

### Run Integration Tests

```bash
# Set API key
export WHALE_ALERT_API_KEY=your_api_key_here

# Run all whale tracking tests
python3 -m pytest tests/integration/test_whale_price_impact.py -v -s

# Run specific test
python3 -m pytest tests/integration/test_whale_price_impact.py::test_whale_alert_historical_fetch -v -s
```

### Run Examples

```bash
# Real-time whale monitoring (no API key needed)
python3 examples/whale_tracking.py

# Whale Alert demo (requires API key)
export WHALE_ALERT_API_KEY=your_key
python3 examples/whale_alert_demo.py
```

## API Reference

### WhaleTransaction Model

```python
class WhaleTransaction(BaseModel):
    # Identification
    symbol: str                          # e.g., "BTC", "ETH"
    timestamp: datetime
    exchange: Optional[str]              # "binance", "coinbase", etc.
    transaction_id: Optional[str]

    # Transaction details
    size: Decimal                        # Volume/quantity
    price: Decimal                       # Price at transaction
    usd_value: Optional[Decimal]         # USD equivalent

    # Whale classification
    percentile: Optional[float]          # 0-100
    volume_rank: Optional[int]           # Rank among recent

    # Context
    transaction_type: str                # "trade", "transfer", "deposit", "withdrawal"
    side: Optional[str]                  # "buy", "sell", "unknown"
    is_maker: Optional[bool]

    # Blockchain-specific
    from_address: Optional[str]
    to_address: Optional[str]
    blockchain: Optional[str]            # "bitcoin", "ethereum", etc.
    tx_hash: Optional[str]

    # Provider metadata
    provider: str
    raw_data: Optional[Dict[str, Any]]
```

### VolumeTracker

```python
class VolumeTracker:
    def __init__(
        self,
        window_size: int = 1000,
        time_window_seconds: Optional[int] = None,
        percentile_threshold: float = 99.0
    )

    def add_transaction(symbol: str, volume: float, timestamp: datetime)
    def is_whale_transaction(symbol: str, volume: float) -> Tuple[bool, float, int]
    def get_statistics(symbol: str) -> Dict
    def get_threshold_volume(symbol: str, percentile: float) -> float
```

### WhaleDetector

```python
class WhaleDetector:
    def __init__(
        self,
        default_percentile: float = 99.0,
        window_size: int = 1000,
        time_window_seconds: Optional[int] = 3600,
        min_usd_value: Optional[float] = None
    )

    def process_transaction(
        symbol: str,
        volume: float,
        price: float,
        exchange: Optional[str] = None
    ) -> Tuple[bool, Dict]

    def get_all_statistics() -> Dict[str, Dict]
```

## Pricing

### Free Tier
- **Binance**: Unlimited, no API key required
- **Coinbase**: Unlimited, no API key required
- **Real-time percentile detection**: Built-in, no cost

### Paid Services
- **Whale Alert API**: Starting at ~$30/month
  - Historical data access
  - Real-time WebSocket alerts
  - Attribution data
  - Cross-chain support

## Performance Considerations

1. **Rolling Window Size**: Default 1000 trades balances accuracy vs memory
2. **Time Window**: 1 hour default prevents stale data
3. **Statistics Caching**: Reduces computation overhead
4. **Thread Safety**: All volume tracking is thread-safe
5. **Non-blocking**: Async architecture for high-frequency streams

## Troubleshooting

### Issue: No whale transactions detected

**Solution**: Lower the percentile threshold (e.g., from 99.0 to 95.0)

### Issue: Too many false positives

**Solution**: Combine percentile with USD threshold:
```python
enable_whale_detection=True,
percentile_threshold=99.0,
min_usd_value=100000  # Minimum $100k
```

### Issue: Whale Alert API errors

**Check**:
1. API key is valid: `provider.validate_connection()`
2. Rate limits: Check `provider.get_status()`
3. Date range within last 30 days (Whale Alert limitation)

## Future Enhancements

Potential additions:

1. **Additional Data Sources**
   - Glassnode on-chain metrics
   - CryptoQuant indicators
   - Etherscan + Infura integration

2. **Advanced Analytics**
   - Machine learning for whale prediction
   - Order book imbalance correlation
   - Sentiment analysis integration

3. **Alert System**
   - Email/SMS notifications
   - Telegram/Discord bots
   - Custom webhook integration

4. **Database Integration**
   - PostgreSQL storage for whale history
   - Time-series optimization
   - Query API for historical analysis

## License

MIT License - See LICENSE file

## Support

- Documentation: See README.md
- Examples: See examples/ directory
- Tests: See tests/integration/
- Issues: GitHub Issues

---

**Happy Whale Watching! 🐋**
