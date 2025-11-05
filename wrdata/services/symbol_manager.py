"""
Service for fetching and synchronizing symbols from data providers.

This is the core symbol management service for wrdata package.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import DataProvider, Symbol


class SymbolManager:
    """Service for synchronizing symbols from data providers."""

    def __init__(self, db: Session):
        self.db = db

    def fetch_yfinance_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Fetch symbols from Yahoo Finance using NASDAQ and NYSE screener.
        Note: YFinance doesn't have an official API, so we fetch from screener CSV.

        Returns:
            List of symbol dictionaries
        """
        try:
            import requests
            import pandas as pd
            from io import StringIO

            symbols = []

            # Fetch NASDAQ stocks
            try:
                nasdaq_url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&exchange=nasdaq"
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(nasdaq_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    for row in data.get('data', {}).get('table', {}).get('rows', []):
                        symbols.append({
                            "symbol": row['symbol'],
                            "name": row.get('name', ''),
                            "description": f"{row.get('name', '')} - NASDAQ",
                            "asset_type": "stock",
                            "exchange": "NASDAQ",
                        })
                    print(f"Fetched {len(symbols)} NASDAQ symbols")
            except Exception as e:
                print(f"Error fetching NASDAQ symbols: {e}")

            # Fetch NYSE stocks
            try:
                nyse_url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&exchange=nyse"
                response = requests.get(nyse_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    nyse_count = 0
                    for row in data.get('data', {}).get('table', {}).get('rows', []):
                        symbols.append({
                            "symbol": row['symbol'],
                            "name": row.get('name', ''),
                            "description": f"{row.get('name', '')} - NYSE",
                            "asset_type": "stock",
                            "exchange": "NYSE",
                        })
                        nyse_count += 1
                    print(f"Fetched {nyse_count} NYSE symbols")
            except Exception as e:
                print(f"Error fetching NYSE symbols: {e}")

            # Add major indices
            indices = [
                {"symbol": "^GSPC", "name": "S&P 500", "description": "S&P 500 Index", "asset_type": "index", "exchange": "INDEX"},
                {"symbol": "^DJI", "name": "Dow Jones", "description": "Dow Jones Industrial Average", "asset_type": "index", "exchange": "INDEX"},
                {"symbol": "^IXIC", "name": "NASDAQ Composite", "description": "NASDAQ Composite Index", "asset_type": "index", "exchange": "INDEX"},
                {"symbol": "^RUT", "name": "Russell 2000", "description": "Russell 2000 Index", "asset_type": "index", "exchange": "INDEX"},
            ]
            symbols.extend(indices)

            return symbols

        except Exception as e:
            print(f"Error in fetch_yfinance_symbols: {e}")
            return []

    def fetch_binance_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Fetch trading pairs from Binance.

        Returns:
            List of symbol dictionaries
        """
        try:
            import requests

            response = requests.get(
                "https://api.binance.com/api/v3/exchangeInfo", timeout=10
            )
            response.raise_for_status()
            data = response.json()

            symbols = []
            for symbol_info in data.get("symbols", []):
                if symbol_info["status"] == "TRADING":
                    symbols.append(
                        {
                            "symbol": symbol_info["symbol"],
                            "name": f"{symbol_info['baseAsset']}/{symbol_info['quoteAsset']}",
                            "description": f"Binance {symbol_info['baseAsset']}/{symbol_info['quoteAsset']} trading pair",
                            "asset_type": "crypto",
                            "exchange": "Binance",
                            "extra_metadata": json.dumps(
                                {
                                    "baseAsset": symbol_info["baseAsset"],
                                    "quoteAsset": symbol_info["quoteAsset"],
                                }
                            ),
                        }
                    )

            return symbols  # Return all trading pairs

        except Exception as e:
            print(f"Error fetching Binance symbols: {e}")
            return []

    def fetch_coingecko_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Fetch cryptocurrency list from CoinGecko.

        Returns:
            List of symbol dictionaries
        """
        try:
            import requests

            response = requests.get(
                "https://api.coingecko.com/api/v3/coins/list", timeout=10
            )
            response.raise_for_status()
            data = response.json()

            symbols = []
            seen_symbols = set()  # Track duplicates
            for coin in data:  # Get all coins
                symbol_key = coin["symbol"].upper()

                # Skip if we've already seen this symbol
                if symbol_key in seen_symbols:
                    continue

                seen_symbols.add(symbol_key)
                symbols.append(
                    {
                        "symbol": symbol_key,
                        "name": coin["name"],
                        "description": f"{coin['name']} ({symbol_key}) cryptocurrency",
                        "asset_type": "crypto",
                        "exchange": "CoinGecko",
                        "extra_metadata": json.dumps({"coingecko_id": coin["id"]}),
                    }
                )

            return symbols

        except Exception as e:
            print(f"Error fetching CoinGecko symbols: {e}")
            return []

    def fetch_common_forex_pairs(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Return common forex trading pairs.

        Returns:
            List of symbol dictionaries
        """
        common_pairs = [
            # Major pairs
            {"symbol": "EUR/USD", "name": "Euro / US Dollar", "description": "EUR/USD - Euro to US Dollar", "asset_type": "forex"},
            {"symbol": "GBP/USD", "name": "British Pound / US Dollar", "description": "GBP/USD - British Pound to US Dollar", "asset_type": "forex"},
            {"symbol": "USD/JPY", "name": "US Dollar / Japanese Yen", "description": "USD/JPY - US Dollar to Japanese Yen", "asset_type": "forex"},
            {"symbol": "USD/CHF", "name": "US Dollar / Swiss Franc", "description": "USD/CHF - US Dollar to Swiss Franc", "asset_type": "forex"},
            {"symbol": "AUD/USD", "name": "Australian Dollar / US Dollar", "description": "AUD/USD - Australian Dollar to US Dollar", "asset_type": "forex"},
            {"symbol": "USD/CAD", "name": "US Dollar / Canadian Dollar", "description": "USD/CAD - US Dollar to Canadian Dollar", "asset_type": "forex"},
            {"symbol": "NZD/USD", "name": "New Zealand Dollar / US Dollar", "description": "NZD/USD - New Zealand Dollar to US Dollar", "asset_type": "forex"},
            # Cross pairs
            {"symbol": "EUR/GBP", "name": "Euro / British Pound", "description": "EUR/GBP - Euro to British Pound", "asset_type": "forex"},
            {"symbol": "EUR/JPY", "name": "Euro / Japanese Yen", "description": "EUR/JPY - Euro to Japanese Yen", "asset_type": "forex"},
            {"symbol": "GBP/JPY", "name": "British Pound / Japanese Yen", "description": "GBP/JPY - British Pound to Japanese Yen", "asset_type": "forex"},
        ]

        return common_pairs

    def fetch_us_treasury_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Return US Treasury bond symbols.

        Returns:
            List of symbol dictionaries
        """
        treasury_symbols = [
            {"symbol": "DGS1MO", "name": "1-Month Treasury", "description": "1-Month Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS3MO", "name": "3-Month Treasury", "description": "3-Month Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS6MO", "name": "6-Month Treasury", "description": "6-Month Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS1", "name": "1-Year Treasury", "description": "1-Year Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS2", "name": "2-Year Treasury", "description": "2-Year Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS5", "name": "5-Year Treasury", "description": "5-Year Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS10", "name": "10-Year Treasury", "description": "10-Year Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS20", "name": "20-Year Treasury", "description": "20-Year Treasury Constant Maturity Rate", "asset_type": "bond"},
            {"symbol": "DGS30", "name": "30-Year Treasury", "description": "30-Year Treasury Constant Maturity Rate", "asset_type": "bond"},
        ]

        return treasury_symbols

    def fetch_fred_indicators(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Return comprehensive FRED economic indicators across multiple categories.

        Returns:
            List of symbol dictionaries
        """
        indicators = [
            # GDP & Economic Output
            {"symbol": "GDP", "name": "Gross Domestic Product", "description": "Gross Domestic Product", "asset_type": "economic"},
            {"symbol": "GDPC1", "name": "Real GDP", "description": "Real Gross Domestic Product", "asset_type": "economic"},
            {"symbol": "GDPPOT", "name": "Potential GDP", "description": "Real Potential Gross Domestic Product", "asset_type": "economic"},
            {"symbol": "INDPRO", "name": "Industrial Production", "description": "Industrial Production Total Index", "asset_type": "economic"},

            # Employment & Labor
            {"symbol": "UNRATE", "name": "Unemployment Rate", "description": "Civilian Unemployment Rate", "asset_type": "economic"},
            {"symbol": "PAYEMS", "name": "Nonfarm Payrolls", "description": "All Employees Total Nonfarm", "asset_type": "economic"},
            {"symbol": "CIVPART", "name": "Labor Force Participation", "description": "Civilian Labor Force Participation Rate", "asset_type": "economic"},
            {"symbol": "EMRATIO", "name": "Employment-Population Ratio", "description": "Employment-Population Ratio", "asset_type": "economic"},
            {"symbol": "ICSA", "name": "Initial Claims", "description": "Initial Unemployment Claims", "asset_type": "economic"},

            # Inflation & Prices
            {"symbol": "CPIAUCSL", "name": "CPI", "description": "Consumer Price Index for All Urban Consumers", "asset_type": "economic"},
            {"symbol": "CPILFESL", "name": "Core CPI", "description": "CPI Less Food and Energy", "asset_type": "economic"},
            {"symbol": "PCEPI", "name": "PCE Price Index", "description": "Personal Consumption Expenditures Price Index", "asset_type": "economic"},
            {"symbol": "PCEPILFE", "name": "Core PCE", "description": "PCE Excluding Food and Energy", "asset_type": "economic"},
            {"symbol": "PPIFIS", "name": "PPI", "description": "Producer Price Index Final Demand", "asset_type": "economic"},

            # Monetary Policy & Interest Rates
            {"symbol": "FEDFUNDS", "name": "Federal Funds Rate", "description": "Effective Federal Funds Rate", "asset_type": "economic"},
            {"symbol": "DFF", "name": "Fed Funds Daily", "description": "Federal Funds Effective Rate Daily", "asset_type": "economic"},
            {"symbol": "DGS2", "name": "2-Year Treasury", "description": "2-Year Treasury Constant Maturity Rate", "asset_type": "economic"},
            {"symbol": "DGS5", "name": "5-Year Treasury", "description": "5-Year Treasury Constant Maturity Rate", "asset_type": "economic"},
            {"symbol": "DGS10", "name": "10-Year Treasury", "description": "10-Year Treasury Constant Maturity Rate", "asset_type": "economic"},
            {"symbol": "DGS30", "name": "30-Year Treasury", "description": "30-Year Treasury Constant Maturity Rate", "asset_type": "economic"},
            {"symbol": "T10Y2Y", "name": "10Y-2Y Spread", "description": "10-Year Treasury Minus 2-Year Treasury", "asset_type": "economic"},
            {"symbol": "T10Y3M", "name": "10Y-3M Spread", "description": "10-Year Treasury Minus 3-Month Treasury", "asset_type": "economic"},

            # Money Supply
            {"symbol": "M1SL", "name": "M1 Money Supply", "description": "M1 Money Stock", "asset_type": "economic"},
            {"symbol": "M2SL", "name": "M2 Money Supply", "description": "M2 Money Stock", "asset_type": "economic"},
            {"symbol": "M2V", "name": "M2 Velocity", "description": "Velocity of M2 Money Stock", "asset_type": "economic"},

            # Consumer Spending & Income
            {"symbol": "PCE", "name": "Personal Consumption", "description": "Personal Consumption Expenditures", "asset_type": "economic"},
            {"symbol": "PSAVERT", "name": "Personal Savings Rate", "description": "Personal Saving Rate", "asset_type": "economic"},
            {"symbol": "DPI", "name": "Disposable Income", "description": "Disposable Personal Income", "asset_type": "economic"},
            {"symbol": "RSXFS", "name": "Retail Sales", "description": "Advance Retail Sales", "asset_type": "economic"},

            # Sentiment & Confidence
            {"symbol": "UMCSENT", "name": "Consumer Sentiment", "description": "University of Michigan Consumer Sentiment", "asset_type": "economic"},
            {"symbol": "CSCICP03USM665S", "name": "Consumer Confidence", "description": "Consumer Opinion Surveys Confidence Indicators", "asset_type": "economic"},

            # Housing
            {"symbol": "HOUST", "name": "Housing Starts", "description": "Housing Starts Total", "asset_type": "economic"},
            {"symbol": "HSN1F", "name": "New Home Sales", "description": "New One Family Houses Sold", "asset_type": "economic"},
            {"symbol": "MORTGAGE30US", "name": "30Y Mortgage Rate", "description": "30-Year Fixed Rate Mortgage Average", "asset_type": "economic"},
            {"symbol": "CSUSHPISA", "name": "Case-Shiller Index", "description": "S&P CoreLogic Case-Shiller US Home Price Index", "asset_type": "economic"},

            # Exchange Rates
            {"symbol": "DEXUSEU", "name": "USD/EUR Exchange Rate", "description": "US Dollar to Euro Exchange Rate", "asset_type": "economic"},
            {"symbol": "DEXCHUS", "name": "CNY/USD Exchange Rate", "description": "Chinese Yuan to US Dollar Exchange Rate", "asset_type": "economic"},
            {"symbol": "DEXJPUS", "name": "JPY/USD Exchange Rate", "description": "Japanese Yen to US Dollar Exchange Rate", "asset_type": "economic"},
            {"symbol": "DEXUSUK", "name": "USD/GBP Exchange Rate", "description": "US Dollar to British Pound Exchange Rate", "asset_type": "economic"},
            {"symbol": "DEXCAUS", "name": "CAD/USD Exchange Rate", "description": "Canadian Dollar to US Dollar Exchange Rate", "asset_type": "economic"},

            # Credit & Debt
            {"symbol": "TOTALSL", "name": "Total Consumer Credit", "description": "Total Consumer Credit Outstanding", "asset_type": "economic"},
            {"symbol": "GFDEBTN", "name": "Federal Debt", "description": "Federal Debt Total Public Debt", "asset_type": "economic"},
            {"symbol": "GFDEGDQ188S", "name": "Debt to GDP", "description": "Federal Debt to GDP Ratio", "asset_type": "economic"},

            # Manufacturing & Business
            {"symbol": "NAPM", "name": "ISM Manufacturing PMI", "description": "ISM Manufacturing Purchasing Managers Index", "asset_type": "economic"},
            {"symbol": "NEWORDER", "name": "New Orders", "description": "Manufacturers New Orders", "asset_type": "economic"},
            {"symbol": "CAPUTLB50001SQ", "name": "Capacity Utilization", "description": "Capacity Utilization Manufacturing", "asset_type": "economic"},

            # Trade & Commodities
            {"symbol": "BOPGSTB", "name": "Trade Balance", "description": "Trade Balance Goods and Services", "asset_type": "economic"},
            {"symbol": "DCOILWTICO", "name": "WTI Crude Oil", "description": "Crude Oil Prices WTI", "asset_type": "economic"},
            {"symbol": "DHHNGSP", "name": "Natural Gas", "description": "Henry Hub Natural Gas Spot Price", "asset_type": "economic"},
            {"symbol": "GOLDAMGBD228NLBM", "name": "Gold Price", "description": "Gold Fixing Price London", "asset_type": "economic"},
        ]

        return indicators

    def fetch_alphavantage_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Fetch stock listings from Alpha Vantage.

        Returns:
            List of symbol dictionaries
        """
        try:
            import requests
            from ..core.config import settings

            symbols = []

            # Alpha Vantage listing endpoint
            url = f"https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={settings.ALPHA_VANTAGE_API_KEY}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            # Parse CSV response
            import csv
            from io import StringIO

            csv_data = StringIO(response.text)
            reader = csv.DictReader(csv_data)

            for row in reader:
                if row['assetType'] in ['Stock', 'ETF']:
                    symbols.append({
                        "symbol": row['symbol'],
                        "name": row['name'],
                        "description": f"{row['name']} - {row['exchange']}",
                        "asset_type": row['assetType'].lower(),
                        "exchange": row['exchange'],
                    })

            print(f"Fetched {len(symbols)} AlphaVantage symbols")
            return symbols

        except Exception as e:
            print(f"Error fetching AlphaVantage symbols: {e}")
            return []

    def fetch_twelvedata_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Fetch stock listings from Twelve Data.

        Returns:
            List of symbol dictionaries
        """
        try:
            import requests
            from ..core.config import settings

            symbols = []
            seen_symbols = set()  # Track duplicates

            # Twelve Data stocks endpoint
            url = f"https://api.twelvedata.com/stocks?apikey={settings.TWELVE_DATA_API_KEY}"
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            for stock in data.get('data', []):
                symbol_key = stock['symbol']

                # Skip if we've already seen this symbol (TwelveData has duplicates)
                if symbol_key in seen_symbols:
                    continue

                seen_symbols.add(symbol_key)
                symbols.append({
                    "symbol": symbol_key,
                    "name": stock['name'],
                    "description": f"{stock['name']} - {stock.get('exchange', 'N/A')}",
                    "asset_type": stock.get('type', 'stock').lower(),
                    "exchange": stock.get('exchange'),
                    "country": stock.get('country'),
                    "currency": stock.get('currency'),
                })

            print(f"Fetched {len(symbols)} TwelveData symbols (deduplicated)")
            return symbols

        except Exception as e:
            print(f"Error fetching TwelveData symbols: {e}")
            return []

    def fetch_kraken_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Fetch trading pairs from Kraken.

        Returns:
            List of symbol dictionaries
        """
        try:
            import requests

            response = requests.get(
                "https://api.kraken.com/0/public/AssetPairs", timeout=10
            )
            response.raise_for_status()
            data = response.json()

            symbols = []
            for pair_name, pair_info in data.get("result", {}).items():
                symbols.append({
                    "symbol": pair_name,
                    "name": f"{pair_info.get('base', '')}/{pair_info.get('quote', '')}",
                    "description": f"Kraken {pair_info.get('wsname', pair_name)} trading pair",
                    "asset_type": "crypto",
                    "exchange": "Kraken",
                    "extra_metadata": json.dumps({
                        "base": pair_info.get("base"),
                        "quote": pair_info.get("quote"),
                        "wsname": pair_info.get("wsname"),
                    }),
                })

            print(f"Fetched {len(symbols)} Kraken symbols")
            return symbols

        except Exception as e:
            print(f"Error fetching Kraken symbols: {e}")
            return []

    def fetch_commodity_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Return common commodity symbols.

        Returns:
            List of symbol dictionaries
        """
        # Common commodities available via API Ninjas
        commodities = [
            {"symbol": "GOLD", "name": "Gold", "description": "Gold Spot Price", "asset_type": "commodity"},
            {"symbol": "SILVER", "name": "Silver", "description": "Silver Spot Price", "asset_type": "commodity"},
            {"symbol": "COPPER", "name": "Copper", "description": "Copper Futures", "asset_type": "commodity"},
            {"symbol": "PLATINUM", "name": "Platinum", "description": "Platinum Spot Price", "asset_type": "commodity"},
            {"symbol": "PALLADIUM", "name": "Palladium", "description": "Palladium Spot Price", "asset_type": "commodity"},
            {"symbol": "WTI", "name": "WTI Crude Oil", "description": "West Texas Intermediate Crude Oil", "asset_type": "commodity"},
            {"symbol": "BRENT", "name": "Brent Crude Oil", "description": "Brent Crude Oil", "asset_type": "commodity"},
            {"symbol": "NATGAS", "name": "Natural Gas", "description": "Natural Gas Futures", "asset_type": "commodity"},
            {"symbol": "WHEAT", "name": "Wheat", "description": "Wheat Futures", "asset_type": "commodity"},
            {"symbol": "CORN", "name": "Corn", "description": "Corn Futures", "asset_type": "commodity"},
            {"symbol": "SOYBEANS", "name": "Soybeans", "description": "Soybean Futures", "asset_type": "commodity"},
            {"symbol": "COFFEE", "name": "Coffee", "description": "Coffee Futures", "asset_type": "commodity"},
            {"symbol": "SUGAR", "name": "Sugar", "description": "Sugar Futures", "asset_type": "commodity"},
            {"symbol": "COTTON", "name": "Cotton", "description": "Cotton Futures", "asset_type": "commodity"},
        ]

        return commodities

    def fetch_worldbank_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Return common World Bank indicators.

        Returns:
            List of symbol dictionaries
        """
        indicators = [
            {"symbol": "NY.GDP.MKTP.CD", "name": "GDP (current US$)", "description": "GDP (current US$)", "asset_type": "economic"},
            {"symbol": "SP.POP.TOTL", "name": "Population, total", "description": "Population, total", "asset_type": "economic"},
            {"symbol": "NY.GDP.PCAP.CD", "name": "GDP per capita", "description": "GDP per capita (current US$)", "asset_type": "economic"},
            {"symbol": "FP.CPI.TOTL.ZG", "name": "Inflation", "description": "Inflation, consumer prices (annual %)", "asset_type": "economic"},
            {"symbol": "SL.UEM.TOTL.ZS", "name": "Unemployment", "description": "Unemployment, total (% of total labor force)", "asset_type": "economic"},
            {"symbol": "NE.TRD.GNFS.ZS", "name": "Trade (% of GDP)", "description": "Trade (% of GDP)", "asset_type": "economic"},
            {"symbol": "GC.DOD.TOTL.GD.ZS", "name": "Debt (% of GDP)", "description": "Central government debt, total (% of GDP)", "asset_type": "economic"},
        ]

        return indicators

    def fetch_ecb_symbols(self, provider: DataProvider) -> List[Dict[str, Any]]:
        """
        Return common ECB (European Central Bank) indicators.

        Returns:
            List of symbol dictionaries
        """
        indicators = [
            {"symbol": "ECB/MRO", "name": "Main Refinancing Rate", "description": "ECB Main Refinancing Operations Rate", "asset_type": "economic"},
            {"symbol": "ECB/DEPOSIT", "name": "Deposit Facility Rate", "description": "ECB Deposit Facility Rate", "asset_type": "economic"},
            {"symbol": "ECB/MARGINAL", "name": "Marginal Lending Rate", "description": "ECB Marginal Lending Facility Rate", "asset_type": "economic"},
            {"symbol": "ECB/HICP", "name": "HICP", "description": "Harmonised Index of Consumer Prices", "asset_type": "economic"},
            {"symbol": "ECB/UNRATE", "name": "Unemployment Rate", "description": "Euro Area Unemployment Rate", "asset_type": "economic"},
            {"symbol": "ECB/GDP", "name": "GDP", "description": "Euro Area GDP", "asset_type": "economic"},
        ]

        return indicators

    def sync_provider_symbols(
        self, provider_id: int, force: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch and sync symbols for a specific provider.

        Args:
            provider_id: Database ID of the provider
            force: If True, re-sync even if recently synced

        Returns:
            Sync result summary
        """
        provider = self.db.query(DataProvider).filter(DataProvider.id == provider_id).first()

        if not provider:
            return {"error": "Provider not found", "provider_id": provider_id}

        if not provider.is_active:
            return {
                "error": "Provider is not active",
                "provider_id": provider_id,
                "provider_name": provider.name,
            }

        # Check if API key is required but not configured
        if provider.api_key_required and not provider.has_api_key:
            return {
                "error": "API key required but not configured",
                "provider_id": provider_id,
                "provider_name": provider.name,
            }

        # Fetch symbols based on provider type
        symbols = []
        if provider.name == "YFinanceSource":
            symbols = self.fetch_yfinance_symbols(provider)
        elif provider.name == "BinanceSource":
            symbols = self.fetch_binance_symbols(provider)
        elif provider.name == "CoinGeckoSource":
            symbols = self.fetch_coingecko_symbols(provider)
        elif provider.name == "AlphaVantageSource":
            symbols = self.fetch_alphavantage_symbols(provider)
        elif provider.name == "TwelveDataSource":
            symbols = self.fetch_twelvedata_symbols(provider)
        elif provider.name == "KrakenSource":
            symbols = self.fetch_kraken_symbols(provider)
        elif provider.name == "ForexAlphaVantageSource":
            symbols = self.fetch_common_forex_pairs(provider)
        elif provider.name == "USTreasurySource":
            symbols = self.fetch_us_treasury_symbols(provider)
        elif provider.name == "FREDSource":
            symbols = self.fetch_fred_indicators(provider)
        elif provider.name == "CommodityAPISource":
            symbols = self.fetch_commodity_symbols(provider)
        elif provider.name == "WorldBankSource":
            symbols = self.fetch_worldbank_symbols(provider)
        elif provider.name == "ECBSource":
            symbols = self.fetch_ecb_symbols(provider)
        else:
            return {
                "warning": "No symbol fetching implemented for this provider",
                "provider_id": provider_id,
                "provider_name": provider.name,
            }

        # Store symbols in database
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for symbol_info in symbols:
            try:
                # Check if symbol exists
                existing_symbol = (
                    self.db.query(Symbol)
                    .filter(
                        Symbol.provider_id == provider_id,
                        Symbol.symbol == symbol_info["symbol"],
                    )
                    .first()
                )

                if existing_symbol:
                    # Update existing symbol
                    existing_symbol.name = symbol_info.get("name")
                    existing_symbol.description = symbol_info.get("description")
                    existing_symbol.asset_type = symbol_info.get("asset_type")
                    existing_symbol.exchange = symbol_info.get("exchange")
                    existing_symbol.extra_metadata = symbol_info.get("extra_metadata")
                    existing_symbol.updated_at = datetime.utcnow()
                    updated_count += 1
                else:
                    # Create new symbol
                    new_symbol = Symbol(
                        provider_id=provider_id,
                        symbol=symbol_info["symbol"],
                        name=symbol_info.get("name"),
                        description=symbol_info.get("description"),
                        asset_type=symbol_info.get("asset_type"),
                        exchange=symbol_info.get("exchange"),
                        extra_metadata=symbol_info.get("extra_metadata"),
                    )
                    self.db.add(new_symbol)
                    created_count += 1

            except Exception as e:
                print(f"Error processing symbol {symbol_info.get('symbol')}: {e}")
                self.db.rollback()  # Rollback this transaction
                skipped_count += 1
                continue

        # Commit all symbol changes first
        self.db.commit()

        # Update provider stats after commit
        provider.last_sync = datetime.utcnow()
        provider.symbol_count = (
            self.db.query(func.count(Symbol.id))
            .filter(Symbol.provider_id == provider_id)
            .scalar()
        )

        self.db.commit()

        return {
            "success": True,
            "provider_id": provider_id,
            "provider_name": provider.name,
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "total_symbols": provider.symbol_count,
            "last_sync": provider.last_sync.isoformat(),
        }

    def sync_all_providers(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync symbols for all active providers.

        Args:
            force: If True, re-sync even if recently synced

        Returns:
            Summary of all sync operations
        """
        providers = self.db.query(DataProvider).filter(DataProvider.is_active == True).all()

        results = []
        total_created = 0
        total_updated = 0
        total_skipped = 0
        total_symbols = 0

        for provider in providers:
            result = self.sync_provider_symbols(provider.id, force=force)
            results.append(result)

            if result.get("success"):
                total_created += result.get("created", 0)
                total_updated += result.get("updated", 0)
                total_skipped += result.get("skipped", 0)
                total_symbols += result.get("total_symbols", 0)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "providers_synced": len(results),
            "total_created": total_created,
            "total_updated": total_updated,
            "total_skipped": total_skipped,
            "total_symbols": total_symbols,
            "results": results,
        }

    def search_symbols(
        self,
        query: str,
        asset_type: Optional[str] = None,
        provider_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search for symbols in the database.

        Args:
            query: Search query string
            asset_type: Filter by asset type (stock, crypto, forex, etc.)
            provider_id: Filter by provider ID
            limit: Maximum number of results

        Returns:
            List of matching symbols
        """
        # Build query
        db_query = self.db.query(Symbol).filter(Symbol.is_active == True)

        # Add search filters
        if query:
            search_filter = f"%{query.upper()}%"
            db_query = db_query.filter(
                (Symbol.symbol.ilike(search_filter))
                | (Symbol.name.ilike(search_filter))
                | (Symbol.description.ilike(search_filter))
            )

        if asset_type:
            db_query = db_query.filter(Symbol.asset_type == asset_type)

        if provider_id:
            db_query = db_query.filter(Symbol.provider_id == provider_id)

        # Execute query with limit
        symbols = db_query.limit(limit).all()

        # Format results
        results = []
        for symbol in symbols:
            results.append(
                {
                    "id": symbol.id,
                    "symbol": symbol.symbol,
                    "name": symbol.name,
                    "description": symbol.description,
                    "asset_type": symbol.asset_type,
                    "exchange": symbol.exchange,
                    "provider_id": symbol.provider_id,
                    "provider_name": symbol.provider.name if symbol.provider else None,
                }
            )

        return results
