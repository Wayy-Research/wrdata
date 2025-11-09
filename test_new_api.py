"""Quick test of the new simplified DataStream API."""

from wrdata import DataStream

print("Testing wrdata DataStream API...")
print("=" * 60)

# Initialize
stream = DataStream()
print(f"✓ DataStream initialized: {stream}")

# Check providers
print(f"✓ Available providers: {list(stream.providers.keys())}")

# Test basic get
print("\nFetching AAPL data...")
df = stream.get("AAPL", start="2024-11-01", end="2024-11-07")
print(f"✓ Got {len(df)} rows of data")
print(f"  Columns: {df.columns}")
print(f"  Latest close: ${df['close'][-1]:.2f}")
print("\nFirst few rows:")
print(df.head())

# Test status
print("\nChecking provider status...")
status = stream.status()
for provider, info in status.items():
    print(f"  {provider}: connected={info.get('connected', False)}")

print("\n" + "=" * 60)
print("All tests passed! 🎉")
