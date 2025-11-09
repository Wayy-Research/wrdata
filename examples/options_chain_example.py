"""
Example script demonstrating how to fetch and store options chain data.

This example shows:
1. How to initialize the database
2. How to fetch current options chain data
3. How to store options chain snapshots
4. How to retrieve historical options timeseries data
"""

from datetime import datetime, date, timedelta
from decimal import Decimal

from wrdata.utils.db_utils import init_database, get_session
from wrdata.services.options_fetcher import OptionsFetcher
from wrdata.models.schemas import (
    OptionsChainRequest,
    OptionsTimeseriesRequest,
)
from wrdata.models.database import DataProvider


def setup_database():
    """Initialize database and ensure yfinance provider exists."""
    print("=== Setting up database ===\n")

    # Initialize database tables
    init_database()

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
        print("Created yfinance provider\n")
    else:
        print("yfinance provider already exists\n")

    return session


def fetch_current_options_chain(session, symbol: str = "AAPL"):
    """
    Fetch and display current options chain for a symbol.
    """
    print(f"=== Fetching current options chain for {symbol} ===\n")

    fetcher = OptionsFetcher(session)

    # Get available expiration dates
    expirations = fetcher.get_available_expirations(symbol)
    print(f"Available expirations: {expirations[:5]}...\n")

    if not expirations:
        print("No options available for this symbol")
        return

    # Fetch options chain for the nearest expiration
    request = OptionsChainRequest(
        symbol=symbol,
        expiration_date=expirations[0],
        option_type=None,  # Get both calls and puts
        min_strike=None,
        max_strike=None
    )

    response = fetcher.fetch_and_store_options_chain(request)

    if response.success:
        print(f"Successfully fetched options chain!")
        print(f"Snapshot time: {response.snapshot_timestamp}")
        print(f"Underlying price: ${response.underlying_price}")
        print(f"Number of calls: {len(response.calls)}")
        print(f"Number of puts: {len(response.puts)}")
        print()

        # Display some sample calls
        print("Sample calls:")
        for call in response.calls[:3]:
            print(f"  Strike ${call.strike_price}: Last ${call.last_price}, "
                  f"IV {call.implied_volatility:.2%} " if call.implied_volatility else "", end='')
            if call.greeks and call.greeks.delta:
                print(f"Delta {call.greeks.delta:.3f}")
            else:
                print()

        print()

        # Display some sample puts
        print("Sample puts:")
        for put in response.puts[:3]:
            print(f"  Strike ${put.strike_price}: Last ${put.last_price}, "
                  f"IV {put.implied_volatility:.2%} " if put.implied_volatility else "", end='')
            if put.greeks and put.greeks.delta:
                print(f"Delta {put.greeks.delta:.3f}")
            else:
                print()

        print()
    else:
        print(f"Failed to fetch options chain: {response.error}\n")


def fetch_filtered_options(session, symbol: str = "AAPL"):
    """
    Fetch options with specific filters (e.g., only calls near the money).
    """
    print(f"=== Fetching filtered options for {symbol} ===\n")

    fetcher = OptionsFetcher(session)
    expirations = fetcher.get_available_expirations(symbol)

    if not expirations:
        print("No options available")
        return

    # Get underlying price to filter near-the-money options
    # For this example, we'll fetch all and then show we could filter
    request = OptionsChainRequest(
        symbol=symbol,
        expiration_date=expirations[0],
        option_type="call",  # Only calls
        min_strike=Decimal("150.00"),  # Example: only strikes above $150
        max_strike=Decimal("200.00")   # and below $200
    )

    response = fetcher.fetch_and_store_options_chain(request)

    if response.success:
        print(f"Fetched {len(response.calls)} calls between $150-$200 strike")
        print(f"Underlying price: ${response.underlying_price}\n")
    else:
        print(f"Failed: {response.error}\n")


def retrieve_historical_options_data(session, symbol: str = "AAPL"):
    """
    Retrieve historical options data that was previously stored.
    """
    print(f"=== Retrieving historical options data for {symbol} ===\n")

    fetcher = OptionsFetcher(session)

    # Get data from the last 7 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)

    request = OptionsTimeseriesRequest(
        underlying_symbol=symbol,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        interval="1d"
    )

    response = fetcher.get_options_timeseries(request)

    if response.success:
        print(f"Retrieved {len(response.data)} snapshots")

        if response.data:
            print("\nSample data points:")
            for snapshot in response.data[:5]:
                print(f"  {snapshot['timestamp']}: {snapshot['contract_symbol']} "
                      f"Last ${snapshot['last_price']}, IV {snapshot['implied_volatility']:.2%}"
                      if snapshot['implied_volatility'] else "")
        else:
            print("No historical data found (you may need to run this script multiple times")
            print("over several days to accumulate historical data)")
        print()
    else:
        print(f"Failed to retrieve data: {response.error}\n")


def main():
    """
    Main example function demonstrating options chain data fetching.
    """
    print("Options Chain Data Example\n")
    print("=" * 50)
    print()

    # Setup database
    session = setup_database()

    try:
        # Example 1: Fetch current options chain for AAPL
        fetch_current_options_chain(session, "AAPL")

        # Example 2: Fetch filtered options
        fetch_filtered_options(session, "AAPL")

        # Example 3: Retrieve historical data
        retrieve_historical_options_data(session, "AAPL")

        print("=" * 50)
        print("\nExample completed successfully!")
        print("\nTo build historical timeseries:")
        print("1. Run this script regularly (e.g., daily via cron)")
        print("2. Each run will add a new snapshot to the database")
        print("3. Query the database to analyze options data over time")
        print("\nExample queries you could run:")
        print("- Track implied volatility changes over time")
        print("- Monitor open interest trends")
        print("- Analyze how options greeks change as expiration approaches")
        print("- Build volatility surfaces from historical IV data")

    finally:
        session.close()


if __name__ == "__main__":
    main()
