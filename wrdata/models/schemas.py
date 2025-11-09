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
