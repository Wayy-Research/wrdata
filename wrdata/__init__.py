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

__all__ = [
    "__version__",
    "DataStream",
]
