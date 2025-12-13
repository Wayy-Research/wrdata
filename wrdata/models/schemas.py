"""
Pydantic models for wrdata package.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ProviderConfig(BaseModel):
    """Configuration for a data provider."""
    name: str
    provider_type: str
    api_key_required: bool = False
    supported_assets: List[str] = []
    base_url: Optional[str] = None
    rate_limit: Optional[int] = None  # requests per minute

    model_config = ConfigDict(from_attributes=True)


class SymbolInfo(BaseModel):
    """Information about a symbol."""
    symbol: str
    name: Optional[str] = None
    description: Optional[str] = None
    asset_type: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    provider_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DataRequest(BaseModel):
    """Request for fetching time series data."""
    symbol: str
    asset_type: str = "equity"  # stock, crypto, forex, economic, bond, commodity
    start_date: str
    end_date: str
    interval: str = "1d"  # 1m, 5m, 15m, 1h, 1d, 1wk, 1mo
    provider: Optional[str] = None  # Optional specific provider


class DataResponse(BaseModel):
    """Response containing time series data."""
    symbol: str
    provider: str
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}
    success: bool = True
    error: Optional[str] = None


class SymbolSearchRequest(BaseModel):
    """Request for searching symbols."""
    query: str
    asset_type: Optional[str] = None
    exchange: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class SymbolSearchResponse(BaseModel):
    """Response from symbol search."""
    query: str
    count: int
    results: List[SymbolInfo]


class ProviderStatus(BaseModel):
    """Status of a data provider."""
    name: str
    is_active: bool
    has_api_key: bool
    api_key_required: bool
    supported_assets: List[str]
    symbol_count: int = 0
    last_sync: Optional[datetime] = None


# Options Chain Schemas

class OptionsContractInfo(BaseModel):
    """Information about a specific options contract."""
    contract_symbol: str
    underlying_symbol: str
    option_type: str  # "call" or "put"
    strike_price: Decimal
    expiration_date: date
    exchange: Optional[str] = None
    contract_size: int = 100
    currency: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OptionsGreeks(BaseModel):
    """Greeks for an options contract."""
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None


class OptionsChainData(BaseModel):
    """Complete options chain data for a specific contract at a point in time."""
    contract_symbol: str
    option_type: str
    strike_price: Decimal
    expiration_date: date

    # Price data
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    last_price: Optional[Decimal] = None
    mark_price: Optional[Decimal] = None

    # Volume and interest
    volume: Optional[int] = None
    open_interest: Optional[int] = None

    # Greeks
    greeks: Optional[OptionsGreeks] = None

    # Volatility
    implied_volatility: Optional[float] = None

    # Additional metrics
    intrinsic_value: Optional[Decimal] = None
    extrinsic_value: Optional[Decimal] = None
    in_the_money: Optional[bool] = None

    # Underlying price at this snapshot
    underlying_price: Optional[Decimal] = None


class OptionsChainRequest(BaseModel):
    """Request for fetching options chain data."""
    symbol: str
    expiration_date: Optional[date] = None  # If None, fetch all available expirations
    start_date: Optional[str] = None  # For historical timeseries
    end_date: Optional[str] = None
    provider: Optional[str] = None  # Optional specific provider

    # Filters
    option_type: Optional[str] = None  # "call", "put", or None for both
    min_strike: Optional[Decimal] = None
    max_strike: Optional[Decimal] = None


class OptionsChainResponse(BaseModel):
    """Response containing options chain data."""
    symbol: str
    provider: str
    snapshot_timestamp: datetime
    underlying_price: Optional[Decimal] = None

    # Separate calls and puts
    calls: List[OptionsChainData] = []
    puts: List[OptionsChainData] = []

    # Available expiration dates
    available_expirations: List[date] = []

    metadata: Dict[str, Any] = {}
    success: bool = True
    error: Optional[str] = None


class OptionsTimeseriesRequest(BaseModel):
    """Request for historical timeseries of options chain data."""
    contract_symbol: Optional[str] = None  # Specific contract
    underlying_symbol: Optional[str] = None  # Or get all contracts for underlying
    expiration_date: Optional[date] = None
    strike_price: Optional[Decimal] = None
    option_type: Optional[str] = None  # "call" or "put"

    start_date: str
    end_date: str
    interval: str = "1d"  # How often snapshots were taken
    provider: Optional[str] = None


class OptionsTimeseriesResponse(BaseModel):
    """Response containing historical timeseries of options data."""
    symbol: str
    provider: str
    data: List[Dict[str, Any]]  # List of snapshots over time
    metadata: Dict[str, Any] = {}
    success: bool = True
    error: Optional[str] = None


# Whale Transaction Schemas

class WhaleTransaction(BaseModel):
    """
    Whale transaction data model for large volume cryptocurrency transactions.

    Represents a single large transaction detected based on percentile thresholds
    or absolute volume/value criteria.
    """
    # Core identification
    symbol: str
    timestamp: datetime
    exchange: Optional[str] = None
    transaction_id: Optional[str] = None  # Exchange-specific trade ID

    # Transaction details
    size: Decimal  # Volume/quantity of the transaction
    price: Decimal  # Price at which transaction occurred
    usd_value: Optional[Decimal] = None  # USD equivalent value

    # Whale classification metrics
    percentile: Optional[float] = None  # Volume percentile (0-100)
    volume_rank: Optional[int] = None  # Rank among recent transactions

    # Transaction context
    transaction_type: str = "trade"  # "trade", "transfer", "deposit", "withdrawal"
    side: Optional[str] = None  # "buy", "sell", "unknown"
    is_maker: Optional[bool] = None  # True if maker order, False if taker

    # Blockchain-specific (for on-chain transactions)
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    blockchain: Optional[str] = None  # "bitcoin", "ethereum", etc.
    tx_hash: Optional[str] = None

    # Provider metadata
    provider: str
    raw_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serialized decimals."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'exchange': self.exchange,
            'transaction_id': self.transaction_id,
            'size': float(self.size) if self.size else None,
            'price': float(self.price) if self.price else None,
            'usd_value': float(self.usd_value) if self.usd_value else None,
            'percentile': self.percentile,
            'volume_rank': self.volume_rank,
            'transaction_type': self.transaction_type,
            'side': self.side,
            'is_maker': self.is_maker,
            'from_address': self.from_address,
            'to_address': self.to_address,
            'blockchain': self.blockchain,
            'tx_hash': self.tx_hash,
            'provider': self.provider,
        }


class WhaleAlert(BaseModel):
    """
    Alert configuration for whale transaction monitoring.

    Defines thresholds and filters for whale detection.
    """
    # Volume thresholds
    percentile_threshold: float = Field(default=99.0, ge=0, le=100)  # Top 1% by default
    min_usd_value: Optional[Decimal] = None  # Absolute minimum USD value

    # Filters
    symbols: Optional[List[str]] = None  # Specific symbols to monitor
    exchanges: Optional[List[str]] = None  # Specific exchanges
    blockchains: Optional[List[str]] = None  # Specific blockchains
    transaction_types: List[str] = ["trade", "transfer", "deposit", "withdrawal"]

    # Alert settings
    alert_name: Optional[str] = None
    enabled: bool = True

    model_config = ConfigDict(from_attributes=True)


class WhaleTransactionBatch(BaseModel):
    """Batch of whale transactions with metadata."""
    transactions: List[WhaleTransaction]
    count: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    filters_applied: Dict[str, Any] = {}
    provider: str

    model_config = ConfigDict(from_attributes=True)
