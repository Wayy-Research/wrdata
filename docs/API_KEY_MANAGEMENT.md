# API Key Management in wrdata

## Overview

wrdata uses a **three-tier configuration system** for API keys and settings:

1. **Environment Variables** (via `.env` file or system environment)
2. **Constructor Parameters** (direct pass to DataStream)
3. **Global Settings Object** (fallback/default)

## Configuration Architecture

```
┌─────────────────────────────────────────────┐
│  User provides API key via:                 │
│  1. Constructor param: DataStream(key=...)  │
│  2. Environment variable: WHALE_ALERT_...   │
│  3. .env file: WHALE_ALERT_API_KEY=...      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  wrdata/core/config.py                      │
│  - Pydantic Settings class                  │
│  - Auto-loads from .env or environment      │
│  - Validates and provides defaults          │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  wrdata/stream.py (DataStream class)        │
│  - Accepts keys via constructor             │
│  - Falls back to settings if not provided   │
│  - Pattern: key_param or settings.KEY_NAME  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Individual Providers                        │
│  - Receive API key from DataStream          │
│  - Or instantiated directly with key        │
└─────────────────────────────────────────────┘
```

## How to Configure API Keys

### Method 1: Environment Variables (Recommended)

**Step 1: Copy example file**
```bash
cd /path/to/wrdata
cp .env.example .env
```

**Step 2: Edit .env file**
```bash
# .env
WHALE_ALERT_API_KEY=your_whale_alert_api_key_here
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
POLYGON_API_KEY=your_polygon_key
```

**Step 3: Use wrdata (keys auto-loaded)**
```python
from wrdata import DataStream

stream = DataStream()  # Keys loaded automatically from .env
df = stream.get("AAPL")
```

### Method 2: Constructor Parameters

```python
from wrdata import DataStream

stream = DataStream(
    polygon_key="your_polygon_key",
    alphavantage_key="your_alpha_vantage_key",
    finnhub_key="your_finnhub_key"
)
```

### Method 3: Direct Provider Instantiation

```python
from wrdata.providers.whale_alert_provider import WhaleAlertProvider

provider = WhaleAlertProvider(api_key="your_whale_alert_key")
batch = provider.fetch_whale_transactions(...)
```

### Method 4: System Environment Variables

```bash
export WHALE_ALERT_API_KEY=your_key_here
export ALPHA_VANTAGE_API_KEY=your_key_here
python your_script.py
```

## Configuration Files

### 1. `wrdata/core/config.py`

Central settings class using Pydantic Settings:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Keys
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    POLYGON_API_KEY: Optional[str] = None
    WHALE_ALERT_API_KEY: Optional[str] = None
    # ... more keys ...

    @property
    def has_whale_alert_key(self) -> bool:
        return self.WHALE_ALERT_API_KEY is not None

# Global instance
settings = Settings()
```

**Features:**
- Auto-loads from `.env` file in project root
- Validates types using Pydantic
- Case-insensitive environment variable names
- Ignores extra variables
- Provides helper properties

### 2. `.env.example`

Template file showing all available configuration options:

```bash
# Copy to .env and fill in your values
cp .env.example .env
```

Contains:
- Free tier API keys (Alpha Vantage, FRED, etc.)
- Premium API keys (Polygon, IEX Cloud, etc.)
- Broker API keys (Alpaca, IBKR, TD Ameritrade)
- Crypto exchange keys (Binance, Coinbase, Kraken)
- Whale tracking keys (Whale Alert)
- Database configuration
- Rate limiting settings
- Security settings

### 3. `wrdata/stream.py`

Main DataStream class with fallback pattern:

```python
class DataStream:
    def __init__(
        self,
        polygon_key: Optional[str] = None,
        alphavantage_key: Optional[str] = None,
        whale_alert_key: Optional[str] = None,
        # ... more params ...
    ):
        # Fallback pattern: constructor param OR environment
        polygon_key = polygon_key or settings.POLYGON_API_KEY
        alphavantage_key = alphavantage_key or settings.ALPHA_VANTAGE_API_KEY
        whale_alert_key = whale_alert_key or settings.WHALE_ALERT_API_KEY

        # Initialize providers with keys
        self._add_polygon_provider(polygon_key)
        self._add_alphavantage_provider(alphavantage_key)
        self._add_whale_alert_provider(whale_alert_key)
```

## API Key Priority

When multiple sources provide an API key, wrdata uses this priority:

1. **Constructor parameter** (highest priority)
2. **Environment variable** (via `.env` or system env)
3. **None** (provider not initialized)

Example:
```python
# .env file has: POLYGON_API_KEY=env_key

stream = DataStream(polygon_key="constructor_key")
# Uses "constructor_key" (constructor wins)

stream = DataStream()
# Uses "env_key" (from .env file)
```

## Provider Categories

### Free Tier (No API Key Required)
- **YFinance**: Yahoo Finance (always enabled)
- **Coinbase**: Public market data
- **Kraken**: Public crypto data
- **CoinGecko**: Public crypto data
- **Binance**: Public market data (higher limits with key)

### Free Tier (API Key Required)
- **Alpha Vantage**: 5 calls/min, 500/day
- **Twelve Data**: 8 calls/min, 800/day
- **FRED**: Unlimited (economic data)
- **Finnhub**: 60 calls/min + WebSocket

### Premium Tier (Paid)
- **Polygon**: $99-249/mo (market data)
- **IEX Cloud**: $99+/mo (market data)
- **Whale Alert**: ~$30/mo (whale transactions)
- **Alpaca**: Free paper trading, paid live
- **IBKR**: Interactive Brokers (requires TWS)

## Security Best Practices

### ✅ DO:
- Use `.env` file for local development
- Add `.env` to `.gitignore` (prevents accidental commits)
- Use environment variables in production
- Rotate API keys regularly
- Use separate keys for dev/staging/production
- Use read-only API keys when possible

### ❌ DON'T:
- Commit API keys to version control
- Share `.env` files
- Use production keys in development
- Hard-code API keys in source code
- Use the same key across multiple projects

## Environment-Specific Configuration

### Development
```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
WHALE_ALERT_API_KEY=dev_key_here
```

### Production
```bash
# Set via system environment or secrets manager
export ENVIRONMENT=production
export DEBUG=false
export WHALE_ALERT_API_KEY=prod_key_here
```

### Docker
```yaml
# docker-compose.yml
services:
  app:
    environment:
      - WHALE_ALERT_API_KEY=${WHALE_ALERT_API_KEY}
      - POLYGON_API_KEY=${POLYGON_API_KEY}
    env_file:
      - .env
```

## Checking Configuration

### Verify API Keys are Loaded

```python
from wrdata.core.config import settings

# Check if key is configured
if settings.has_whale_alert_key:
    print("✅ Whale Alert API key configured")
else:
    print("❌ Whale Alert API key not found")

# Print all configured keys (masked)
print(f"Alpha Vantage: {'✅' if settings.ALPHA_VANTAGE_API_KEY else '❌'}")
print(f"Polygon: {'✅' if settings.POLYGON_API_KEY else '❌'}")
print(f"Whale Alert: {'✅' if settings.WHALE_ALERT_API_KEY else '❌'}")
```

### Validate Provider Connections

```python
from wrdata.providers.whale_alert_provider import WhaleAlertProvider

provider = WhaleAlertProvider(api_key=settings.WHALE_ALERT_API_KEY)

if provider.validate_connection():
    print("✅ Successfully connected to Whale Alert API")
    status = provider.get_status()
    print(f"Usage: {status.get('usage', {})}")
    print(f"Limits: {status.get('limits', {})}")
else:
    print("❌ Failed to connect - check your API key")
```

## Troubleshooting

### Issue: API key not being recognized

**Check these in order:**

1. **Is .env file in the correct location?**
   ```bash
   ls -la .env  # Should be in project root
   ```

2. **Is the variable name correct?**
   ```bash
   grep WHALE_ALERT .env
   # Should see: WHALE_ALERT_API_KEY=your_key
   ```

3. **Are there any spaces around the equals sign?**
   ```bash
   # ❌ Wrong: WHALE_ALERT_API_KEY = your_key
   # ✅ Correct: WHALE_ALERT_API_KEY=your_key
   ```

4. **Is the .env file being loaded?**
   ```python
   from wrdata.core.config import settings
   print(settings.WHALE_ALERT_API_KEY)  # Should print your key (not None)
   ```

5. **Try setting via environment variable:**
   ```bash
   export WHALE_ALERT_API_KEY=your_key
   python your_script.py
   ```

### Issue: Wrong API key being used

Check the priority order:
1. Constructor parameter (highest)
2. Environment variable
3. .env file

```python
# Debug which key is being used
from wrdata.core.config import settings

print("From settings:", settings.WHALE_ALERT_API_KEY)

stream = DataStream(whale_alert_key="override_key")
# Will use "override_key" instead of settings value
```

## Advanced: Custom Configuration

### Using a Custom .env File

```python
from wrdata.core.config import Settings

# Load from custom location
custom_settings = Settings(_env_file="/path/to/custom.env")
```

### Runtime Configuration Updates

```python
from wrdata.core.config import settings

# Update at runtime (not recommended for production)
settings.WHALE_ALERT_API_KEY = "new_key"
```

### Per-Provider Configuration

```python
# Different keys for different providers
stream = DataStream()

# Later, add Whale Alert with specific key
from wrdata.providers.whale_alert_provider import WhaleAlertProvider
whale_provider = WhaleAlertProvider(api_key="specific_whale_key")
```

## Summary

wrdata's API key management is designed to be:
- **Flexible**: Multiple ways to provide keys
- **Secure**: Encourages environment variables over hardcoding
- **Simple**: Zero configuration for free providers
- **Scalable**: Easy to add keys as you need premium features

**Recommended workflow:**
1. Start with free providers (no keys needed)
2. Add API keys to `.env` as you need premium features
3. Never commit `.env` to version control
4. Use environment variables in production

## Quick Reference

| Provider | Required? | Cost | How to Get |
|----------|-----------|------|------------|
| YFinance | No | Free | N/A |
| Binance | No | Free | N/A (public data) |
| Coinbase | No | Free | N/A (public data) |
| Alpha Vantage | Yes | Free | https://www.alphavantage.co/support/#api-key |
| FRED | Yes | Free | https://fred.stlouisfed.org/docs/api/api_key.html |
| Finnhub | Yes | Free | https://finnhub.io/register |
| Whale Alert | Yes | ~$30/mo | https://whale-alert.io/ |
| Polygon | Yes | $99+/mo | https://polygon.io/ |
| Alpaca | Yes | Free paper | https://app.alpaca.markets/ |
