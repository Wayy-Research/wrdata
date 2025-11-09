"""
Integration tests for YFinance provider.

These tests make real API calls and are marked with @pytest.mark.integration.
Run with: pytest -m integration
"""

import pytest
from datetime import datetime, timedelta

from wrdata.providers.yfinance_provider import YFinanceProvider
from wrdata.models.schemas import OptionsChainRequest


@pytest.mark.integration
@pytest.mark.requires_network
class TestYFinanceIntegration:
    """Integration tests for YFinance provider."""

    def test_fetch_stock_data(self, skip_if_no_network):
        """Test fetching real stock data."""
        provider = YFinanceProvider()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        response = provider.fetch_timeseries(
            symbol='AAPL',
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval='1d'
        )

        assert response.success is True
        assert len(response.data) > 0
        assert 'Open' in response.data[0]
        assert 'Close' in response.data[0]

    def test_validate_connection(self, skip_if_no_network):
        """Test validating connection to YFinance."""
        provider = YFinanceProvider()
        is_connected = provider.validate_connection()

        assert is_connected is True

    def test_get_available_expirations(self, skip_if_no_network):
        """Test getting available option expirations."""
        provider = YFinanceProvider()
        expirations = provider.get_available_expirations('AAPL')

        # AAPL should have options available
        assert len(expirations) > 0
        assert all(hasattr(exp, 'year') for exp in expirations)

    @pytest.mark.slow
    def test_fetch_options_chain(self, skip_if_no_network):
        """Test fetching real options chain data."""
        provider = YFinanceProvider()

        request = OptionsChainRequest(
            symbol='AAPL',
            expiration_date=None  # Use nearest expiration
        )

        response = provider.fetch_options_chain(request)

        if response.success:
            assert len(response.calls) > 0 or len(response.puts) > 0
            assert response.underlying_price is not None

            # Check data structure
            if response.calls:
                call = response.calls[0]
                assert call.option_type == 'call'
                assert call.strike_price is not None
                assert call.expiration_date is not None
