"""
Quick test script to verify options chain functionality works.
"""

from datetime import datetime
from wrdata.utils.db_utils import get_session
from wrdata.services.options_fetcher import OptionsFetcher
from wrdata.models.schemas import OptionsChainRequest
from wrdata.models.database import DataProvider

# Create session
session = get_session()

# Ensure yfinance provider exists
provider = session.query(DataProvider).filter(
    DataProvider.name == 'yfinance'
).first()

if not provider:
    provider = DataProvider(
        name='yfinance',
        provider_type='market_data',
        api_key_required=False,
        has_api_key=False,
        is_active=True,
        supported_assets='["equity", "options"]',
        rate_limit=2000
    )
    session.add(provider)
    session.commit()
    print("Created yfinance provider")

# Create fetcher
fetcher = OptionsFetcher(session)

# Get available expirations for SPY (highly liquid)
print("\nFetching available expirations for SPY...")
expirations = fetcher.get_available_expirations("SPY")
print(f"Found {len(expirations)} expiration dates")
print(f"Next 3 expirations: {expirations[:3]}")

# Fetch options chain for the nearest expiration
if expirations:
    print(f"\nFetching options chain for SPY expiring {expirations[0]}...")

    request = OptionsChainRequest(
        symbol="SPY",
        expiration_date=expirations[0],
    )

    response = fetcher.fetch_and_store_options_chain(request)

    if response.success:
        print(f"✓ Successfully fetched and stored options chain!")
        print(f"  Snapshot time: {response.snapshot_timestamp}")
        print(f"  Underlying price: ${response.underlying_price}")
        print(f"  Number of calls: {len(response.calls)}")
        print(f"  Number of puts: {len(response.puts)}")

        print("\n  Sample call contracts:")
        for call in response.calls[:3]:
            iv = f"IV {call.implied_volatility:.2%}" if call.implied_volatility else "IV N/A"
            delta = f"Δ {call.greeks.delta:.3f}" if call.greeks and call.greeks.delta else ""
            print(f"    ${call.strike_price} - Last ${call.last_price} {iv} {delta}")

        print("\n  Sample put contracts:")
        for put in response.puts[:3]:
            iv = f"IV {put.implied_volatility:.2%}" if put.implied_volatility else "IV N/A"
            delta = f"Δ {put.greeks.delta:.3f}" if put.greeks and put.greeks.delta else ""
            print(f"    ${put.strike_price} - Last ${put.last_price} {iv} {delta}")

        print("\n✓ Options chain data successfully stored in database!")
    else:
        print(f"✗ Failed to fetch options chain: {response.error}")
else:
    print("No expirations available")

session.close()
