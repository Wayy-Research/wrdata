"""
WRData - Universal Data Gathering Package

A unified interface for fetching financial and market data from multiple providers.

Quick Start:
    >>> from wrdata import DataStream
    >>> stream = DataStream()
    >>> df = stream.get("AAPL", start="2024-01-01", end="2024-12-31")
    >>> print(df.head())
"""

__version__ = "0.1.0"

# Main API - this is what users should use
from .stream import DataStream

# Legacy/advanced imports (for backwards compatibility)
from .models import (
    Base,
    DataProvider,
    Symbol,
    ProviderConfig,
    SymbolInfo,
    DataRequest,
    DataResponse,
    SymbolSearchRequest,
    SymbolSearchResponse,
    ProviderStatus,
)

__all__ = [
    "__version__",
    # Main API
    "DataStream",
    # Database models (legacy)
    "Base",
    "DataProvider",
    "Symbol",
    # Pydantic schemas (advanced use)
    "ProviderConfig",
    "SymbolInfo",
    "DataRequest",
    "DataResponse",
    "SymbolSearchRequest",
    "SymbolSearchResponse",
    "ProviderStatus",
]
