import requests
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to sys.path for relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import RAW_DIR
from common.logging_utils import setup_logger
from common.io import save_to_csv

logger = setup_logger("SMHI_Extractor")

class SMHIExtractor:
    """
    Modular extractor for SMHI Open Data (Station Observations).
    Reference: https://opendata.smhi.se/apidocs/metobs/index.html
    """
    BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/1.0"

    def __init__(self, parameter_id: int):
        self.parameter_id = parameter_id

    def get_stations(self) -> List[Dict]:
        """
        Retrieves a list of all stations for the given parameter.
        """
        url = f"{self.BASE_URL}/parameter/{self.parameter_id}.json"
        logger.info(f"Fetching station list from: {url}")
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('station', [])

    def fetch_station_data(self, station_id: int, period: str = "latest-day") -> Optional[Dict]:
        """
        Retrieves observation data for a specific station.
        Periods: 'latest-hour', 'latest-day', 'latest-months', 'corrected-archive'.
        """
        url = f"{self.BASE_URL}/parameter/{self.parameter_id}/station/{station_id}/period/{period}/data.json"
        logger.debug(f"Fetching data from station {station_id}: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch station {station_id}: {e}")
            return None

def run_extraction_workflow(param_id: int = 1):
    """
    Main extraction workflow for a parameter (e.g., 1 = Air Temperature).
    """
    extractor = SMHIExtractor(param_id)
    stations = extractor.get_stations()
    logger.info(f"Found {len(stations)} stations for parameter {param_id}")

    # For Phase 1 Alpha, we fetch data for the first 5 stations as a test
    for station in stations[:5]:
        data = extractor.fetch_station_data(station['id'])
        if data:
            # Process and save (Stub: For now we just log success)
            logger.info(f"Station {station['name']} ({station['id']}) data fetched successfully.")

if __name__ == "__main__":
    # Example: 1 = Air Temperature (Hourly), 6 = Humidity, 5 = Precipitation
    run_extraction_workflow(param_id=1)
