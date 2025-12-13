"""
Configuration management for wrdata package.

API key management with multiple loading options:

1. Environment variables (highest priority)
2. Custom env file via WRDATA_ENV_FILE environment variable
3. ~/.wrdata.env (user's home directory)
4. .env in current working directory

Example usage:
    # Option 1: Set environment variable before importing
    export WRDATA_ENV_FILE=/path/to/your/.env

    # Option 2: Use ~/.wrdata.env
    cp your-credentials.env ~/.wrdata.env

    # Option 3: Load custom settings programmatically
    from wrdata.core.config import load_settings
    settings = load_settings("/path/to/your/.env")

    # Option 4: Pass credentials directly
    from wrdata.providers.coinbase_advanced_provider import CoinbaseAdvancedProvider
    provider = CoinbaseAdvancedProvider(api_key="...", api_secret="...")
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_files() -> List[Path]:
    """
    Find env files in priority order.

    Returns list of existing env file paths, highest priority first.
    """
    candidates = []

    # 1. Custom path via WRDATA_ENV_FILE environment variable
    custom_path = os.environ.get("WRDATA_ENV_FILE")
    if custom_path:
        candidates.append(Path(custom_path))

    # 2. User's home directory: ~/.wrdata.env
    home_env = Path.home() / ".wrdata.env"
    candidates.append(home_env)

    # 3. XDG config: ~/.config/wrdata/.env
    xdg_config = Path.home() / ".config" / "wrdata" / ".env"
    candidates.append(xdg_config)

    # 4. Current working directory: .env
    candidates.append(Path.cwd() / ".env")

    # Return only existing files
    return [p for p in candidates if p.exists()]


def _get_env_file() -> Optional[str]:
    """Get the first available env file path."""
    env_files = _find_env_files()
    if env_files:
        return str(env_files[0])
    return None


class Settings(BaseSettings):
    """
    Application settings for API keys.

    Credentials are loaded from (in priority order):
    1. Environment variables
    2. WRDATA_ENV_FILE path (if set)
    3. ~/.wrdata.env
    4. ~/.config/wrdata/.env
    5. .env in current directory
    """

    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
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

    # Legacy Coinbase Pro credentials (deprecated)
    COINBASE_API_KEY: Optional[str] = Field(
        default=None,
        description="Coinbase Pro API key (legacy)"
    )

    COINBASE_API_SECRET: Optional[str] = Field(
        default=None,
        description="Coinbase Pro API secret (legacy)"
    )

    COINBASE_PASSPHRASE: Optional[str] = Field(
        default=None,
        description="Coinbase Pro API passphrase (legacy)"
    )

    # Coinbase Advanced Trade API credentials (CDP keys)
    COINBASE_KEY: Optional[str] = Field(
        default=None,
        description="Coinbase CDP API key (format: organizations/{org_id}/apiKeys/{key_id})"
    )

    COINBASE_PRIVATE_KEY: Optional[str] = Field(
        default=None,
        description="Coinbase CDP private key (EC PEM format)"
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
    # WHALE TRACKING
    # ============================================================================
    WHALE_ALERT_API_KEY: Optional[str] = Field(
        default=None,
        description="Whale Alert API key (Paid: ~$30/mo for whale transaction tracking)"
    )

    # ============================================================================
    # PREDICTION MARKETS
    # ============================================================================
    KALSHI_KEY: Optional[str] = Field(
        default=None,
        description="Kalshi API key ID"
    )

    KALSHI_PRIVATE_KEY: Optional[str] = Field(
        default=None,
        description="Kalshi RSA private key (PEM format)"
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

    @property
    def has_whale_alert_key(self) -> bool:
        """Check if Whale Alert API key is configured."""
        return self.WHALE_ALERT_API_KEY is not None and len(self.WHALE_ALERT_API_KEY) > 0

    @property
    def has_coinbase_advanced_key(self) -> bool:
        """Check if Coinbase Advanced Trade API credentials are configured."""
        return (
            self.COINBASE_KEY is not None
            and self.COINBASE_PRIVATE_KEY is not None
            and len(self.COINBASE_KEY) > 0
            and len(self.COINBASE_PRIVATE_KEY) > 0
        )


def load_settings(env_file: Optional[str] = None) -> Settings:
    """
    Load settings from a specific env file.

    Args:
        env_file: Path to env file. If None, uses default search order.

    Returns:
        Settings instance with loaded credentials.

    Example:
        settings = load_settings("/home/user/.env.fin")
        provider = CoinbaseAdvancedProvider(
            api_key=settings.COINBASE_KEY,
            api_secret=settings.COINBASE_PRIVATE_KEY
        )
    """
    if env_file:
        # Create settings with specific env file
        return Settings(_env_file=env_file)
    return Settings()


def get_env_file_location() -> Optional[str]:
    """
    Get the path of the env file currently being used.

    Returns:
        Path to env file, or None if no env file found.
    """
    return _get_env_file()


# Global settings instance
settings = Settings()
