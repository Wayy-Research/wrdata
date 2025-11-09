"""
Base provider interface for data fetching.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
    OptionsTimeseriesRequest,
    OptionsTimeseriesResponse,
)


class BaseProvider(ABC):
    """
    Base class for all data providers.
    Defines the interface that all providers must implement.
    """

    def __init__(self, name: str, api_key: Optional[str] = None):
        self.name = name
        self.api_key = api_key

    @abstractmethod
    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch historical timeseries data for a symbol.

        Args:
            symbol: The ticker symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Time interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
            **kwargs: Additional provider-specific parameters

        Returns:
            DataResponse with timeseries data
        """
        pass

    @abstractmethod
    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """
        Fetch current options chain data for a symbol.

        Args:
            request: OptionsChainRequest with symbol and filter parameters

        Returns:
            OptionsChainResponse with options chain data
        """
        pass

    def fetch_options_timeseries(
        self,
        request: OptionsTimeseriesRequest
    ) -> OptionsTimeseriesResponse:
        """
        Fetch historical timeseries of options chain data.

        Note: Not all providers support historical options data.
        Default implementation raises NotImplementedError.

        Args:
            request: OptionsTimeseriesRequest with parameters

        Returns:
            OptionsTimeseriesResponse with historical options data
        """
        raise NotImplementedError(
            f"{self.name} does not support historical options timeseries"
        )

    @abstractmethod
    def get_available_expirations(self, symbol: str) -> List[date]:
        """
        Get list of available expiration dates for a symbol.

        Args:
            symbol: The ticker symbol

        Returns:
            List of available expiration dates
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate that the provider connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        pass

    def supports_historical_options(self) -> bool:
        """
        Check if this provider supports historical options data.

        Returns:
            True if historical options are supported
        """
        return False
