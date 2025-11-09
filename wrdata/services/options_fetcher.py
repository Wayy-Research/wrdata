"""
Service for fetching and storing options chain data.
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_

from wrdata.models.database import (
    Symbol,
    DataProvider,
    OptionsContract,
    OptionsChainSnapshot
)
from wrdata.models.schemas import (
    OptionsChainRequest,
    OptionsChainResponse,
    OptionsChainData,
    OptionsTimeseriesRequest,
    OptionsTimeseriesResponse,
)
from wrdata.providers.base import BaseProvider
from wrdata.providers.yfinance_provider import YFinanceProvider


class OptionsFetcher:
    """
    Service for fetching and storing options chain data.
    """

    def __init__(self, db: Session):
        self.db = db
        self.providers = {
            'yfinance': YFinanceProvider()
        }

    def add_provider(self, name: str, provider: BaseProvider):
        """Add a custom provider to the fetcher."""
        self.providers[name] = provider

    def fetch_and_store_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Fetch options chain data and store it in the database.

        Args:
            request: OptionsChainRequest with symbol and parameters

        Returns:
            OptionsChainResponse with the fetched data
        """
        # Determine which provider to use
        provider_name = request.provider or 'yfinance'
        provider = self.providers.get(provider_name)

        if provider is None:
            return OptionsChainResponse(
                symbol=request.symbol,
                provider=provider_name,
                snapshot_timestamp=datetime.utcnow(),
                success=False,
                error=f"Provider '{provider_name}' not found"
            )

        # Fetch the options chain
        response = provider.fetch_options_chain(request)

        if not response.success:
            return response

        # Store the data in the database
        try:
            self._store_options_chain(response, provider_name)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            response.success = False
            response.error = f"Failed to store data: {str(e)}"

        return response

    def _store_options_chain(
        self,
        response: OptionsChainResponse,
        provider_name: str
    ):
        """
        Store options chain data in the database.
        """
        # Get or create the underlying symbol
        symbol = self._get_or_create_symbol(response.symbol, provider_name)

        # Get the data provider
        provider = self.db.query(DataProvider).filter(
            DataProvider.name == provider_name
        ).first()

        if not provider:
            raise ValueError(f"Provider {provider_name} not found in database")

        # Store all options contracts and snapshots
        for options_data in response.calls + response.puts:
            self._store_options_contract_and_snapshot(
                options_data,
                symbol,
                provider,
                response.snapshot_timestamp
            )

    def _get_or_create_symbol(self, symbol_str: str, provider_name: str) -> Symbol:
        """Get or create a symbol in the database."""
        provider = self.db.query(DataProvider).filter(
            DataProvider.name == provider_name
        ).first()

        if not provider:
            raise ValueError(f"Provider {provider_name} not found in database")

        symbol = self.db.query(Symbol).filter(
            and_(
                Symbol.symbol == symbol_str,
                Symbol.provider_id == provider.id
            )
        ).first()

        if not symbol:
            symbol = Symbol(
                provider_id=provider.id,
                symbol=symbol_str,
                asset_type='equity'
            )
            self.db.add(symbol)
            self.db.flush()

        return symbol

    def _store_options_contract_and_snapshot(
        self,
        options_data: OptionsChainData,
        underlying_symbol: Symbol,
        provider: DataProvider,
        snapshot_timestamp: datetime
    ):
        """
        Store an options contract and its snapshot data.
        """
        # Get or create the options contract
        contract = self.db.query(OptionsContract).filter(
            OptionsContract.contract_symbol == options_data.contract_symbol
        ).first()

        if not contract:
            contract = OptionsContract(
                underlying_symbol_id=underlying_symbol.id,
                contract_symbol=options_data.contract_symbol,
                option_type=options_data.option_type,
                strike_price=options_data.strike_price,
                expiration_date=options_data.expiration_date
            )
            self.db.add(contract)
            self.db.flush()

        # Create the snapshot
        snapshot = OptionsChainSnapshot(
            contract_id=contract.id,
            provider_id=provider.id,
            snapshot_timestamp=snapshot_timestamp,
            bid=options_data.bid,
            ask=options_data.ask,
            last_price=options_data.last_price,
            mark_price=options_data.mark_price,
            volume=options_data.volume,
            open_interest=options_data.open_interest,
            delta=options_data.greeks.delta if options_data.greeks else None,
            gamma=options_data.greeks.gamma if options_data.greeks else None,
            theta=options_data.greeks.theta if options_data.greeks else None,
            vega=options_data.greeks.vega if options_data.greeks else None,
            rho=options_data.greeks.rho if options_data.greeks else None,
            implied_volatility=options_data.implied_volatility,
            intrinsic_value=options_data.intrinsic_value,
            extrinsic_value=options_data.extrinsic_value,
            in_the_money=options_data.in_the_money,
            underlying_price=options_data.underlying_price
        )

        self.db.add(snapshot)

    def get_options_timeseries(
        self,
        request: OptionsTimeseriesRequest
    ) -> OptionsTimeseriesResponse:
        """
        Retrieve historical timeseries of options data from the database.

        Args:
            request: OptionsTimeseriesRequest with query parameters

        Returns:
            OptionsTimeseriesResponse with historical data
        """
        try:
            # Build the query
            query = self.db.query(OptionsChainSnapshot)

            # Filter by contract if specified
            if request.contract_symbol:
                contract = self.db.query(OptionsContract).filter(
                    OptionsContract.contract_symbol == request.contract_symbol
                ).first()

                if not contract:
                    return OptionsTimeseriesResponse(
                        symbol=request.contract_symbol or request.underlying_symbol or "",
                        provider=request.provider or "unknown",
                        data=[],
                        success=False,
                        error="Contract not found"
                    )

                query = query.filter(OptionsChainSnapshot.contract_id == contract.id)

            # Filter by underlying symbol if specified
            elif request.underlying_symbol:
                symbol = self.db.query(Symbol).filter(
                    Symbol.symbol == request.underlying_symbol
                ).first()

                if not symbol:
                    return OptionsTimeseriesResponse(
                        symbol=request.underlying_symbol,
                        provider=request.provider or "unknown",
                        data=[],
                        success=False,
                        error="Symbol not found"
                    )

                # Get all contracts for this symbol
                contract_ids = [
                    c.id for c in symbol.options_contracts
                    if (not request.expiration_date or c.expiration_date == request.expiration_date)
                    and (not request.option_type or c.option_type == request.option_type)
                    and (not request.strike_price or c.strike_price == request.strike_price)
                ]

                query = query.filter(OptionsChainSnapshot.contract_id.in_(contract_ids))

            # Filter by date range
            start_dt = datetime.fromisoformat(request.start_date)
            end_dt = datetime.fromisoformat(request.end_date)
            query = query.filter(
                and_(
                    OptionsChainSnapshot.snapshot_timestamp >= start_dt,
                    OptionsChainSnapshot.snapshot_timestamp <= end_dt
                )
            )

            # Filter by provider if specified
            if request.provider:
                provider = self.db.query(DataProvider).filter(
                    DataProvider.name == request.provider
                ).first()
                if provider:
                    query = query.filter(OptionsChainSnapshot.provider_id == provider.id)

            # Execute query and order by timestamp
            snapshots = query.order_by(OptionsChainSnapshot.snapshot_timestamp).all()

            # Convert to list of dicts
            data = []
            for snapshot in snapshots:
                data.append({
                    'timestamp': snapshot.snapshot_timestamp.isoformat(),
                    'contract_symbol': snapshot.contract.contract_symbol,
                    'option_type': snapshot.contract.option_type,
                    'strike_price': float(snapshot.contract.strike_price),
                    'expiration_date': snapshot.contract.expiration_date.isoformat(),
                    'bid': float(snapshot.bid) if snapshot.bid else None,
                    'ask': float(snapshot.ask) if snapshot.ask else None,
                    'last_price': float(snapshot.last_price) if snapshot.last_price else None,
                    'mark_price': float(snapshot.mark_price) if snapshot.mark_price else None,
                    'volume': snapshot.volume,
                    'open_interest': snapshot.open_interest,
                    'delta': snapshot.delta,
                    'gamma': snapshot.gamma,
                    'theta': snapshot.theta,
                    'vega': snapshot.vega,
                    'rho': snapshot.rho,
                    'implied_volatility': snapshot.implied_volatility,
                    'intrinsic_value': float(snapshot.intrinsic_value) if snapshot.intrinsic_value else None,
                    'extrinsic_value': float(snapshot.extrinsic_value) if snapshot.extrinsic_value else None,
                    'in_the_money': snapshot.in_the_money,
                    'underlying_price': float(snapshot.underlying_price) if snapshot.underlying_price else None,
                })

            return OptionsTimeseriesResponse(
                symbol=request.contract_symbol or request.underlying_symbol or "",
                provider=request.provider or "database",
                data=data,
                metadata={
                    'start_date': request.start_date,
                    'end_date': request.end_date,
                    'records': len(data)
                },
                success=True
            )

        except Exception as e:
            return OptionsTimeseriesResponse(
                symbol=request.contract_symbol or request.underlying_symbol or "",
                provider=request.provider or "unknown",
                data=[],
                success=False,
                error=str(e)
            )

    def get_available_expirations(
        self,
        symbol: str,
        provider_name: Optional[str] = None
    ) -> List[date]:
        """
        Get available expiration dates for a symbol.

        Args:
            symbol: The ticker symbol
            provider_name: Optional provider name (defaults to yfinance)

        Returns:
            List of available expiration dates
        """
        provider_name = provider_name or 'yfinance'
        provider = self.providers.get(provider_name)

        if provider is None:
            return []

        return provider.get_available_expirations(symbol)
