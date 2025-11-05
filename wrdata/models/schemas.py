"""
Pydantic models for wrdata package.
"""

from datetime import datetime
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
