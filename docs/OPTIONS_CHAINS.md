# Options Chain Data - User Guide

This guide explains how to collect, store, and analyze historical timeseries of options chain data using the wrdata package.

## Overview

The options chain functionality allows you to:

- **Fetch current options chains** from providers like YFinance
- **Store options data** including prices, greeks, implied volatility, and open interest
- **Build historical timeseries** by collecting snapshots over time
- **Query historical data** to analyze trends and patterns

## Database Schema

The options data is stored in three main tables:

### 1. `options_contracts`
Stores metadata about each unique options contract:
- Contract symbol (e.g., "AAPL250117C00150000")
- Underlying symbol
- Option type (call/put)
- Strike price
- Expiration date

### 2. `options_chain_snapshots`
Stores point-in-time snapshots of options data:
- Price data (bid, ask, last, mark)
- Volume and open interest
- Greeks (delta, gamma, theta, vega, rho)
- Implied volatility
- Intrinsic/extrinsic value
- Underlying price at snapshot time

### 3. `symbols`
Links options contracts to their underlying securities.

## Quick Start

### 1. Initialize the Database

```python
from wrdata.utils.db_utils import init_database

# Initialize all tables
init_database()
```

Or use the command line:

```bash
python -m wrdata.utils.db_utils init
```

### 2. Fetch Current Options Chain

```python
from wrdata.utils.db_utils import get_session
from wrdata.services.options_fetcher import OptionsFetcher
from wrdata.models.schemas import OptionsChainRequest

# Create session and fetcher
session = get_session()
fetcher = OptionsFetcher(session)

# Fetch options chain for AAPL
request = OptionsChainRequest(
    symbol="AAPL",
    expiration_date=None,  # Will use nearest expiration
    option_type=None,      # Both calls and puts
)

response = fetcher.fetch_and_store_options_chain(request)

if response.success:
    print(f"Fetched {len(response.calls)} calls and {len(response.puts)} puts")
    print(f"Underlying price: ${response.underlying_price}")
```

### 3. Filter Options Chain

You can filter by option type and strike range:

```python
from decimal import Decimal

request = OptionsChainRequest(
    symbol="AAPL",
    option_type="call",              # Only calls
    min_strike=Decimal("150.00"),    # Minimum strike
    max_strike=Decimal("200.00"),    # Maximum strike
)

response = fetcher.fetch_and_store_options_chain(request)
```

### 4. Retrieve Historical Timeseries

After collecting snapshots over time, query historical data:

```python
from datetime import datetime, timedelta
from wrdata.models.schemas import OptionsTimeseriesRequest

# Get data from last 30 days
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=30)

request = OptionsTimeseriesRequest(
    underlying_symbol="AAPL",
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat(),
)

response = fetcher.get_options_timeseries(request)

for snapshot in response.data:
    print(f"{snapshot['timestamp']}: {snapshot['contract_symbol']}")
    print(f"  Last: ${snapshot['last_price']}")
    print(f"  IV: {snapshot['implied_volatility']:.2%}")
    print(f"  Delta: {snapshot['delta']}")
```

## Building Historical Timeseries

To build a historical database of options data:

### Method 1: Manual Collection

Run your data collection script regularly (e.g., daily):

```python
# daily_options_snapshot.py
from wrdata.utils.db_utils import get_session
from wrdata.services.options_fetcher import OptionsFetcher
from wrdata.models.schemas import OptionsChainRequest

symbols = ["AAPL", "MSFT", "TSLA", "SPY"]

session = get_session()
fetcher = OptionsFetcher(session)

for symbol in symbols:
    request = OptionsChainRequest(symbol=symbol)
    response = fetcher.fetch_and_store_options_chain(request)
    print(f"Fetched {symbol}: {response.success}")

session.close()
```

Schedule with cron:
```bash
# Run daily at 4:30 PM (after market close)
30 16 * * 1-5 python /path/to/daily_options_snapshot.py
```

### Method 2: Automated Service

Create a service that runs continuously:

```python
import schedule
import time

def collect_options_data():
    # Your data collection logic here
    pass

# Run every day at 4:30 PM
schedule.every().day.at("16:30").do(collect_options_data)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Data Providers

### YFinance (Default)

- **Pros**: Free, no API key required, includes greeks
- **Cons**: No historical options data (only current chain)
- **Rate limits**: ~2000 requests/hour

```python
from wrdata.providers.yfinance_provider import YFinanceProvider

provider = YFinanceProvider()
expirations = provider.get_available_expirations("AAPL")
```

### Adding Custom Providers

You can add other providers that support historical options data:

```python
from wrdata.providers.base import BaseProvider

class MyOptionsProvider(BaseProvider):
    def fetch_options_chain(self, request):
        # Your implementation
        pass

    def supports_historical_options(self):
        return True  # If your provider has historical data

# Register with fetcher
fetcher.add_provider("myprovider", MyOptionsProvider())
```

## Example Use Cases

### 1. Implied Volatility Surface

Collect options across multiple strikes and expirations to build a volatility surface:

```python
# Fetch all available expirations
expirations = fetcher.get_available_expirations("AAPL")

for exp_date in expirations[:6]:  # Next 6 expirations
    request = OptionsChainRequest(
        symbol="AAPL",
        expiration_date=exp_date
    )
    fetcher.fetch_and_store_options_chain(request)
```

### 2. Track Specific Contract Over Time

Monitor how a specific options contract changes as it approaches expiration:

```python
request = OptionsTimeseriesRequest(
    contract_symbol="AAPL250117C00150000",  # Specific contract
    start_date="2025-01-01",
    end_date="2025-01-17",
)

response = fetcher.get_options_timeseries(request)

# Analyze theta decay, delta changes, etc.
for snapshot in response.data:
    print(f"Days to expiry: {snapshot['days_to_expiry']}")
    print(f"Theta: {snapshot['theta']}")
```

### 3. Open Interest Analysis

Track open interest changes to identify where traders are positioning:

```python
# Query for all put contracts at a specific strike
request = OptionsTimeseriesRequest(
    underlying_symbol="SPY",
    strike_price=Decimal("450.00"),
    option_type="put",
    start_date=(datetime.now() - timedelta(days=30)).isoformat(),
    end_date=datetime.now().isoformat(),
)

response = fetcher.get_options_timeseries(request)

# Plot open interest over time
for snapshot in response.data:
    print(f"{snapshot['timestamp']}: OI = {snapshot['open_interest']}")
```

## Best Practices

1. **Collect Regularly**: Run data collection at consistent times (e.g., after market close)

2. **Filter Smartly**: Don't store every strike - focus on liquid strikes near the money

3. **Monitor Storage**: Options data can grow large - implement data retention policies

4. **Handle Errors**: Provider APIs can fail - implement retry logic and error handling

5. **Respect Rate Limits**: Space out requests to avoid hitting provider rate limits

6. **Validate Data**: Check for missing or invalid data before analysis

## Database Maintenance

### Check Database Schema

```bash
python -m wrdata.utils.db_utils verify
```

### Run Migration (for existing databases)

If you already have a wrdata database without options tables:

```bash
python -m wrdata.utils.db_utils migrate
```

### Reset Database

To start fresh (⚠️ destroys existing data):

```bash
python -m wrdata.utils.db_utils init --drop
```

## Troubleshooting

### "No options available for this symbol"

- Not all stocks have options - verify on a financial website
- Some providers may not support options for certain symbols

### "Provider rate limit exceeded"

- Add delays between requests: `time.sleep(0.5)`
- Implement exponential backoff for retries

### "Missing greeks in data"

- Not all providers calculate greeks
- YFinance includes greeks, but they may be None for illiquid contracts

## Performance Tips

1. **Use Indexes**: The schema includes indexes on common query patterns
2. **Batch Queries**: Fetch multiple expirations in one session
3. **Filter Early**: Use SQL WHERE clauses rather than filtering in Python
4. **Archive Old Data**: Move expired contracts to archive tables

## Future Enhancements

Potential additions to the options functionality:

- [ ] Support for additional providers (Polygon, TDAmeritrade, etc.)
- [ ] Built-in volatility surface calculations
- [ ] Greeks calculations for providers that don't provide them
- [ ] Automated data quality checks
- [ ] Export to common formats (CSV, Parquet)
- [ ] Real-time options streaming (for intraday data)

## Contributing

To add support for a new options data provider:

1. Inherit from `BaseProvider`
2. Implement `fetch_options_chain()`
3. Set `supports_historical_options()` if applicable
4. Add tests for your provider
5. Submit a pull request

## License

This options chain functionality is part of the wrdata package and follows the same license.
