from typing import List, Dict, Any, Optional
import requests
from datetime import datetime
import pandas as pd  # Using pandas for easier data processing
import io

from ..providers.base import BaseProvider
from ..models.schemas import DataResponse, DataRequest
from ..core.config import settings


class FredProvider(BaseProvider):
    """
    FRED (Federal Reserve Economic Data) data provider.
    Fetches economic time series data.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("FRED_API_KEY must be provided for FredProvider")
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/"
        self.session = requests.Session()
        self.session.params.update({"api_key": self.api_key, "file_type": "json"})

    def validate_connection(self) -> bool:
        """
        Validate FRED API connection by fetching a sample series.
        """
        try:
            # Try to fetch a well-known series like FEDFUNDS
            response = self.session.get(
                f"{self.base_url}series/observations",
                params={"series_id": "FEDFUNDS", "limit": 1},
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False

    def fetch_timeseries(
        self, symbol: str, start_date: str, end_date: str, interval: str = "1d"
    ) -> DataResponse:
        """
        Fetch historical data for a FRED series ID.
        FRED does not have 'open', 'high', 'low', 'volume' for most series.
        We return 'close' as the series value and other OHLCV as None/0.
        """
        params = {
            "series_id": symbol,
            "observation_start": start_date,
            "observation_end": end_date,
            "frequency": self._map_interval_to_fred_frequency(interval),
        }

        try:
            response = self.session.get(
                f"{self.base_url}series/observations", params=params
            )
            response.raise_for_status()
            data = response.json()

            observations = data.get("observations", [])
            df_data = []
            for obs in observations:
                if obs["value"] != ".":  # FRED uses "." for missing values
                    df_data.append(
                        {
                            "timestamp": datetime.strptime(obs["date"], "%Y-%m-%d"),
                            "open": float(obs["value"]),
                            "high": float(obs["value"]),
                            "low": float(obs["value"]),
                            "close": float(obs["value"]),
                            "volume": 0,
                        }
                    )

            # Sort data by timestamp if not already sorted
            df_data.sort(key=lambda x: x["timestamp"])

            return DataResponse(
                symbol=symbol, provider="fred", data=df_data, success=True, error=None
            )

        except requests.exceptions.RequestException as e:
            return DataResponse(
                symbol=symbol,
                provider="fred",
                data=[],
                success=False,
                error=f"FRED API error: {e}",
            )
        except Exception as e:
            return DataResponse(
                symbol=symbol,
                provider="fred",
                data=[],
                success=False,
                error=f"Error processing FRED data: {e}",
            )

    def search_series(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for FRED series.
        """
        params = {"search_text": query, "limit": 100}
        try:
            response = self.session.get(f"{self.base_url}series/search", params=params)
            response.raise_for_status()
            data = response.json()

            series_results = []
            for series in data.get("seriess", []):
                series_results.append(
                    {
                        "symbol": series["id"],
                        "name": series["title"],
                        "description": series.get("notes", ""),
                        "asset_type": "economic",
                        "provider": "fred",
                        "frequency": series.get("frequency_short"),
                    }
                )
            return series_results
        except requests.exceptions.RequestException as e:
            print(f"Error searching FRED series: {e}")
            return []
        except Exception as e:
            print(f"Error processing FRED search results: {e}")
            return []

    def _map_interval_to_fred_frequency(self, interval: str) -> str:
        """
        Maps a generic interval string to FRED API frequency.
        FRED frequencies: 'd' (daily), 'w' (weekly), 'm' (monthly), 'q' (quarterly), 'a' (annual), 'bh' (business hour), 'b' (business day), 'wef' (weekly, ending Friday).
        """
        if interval in ["1d", "D"]:
            return "d"
        elif interval in ["1w", "W", "WK"]:
            return "w"
        elif interval in ["1M", "M", "MON"]:
            return "m"
        elif interval in ["1q", "Q"]:
            return "q"
        elif interval in ["1y", "Y", "ANN"]:
            return "a"
        # FRED does not support intraday frequencies like 1m, 5m, 1h for general series
        # Default to daily if no specific mapping, or the closest reasonable frequency
        return "d"

    def supports_historical_options(self) -> bool:
        return False
