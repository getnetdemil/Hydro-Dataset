"""
fetch_smhi_hydobs.py — SMHI HydObs discharge extractor

Downloads daily mean discharge (m³/s) for all SMHI HydObs stations within the
Nordic bounding box from the corrected-archive. Output saved to data/raw/smhi/.

SMHI HydObs API: https://opendata.smhi.se/apidocs/hydobs/
  Parameter 1 = Vattenföring (discharge, m³/s), daily mean
"""

import requests
import time
import sys
import logging
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import RAW_DIR
from common.logging_utils import setup_logger
from common.io import save_to_csv

logger = setup_logger('SMHI_HydObs')

BASE_URL   = 'https://opendata-download-hydobs.smhi.se/api/version/1.0'
PARAM_ID   = 1          # Vattenföring (discharge) m³/s
PARAM_NAME = 'discharge'

GEO_BOUNDS = {'lat_min': 55.0, 'lat_max': 70.0, 'lon_min': 10.0, 'lon_max': 30.0}


def get_stations() -> list:
    url = f'{BASE_URL}/parameter/{PARAM_ID}.json'
    logger.info(f'Fetching HydObs station list: {url}')
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json().get('station', [])


def fetch_station_csv(station_id: int) -> str | None:
    """Download corrected-archive CSV for a station. Returns None on 404 or error."""
    url = (
        f'{BASE_URL}/parameter/{PARAM_ID}'
        f'/station/{station_id}/period/corrected-archive/data.csv'
    )
    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f'Station {station_id} failed: {e}')
        return None


def parse_csv(csv_text: str, station: dict) -> pd.DataFrame:
    """
    Parse SMHI HydObs corrected-archive CSV.

    Header: Från Datum Tid (UTC);Till Datum Tid (UTC);Representativt dygn;Vattenföring;Kvalitet
    Representative day (col 2) is used as the observation date.
    """
    lines = csv_text.split('\n')
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith('Från Datum Tid'):
            data_start = i
            break

    if data_start is None:
        return pd.DataFrame()

    records = []
    for line in lines[data_start + 1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(';')
        if len(parts) < 5:
            continue
        date_str   = parts[2]
        value_str  = parts[3]
        quality    = parts[4]

        if len(date_str) < 10 or date_str[4] != '-':
            continue

        val = pd.to_numeric(value_str, errors='coerce')
        records.append({
            'date':         date_str[:10],
            'station_id':   station['id'],
            'station_name': station.get('name', ''),
            'lat':          station.get('latitude'),
            'lon':          station.get('longitude'),
            PARAM_NAME:     val,
            f'{PARAM_NAME}_quality': quality.strip(),
        })

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    return df


def run_extraction_workflow(
    bounds: dict = GEO_BOUNDS,
    request_delay: float = 0.2,
) -> None:
    out_dir = RAW_DIR / 'smhi'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'smhi_discharge.csv'

    stations = get_stations()
    in_bounds = [
        s for s in stations
        if (bounds['lat_min'] <= s.get('latitude', 0) <= bounds['lat_max']
            and bounds['lon_min'] <= s.get('longitude', 0) <= bounds['lon_max'])
    ]
    logger.info(f'{len(in_bounds)}/{len(stations)} HydObs stations within Nordic bounds')

    frames = []
    for i, station in enumerate(in_bounds):
        csv_text = fetch_station_csv(station['id'])
        if csv_text:
            df = parse_csv(csv_text, station)
            if not df.empty:
                frames.append(df)
        if (i + 1) % 50 == 0:
            logger.info(f'  [{i+1}/{len(in_bounds)}] stations processed')
        time.sleep(request_delay)

    if not frames:
        logger.warning('No discharge data collected. Check API availability.')
        return

    combined = pd.concat(frames, ignore_index=True)
    combined.sort_values(['station_id', 'date'], inplace=True)
    save_to_csv(combined, out_path)
    logger.info(
        f'Saved {len(combined):,} rows, '
        f'{combined["station_id"].nunique()} stations → {out_path}'
    )


if __name__ == '__main__':
    run_extraction_workflow()
