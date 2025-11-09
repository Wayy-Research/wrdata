"""
Pytest configuration and fixtures for wrdata tests.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from wrdata.models.database import Base, DataProvider, Symbol
from wrdata.core.config import settings


@pytest.fixture
def test_db_engine():
    """Create a test database engine (in-memory SQLite)."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def test_db_session(test_db_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    # Seed with test data providers
    providers = [
        DataProvider(
            name='yfinance',
            provider_type='yfinance',
            api_key_required=False,
            has_api_key=False,
            is_active=True,
        ),
        DataProvider(
            name='binance',
            provider_type='binance',
            api_key_required=False,
            has_api_key=False,
            is_active=True,
        ),
    ]
    for provider in providers:
        session.add(provider)

    session.commit()

    yield session

    session.close()


@pytest.fixture
def sample_symbol(test_db_session):
    """Create a sample symbol for testing."""
    provider = test_db_session.query(DataProvider).filter_by(name='yfinance').first()

    symbol = Symbol(
        provider_id=provider.id,
        symbol='AAPL',
        name='Apple Inc.',
        description='Apple Inc. - NASDAQ',
        asset_type='stock',
        exchange='NASDAQ',
    )

    test_db_session.add(symbol)
    test_db_session.commit()

    return symbol


@pytest.fixture
def date_range():
    """Provide a common date range for testing."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    return {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }


@pytest.fixture
def mock_ohlcv_data():
    """Provide mock OHLCV data for testing."""
    return [
        {
            'timestamp': '2024-01-01T00:00:00',
            'open': 100.0,
            'high': 105.0,
            'low': 99.0,
            'close': 103.0,
            'volume': 1000000,
        },
        {
            'timestamp': '2024-01-02T00:00:00',
            'open': 103.0,
            'high': 108.0,
            'low': 102.0,
            'close': 107.0,
            'volume': 1200000,
        },
    ]


@pytest.fixture
def skip_if_no_network():
    """Skip test if network is not available."""
    pytest.importorskip("requests")

    import requests
    try:
        requests.get("https://www.google.com", timeout=3)
    except requests.exceptions.RequestException:
        pytest.skip("Network not available")
