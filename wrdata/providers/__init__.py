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

# Options providers
try:
    from wrdata.providers.alpaca_options_provider import AlpacaOptionsProvider
except ImportError:
    AlpacaOptionsProvider = None  # type: ignore[assignment, misc]

# DeFi providers
try:
    from wrdata.providers.panoptic_provider import PanopticProvider
except ImportError:
    PanopticProvider = None  # type: ignore[assignment, misc]

# Prediction market providers
try:
    from wrdata.providers.polymarket_provider import PolymarketProvider
except ImportError:
    PolymarketProvider = None  # type: ignore[assignment, misc]

# DEX providers
try:
    from wrdata.providers.dex_arb_provider import DexArbProvider
except ImportError:
    DexArbProvider = None  # type: ignore[assignment, misc]

# Restaking providers
try:
    from wrdata.providers.symbiotic_provider import SymbioticProvider
except ImportError:
    SymbioticProvider = None  # type: ignore[assignment, misc]

__all__ = [
    "BaseProvider",
    "YFinanceProvider",
    "BinanceProvider",
    "AlpacaOptionsProvider",
    "PanopticProvider",
    "PolymarketProvider",
    "DexArbProvider",
    "SymbioticProvider",
]
