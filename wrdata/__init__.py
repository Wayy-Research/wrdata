"""
WRData - Universal Data Gathering Package

A unified interface for fetching financial and market data from multiple providers.
"""

__version__ = "0.1.0"

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
    # Database models
    "Base",
    "DataProvider",
    "Symbol",
    # Pydantic schemas
    "ProviderConfig",
    "SymbolInfo",
    "DataRequest",
    "DataResponse",
    "SymbolSearchRequest",
    "SymbolSearchResponse",
    "ProviderStatus",
]
