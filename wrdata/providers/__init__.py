"""
Data providers for wrdata package.

Providers are imported lazily to avoid dependency issues.
Only import what you need.
"""

from wrdata.providers.base import BaseProvider
from wrdata.providers.yfinance_provider import YFinanceProvider
from wrdata.providers.binance_provider import BinanceProvider

# Other providers can be imported when needed
# from wrdata.providers.ibkr_provider import IBKRProvider
# from wrdata.providers.alpaca_provider import AlpacaProvider
# etc.

__all__ = [
    "BaseProvider",
    "YFinanceProvider",
    "BinanceProvider",
]
