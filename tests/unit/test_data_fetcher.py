"""
Unit tests for DataFetcher service.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from wrdata.services.data_fetcher import DataFetcher
from wrdata.models.schemas import DataRequest, DataResponse


@pytest.mark.unit
class TestDataFetcher:
    """Test DataFetcher service."""

    def test_initialization(self):
        """Test data fetcher initialization."""
        fetcher = DataFetcher()

        assert 'yfinance' in fetcher.providers
        assert fetcher.db is None

    def test_initialization_with_db(self, test_db_session):
        """Test data fetcher initialization with database session."""
        fetcher = DataFetcher(db=test_db_session)

        assert fetcher.db is not None

    def test_get_supported_asset_types(self):
        """Test getting supported asset types."""
        fetcher = DataFetcher()
        asset_types = fetcher.get_supported_asset_types()

        assert 'stock' in asset_types
        assert 'crypto' in asset_types
        assert 'forex' in asset_types
        assert 'equity' in asset_types

    def test_add_provider(self):
        """Test adding a custom provider."""
        fetcher = DataFetcher()
        mock_provider = Mock()

        fetcher.add_provider('custom', mock_provider)

        assert 'custom' in fetcher.providers
        assert fetcher.providers['custom'] == mock_provider

    def test_select_provider_explicit(self):
        """Test provider selection with explicit provider."""
        fetcher = DataFetcher()
        request = DataRequest(
            symbol='AAPL',
            asset_type='stock',
            start_date='2024-01-01',
            end_date='2024-01-07',
            provider='yfinance'
        )

        provider_name = fetcher._select_provider(request)

        assert provider_name == 'yfinance'

    def test_select_provider_by_asset_type(self):
        """Test provider selection based on asset type."""
        fetcher = DataFetcher()

        # Stock should use yfinance
        request = DataRequest(
            symbol='AAPL',
            asset_type='stock',
            start_date='2024-01-01',
            end_date='2024-01-07'
        )
        assert fetcher._select_provider(request) == 'yfinance'

        # Crypto should use binance
        request = DataRequest(
            symbol='BTC/USDT',
            asset_type='crypto',
            start_date='2024-01-01',
            end_date='2024-01-07'
        )
        assert fetcher._select_provider(request) == 'binance'

    def test_get_available_providers(self):
        """Test getting available providers info."""
        fetcher = DataFetcher()
        providers_info = fetcher.get_available_providers()

        assert 'yfinance' in providers_info
        assert 'is_connected' in providers_info['yfinance']
        assert 'supports_options' in providers_info['yfinance']

    def test_validate_all_providers(self):
        """Test validating all providers."""
        fetcher = DataFetcher()
        status = fetcher.validate_all_providers()

        assert isinstance(status, dict)
        assert 'yfinance' in status
        assert isinstance(status['yfinance'], bool)

    def test_fetch_data_provider_not_found(self):
        """Test fetching data with non-existent provider."""
        fetcher = DataFetcher()
        request = DataRequest(
            symbol='AAPL',
            asset_type='stock',
            start_date='2024-01-01',
            end_date='2024-01-07',
            provider='nonexistent'
        )

        response = fetcher.fetch_data(request)

        assert response.success is False
        assert 'not available' in response.error

    @patch('wrdata.services.data_fetcher.YFinanceProvider')
    def test_fetch_data_success(self, mock_provider_class):
        """Test successful data fetching."""
        # Setup mock
        mock_provider = Mock()
        mock_response = DataResponse(
            symbol='AAPL',
            provider='yfinance',
            data=[{'close': 150.0}],
            success=True
        )
        mock_provider.fetch_timeseries.return_value = mock_response
        mock_provider_class.return_value = mock_provider

        # Create fetcher and replace provider
        fetcher = DataFetcher()
        fetcher.providers['yfinance'] = mock_provider

        request = DataRequest(
            symbol='AAPL',
            asset_type='stock',
            start_date='2024-01-01',
            end_date='2024-01-07'
        )

        response = fetcher.fetch_data(request)

        assert response.success is True
        assert len(response.data) == 1
        mock_provider.fetch_timeseries.assert_called_once()

    def test_fetch_multiple(self):
        """Test fetching data for multiple symbols."""
        fetcher = DataFetcher()

        # Mock the providers
        mock_provider = Mock()
        mock_provider.fetch_timeseries.return_value = DataResponse(
            symbol='TEST',
            provider='yfinance',
            data=[],
            success=True
        )
        fetcher.providers['yfinance'] = mock_provider

        requests = [
            DataRequest(
                symbol='AAPL',
                asset_type='stock',
                start_date='2024-01-01',
                end_date='2024-01-07'
            ),
            DataRequest(
                symbol='MSFT',
                asset_type='stock',
                start_date='2024-01-01',
                end_date='2024-01-07'
            ),
        ]

        responses = fetcher.fetch_multiple(requests)

        assert len(responses) == 2
        assert all(isinstance(r, DataResponse) for r in responses)
