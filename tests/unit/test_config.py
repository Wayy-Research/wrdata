"""
Unit tests for configuration module.
"""

import pytest
from wrdata.core.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test the Settings configuration class."""

    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        settings = Settings(_env_file=None)

        # API keys should be None by default
        assert settings.ALPHA_VANTAGE_API_KEY is None
        assert settings.BINANCE_API_KEY is None
        assert settings.COINBASE_API_KEY is None

    def test_alpaca_paper_default(self):
        """Test default Alpaca paper trading setting."""
        settings = Settings(_env_file=None)

        assert settings.ALPACA_PAPER is True

    def test_ibkr_gateway_port_default(self):
        """Test default IBKR gateway port."""
        settings = Settings(_env_file=None)

        assert settings.IBKR_GATEWAY_PORT == 4002

    def test_has_alpha_vantage_key(self):
        """Test the has_alpha_vantage_key property."""
        settings = Settings(_env_file=None, ALPHA_VANTAGE_API_KEY=None)
        assert settings.has_alpha_vantage_key is False

        settings = Settings(_env_file=None, ALPHA_VANTAGE_API_KEY='test_key')
        assert settings.has_alpha_vantage_key is True

    def test_has_binance_key(self):
        """Test the has_binance_key property."""
        settings = Settings(_env_file=None, BINANCE_API_KEY=None)
        assert settings.has_binance_key is False

        settings = Settings(
            _env_file=None,
            BINANCE_API_KEY='test_key',
            BINANCE_API_SECRET='test_secret'
        )
        assert settings.has_binance_key is True

    def test_has_whale_alert_key(self):
        """Test the has_whale_alert_key property."""
        settings = Settings(_env_file=None, WHALE_ALERT_API_KEY=None)
        assert settings.has_whale_alert_key is False

        settings = Settings(_env_file=None, WHALE_ALERT_API_KEY='test_key')
        assert settings.has_whale_alert_key is True

    def test_has_coinbase_advanced_key(self):
        """Test the has_coinbase_advanced_key property."""
        settings = Settings(_env_file=None, COINBASE_KEY=None)
        assert settings.has_coinbase_advanced_key is False

        settings = Settings(
            _env_file=None,
            COINBASE_KEY='organizations/123/apiKeys/456',
            COINBASE_PRIVATE_KEY='-----BEGIN EC PRIVATE KEY-----\ntest\n-----END EC PRIVATE KEY-----'
        )
        assert settings.has_coinbase_advanced_key is True

    def test_has_twelve_data_key(self):
        """Test the has_twelve_data_key property."""
        settings = Settings(_env_file=None, TWELVE_DATA_API_KEY=None)
        assert settings.has_twelve_data_key is False

        settings = Settings(_env_file=None, TWELVE_DATA_API_KEY='test_key')
        assert settings.has_twelve_data_key is True
