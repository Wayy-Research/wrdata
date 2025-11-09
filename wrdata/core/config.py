"""
Configuration management for wrdata package.

Uses pydantic-settings to load and validate configuration from environment variables.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden by setting environment variables.
    Settings are loaded from .env file if present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    DATABASE_URL: str = Field(
        default="postgresql://wrdata_user:wrdata_dev_password@localhost:5432/wrdata",
        description="PostgreSQL database URL"
    )

    # ============================================================================
    # REDIS CONFIGURATION
    # ============================================================================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # ============================================================================
    # APPLICATION SETTINGS
    # ============================================================================
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )

    # API Server
    API_HOST: str = Field(default="0.0.0.0", description="API server host")
    API_PORT: int = Field(default=8000, description="API server port")
    API_WORKERS: int = Field(default=4, description="Number of API workers")

    # ============================================================================
    # DATA PROVIDER API KEYS - FREE TIER
    # ============================================================================
    ALPHA_VANTAGE_API_KEY: Optional[str] = Field(
        default=None,
        description="Alpha Vantage API key (Free: 5 calls/min)"
    )

    TWELVE_DATA_API_KEY: Optional[str] = Field(
        default=None,
        description="Twelve Data API key (Free: 8 calls/min)"
    )

    COINGECKO_API_KEY: Optional[str] = Field(
        default=None,
        description="CoinGecko API key (Optional for free tier)"
    )

    FRED_API_KEY: Optional[str] = Field(
        default=None,
        description="FRED (Federal Reserve) API key"
    )

    # ============================================================================
    # STOCK MARKET DATA FEEDS
    # ============================================================================
    FINNHUB_API_KEY: Optional[str] = Field(
        default=None,
        description="Finnhub API key (Free tier: 60 calls/min + WebSocket streaming!)"
    )

    # ============================================================================
    # DATA PROVIDER API KEYS - PRO TIER (PAID)
    # ============================================================================
    POLYGON_API_KEY: Optional[str] = Field(
        default=None,
        description="Polygon.io API key (Paid)"
    )

    TIINGO_API_KEY: Optional[str] = Field(
        default=None,
        description="Tiingo API key"
    )

    # ============================================================================
    # BROKER API KEYS (DATA + TRADING)
    # ============================================================================
    ALPACA_API_KEY: Optional[str] = Field(
        default=None,
        description="Alpaca API key (Free: Real-time IEX data + paper trading)"
    )

    ALPACA_API_SECRET: Optional[str] = Field(
        default=None,
        description="Alpaca API secret"
    )

    ALPACA_PAPER: bool = Field(
        default=True,
        description="Use Alpaca paper trading (True) or live trading (False)"
    )

    IBKR_USERNAME: Optional[str] = Field(
        default=None,
        description="Interactive Brokers username"
    )

    IBKR_PASSWORD: Optional[str] = Field(
        default=None,
        description="Interactive Brokers password"
    )

    IBKR_ACCOUNT: Optional[str] = Field(
        default=None,
        description="Interactive Brokers account ID"
    )

    IBKR_GATEWAY_PORT: int = Field(
        default=4002,
        description="Interactive Brokers gateway port"
    )

    TD_AMERITRADE_API_KEY: Optional[str] = Field(
        default=None,
        description="TD Ameritrade API key"
    )

    TD_AMERITRADE_REDIRECT_URI: Optional[str] = Field(
        default=None,
        description="TD Ameritrade OAuth redirect URI"
    )

    TD_AMERITRADE_ACCOUNT_ID: Optional[str] = Field(
        default=None,
        description="TD Ameritrade account ID"
    )

    # ============================================================================
    # CRYPTO EXCHANGE API KEYS (OPTIONAL - HIGHER RATE LIMITS)
    # ============================================================================
    BINANCE_API_KEY: Optional[str] = Field(
        default=None,
        description="Binance API key (optional, increases rate limits)"
    )

    BINANCE_API_SECRET: Optional[str] = Field(
        default=None,
        description="Binance API secret"
    )

    COINBASE_API_KEY: Optional[str] = Field(
        default=None,
        description="Coinbase Pro API key"
    )

    COINBASE_API_SECRET: Optional[str] = Field(
        default=None,
        description="Coinbase Pro API secret"
    )

    COINBASE_PASSPHRASE: Optional[str] = Field(
        default=None,
        description="Coinbase Pro API passphrase"
    )

    KRAKEN_API_KEY: Optional[str] = Field(
        default=None,
        description="Kraken API key (optional, increases rate limits)"
    )

    KRAKEN_API_SECRET: Optional[str] = Field(
        default=None,
        description="Kraken API secret"
    )

    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enable rate limiting"
    )

    RATE_LIMIT_PER_MINUTE: int = Field(
        default=100,
        description="Requests per minute per API key"
    )

    RATE_LIMIT_BURST: int = Field(
        default=20,
        description="Burst allowance for rate limiting"
    )

    # ============================================================================
    # CACHING
    # ============================================================================
    CACHE_ENABLED: bool = Field(default=True, description="Enable caching")
    CACHE_TTL: int = Field(
        default=300,
        description="Cache time-to-live in seconds"
    )
    CACHE_MAX_SIZE: int = Field(
        default=1000,
        description="Maximum number of cached items"
    )

    # ============================================================================
    # SECURITY
    # ============================================================================
    SECRET_KEY: str = Field(
        default="change-this-to-a-random-secret-key-in-production",
        description="Application secret key"
    )

    JWT_SECRET_KEY: str = Field(
        default="change-this-to-a-different-random-secret-key",
        description="JWT signing secret key"
    )

    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm"
    )

    JWT_EXPIRATION_HOURS: int = Field(
        default=24,
        description="JWT token expiration in hours"
    )

    ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        description="Fernet encryption key for storing API keys"
    )

    # ============================================================================
    # MONITORING & LOGGING
    # ============================================================================
    SENTRY_DSN: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )

    METRICS_ENABLED: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )

    METRICS_PORT: int = Field(
        default=9090,
        description="Prometheus metrics port"
    )

    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    ENABLE_OPTIONS_CHAIN: bool = Field(
        default=True,
        description="Enable options chain functionality"
    )

    ENABLE_TICK_DATA: bool = Field(
        default=False,
        description="Enable tick data (coming soon)"
    )

    ENABLE_WEBSOCKETS: bool = Field(
        default=False,
        description="Enable WebSocket streaming (coming soon)"
    )

    ENABLE_ORDER_BOOK: bool = Field(
        default=False,
        description="Enable order book data (coming soon)"
    )

    # ============================================================================
    # TIER CONFIGURATION
    # ============================================================================
    DEFAULT_TIER: str = Field(
        default="free",
        description="Default tier: free, pro, enterprise"
    )

    FREE_TIER_RATE_LIMIT: int = Field(
        default=100,
        description="Free tier rate limit (requests/min)"
    )

    PRO_TIER_RATE_LIMIT: int = Field(
        default=1000,
        description="Pro tier rate limit (requests/min)"
    )

    ENTERPRISE_TIER_RATE_LIMIT: int = Field(
        default=10000,
        description="Enterprise tier rate limit (requests/min)"
    )

    # ============================================================================
    # DATA RETENTION
    # ============================================================================
    OHLCV_RETENTION_DAYS: int = Field(
        default=365,
        description="OHLCV data retention in days"
    )

    TICK_RETENTION_DAYS: int = Field(
        default=90,
        description="Tick data retention in days"
    )

    OPTIONS_RETENTION_DAYS: int = Field(
        default=180,
        description="Options data retention in days"
    )

    # ============================================================================
    # DEVELOPMENT TOOLS
    # ============================================================================
    PGADMIN_EMAIL: str = Field(
        default="admin@wrdata.local",
        description="PgAdmin login email"
    )

    PGADMIN_PASSWORD: str = Field(
        default="admin",
        description="PgAdmin login password"
    )

    GRAFANA_ADMIN_PASSWORD: str = Field(
        default="admin",
        description="Grafana admin password"
    )

    # Helper properties
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def has_alpha_vantage_key(self) -> bool:
        """Check if Alpha Vantage API key is configured."""
        return self.ALPHA_VANTAGE_API_KEY is not None and len(self.ALPHA_VANTAGE_API_KEY) > 0

    @property
    def has_twelve_data_key(self) -> bool:
        """Check if Twelve Data API key is configured."""
        return self.TWELVE_DATA_API_KEY is not None and len(self.TWELVE_DATA_API_KEY) > 0

    @property
    def has_binance_key(self) -> bool:
        """Check if Binance API key is configured."""
        return (
            self.BINANCE_API_KEY is not None
            and self.BINANCE_API_SECRET is not None
            and len(self.BINANCE_API_KEY) > 0
        )


# Global settings instance
settings = Settings()
