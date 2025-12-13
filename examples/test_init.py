"""Quick test to see if DataStream initializes properly."""

print("Importing wrdata...")
from wrdata import DataStream

print("Creating DataStream...")
stream = DataStream()

print("Checking providers...")
print(f"Available providers: {list(stream.providers.keys())}")

print("Checking crypto priority...")
print(f"Crypto priority: {stream._provider_priority.get('crypto', [])}")

print("✅ Initialization successful!")
