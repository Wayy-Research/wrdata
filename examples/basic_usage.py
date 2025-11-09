"""
Basic usage examples for wrdata DataStream API.

This shows how ridiculously simple it is to get market data now.
"""

from wrdata import DataStream

# ============================================================================
# EXAMPLE 1: Dead Simple - Get stock data
# ============================================================================
print("=" * 60)
print("EXAMPLE 1: Basic stock data")
print("=" * 60)

stream = DataStream()

# Get 1 year of AAPL data (default)
df = stream.get("AAPL")
print(f"\nAAPL data shape: {df.shape}")
print(df.head())
print(df.tail())


# ============================================================================
# EXAMPLE 2: Custom date range
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 2: Custom date range")
print("=" * 60)

# Get specific date range
df = stream.get("AAPL", start="2024-01-01", end="2024-06-30")
print(f"\nAAPL Q1-Q2 2024 shape: {df.shape}")
print(df.head())


# ============================================================================
# EXAMPLE 3: Crypto data
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 3: Crypto data")
print("=" * 60)

# Get Bitcoin data (automatically uses Binance)
df = stream.get("BTCUSDT", asset_type="crypto", start="2024-01-01")
print(f"\nBTC data shape: {df.shape}")
print(df.head())


# ============================================================================
# EXAMPLE 4: Intraday data
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 4: Intraday data")
print("=" * 60)

# Get 5-minute bars for today
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")

df = stream.get(
    "AAPL",
    start=today,
    end=today,
    interval="5m"
)
print(f"\nAAPL 5m data shape: {df.shape}")
print(df.head())


# ============================================================================
# EXAMPLE 5: Multiple symbols
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 5: Multiple symbols")
print("=" * 60)

# Get data for multiple stocks
data = stream.get_many(["AAPL", "GOOGL", "MSFT"])

for symbol, df in data.items():
    print(f"\n{symbol}: {df.shape[0]} rows")
    print(f"  Latest close: ${df['close'].iloc[-1]:.2f}")


# ============================================================================
# EXAMPLE 6: Options chains
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 6: Options chain")
print("=" * 60)

# Get available expirations
expirations = stream.get_expirations("SPY")
print(f"\nSPY has {len(expirations)} available expirations")
print(f"Next 3 expirations: {expirations[:3]}")

# Get options chain for nearest expiry
chain = stream.options("SPY")
print(f"\nSPY options chain shape: {chain.shape}")
print(chain.head())

# Get only calls near current price
chain_calls = stream.options(
    "SPY",
    option_type="call",
    strike_min=580,
    strike_max=600
)
print(f"\nSPY calls near money: {chain_calls.shape}")
print(chain_calls)


# ============================================================================
# EXAMPLE 7: Provider status
# ============================================================================
print("\n" + "=" * 60)
print("EXAMPLE 7: Check provider status")
print("=" * 60)

status = stream.status()
print("\nProvider Status:")
for provider, info in status.items():
    print(f"  {provider}:")
    for key, value in info.items():
        print(f"    {key}: {value}")


print("\n" + "=" * 60)
print("All examples completed successfully!")
print("=" * 60)
