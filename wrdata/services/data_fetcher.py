"""
Service for fetching market data (OHLCV) from various providers.

This is the main entry point for fetching historical timeseries data.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from wrdata.models.schemas import DataRequest, DataResponse
from wrdata.providers.base import BaseProvider
from wrdata.providers.yfinance_provider import YFinanceProvider
from wrdata.providers.binance_provider import BinanceProvider
from wrdata.core.config import settings


class DataFetcher:
    """
    Service for fetching market data from multiple providers.

    Automatically routes requests to appropriate providers based on asset type.
    Supports stocks, crypto, forex, commodities, economic indicators, and more.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize the DataFetcher.

        Args:
            db: Optional database session for storing fetched data
        """
        self.db = db

        # Initialize providers
        self.providers: Dict[str, BaseProvider] = {}

        # Add YFinance provider (stocks, ETFs, indices, forex)
        self.providers['yfinance'] = YFinanceProvider()

        # Add Binance provider if available (crypto)
        try:
            if settings.has_binance_key:
                self.providers['binance'] = BinanceProvider(
                    api_key=settings.BINANCE_API_KEY,
                    api_secret=settings.BINANCE_API_SECRET
                )
            else:
                # Use unauthenticated Binance (lower rate limits)
                self.providers['binance'] = BinanceProvider()
        except Exception as e:
            print(f"Warning: Could not initialize Binance provider: {e}")

        # Default provider mapping by asset type
        self.default_providers = {
            'equity': 'yfinance',
            'stock': 'yfinance',
            'etf': 'yfinance',
            'index': 'yfinance',
            'forex': 'yfinance',
            'crypto': 'binance',
            'cryptocurrency': 'binance',
            'economic': 'yfinance',
            'bond': 'yfinance',
            'commodity': 'yfinance',
        }

    def add_provider(self, name: str, provider: BaseProvider):
        """
        Add a custom provider to the fetcher.

        Args:
            name: Provider name
            provider: Provider instance
        """
        self.providers[name] = provider

    def fetch_data(self, request: DataRequest) -> DataResponse:
        """
        Fetch market data based on the request.

        Automatically selects the appropriate provider based on asset type
        or uses the explicitly specified provider.

        Args:
            request: DataRequest with symbol, dates, and parameters

        Returns:
            DataResponse with the fetched data
        """
        # Determine which provider to use
        provider_name = self._select_provider(request)

        if provider_name not in self.providers:
            return DataResponse(
                symbol=request.symbol,
                provider=provider_name,
                data=[],
                success=False,
                error=f"Provider '{provider_name}' not available"
            )

        provider = self.providers[provider_name]

        # Fetch the data
        try:
            response = provider.fetch_timeseries(
                symbol=request.symbol,
                start_date=request.start_date,
                end_date=request.end_date,
                interval=request.interval
            )

            # Optionally store in database (future enhancement)
            if self.db and response.success:
                # TODO: Implement database storage for OHLCV data
                pass

            return response

        except Exception as e:
            return DataResponse(
                symbol=request.symbol,
                provider=provider_name,
                data=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _select_provider(self, request: DataRequest) -> str:
        """
        Select the appropriate provider based on the request.

        Args:
            request: DataRequest

        Returns:
            Provider name
        """
        # If provider is explicitly specified, use it
        if request.provider:
            return request.provider

        # Otherwise, select based on asset type
        asset_type = request.asset_type.lower()
        return self.default_providers.get(asset_type, 'yfinance')

    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about available providers.

        Returns:
            Dictionary of provider info
        """
        provider_info = {}

        for name, provider in self.providers.items():
            is_connected = provider.validate_connection()

            provider_info[name] = {
                'name': name,
                'is_connected': is_connected,
                'supports_options': hasattr(provider, 'fetch_options_chain'),
                'supports_historical_options': provider.supports_historical_options(),
            }

        return provider_info

    def validate_all_providers(self) -> Dict[str, bool]:
        """
        Validate connection to all providers.

        Returns:
            Dictionary mapping provider names to connection status
        """
        return {
            name: provider.validate_connection()
            for name, provider in self.providers.items()
        }

    def fetch_multiple(self, requests: list[DataRequest]) -> list[DataResponse]:
        """
        Fetch data for multiple symbols efficiently.

        Args:
            requests: List of DataRequest objects

        Returns:
            List of DataResponse objects
        """
        responses = []

        for request in requests:
            response = self.fetch_data(request)
            responses.append(response)

        return responses

    def get_supported_asset_types(self) -> list[str]:
        """
        Get list of supported asset types.

        Returns:
            List of asset type strings
        """
        return list(self.default_providers.keys())
