#!/usr/bin/env python3
"""
Download snow depth data from SMHI Open Data API.

SMHI API structure:
- Parameter 8 = Snow depth (Snödjup)
- Data available as CSV files per station
- Quality codes: G=approved, Y=suspect

Usage:
    python scripts/download_smhi_snow.py --output data/raw/smhi_snow.csv
"""

import requests
import pandas as pd
import time
import sys
from pathlib import Path
from datetime import datetime
from io import StringIO
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SMHI API configuration
BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/1.0"
PARAMETER_SNOW_DEPTH = "8"  # Snödjup (snow depth)


def get_snow_stations(
    min_lat: float = 55.0,
    max_lat: float = 70.0,
    min_lon: float = 10.0,
    max_lon: float = 25.0,
    active_only: bool = False
) -> List[Dict]:
    """Get list of stations with snow depth data within geographic bounds."""

    url = f"{BASE_URL}/parameter/{PARAMETER_SNOW_DEPTH}.json"
    logger.info(f"Fetching station list from {url}")

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    stations = []
    for s in data.get('station', []):
        lat = s.get('latitude', 0)
        lon = s.get('longitude', 0)

        # Filter by geographic bounds
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            if active_only and not s.get('active', False):
                continue
            stations.append({
                'id': s.get('key'),
                'name': s.get('name'),
                'latitude': lat,
                'longitude': lon,
                'active': s.get('active', False)
            })

    logger.info(f"Found {len(stations)} stations in bounds")
    return stations


def download_station_data(
    station_id: str,
    station_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """Download snow depth data for a single station."""

    # Get CSV data URL
    url = f"{BASE_URL}/parameter/{PARAMETER_SNOW_DEPTH}/station/{station_id}/period/corrected-archive/data.csv"

    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            logger.debug(f"No data for station {station_name} ({station_id}): HTTP {resp.status_code}")
            return None

        # Parse CSV content
        content = resp.text

        # Find the data section (starts with "Datum;Tid")
        lines = content.split('\n')
        data_start = None
        for i, line in enumerate(lines):
            if line.startswith('Datum;Tid'):
                data_start = i
                break

        if data_start is None:
            logger.debug(f"No data section found for station {station_name}")
            return None

        # Extract data lines - parse each row individually
        records = []
        for line in lines[data_start + 1:]:
            if line.strip():
                parts = line.split(';')
                if len(parts) >= 4:
                    date_str = parts[0].strip()
                    time_str = parts[1].strip()
                    value_str = parts[2].strip()
                    quality = parts[3].strip()

                    # Validate date format (YYYY-MM-DD)
                    if date_str and len(date_str) == 10 and date_str[4] == '-':
                        try:
                            snow_val = float(value_str) if value_str else None
                            if snow_val is not None:
                                records.append({
                                    'date': date_str,
                                    'time': time_str,
                                    'snow_depth': snow_val,
                                    'quality': quality
                                })
                        except ValueError:
                            continue

        if not records:
            return None

        # Create DataFrame
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])

        # Filter by date range if specified
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]

        if len(df) == 0:
            return None

        # Add station info
        df['station_id'] = station_id
        df['station_name'] = station_name

        # Snow depth is in meters, convert to cm
        df['snow_depth_cm'] = df['snow_depth'] * 100

        return df

    except Exception as e:
        logger.debug(f"Error downloading station {station_name}: {e}")
        return None


def download_all_snow_data(
    output_path: str,
    start_date: str = "2015-01-01",
    end_date: str = "2023-12-31",
    min_lat: float = 55.0,
    max_lat: float = 70.0,
    min_lon: float = 10.0,
    max_lon: float = 25.0,
    active_only: bool = False,
    delay: float = 0.2
) -> pd.DataFrame:
    """Download snow depth data from all stations."""

    logger.info(f"Downloading SMHI snow depth data")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Geographic bounds: lat [{min_lat}, {max_lat}], lon [{min_lon}, {max_lon}]")

    # Get stations
    stations = get_snow_stations(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        active_only=active_only
    )

    if not stations:
        logger.error("No stations found!")
        return None

    # Download data from each station
    all_data = []
    successful = 0

    for i, station in enumerate(stations):
        station_id = station['id']
        station_name = station['name']

        if (i + 1) % 50 == 0:
            logger.info(f"Processing station {i + 1}/{len(stations)}: {station_name}")

        df = download_station_data(
            station_id=station_id,
            station_name=station_name,
            start_date=start_date,
            end_date=end_date
        )

        if df is not None and len(df) > 0:
            # Add coordinates
            df['latitude'] = station['latitude']
            df['longitude'] = station['longitude']
            all_data.append(df)
            successful += 1

        # Rate limiting
        time.sleep(delay)

    logger.info(f"Downloaded data from {successful}/{len(stations)} stations")

    if not all_data:
        logger.error("No data downloaded!")
        return None

    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)

    # Sort by date and station
    combined_df = combined_df.sort_values(['station_name', 'date'])

    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)

    logger.info(f"Saved {len(combined_df)} records to {output_path}")
    logger.info(f"Stations with data: {combined_df['station_name'].nunique()}")
    logger.info(f"Date range in data: {combined_df['date'].min()} to {combined_df['date'].max()}")

    return combined_df


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Download SMHI Snow Depth Data')
    parser.add_argument('--output', type=str, default='data/raw/smhi_snow.csv',
                        help='Output file path')
    parser.add_argument('--start-date', type=str, default='2015-01-01',
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31',
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--min-lat', type=float, default=55.0)
    parser.add_argument('--max-lat', type=float, default=70.0)
    parser.add_argument('--min-lon', type=float, default=10.0)
    parser.add_argument('--max-lon', type=float, default=25.0)
    parser.add_argument('--active-only', action='store_true',
                        help='Only download from active stations')
    args = parser.parse_args()

    df = download_all_snow_data(
        output_path=args.output,
        start_date=args.start_date,
        end_date=args.end_date,
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        active_only=args.active_only
    )

    if df is not None:
        print(f"\nDownload complete!")
        print(f"  Total records: {len(df):,}")
        print(f"  Stations: {df['station_name'].nunique()}")
        print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        print(f"  Output: {args.output}")


if __name__ == '__main__':
    main()
