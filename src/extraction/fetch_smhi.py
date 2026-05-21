import requests
import time
import sys
import pandas as pd
from io import StringIO
from pathlib import Path
from typing import List, Dict, Optional, Tuple

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import RAW_DIR
from common.logging_utils import setup_logger
from common.io import save_to_csv

logger = setup_logger("SMHI_Extractor")

# Tier 0 parameters: (smhi_param_id, output_col_name, units)
TIER0_PARAMS: List[Tuple[int, str, str]] = [
    (8, "snow_depth", "m"),
    (2, "temp_mean",  "degC"),
    (5, "precip",     "mm"),
]

# Full Nordic domain; Dalarna pilot sub-filter is applied in build_pilot_netcdf.py
GEO_BOUNDS = {"lat_min": 55.0, "lat_max": 70.0, "lon_min": 10.0, "lon_max": 30.0}


class SMHIExtractor:
    """
    Modular extractor for SMHI MetObs Open Data (corrected-archive CSV).
    Reference: https://opendata.smhi.se/apidocs/metobs/index.html
    """
    BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/1.0"

    def __init__(self, parameter_id: int):
        self.parameter_id = parameter_id

    def get_stations(self) -> List[Dict]:
        url = f"{self.BASE_URL}/parameter/{self.parameter_id}.json"
        logger.info(f"Fetching station list: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json().get('station', [])

    def fetch_station_csv(self, station_id: int) -> Optional[str]:
        """Download corrected-archive CSV text for a station. Returns None on error or 404."""
        url = (
            f"{self.BASE_URL}/parameter/{self.parameter_id}"
            f"/station/{station_id}/period/corrected-archive/data.csv"
        )
        logger.debug(f"Fetching station {station_id}: {url}")
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.warning(f"Station {station_id} failed: {e}")
            return None

    def parse_csv(self, csv_text: str, station: Dict, param_name: str) -> pd.DataFrame:
        """
        Parse SMHI corrected-archive CSV into a DataFrame.

        Two header/column layouts exist across SMHI parameters:
          Format A (snow depth, param 8):
            Header: "Datum;Tid (UTC);<param>;Kvalitet"
            Columns: date@0, time@1, value@2, quality@3
          Format B (temp, precip, most other params):
            Header: "Från Datum Tid (UTC);Till Datum Tid (UTC);Representativt dygn;<param>;Kvalitet"
            Columns: from@0, to@1, rep_day@2, value@3, quality@4
        """
        lines = csv_text.split('\n')

        data_start = None
        fmt = None
        for i, line in enumerate(lines):
            if line.startswith('Datum;Tid'):
                data_start, fmt = i, 'A'
                break
            if line.startswith('Från Datum Tid'):
                data_start, fmt = i, 'B'
                break

        if data_start is None:
            return pd.DataFrame()

        records = []
        for line in lines[data_start + 1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split(';')
            if fmt == 'A':
                if len(parts) < 4:
                    continue
                date_str, value_str, quality = parts[0], parts[2], parts[3]
            else:  # Format B
                if len(parts) < 5:
                    continue
                date_str, value_str, quality = parts[2], parts[3], parts[4]

            # Quick date validity check (YYYY-MM-DD)
            if len(date_str) != 10 or date_str[4] != '-':
                continue
            val = pd.to_numeric(value_str, errors='coerce')
            records.append({
                'date': date_str,
                'station_id': station['id'],
                'station_name': station['name'],
                'lat': station.get('latitude'),
                'lon': station.get('longitude'),
                param_name: val,
                f'{param_name}_quality': quality,
            })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        return df


def run_extraction_workflow(
    params: List[Tuple[int, str, str]] = TIER0_PARAMS,
    bounds: Dict = GEO_BOUNDS,
    request_delay: float = 0.2,
) -> None:
    out_dir = RAW_DIR / 'smhi'
    out_dir.mkdir(parents=True, exist_ok=True)

    for param_id, param_name, units in params:
        logger.info(f"=== Parameter {param_id}: {param_name} ({units}) ===")
        extractor = SMHIExtractor(param_id)
        stations = extractor.get_stations()

        in_bounds = [
            s for s in stations
            if (bounds['lat_min'] <= s.get('latitude', 0) <= bounds['lat_max']
                and bounds['lon_min'] <= s.get('longitude', 0) <= bounds['lon_max'])
        ]
        logger.info(f"  {len(in_bounds)}/{len(stations)} stations within bounds")

        frames = []
        for i, station in enumerate(in_bounds):
            csv_text = extractor.fetch_station_csv(station['id'])
            if csv_text:
                df = extractor.parse_csv(csv_text, station, param_name)
                if not df.empty:
                    frames.append(df)
                    if (i + 1) % 100 == 0:
                        logger.info(f"  [{i+1}/{len(in_bounds)}] processed so far")
            time.sleep(request_delay)

        if frames:
            combined = pd.concat(frames, ignore_index=True)
            combined.sort_values(['station_id', 'date'], inplace=True)
            out_path = out_dir / f'smhi_{param_name}.csv'
            save_to_csv(combined, out_path)
            logger.info(
                f"  Saved {len(combined):,} rows, "
                f"{combined['station_id'].nunique()} stations → {out_path}"
            )
        else:
            logger.warning(f"  No data collected for parameter {param_name} (id={param_id})")


if __name__ == "__main__":
    run_extraction_workflow()
