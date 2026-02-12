"""
WRData - Universal Data Gathering Package

A unified interface for fetching financial and market data from multiple providers.

Quick Start:
    >>> from wrdata import DataStream
    >>> stream = DataStream()
    >>> df = stream.get("AAPL", start="2024-01-01", end="2024-12-31")
    >>> print(df.head())
"""

__version__ = "0.1.6"

# Main API - this is what users should use
from .stream import DataStream
from .symbol_ops import (
    search_async,
    validate_async,
    resolve_async,
    get_metadata_async,
    get_economic_calendar_async,
)

__all__ = [
    "__version__",
    "DataStream",
    "search_async",
    "validate_async",
    "resolve_async",
    "get_metadata_async",
    "get_economic_calendar_async",
]
