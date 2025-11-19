"""Integration tests for DataStream API."""

import pytest
from wrdata import DataStream


@pytest.fixture
def stream():
    """Create DataStream instance for testing."""
    return DataStream()


def test_datastream_initialization(stream):
    """Test that DataStream initializes correctly."""
    assert stream is not None
    assert isinstance(stream.providers, dict)
    assert len(stream.providers) > 0


def test_available_providers(stream):
    """Test that providers are available."""
    providers = list(stream.providers.keys())
    assert 'yfinance' in providers  # YFinance should always be available


def test_get_basic_data(stream):
    """Test basic data fetching."""
    df = stream.get("AAPL", start="2024-11-01", end="2024-11-07")

    assert df is not None
    assert len(df) > 0
    assert 'close' in df.columns
    assert 'timestamp' in df.columns or 'date' in df.columns


def test_provider_status(stream):
    """Test provider status check."""
    status = stream.status()

    assert isinstance(status, dict)
    assert len(status) > 0

    for provider, info in status.items():
        assert 'connected' in info
        assert isinstance(info['connected'], bool)
