# Data Provider Terms of Service Analysis
## Legal Review for Data Redistribution & Reselling

**Last Updated:** 2025-11-05
**Purpose:** Determine which data providers allow redistribution/reselling vs personal use only

---

## Summary Table

| Provider | Free Tier | Redistribution Allowed? | Notes | Freemium Tier |
|----------|-----------|------------------------|-------|---------------|
| **EQUITIES** |
| YFinance | ✅ Yes | ❌ NO | Yahoo's data, unclear ToS. Use at own risk. | Free only |
| Alpha Vantage | ✅ Yes (5 calls/min) | ❌ NO | "Personal use only", no redistribution | Free only |
| IEX Cloud | ✅ Yes (limited) | ✅ YES with license | Offers redistribution licenses | Pro tier |
| Polygon.io | ❌ No | ✅ YES with paid plan | No free tier, $99+/mo for redistribution | Pro tier |
| Tiingo | ✅ Yes | ⚠️ UNCLEAR | Check with Tiingo support | TBD |
| **CRYPTO EXCHANGES** |
| Binance | ✅ Yes | ✅ YES | Public market data redistributable | Free & Pro |
| Coinbase | ✅ Yes | ✅ YES | Public API data redistributable | Free & Pro |
| Kraken | ✅ Yes | ✅ YES | Public market data OK to redistribute | Free & Pro |
| CoinGecko | ✅ Yes | ⚠️ PERSONAL USE | Free tier personal only, Pro allows commercial | Pro tier |
| **ECONOMIC DATA** |
| FRED (St. Louis Fed) | ✅ Yes | ✅ YES | Public domain, fully redistributable | Free |
| World Bank | ✅ Yes | ✅ YES | Open data, CC BY 4.0 license | Free |
| ECB Data | ✅ Yes | ✅ YES | Public data with attribution | Free |
| US Treasury | ✅ Yes | ✅ YES | Government data, public domain | Free |
| **FOREX** |
| ECB Reference Rates | ✅ Yes | ✅ YES | Free with attribution | Free |
| Alpha Vantage FX | ✅ Yes | ❌ NO | Same as equity restrictions | Free only |
| Twelve Data | ✅ Yes (limited) | ❌ NO | Personal use only on free tier | Pro tier |
| **OPTIONS** |
| CBOE DataShop | ❌ No | ✅ YES (expensive) | $1000s/month, full redistribution | Pro tier |
| YFinance Options | ✅ Yes | ❌ NO | Same as YFinance equity ToS | Free only |
| **BROKER APIs** |
| Alpaca | ✅ Yes (paper) | ⚠️ LIMITED | Real-time OK if user has Alpaca account | Pro tier |
| Interactive Brokers | ❌ No | ❌ NO | Requires account, no redistribution | Pro only |
| TD Ameritrade | ❌ No | ❌ NO | Account required, personal use only | Pro only |

---

## Detailed Analysis

### ✅ SAFE TO REDISTRIBUTE (No Special License Needed)

#### **Government/Public Data Sources**
These are **public domain** or **openly licensed** - you can redistribute freely:

1. **FRED (Federal Reserve Economic Data)**
   - License: Public domain (US Government data)
   - Coverage: 800,000+ economic time series
   - Restrictions: None, attribution appreciated
   - **Verdict: ✅ SAFE - Full redistribution allowed**

2. **US Treasury Data**
   - License: Public domain
   - Coverage: Bond yields, auction data
   - Restrictions: None
   - **Verdict: ✅ SAFE - Full redistribution allowed**

3. **World Bank Open Data**
   - License: Creative Commons Attribution 4.0 (CC BY 4.0)
   - Coverage: Global economic indicators
   - Restrictions: Must attribute World Bank
   - **Verdict: ✅ SAFE - Redistribution with attribution**

4. **European Central Bank (ECB)**
   - License: Free to use with attribution
   - Coverage: European economic data, EUR reference rates
   - Restrictions: Attribute ECB as source
   - **Verdict: ✅ SAFE - Redistribution with attribution**

#### **Crypto Exchange Public APIs**
Most crypto exchanges **explicitly allow** redistribution of public market data:

5. **Binance Public API**
   - ToS: Public market data can be redistributed
   - Coverage: Spot, futures, options (multi-asset)
   - Rate Limits: 1200 requests/minute (IP based)
   - **Verdict: ✅ SAFE - Redistribution allowed**
   - Source: Binance API docs state public data is redistributable

6. **Coinbase Public API**
   - ToS: Public market data redistributable
   - Coverage: Spot trading data
   - Rate Limits: 10 requests/second (IP based)
   - **Verdict: ✅ SAFE - Redistribution allowed**

7. **Kraken Public API**
   - ToS: Public market data can be used/redistributed
   - Coverage: Spot, futures
   - Rate Limits: Varies by endpoint
   - **Verdict: ✅ SAFE - Redistribution allowed**

---

### ⚠️ REQUIRES PAID LICENSE FOR REDISTRIBUTION

8. **IEX Cloud**
   - Free Tier: Personal use only
   - Paid Plans: Offer "Data Redistribution License"
   - Cost: $99-$999/month depending on volume
   - **Verdict: ⚠️ PAY FOR LICENSE - Can resell with paid plan**
   - Recommendation: Good option for Pro tier

9. **Polygon.io**
   - No free tier
   - Starter: $99/mo (no redistribution)
   - Business: $249/mo (allows redistribution to customers)
   - **Verdict: ⚠️ PAY FOR LICENSE - $249/mo minimum**
   - Recommendation: Excellent data quality, worth it for Pro tier

10. **CoinGecko**
    - Free Tier: Personal/non-commercial use only
    - Pro Tier: $129/mo, allows commercial use
    - **Verdict: ⚠️ FREE=NO, PRO=YES**
    - Recommendation: Free tier for free users, Pro for our Pro tier

---

### ❌ NO REDISTRIBUTION ALLOWED (Personal Use Only)

11. **YFinance / Yahoo Finance**
    - ToS: Unclear/unofficial API
    - Yahoo's official ToS: Prohibits redistribution
    - Legal Status: Gray area (unofficial scraping)
    - **Verdict: ❌ RISKY - Not recommended for commercial redistribution**
    - Recommendation: Use only for free tier, at-your-own-risk basis

12. **Alpha Vantage**
    - Free Tier ToS: "Personal use only", no commercial redistribution
    - Premium Plans: Still no redistribution allowed
    - **Verdict: ❌ NO REDISTRIBUTION - Even paid plans**
    - Recommendation: Free tier only, users fetch directly

13. **Twelve Data**
    - Free Tier: Personal use only
    - Paid Plans: Check with support (likely no redistribution)
    - **Verdict: ❌ LIKELY NO**
    - Recommendation: Contact them to confirm

14. **Interactive Brokers (IBKR)**
    - ToS: Data is for account holder only, no redistribution
    - Market data fees: Separate subscription required
    - **Verdict: ❌ NO REDISTRIBUTION**
    - Recommendation: Pro tier users fetch with their own API keys

15. **TD Ameritrade**
    - ToS: Account required, personal use only
    - **Verdict: ❌ NO REDISTRIBUTION**
    - Recommendation: Users provide their own API keys

---

## Recommended Architecture Based on ToS

### **Free Tier (100% Legal, No Redistribution Issues)**
Only include data sources that explicitly allow redistribution:
- ✅ FRED (economic data)
- ✅ World Bank (economic data)
- ✅ ECB (economic data, EUR FX rates)
- ✅ US Treasury (bond yields)
- ✅ Binance (crypto OHLCV, order books, trades)
- ✅ Coinbase (crypto OHLCV, trades)
- ✅ Kraken (crypto OHLCV, trades)

**What users get:**
- Comprehensive economic indicators
- Full crypto market coverage (spot)
- Daily/historical data
- No legal risk

**What's missing:**
- US equities (stocks)
- Options chains
- Forex (except EUR from ECB)
- High-frequency data (minute/second)

### **Pro Tier ($49-99/mo) - Licensed Redistribution**
Purchase redistribution licenses and include:
- ✅ IEX Cloud ($99/mo plan) - US equities, intraday
- ✅ Polygon.io ($249/mo plan) - Stocks, options, forex, crypto
- ✅ CoinGecko Pro ($129/mo) - Enhanced crypto data
- ⚠️ YFinance (gray area - include but with disclaimer)

**Cost to provide:**
- IEX: $99/mo
- Polygon: $249/mo
- CoinGecko Pro: $129/mo
- **Total: ~$477/mo** in data costs

**Pricing strategy:**
- Charge $99/mo per user
- Break-even at ~5 users
- Margin at 10+ users

### **Enterprise Tier ($299-499/mo) - User-Owned API Keys**
Advanced users bring their own API keys:
- Interactive Brokers integration (user's account)
- TD Ameritrade integration (user's API key)
- Alpaca integration (user's API key)
- CBOE DataShop (if user has license)

**Benefits:**
- No redistribution concerns (user fetches their own data)
- We provide: infrastructure, storage, query optimization
- User pays: their own data provider fees

---

## Legal Safeguards

### 1. Terms of Service (Our Platform)
```markdown
**Data Usage & Ownership**
- Free Tier: Data sourced from public/redistributable sources only
- Pro Tier: We license data from providers for redistribution to subscribers
- Enterprise Tier: You provide your own API keys; data is yours
- Users are responsible for compliance with original data provider ToS
- Not financial advice; data provided "as-is" without guarantees

**Acceptable Use**
- Personal/commercial use permitted
- No reverse engineering of our platform
- No bulk export for competing services
- Rate limits apply
```

### 2. Attribution Requirements
For data we redistribute:
```python
# In API responses, include source attribution
{
  "symbol": "BTC-USD",
  "data": [...],
  "metadata": {
    "source": "Binance Public API",
    "attribution": "Data provided by Binance",
    "license": "Redistributable per Binance ToS"
  }
}
```

### 3. Disclaimers
```markdown
**Data Accuracy Disclaimer**
Data is aggregated from third-party sources. We do not guarantee accuracy,
completeness, or timeliness. Not suitable for critical financial decisions
without independent verification.

**Regulatory Compliance**
Users are responsible for ensuring their use complies with local regulations
(SEC, FINRA, MiFID II, etc.). This service does not provide investment advice.
```

---

## Recommended Data Strategy (Freemium Model)

### **Phase 1: Free Tier MVP (Months 1-2)**
Focus on 100% legally redistributable sources:

**Economic Data:**
- FRED API (800k series)
- World Bank API
- ECB Statistical Warehouse
- US Treasury Direct

**Crypto:**
- Binance Public API (spot + futures)
- Coinbase Public API
- Kraken Public API

**Coverage:**
- ✅ Excellent economic data
- ✅ Complete crypto coverage
- ❌ No US equities
- ❌ No options
- ❌ Limited forex

### **Phase 2: Pro Tier Launch (Month 3)**
Purchase redistribution licenses:

**Priority 1: Polygon.io ($249/mo)**
- Adds: US stocks, options, forex
- Quality: Excellent
- Frequency: Second-level data available
- WebSocket: Yes

**Priority 2: IEX Cloud ($99/mo)**
- Adds: US stocks (alternative/backup to Polygon)
- Quality: Good
- Frequency: Intraday
- WebSocket: Yes

**Optional: CoinGecko Pro ($129/mo)**
- Enhances existing crypto data
- Adds: Enhanced historical data, more coins
- May not be necessary given Binance/Coinbase

**Total Pro Tier Cost:** $348-477/mo

### **Phase 3: Enterprise Tier (Month 4+)**
User-owned API key architecture:
- IBKR connector
- TD Ameritrade connector
- Alpaca connector
- User provides keys, we provide infrastructure

---

## Open Questions to Research Further

1. **Tiingo** - Need to confirm their ToS on redistribution
2. **YFinance Legal Status** - Consult with lawyer about unofficial API usage
3. **SEC EDGAR Data** - Confirm redistribution rights for filings
4. **Alternative Data** - Satellite imagery, web scraping (different legal considerations)

---

## Recommendations

### ✅ DO THIS:
1. **Start with free tier using only 100% legal sources** (gov data + crypto exchanges)
2. **For Pro tier, budget $250-500/mo for licensed data** (Polygon or IEX)
3. **Enterprise tier = user-owned keys** (no redistribution concerns)
4. **Clear attribution** in all API responses
5. **Strong Terms of Service** protecting you and users

### ❌ DON'T DO THIS:
1. Don't redistribute Alpha Vantage, YFinance, or other personal-use-only data
2. Don't scrape websites that prohibit it
3. Don't claim data accuracy guarantees
4. Don't launch without proper ToS/disclaimers
5. Don't ignore rate limits (can get banned)

### ⚠️ LEGAL CONSULTATION NEEDED:
Before launching a commercial service, consult with a lawyer about:
- Your Terms of Service
- Data licensing agreements
- Regulatory compliance (if offering to institutions)
- Liability limitations
- GDPR/privacy compliance (if serving EU users)

---

## Next Steps

1. ✅ Focus on free tier with legally safe sources (FRED, crypto exchanges)
2. ⚠️ Contact IEX Cloud and Polygon.io about redistribution licenses
3. ⚠️ Consult lawyer before launching Pro tier
4. ✅ Design architecture that separates "free data" from "licensed data" from "user data"
5. ✅ Implement attribution system in API responses

**Bottom Line:** Start conservative (free tier with public data), then add licensed providers for Pro tier once you have revenue to cover costs.
