"""
Advanced usage examples for wrdata DataStream API.

Shows configuration with API keys, custom providers, and more.
"""

from wrdata import DataStream

# ============================================================================
# EXAMPLE 1: Configuration from environment
# ============================================================================
print("=" * 60)
print("EXAMPLE 1: Configuration from environment")
print("=" * 60)

# Set API keys via environment variables or .env file:
# BINANCE_API_KEY=your_key_here
# BINANCE_API_SECRET=your_secret_here

# DataStream automatically picks up env vars
stream = DataStream()
print(f"Stream initialized: {stream}")
print(f"Available providers: {list(stream.providers.keys())}")


# ============================================================================
# EXAMPLE 2: Passing API keys directly
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 2: Direct API key configuration")
print("=" * 60)

# Pass API keys directly (useful for multi-account setups)
import os

stream = DataStream(
    binance_key=os.getenv('BINANCE_API_KEY'),
    binance_secret=os.getenv('BINANCE_API_SECRET'),
    polygon_key=os.getenv('POLYGON_API_KEY'),
    alphavantage_key=os.getenv('ALPHAVANTAGE_API_KEY'),
)

print(f"Stream with custom keys: {stream}")


# ============================================================================
# EXAMPLE 3: Forcing specific provider
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 3: Force specific provider")
print("=" * 60)

stream = DataStream()

# Force YFinance even for crypto
df = stream.get(
    "BTC-USD",  # YFinance crypto format
    provider="yfinance",
    start="2024-01-01"
)
print(f"BTC from YFinance: {df.shape}")


# ============================================================================
# EXAMPLE 4: Disable fallbacks (fail fast)
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 4: Disable fallbacks")
print("=" * 60)

stream = DataStream(fallback_enabled=False)

try:
    # If primary provider fails, this will fail immediately
    # instead of trying other providers
    df = stream.get("INVALID_SYMBOL_XYZ123")
except Exception as e:
    print(f"Failed fast without fallback: {e}")


# ============================================================================
# EXAMPLE 5: Research workflow - analyze multiple stocks
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 5: Real research workflow")
print("=" * 60)

stream = DataStream()

# Define your universe
tech_stocks = ["AAPL", "GOOGL", "MSFT", "NVDA", "META"]

# Get data for all
data = stream.get_many(tech_stocks, start="2024-01-01")

# Calculate simple metrics
print("\nTech Stock Performance (2024 YTD):")
for symbol, df in data.items():
    if df.empty:
        continue

    start_price = df['close'].iloc[0]
    end_price = df['close'].iloc[-1]
    return_pct = ((end_price - start_price) / start_price) * 100

    print(f"  {symbol:6s}: {return_pct:+6.2f}%  (${start_price:.2f} -> ${end_price:.2f})")


# ============================================================================
# EXAMPLE 6: Options strategy analysis
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 6: Options strategy analysis")
print("=" * 60)

stream = DataStream()

# Get current SPY price
spy_data = stream.get("SPY", start="2024-11-01")
current_price = spy_data['close'].iloc[-1]
print(f"\nSPY current price: ${current_price:.2f}")

# Get options near the money
atm_calls = stream.options(
    "SPY",
    option_type="call",
    strike_min=current_price - 10,
    strike_max=current_price + 10
)

print(f"\nATM Calls ({atm_calls.shape[0]} contracts):")
if not atm_calls.empty and 'strike' in atm_calls.columns:
    for _, row in atm_calls.head(5).iterrows():
        print(f"  Strike ${row['strike']}: Last=${row.get('last_price', 'N/A')}, IV={row.get('implied_volatility', 'N/A')}")


# ============================================================================
# EXAMPLE 7: Combine stock + options analysis
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 7: Complete analysis - stock + options")
print("=" * 60)

def analyze_symbol(symbol: str):
    """Complete analysis of a symbol."""
    print(f"\n--- Analyzing {symbol} ---")

    # Get stock data
    df = stream.get(symbol, start="2024-01-01")
    current_price = df['close'].iloc[-1]
    ytd_return = ((current_price - df['close'].iloc[0]) / df['close'].iloc[0]) * 100

    print(f"Current Price: ${current_price:.2f}")
    print(f"YTD Return: {ytd_return:+.2f}%")

    # Get volatility (simple 30-day)
    returns = df['close'].pct_change()
    volatility = returns.tail(30).std() * (252 ** 0.5) * 100  # Annualized
    print(f"30-day volatility: {volatility:.2f}%")

    # Get options data
    try:
        expirations = stream.get_expirations(symbol)
        print(f"Available expirations: {len(expirations)}")

        if expirations:
            # Get near-term options
            chain = stream.options(symbol, expiry=expirations[0])
            print(f"Contracts for {expirations[0]}: {len(chain)}")
    except Exception as e:
        print(f"Options not available: {e}")


# Analyze a few symbols
for symbol in ["AAPL", "SPY"]:
    analyze_symbol(symbol)


print("\n" + "=" * 60)
print("Advanced examples completed!")
print("=" * 60)
