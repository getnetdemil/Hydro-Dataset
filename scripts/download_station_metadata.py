#!/usr/bin/env python3
"""
Download station metadata from SMHI Open Data API.

Retrieves latitude, longitude, elevation, and other metadata for all
stations that measure snow depth (parameter 8). This metadata is needed
to extract MESAN grid values at station locations.

SMHI API:
    https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/8.json

Usage:
    python scripts/download_station_metadata.py
    python scripts/download_station_metadata.py --output data/raw/station_metadata.csv
    python scripts/download_station_metadata.py --parameter 8 --active-only
"""

import argparse
import requests
import pandas as pd
import sys
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SMHI API
BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/1.0"

# Parameters of interest
PARAMETERS = {
    8: "Snow depth (Snödjup)",
    1: "Air temperature (momentary, 1/min)",
    2: "Air temperature (mean, 1/day)",
    5: "Precipitation (sum, 1/day)",
    6: "Relative humidity (momentary, 1/h)",
    7: "Precipitation (sum, 1/h)",
    4: "Wind speed (mean, 10 min)",
}


def get_station_list(parameter: int = 8, timeout: int = 30) -> List[Dict]:
    """
    Get station metadata from SMHI API for a given parameter.

    Args:
        parameter: SMHI parameter ID (default 8 = snow depth)
        timeout: Request timeout in seconds

    Returns:
        List of station dictionaries
    """
    url = f"{BASE_URL}/parameter/{parameter}.json"
    logger.info(f"Fetching stations for parameter {parameter} from {url}")

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    stations = []
    for s in data.get('station', []):
        station = {
            'station_id': s.get('key'),
            'name': s.get('name', ''),
            'latitude': s.get('latitude'),
            'longitude': s.get('longitude'),
            'height': s.get('height'),  # elevation in meters
            'active': s.get('active', False),
            'owner': s.get('owner', ''),
            'owner_category': s.get('ownerCategory', ''),
            'from_epoch_ms': s.get('from'),
            'to_epoch_ms': s.get('to'),
        }

        # Convert epoch ms to datetime string
        if station['from_epoch_ms'] is not None:
            try:
                station['from_date'] = pd.Timestamp(station['from_epoch_ms'], unit='ms').strftime('%Y-%m-%d')
            except Exception:
                station['from_date'] = None
        else:
            station['from_date'] = None

        if station['to_epoch_ms'] is not None:
            try:
                station['to_date'] = pd.Timestamp(station['to_epoch_ms'], unit='ms').strftime('%Y-%m-%d')
            except Exception:
                station['to_date'] = None
        else:
            station['to_date'] = None

        stations.append(station)

    logger.info(f"Found {len(stations)} stations for parameter {parameter}")
    return stations


def get_station_period_info(
    station_id: str,
    parameter: int = 8,
    timeout: int = 30
) -> Optional[Dict]:
    """
    Get available data periods for a specific station.

    Args:
        station_id: SMHI station ID
        parameter: SMHI parameter ID
        timeout: Request timeout

    Returns:
        Dictionary with period information or None
    """
    url = f"{BASE_URL}/parameter/{parameter}/station/{station_id}.json"

    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            return None

        data = resp.json()
        periods = []
        for p in data.get('period', []):
            periods.append({
                'key': p.get('key'),
                'from': p.get('summary', {}).get('from'),
                'to': p.get('summary', {}).get('to'),
            })

        return {
            'station_id': station_id,
            'periods': periods,
            'owner': data.get('owner', ''),
            'ownerCategory': data.get('ownerCategory', ''),
        }

    except Exception as e:
        logger.debug(f"Error fetching period info for station {station_id}: {e}")
        return None


def download_station_metadata(
    output_path: str = "data/raw/station_metadata.csv",
    parameter: int = 8,
    active_only: bool = False,
    min_lat: float = 55.0,
    max_lat: float = 70.0,
    min_lon: float = 10.0,
    max_lon: float = 25.0
) -> pd.DataFrame:
    """
    Download and save station metadata.

    Args:
        output_path: Output CSV path
        parameter: SMHI parameter ID
        active_only: Only include active stations
        min_lat/max_lat/min_lon/max_lon: Geographic bounds (Sweden)

    Returns:
        DataFrame with station metadata
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get station list
    stations = get_station_list(parameter=parameter)

    if not stations:
        logger.error("No stations found!")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(stations)

    # Rename height to elevation for consistency
    df = df.rename(columns={'height': 'elevation'})

    # Drop epoch columns (human-readable dates are sufficient)
    df = df.drop(columns=['from_epoch_ms', 'to_epoch_ms'], errors='ignore')

    logger.info(f"Total stations: {len(df)}")

    # Filter by geographic bounds (Sweden)
    mask = (
        (df['latitude'] >= min_lat) & (df['latitude'] <= max_lat) &
        (df['longitude'] >= min_lon) & (df['longitude'] <= max_lon)
    )
    df = df[mask].copy()
    logger.info(f"After geographic filter (Sweden): {len(df)}")

    # Filter active only
    if active_only:
        df = df[df['active'] == True].copy()
        logger.info(f"After active filter: {len(df)}")

    # Sort by station_id
    df = df.sort_values('station_id').reset_index(drop=True)

    # Save
    df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(df)} stations to {output_path}")

    # Summary statistics
    logger.info("")
    logger.info("Station Summary:")
    logger.info(f"  Total stations:  {len(df)}")
    logger.info(f"  Active:          {df['active'].sum()}")
    logger.info(f"  Inactive:        {(~df['active']).sum()}")
    logger.info(f"  With elevation:  {df['elevation'].notna().sum()}")
    logger.info(f"  Latitude range:  {df['latitude'].min():.2f} - {df['latitude'].max():.2f}")
    logger.info(f"  Longitude range: {df['longitude'].min():.2f} - {df['longitude'].max():.2f}")

    if df['elevation'].notna().any():
        logger.info(f"  Elevation range: {df['elevation'].min():.0f} - {df['elevation'].max():.0f} m")

    return df


def main():
    parser = argparse.ArgumentParser(
        description='Download SMHI station metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download snow depth station metadata (default)
  python scripts/download_station_metadata.py

  # Only active stations
  python scripts/download_station_metadata.py --active-only

  # Different parameter (e.g., temperature)
  python scripts/download_station_metadata.py --parameter 1 --output data/raw/temp_stations.csv
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/station_metadata.csv',
                        help='Output CSV path (default: data/raw/station_metadata.csv)')
    parser.add_argument('--parameter', type=int, default=8,
                        help='SMHI parameter ID (default: 8 = snow depth)')
    parser.add_argument('--active-only', action='store_true',
                        help='Only include active stations')
    parser.add_argument('--min-lat', type=float, default=55.0)
    parser.add_argument('--max-lat', type=float, default=70.0)
    parser.add_argument('--min-lon', type=float, default=10.0)
    parser.add_argument('--max-lon', type=float, default=25.0)

    args = parser.parse_args()

    df = download_station_metadata(
        output_path=args.output,
        parameter=args.parameter,
        active_only=args.active_only,
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon
    )

    if df is not None:
        print(f"\nDone! Saved {len(df)} stations to {args.output}")


if __name__ == '__main__':
    main()
