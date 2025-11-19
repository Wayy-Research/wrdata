"""
Configuration management for wrdata package.

Simple API key management - load from environment variables or .env file.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings for API keys.

    All settings can be set via environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================================================
    # FREE TIER DATA PROVIDERS
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
        description="CoinGecko API key (Optional - free tier available)"
    )

    FRED_API_KEY: Optional[str] = Field(
        default=None,
        description="FRED (Federal Reserve) API key"
    )

    FINNHUB_API_KEY: Optional[str] = Field(
        default=None,
        description="Finnhub API key (Free tier: 60 calls/min + WebSocket)"
    )

    TIINGO_API_KEY: Optional[str] = Field(
        default=None,
        description="Tiingo API key"
    )

    # ============================================================================
    # PREMIUM DATA PROVIDERS
    # ============================================================================
    POLYGON_API_KEY: Optional[str] = Field(
        default=None,
        description="Polygon.io API key (Paid)"
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
        description="Interactive Brokers gateway port (4002=paper, 4001=live)"
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

    # Helper properties
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
