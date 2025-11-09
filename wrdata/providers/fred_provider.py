"""
FRED (Federal Reserve Economic Data) provider.

Access to 800,000+ economic data series from the Federal Reserve Bank of St. Louis.

Get your free API key: https://fred.stlouisfed.org/docs/api/api_key.html

Popular series:
- GDP: Gross Domestic Product
- UNRATE: Unemployment Rate
- CPIAUCSL: Consumer Price Index (CPI)
- DGS10: 10-Year Treasury Rate
- DEXUSEU: USD/EUR Exchange Rate
- DCOILWTICO: WTI Crude Oil Prices
- MORTGAGE30US: 30-Year Mortgage Rate
"""

import requests
from typing import Optional, List
from datetime import datetime, date
from wrdata.providers.base import BaseProvider
from wrdata.models.schemas import DataResponse, OptionsChainRequest, OptionsChainResponse


class FREDProvider(BaseProvider):
    """
    FRED (Federal Reserve Economic Data) provider.

    Provides access to economic indicators from the St. Louis Federal Reserve.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(name="fred", api_key=api_key)
        self.base_url = "https://api.stlouisfed.org/fred"

        if not api_key:
            raise ValueError(
                "FRED API key required. Get one free at: "
                "https://fred.stlouisfed.org/docs/api/api_key.html"
            )

    def fetch_timeseries(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        **kwargs
    ) -> DataResponse:
        """
        Fetch economic data series from FRED.

        Args:
            symbol: FRED series ID (e.g., "GDP", "UNRATE", "CPIAUCSL")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interval: Not used for FRED (data frequency is series-specific)

        Returns:
            DataResponse with economic data
        """
        try:
            # FRED uses series_id instead of symbol
            series_id = symbol.upper()

            # Build request URL
            url = f"{self.base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date,
                'observation_end': end_date,
            }

            # Make request
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if 'error_message' in data:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=data['error_message']
                )

            # Parse observations
            observations = data.get('observations', [])

            if not observations:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No data found for series {series_id}"
                )

            # Convert to standard format
            records = []
            for obs in observations:
                # Skip missing values (FRED uses "." for missing)
                if obs['value'] == '.':
                    continue

                try:
                    records.append({
                        'Date': obs['date'],
                        'close': float(obs['value']),  # Economic data as "close" price
                        'value': float(obs['value']),  # Also keep as "value"
                        'open': float(obs['value']),   # For compatibility
                        'high': float(obs['value']),
                        'low': float(obs['value']),
                        'volume': 0,  # No volume for economic data
                    })
                except (ValueError, KeyError):
                    continue

            if not records:
                return DataResponse(
                    symbol=symbol,
                    provider=self.name,
                    data=[],
                    success=False,
                    error=f"No valid data points for series {series_id}"
                )

            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=records,
                metadata={
                    'series_id': series_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'records': len(records),
                    'source': 'Federal Reserve Economic Data (FRED)'
                },
                success=True
            )

        except requests.exceptions.RequestException as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"FRED API request failed: {str(e)}"
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider=self.name,
                data=[],
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def fetch_options_chain(
        self,
        request: OptionsChainRequest
    ) -> OptionsChainResponse:
        """FRED does not support options data."""
        return OptionsChainResponse(
            symbol=request.symbol,
            provider=self.name,
            snapshot_timestamp=datetime.utcnow(),
            success=False,
            error="FRED does not provide options data"
        )

    def get_available_expirations(self, symbol: str) -> List[date]:
        """FRED does not support options data."""
        return []

    def validate_connection(self) -> bool:
        """
        Validate FRED API connection.

        Tests by fetching GDP series metadata.
        """
        try:
            url = f"{self.base_url}/series"
            params = {
                'series_id': 'GDP',
                'api_key': self.api_key,
                'file_type': 'json'
            }

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()
            return 'seriess' in data or 'series' in data

        except Exception:
            return False

    def search_series(self, search_text: str, limit: int = 10) -> List[dict]:
        """
        Search for FRED data series.

        Args:
            search_text: Search query (e.g., "unemployment", "inflation")
            limit: Maximum number of results

        Returns:
            List of series information dictionaries

        Example:
            >>> provider = FREDProvider(api_key="...")
            >>> results = provider.search_series("gdp")
            >>> for series in results:
            ...     print(f"{series['id']}: {series['title']}")
        """
        try:
            url = f"{self.base_url}/series/search"
            params = {
                'search_text': search_text,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            series_list = data.get('seriess', [])

            results = []
            for series in series_list:
                results.append({
                    'id': series.get('id'),
                    'title': series.get('title'),
                    'units': series.get('units'),
                    'frequency': series.get('frequency'),
                    'seasonal_adjustment': series.get('seasonal_adjustment'),
                    'last_updated': series.get('last_updated'),
                    'popularity': series.get('popularity'),
                })

            return results

        except Exception as e:
            print(f"FRED search failed: {e}")
            return []

    def get_series_info(self, series_id: str) -> dict:
        """
        Get detailed information about a FRED series.

        Args:
            series_id: FRED series ID

        Returns:
            Dictionary with series metadata
        """
        try:
            url = f"{self.base_url}/series"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json'
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            series_list = data.get('seriess', [])

            if series_list:
                return series_list[0]

            return {}

        except Exception as e:
            print(f"Failed to get series info: {e}")
            return {}

    def supports_historical_options(self) -> bool:
        """FRED does not support options."""
        return False


# Popular FRED series IDs for easy reference
POPULAR_SERIES = {
    # GDP & Growth
    'GDP': 'Gross Domestic Product',
    'GDPC1': 'Real Gross Domestic Product',
    'A191RL1Q225SBEA': 'Real GDP Growth Rate',

    # Unemployment & Jobs
    'UNRATE': 'Unemployment Rate',
    'PAYEMS': 'Nonfarm Payrolls',
    'CIVPART': 'Labor Force Participation Rate',
    'U6RATE': 'Total Unemployed (U-6)',

    # Inflation & Prices
    'CPIAUCSL': 'Consumer Price Index (CPI)',
    'PCEPI': 'Personal Consumption Expenditures Price Index',
    'CORESTICKM159SFRBATL': 'Core CPI (Sticky Price)',

    # Interest Rates
    'DGS10': '10-Year Treasury Constant Maturity Rate',
    'DGS2': '2-Year Treasury Constant Maturity Rate',
    'DFF': 'Federal Funds Effective Rate',
    'MORTGAGE30US': '30-Year Fixed Rate Mortgage Average',

    # Money & Credit
    'M1SL': 'M1 Money Stock',
    'M2SL': 'M2 Money Stock',
    'TOTCI': 'Commercial and Industrial Loans',

    # Housing
    'CSUSHPISA': 'Case-Shiller U.S. Home Price Index',
    'HOUST': 'Housing Starts',
    'PERMIT': 'New Private Housing Units Authorized by Building Permits',

    # Consumer & Retail
    'RSXFS': 'Retail Sales',
    'UMCSENT': 'University of Michigan Consumer Sentiment',
    'PCE': 'Personal Consumption Expenditures',

    # Manufacturing & Production
    'INDPRO': 'Industrial Production Index',
    'IPMAN': 'Industrial Production: Manufacturing',
    'NAPM': 'ISM Manufacturing PMI',

    # Trade & Exchange
    'DEXUSEU': 'USD/EUR Exchange Rate',
    'DEXCHUS': 'China/USD Exchange Rate',
    'BOPGSTB': 'Trade Balance: Goods and Services',

    # Commodities
    'DCOILWTICO': 'Crude Oil Prices: WTI',
    'DCOILBRENTEU': 'Crude Oil Prices: Brent',
    'GOLDAMGBD228NLBM': 'Gold Fixing Price',
}
