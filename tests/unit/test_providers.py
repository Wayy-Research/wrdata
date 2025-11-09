"""
Unit tests for data providers.
"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from wrdata.providers.yfinance_provider import YFinanceProvider
from wrdata.providers.binance_provider import BinanceProvider
from wrdata.models.schemas import (
    DataResponse,
    OptionsChainRequest,
    OptionsChainResponse,
)


@pytest.mark.unit
class TestYFinanceProvider:
    """Test YFinance provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = YFinanceProvider()

        assert provider.name == 'yfinance'
        assert provider.api_key is None

    def test_supports_historical_options(self):
        """Test that YFinance doesn't support historical options."""
        provider = YFinanceProvider()

        assert provider.supports_historical_options() is False

    @patch('wrdata.providers.yfinance_provider.yf.Ticker')
    def test_validate_connection_success(self, mock_ticker):
        """Test successful connection validation."""
        mock_ticker.return_value.info = {'symbol': 'AAPL', 'price': 150}

        provider = YFinanceProvider()
        result = provider.validate_connection()

        assert result is True
        mock_ticker.assert_called_once_with('AAPL')

    @patch('wrdata.providers.yfinance_provider.yf.Ticker')
    def test_validate_connection_failure(self, mock_ticker):
        """Test failed connection validation."""
        mock_ticker.side_effect = Exception("Network error")

        provider = YFinanceProvider()
        result = provider.validate_connection()

        assert result is False

    @patch('wrdata.providers.yfinance_provider.yf.Ticker')
    def test_get_available_expirations(self, mock_ticker):
        """Test getting available expiration dates."""
        mock_ticker.return_value.options = ['2024-01-19', '2024-02-16']

        provider = YFinanceProvider()
        expirations = provider.get_available_expirations('AAPL')

        assert len(expirations) == 2
        assert isinstance(expirations[0], date)
        assert expirations[0] == date(2024, 1, 19)

    @patch('wrdata.providers.yfinance_provider.yf.Ticker')
    def test_fetch_timeseries_empty_data(self, mock_ticker):
        """Test fetching timeseries with no data."""
        import pandas as pd
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        provider = YFinanceProvider()
        response = provider.fetch_timeseries(
            symbol='INVALID',
            start_date='2024-01-01',
            end_date='2024-01-07',
            interval='1d'
        )

        assert response.success is False
        assert 'No data found' in response.error


@pytest.mark.unit
class TestBinanceProvider:
    """Test Binance provider."""

    def test_initialization_without_keys(self):
        """Test provider initialization without API keys."""
        provider = BinanceProvider()

        assert provider.name == 'binance'
        assert provider.api_key is None
        assert provider.exchange is not None

    def test_initialization_with_keys(self):
        """Test provider initialization with API keys."""
        provider = BinanceProvider(
            api_key='test_key',
            api_secret='test_secret'
        )

        assert provider.api_key == 'test_key'
        assert provider.api_secret == 'test_secret'

    def test_supports_historical_options(self):
        """Test that Binance doesn't support options."""
        provider = BinanceProvider()

        assert provider.supports_historical_options() is False

    def test_get_available_expirations(self):
        """Test that Binance returns empty expirations list."""
        provider = BinanceProvider()
        expirations = provider.get_available_expirations('BTC/USDT')

        assert expirations == []

    def test_fetch_options_chain_raises_error(self):
        """Test that fetching options chain raises NotImplementedError."""
        provider = BinanceProvider()

        with pytest.raises(NotImplementedError) as exc_info:
            provider.fetch_options_chain(
                OptionsChainRequest(symbol='BTC/USDT')
            )

        assert 'does not support options' in str(exc_info.value)

    def test_fetch_timeseries_network_error(self):
        """Test network error handling in fetch_timeseries."""
        import ccxt

        provider = BinanceProvider()

        # Mock the exchange to raise NetworkError
        mock_exchange = Mock()
        mock_exchange.options = {}
        mock_exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("Connection failed")
        provider.exchange = mock_exchange

        response = provider.fetch_timeseries(
            symbol='BTC/USDT',
            start_date='2024-01-01',
            end_date='2024-01-07',
            interval='1d'
        )

        assert response.success is False
        assert 'Network error' in response.error

    def test_get_supported_symbols(self):
        """Test getting supported symbols."""
        provider = BinanceProvider()

        # Mock the exchange markets
        provider.exchange.load_markets = Mock(return_value={
            'BTC/USDT': {},
            'ETH/USDT': {},
        })

        symbols = provider.get_supported_symbols()

        assert 'BTC/USDT' in symbols
        assert 'ETH/USDT' in symbols
