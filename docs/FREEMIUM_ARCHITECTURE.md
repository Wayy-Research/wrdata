# WRData Freemium Architecture
## Three-Tier Business Model Design

**Last Updated:** 2025-11-05

---

## Overview

WRData implements a **freemium** subscription model with three tiers:
- **Free Tier** - Public/redistributable data sources only
- **Pro Tier** - Licensed premium data providers
- **Enterprise Tier** - User-owned API keys + custom features

---

## Tier Comparison

| Feature | Free | Pro ($99/mo) | Enterprise ($299/mo) |
|---------|------|--------------|----------------------|
| **DATA SOURCES** |
| Economic Data (FRED, World Bank, ECB) | ✅ | ✅ | ✅ |
| Crypto (Binance, Coinbase, Kraken) | ✅ | ✅ | ✅ |
| US Stocks (daily) | ❌ | ✅ | ✅ |
| Options Chains | ❌ | ✅ | ✅ |
| Forex | Limited (EUR) | ✅ All pairs | ✅ All pairs |
| Futures | ❌ | ❌ | ✅ (user API) |
| **DATA FREQUENCY** |
| Daily/Hourly | ✅ | ✅ | ✅ |
| Minute | ❌ | ✅ | ✅ |
| Second | ❌ | ✅ Limited | ✅ |
| Tick (sub-second) | ❌ | ❌ | ✅ |
| **FEATURES** |
| API Access | ✅ | ✅ | ✅ |
| WebSocket Streaming | ❌ | ✅ | ✅ |
| Order Book Snapshots | ❌ | ❌ | ✅ |
| Historical Data | 1 year | 5 years | Unlimited |
| Rate Limit (req/min) | 100 | 1,000 | 10,000 |
| **INTEGRATIONS** |
| Bring Your Own API Keys | ❌ | ❌ | ✅ |
| IBKR, TD Ameritrade, Alpaca | ❌ | ❌ | ✅ |
| Custom Providers | ❌ | ❌ | ✅ |
| Dedicated Support | ❌ | Email | Priority |
| **STORAGE** |
| Data Retention | 1 month | 1 year | Unlimited |
| Export to Parquet/CSV | ✅ | ✅ | ✅ |
| Direct Database Access | ❌ | ❌ | ✅ |

---

## Data Sources by Tier

### Free Tier (100% Legal, Redistributable)

#### **Economic Data**
- ✅ **FRED** (St. Louis Fed) - 800k+ economic series
  - GDP, inflation, unemployment, interest rates
  - License: Public domain
  - Update frequency: Daily (after release)

- ✅ **World Bank Open Data** - Global economic indicators
  - GDP by country, poverty rates, trade data
  - License: CC BY 4.0 (attribution required)
  - Update frequency: Quarterly/Annual

- ✅ **ECB Statistical Data** - European economic data
  - EUR exchange rates (vs USD, GBP, JPY, etc.)
  - EU economic indicators
  - License: Free with attribution
  - Update frequency: Daily

- ✅ **US Treasury** - Bond yields, auction data
  - Treasury rates (1mo to 30yr)
  - Auction schedules and results
  - License: Public domain
  - Update frequency: Daily

#### **Cryptocurrency**
- ✅ **Binance Public API**
  - Spot, futures, options (multi-asset)
  - OHLCV klines: 1m, 5m, 15m, 1h, 4h, 1d, 1w
  - Trade history
  - Order book snapshots (limit 1000)
  - License: Redistributable per ToS
  - Rate limit: 1200 req/min (no API key)

- ✅ **Coinbase Public API**
  - Spot trading pairs
  - OHLCV candles: 1m, 5m, 15m, 1h, 6h, 1d
  - Trade history
  - License: Redistributable
  - Rate limit: 10 req/sec (no API key)

- ✅ **Kraken Public API**
  - Spot and futures
  - OHLCV: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
  - Trade history
  - License: Redistributable
  - Rate limit: 15 req/sec (no API key)

### **What Free Tier Gets:**
- ✅ Excellent economic data coverage (better than many paid services)
- ✅ Complete crypto market data (all major coins + altcoins)
- ✅ High-frequency crypto (1-minute candles)
- ✅ Historical data (limited to 1 year)
- ❌ No US stocks/equities
- ❌ No options chains
- ❌ Limited forex (only EUR rates from ECB)

---

### Pro Tier ($99/mo) - Licensed Premium Data

**Cost to Provide:** ~$350-500/mo in data licensing fees

#### **Stocks & Options**
- ✅ **Polygon.io** ($249/mo Business plan for redistribution)
  - US stocks (NYSE, NASDAQ, AMEX)
  - Options chains (current + historical)
  - Forex (28+ currency pairs)
  - Crypto (via Polygon Crypto)
  - Frequency: Second-level bars available
  - Historical: Full history
  - WebSocket: Real-time quotes, trades, aggregates
  - License: Allows redistribution to subscribers

- ✅ **IEX Cloud** ($99/mo plan for redistribution)
  - US stocks (all exchanges)
  - Intraday data (1-minute bars)
  - Historical data (5+ years)
  - Company fundamentals
  - News and sentiment
  - License: Allows redistribution
  - Rate limit: Generous (varies by plan)

#### **Enhanced Crypto** (Optional: $129/mo)
- ⚠️ **CoinGecko Pro**
  - Enhanced historical data
  - More coins (14,000+)
  - Developer API (commercial use allowed)
  - License: Pro tier allows commercial use
  - Decision: May skip this since free crypto sources are good

### **What Pro Tier Gets:**
- ✅ Everything from Free Tier
- ✅ US stocks (real-time + historical)
- ✅ Options chains (current snapshots)
- ✅ Full forex coverage (28+ pairs)
- ✅ Minute and second-level data
- ✅ WebSocket streaming
- ✅ 5 years of historical data
- ✅ Higher rate limits (1000 req/min)

---

### Enterprise Tier ($299/mo) - User-Owned API Keys

**Cost to Provide:** ~$50-100/mo (infrastructure only, no data licensing)

#### **User Provides Their Own API Keys:**
- ✅ Interactive Brokers (IBKR)
- ✅ TD Ameritrade
- ✅ Alpaca Markets
- ✅ CBOE DataShop (if user has license)
- ✅ Any other provider we integrate

#### **Why This Works:**
- ✅ **No redistribution issues** (user fetches their own data)
- ✅ **Higher margins** (we provide infrastructure, not data)
- ✅ **Professional users** already have these accounts
- ✅ **We charge for:**
  - Infrastructure & storage
  - Query optimization
  - WebSocket management
  - Data cleaning & normalization
  - Historical database
  - Direct database access

### **What Enterprise Tier Gets:**
- ✅ Everything from Pro Tier
- ✅ Broker API integrations (IBKR, TDA, Alpaca)
- ✅ Tick-level data (sub-second)
- ✅ Order book depth (full L2/L3)
- ✅ Unlimited historical data retention
- ✅ Direct database access (PostgreSQL read replica)
- ✅ Custom provider integrations
- ✅ Priority support (SLA)
- ✅ Highest rate limits (10k req/min)

---

## Architecture: Tier Separation

### Database Schema (Multi-Tenancy)

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    tier VARCHAR(20) NOT NULL,  -- 'free', 'pro', 'enterprise'
    api_key VARCHAR(64) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    subscription_expires_at TIMESTAMPTZ
);

-- User API keys (for Enterprise tier)
CREATE TABLE user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,  -- 'ibkr', 'alpaca', 'tda'
    encrypted_api_key TEXT NOT NULL,
    encrypted_api_secret TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rate limiting
CREATE TABLE api_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    endpoint VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    response_time_ms INTEGER
);

-- Index for rate limiting queries
CREATE INDEX idx_api_usage_user_time
ON api_usage (user_id, timestamp DESC);
```

### API Endpoint Access Control

```python
# wrdata/core/auth.py
from enum import Enum
from functools import wraps
from flask import request, jsonify

class Tier(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

def require_tier(min_tier: Tier):
    """Decorator to restrict endpoints by tier."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()  # From JWT or API key

            tier_hierarchy = {
                Tier.FREE: 0,
                Tier.PRO: 1,
                Tier.ENTERPRISE: 2
            }

            user_tier_level = tier_hierarchy[Tier(user.tier)]
            required_tier_level = tier_hierarchy[min_tier]

            if user_tier_level < required_tier_level:
                return jsonify({
                    "error": "Upgrade required",
                    "message": f"This endpoint requires {min_tier.value} tier or higher",
                    "current_tier": user.tier,
                    "upgrade_url": "https://wrdata.com/pricing"
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Example usage:
@app.route("/api/v1/stocks/aapl")
@require_tier(Tier.PRO)  # Pro or Enterprise only
def get_stock_data():
    # Implementation
    pass

@app.route("/api/v1/orderbook/btcusd")
@require_tier(Tier.ENTERPRISE)  # Enterprise only
def get_order_book():
    # Implementation
    pass
```

### Provider Selection by Tier

```python
# wrdata/core/provider_router.py
from wrdata.core.auth import Tier

class ProviderRouter:
    """Routes data requests to appropriate providers based on user tier."""

    FREE_PROVIDERS = {
        'crypto': ['binance', 'coinbase', 'kraken'],
        'economic': ['fred', 'worldbank', 'ecb'],
        'forex': ['ecb'],  # EUR only
    }

    PRO_PROVIDERS = {
        **FREE_PROVIDERS,
        'stocks': ['polygon', 'iex'],
        'options': ['polygon'],
        'forex': ['polygon', 'ecb'],  # All pairs
    }

    def get_provider(self, user_tier: Tier, asset_class: str, symbol: str):
        """Select best provider for user's tier."""
        if user_tier == Tier.FREE:
            providers = self.FREE_PROVIDERS.get(asset_class, [])
        elif user_tier == Tier.PRO:
            providers = self.PRO_PROVIDERS.get(asset_class, [])
        else:  # Enterprise
            # Check if user has their own API keys
            user_providers = self.get_user_providers(user_id)
            if user_providers:
                return user_providers[0]  # Use user's provider
            else:
                providers = self.PRO_PROVIDERS.get(asset_class, [])

        # Return first available provider (or implement load balancing)
        return providers[0] if providers else None
```

---

## Rate Limiting Strategy

### Per-Tier Limits

```python
# wrdata/core/rate_limiter.py
from redis import Redis
from datetime import datetime, timedelta

class RateLimiter:
    """Token bucket rate limiter using Redis."""

    TIER_LIMITS = {
        Tier.FREE: 100,       # requests per minute
        Tier.PRO: 1000,
        Tier.ENTERPRISE: 10000
    }

    def __init__(self, redis: Redis):
        self.redis = redis

    def check_rate_limit(self, user_id: int, tier: Tier) -> bool:
        """Check if user is within rate limit."""
        key = f"rate_limit:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        limit = self.TIER_LIMITS[tier]

        current = self.redis.incr(key)
        if current == 1:
            self.redis.expire(key, 60)  # Expire after 1 minute

        return current <= limit

    def get_remaining(self, user_id: int, tier: Tier) -> int:
        """Get remaining requests in current window."""
        key = f"rate_limit:{user_id}:{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        current = int(self.redis.get(key) or 0)
        limit = self.TIER_LIMITS[tier]
        return max(0, limit - current)
```

---

## Billing & Subscription Management

### Recommended: Stripe Integration

```python
# wrdata/core/billing.py
import stripe
from datetime import datetime, timedelta

class BillingManager:
    """Manage subscriptions via Stripe."""

    PRICE_IDS = {
        'pro_monthly': 'price_pro_monthly_99',
        'pro_annual': 'price_pro_annual_950',  # ~20% discount
        'enterprise_monthly': 'price_enterprise_monthly_299',
        'enterprise_annual': 'price_enterprise_annual_2990',
    }

    def create_subscription(self, user_id: int, plan: str):
        """Create new subscription."""
        user = User.get(user_id)

        # Create Stripe customer if doesn't exist
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email)
            user.stripe_customer_id = customer.id
            user.save()

        # Create subscription
        subscription = stripe.Subscription.create(
            customer=user.stripe_customer_id,
            items=[{'price': self.PRICE_IDS[plan]}],
            trial_period_days=7,  # Optional: 7-day trial
        )

        # Update user tier
        if 'pro' in plan:
            user.tier = Tier.PRO
        elif 'enterprise' in plan:
            user.tier = Tier.ENTERPRISE

        user.subscription_expires_at = datetime.fromtimestamp(
            subscription.current_period_end
        )
        user.save()

        return subscription

    def handle_webhook(self, event):
        """Handle Stripe webhooks."""
        if event.type == 'invoice.payment_succeeded':
            # Extend subscription
            self.extend_subscription(event.data.object)

        elif event.type == 'invoice.payment_failed':
            # Downgrade to free tier
            self.downgrade_user(event.data.object)

        elif event.type == 'customer.subscription.deleted':
            # Cancel subscription
            self.cancel_subscription(event.data.object)
```

---

## Upgrade/Downgrade Flow

### Upgrade: Free → Pro

```
User clicks "Upgrade to Pro"
    ↓
Redirect to Stripe Checkout
    ↓
Payment successful
    ↓
Stripe webhook → Update user.tier = 'pro'
    ↓
User can now access Pro endpoints
```

### Downgrade: Pro → Free

```
User clicks "Cancel subscription"
    ↓
Subscription canceled (end of billing period)
    ↓
Stripe webhook → Update user.tier = 'free'
    ↓
User loses access to Pro endpoints
(Data is retained but read-only)
```

---

## Revenue Projections

### Conservative Estimate (12 months)

| Month | Free Users | Pro Users | Enterprise | MRR | Costs | Net |
|-------|------------|-----------|------------|-----|-------|-----|
| 1 | 100 | 5 | 0 | $495 | $500 | -$5 |
| 3 | 500 | 20 | 2 | $2,580 | $750 | $1,830 |
| 6 | 2,000 | 100 | 10 | $12,900 | $1,500 | $11,400 |
| 12 | 10,000 | 500 | 50 | $64,450 | $5,000 | $59,450 |

**Conversion Rate Assumptions:**
- Free → Pro: 5%
- Pro → Enterprise: 10%

### Optimistic Estimate (12 months)

| Month | Free Users | Pro Users | Enterprise | MRR | Costs | Net |
|-------|------------|-----------|------------|-----|-------|-----|
| 1 | 500 | 10 | 0 | $990 | $500 | $490 |
| 3 | 2,000 | 100 | 5 | $11,385 | $1,000 | $10,385 |
| 6 | 10,000 | 500 | 30 | $58,470 | $3,000 | $55,470 |
| 12 | 50,000 | 2,500 | 150 | $292,350 | $15,000 | $277,350 |

---

## Next Steps

1. ✅ Finalize tier feature matrix
2. ⏭️ Implement authentication & API key system
3. ⏭️ Implement rate limiting (Redis-based)
4. ⏭️ Set up Stripe integration
5. ⏭️ Build pricing page & landing page
6. ⏭️ Launch beta (free tier only)
7. ⏭️ Add first Pro provider (Polygon.io)
8. ⏭️ Launch Pro tier publicly

**Timeline:** 8-12 weeks to launch Free + Pro tiers
