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
        settings = Settings()

        assert settings.ENVIRONMENT == 'development'
        assert settings.API_PORT == 8000
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == 'INFO'

    def test_database_url_default(self):
        """Test default database URL."""
        settings = Settings()

        assert settings.DATABASE_URL.startswith('postgresql://')
        assert 'wrdata' in settings.DATABASE_URL

    def test_is_development_property(self):
        """Test the is_development helper property."""
        settings = Settings(_env_file=None, ENVIRONMENT='development')
        assert settings.is_development is True

        settings = Settings(_env_file=None, ENVIRONMENT='production')
        assert settings.is_development is False

    def test_is_production_property(self):
        """Test the is_production helper property."""
        settings = Settings(_env_file=None, ENVIRONMENT='production')
        assert settings.is_production is True

        settings = Settings(_env_file=None, ENVIRONMENT='development')
        assert settings.is_production is False

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

    def test_rate_limiting_defaults(self):
        """Test rate limiting default values."""
        settings = Settings()

        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_PER_MINUTE == 100
        assert settings.FREE_TIER_RATE_LIMIT == 100
        assert settings.PRO_TIER_RATE_LIMIT == 1000

    def test_feature_flags(self):
        """Test feature flag defaults."""
        settings = Settings()

        assert settings.ENABLE_OPTIONS_CHAIN is True
        assert settings.ENABLE_TICK_DATA is False
        assert settings.ENABLE_WEBSOCKETS is False
