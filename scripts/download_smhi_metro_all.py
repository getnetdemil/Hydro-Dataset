#!/usr/bin/env python3
"""
Download SMHI data from ALL stations that have multiple meteorological parameters.

This script dynamically discovers stations by querying the SMHI API for each parameter,
then finds stations that have snow PLUS at least N other parameters.

Usage:
    # Find and download from all multi-parameter stations (snow + 2 others)
    python scripts/download_smhi_metro_all.py --output data/raw/smhi_metro_all.csv

    # Require more parameters (snow + 4 others)
    python scripts/download_smhi_metro_all.py --output data/raw/smhi_metro_strict.csv --min-params 5

    # Just discover stations without downloading
    python scripts/download_smhi_metro_all.py --discover-only
"""

import requests
import pandas as pd
import numpy as np
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
import logging
import argparse
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SMHI API configuration
BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/1.0"

# Parameters to check for multi-parameter stations
# Format: {name: (parameter_id, unit, description, aggregation_method)}
PARAMETERS = {
    'snow': (8, 'm', 'Snow depth (daily at 06 UTC)', 'last'),
    'temp': (2, '°C', 'Air temperature (daily mean)', 'mean'),
    'temp_min': (19, '°C', 'Air temperature (daily min)', 'min'),
    'temp_max': (20, '°C', 'Air temperature (daily max)', 'max'),
    'precip': (14, 'mm', 'Precipitation (daily sum)', 'sum'),
    'wind': (4, 'm/s', 'Wind speed (10-min mean, hourly)', 'mean'),
    'humidity': (29, '%', 'Relative humidity (hourly)', 'mean'),
    'pressure': (9, 'hPa', 'Sea-level pressure (hourly)', 'mean'),
    'dew_point': (39, '°C', 'Dew point temperature (hourly)', 'mean'),
    'cloud_cover': (16, '%', 'Total cloud cover (hourly)', 'mean'),
    'ground_state': (40, 'code', 'Ground state code (daily)', 'last'),
}

# Core parameters that define a "metro" station (must have snow + some of these)
CORE_PARAMS = ['snow', 'wind', 'pressure', 'dew_point', 'humidity', 'cloud_cover']


def get_stations_for_parameter(parameter_id: int, delay: float = 0.3) -> Dict[int, Dict]:
    """Get all stations that have data for a specific parameter."""
    url = f"{BASE_URL}/parameter/{parameter_id}.json"

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"Failed to get stations for parameter {parameter_id}: {resp.status_code}")
            return {}

        data = resp.json()
        stations = {}

        for station in data.get('station', []):
            station_id = station.get('id')
            if station_id:
                stations[station_id] = {
                    'id': station_id,
                    'name': station.get('name', f'Station_{station_id}'),
                    'latitude': station.get('latitude'),
                    'longitude': station.get('longitude'),
                    'height': station.get('height', 0),
                    'active': station.get('active', False),
                    'from': station.get('from'),
                    'to': station.get('to'),
                }

        time.sleep(delay)
        return stations

    except Exception as e:
        logger.error(f"Error getting stations for parameter {parameter_id}: {e}")
        return {}


def discover_metro_stations(min_params: int = 3, require_snow: bool = True) -> Dict[int, Dict]:
    """
    Discover all stations that have multiple parameters.

    Args:
        min_params: Minimum number of parameters a station must have
        require_snow: If True, station must have snow depth parameter

    Returns:
        Dictionary of station_id -> station_info with parameter list
    """
    logger.info("=" * 70)
    logger.info("DISCOVERING MULTI-PARAMETER STATIONS")
    logger.info("=" * 70)

    # Get stations for each parameter
    param_stations = {}
    all_stations = {}

    for param_name, (param_id, unit, desc, _) in PARAMETERS.items():
        logger.info(f"Querying stations for {param_name} (ID: {param_id})...")
        stations = get_stations_for_parameter(param_id)
        param_stations[param_name] = set(stations.keys())

        # Merge station info
        for sid, info in stations.items():
            if sid not in all_stations:
                all_stations[sid] = info
                all_stations[sid]['parameters'] = []
            all_stations[sid]['parameters'].append(param_name)

        logger.info(f"  Found {len(stations)} stations with {param_name}")

    # Filter to multi-parameter stations
    metro_stations = {}

    for sid, info in all_stations.items():
        params = info['parameters']

        # Check minimum parameter count
        if len(params) < min_params:
            continue

        # Check if snow is required
        if require_snow and 'snow' not in params:
            continue

        # Count core parameters
        core_count = sum(1 for p in params if p in CORE_PARAMS)
        info['core_param_count'] = core_count
        info['total_param_count'] = len(params)

        metro_stations[sid] = info

    logger.info(f"\nFound {len(metro_stations)} stations with {min_params}+ parameters")
    if require_snow:
        logger.info(f"  (all have snow depth)")

    return metro_stations


def print_discovered_stations(stations: Dict[int, Dict]):
    """Print discovered stations in a nice format."""
    print("\n" + "=" * 100)
    print("DISCOVERED MULTI-PARAMETER STATIONS")
    print("=" * 100)

    # Sort by parameter count (descending)
    sorted_stations = sorted(stations.items(), key=lambda x: -x[1]['total_param_count'])

    print(f"\n{'ID':<10} {'Station Name':<35} {'Lat':>8} {'Lon':>8} {'Elev':>6} {'Params':>6} {'Parameters'}")
    print("-" * 100)

    for sid, info in sorted_stations:
        params_str = ', '.join(sorted(info['parameters']))
        print(f"{sid:<10} {info['name'][:34]:<35} {info['latitude'] or 0:>8.4f} {info['longitude'] or 0:>8.4f} "
              f"{info['height'] or 0:>6.0f} {info['total_param_count']:>6} {params_str}")

    print("\n" + "=" * 100)
    print("SUMMARY BY PARAMETER COUNT")
    print("=" * 100)

    count_dist = defaultdict(int)
    for info in stations.values():
        count_dist[info['total_param_count']] += 1

    for count in sorted(count_dist.keys(), reverse=True):
        print(f"  {count} parameters: {count_dist[count]} stations")

    # Geographic summary
    lats = [info['latitude'] for info in stations.values() if info['latitude']]
    lons = [info['longitude'] for info in stations.values() if info['longitude']]
    elevs = [info['height'] for info in stations.values() if info['height']]

    if lats:
        print(f"\nGeographic coverage:")
        print(f"  Latitude:  {min(lats):.2f}°N to {max(lats):.2f}°N")
        print(f"  Longitude: {min(lons):.2f}°E to {max(lons):.2f}°E")
        print(f"  Elevation: {min(elevs):.0f}m to {max(elevs):.0f}m")


def download_station_parameter(
    station_id: int,
    parameter_id: int,
    start_date: str,
    end_date: str,
    delay: float = 0.2
) -> Optional[pd.DataFrame]:
    """Download data for a specific station and parameter."""
    url = f"{BASE_URL}/parameter/{parameter_id}/station/{station_id}/period/corrected-archive/data.csv"

    try:
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            return None

        content = resp.text
        lines = content.split('\n')

        # Find header line
        data_start = None
        for i, line in enumerate(lines):
            if line.startswith('Datum'):
                data_start = i
                break

        if data_start is None:
            return None

        # Parse data
        records = []
        for line in lines[data_start + 1:]:
            if line.strip():
                parts = line.split(';')
                if len(parts) >= 3:
                    date_str = parts[0].strip()
                    time_str = parts[1].strip() if len(parts) > 1 else "00:00:00"
                    value_str = parts[2].strip()

                    if date_str and len(date_str) == 10 and date_str[4] == '-':
                        try:
                            value = float(value_str) if value_str else None
                            if value is not None:
                                records.append({
                                    'date': date_str,
                                    'time': time_str,
                                    'value': value
                                })
                        except ValueError:
                            continue

        if not records:
            return None

        df = pd.DataFrame(records)
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        df['date'] = pd.to_datetime(df['date'])

        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

        time.sleep(delay)
        return df if len(df) > 0 else None

    except Exception as e:
        logger.debug(f"Error downloading station {station_id}, param {parameter_id}: {e}")
        return None


def aggregate_to_daily(df: pd.DataFrame, method: str = 'mean') -> pd.DataFrame:
    """Aggregate hourly data to daily values."""
    if method == 'mean':
        daily = df.groupby('date')['value'].mean().reset_index()
    elif method == 'sum':
        daily = df.groupby('date')['value'].sum().reset_index()
    elif method == 'max':
        daily = df.groupby('date')['value'].max().reset_index()
    elif method == 'min':
        daily = df.groupby('date')['value'].min().reset_index()
    elif method == 'last':
        daily = df.groupby('date')['value'].last().reset_index()
    else:
        daily = df.groupby('date')['value'].mean().reset_index()
    return daily


def download_metro_station(
    station_id: int,
    station_info: Dict,
    start_date: str,
    end_date: str,
    delay: float = 0.2
) -> Optional[pd.DataFrame]:
    """Download all parameters for a single station."""

    station_name = station_info['name']
    lat = station_info.get('latitude', 0)
    lon = station_info.get('longitude', 0)
    elev = station_info.get('height', 0)

    # Start with date range as base
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    station_df = pd.DataFrame({'date': date_range})
    station_df['station_id'] = station_id
    station_df['station_name'] = station_name
    station_df['latitude'] = lat
    station_df['longitude'] = lon
    station_df['elevation'] = elev

    # Download each parameter
    params_downloaded = 0
    for param_name, (param_id, unit, desc, agg_method) in PARAMETERS.items():
        df = download_station_parameter(station_id, param_id, start_date, end_date, delay)

        if df is not None and len(df) > 0:
            # Aggregate to daily
            daily_df = aggregate_to_daily(df, agg_method)
            daily_df = daily_df.rename(columns={'value': param_name})

            # Merge with station data
            station_df = station_df.merge(daily_df, on='date', how='left')
            params_downloaded += 1
        else:
            # Add empty column
            if param_name not in station_df.columns:
                station_df[param_name] = np.nan

    # Remove rows where ALL parameters are NaN
    param_cols = list(PARAMETERS.keys())
    station_df = station_df.dropna(subset=param_cols, how='all')

    return station_df if len(station_df) > 0 else None, params_downloaded


def download_all_metro_stations(
    stations: Dict[int, Dict],
    output_path: str,
    start_date: str = "2015-01-01",
    end_date: str = "2025-12-31",
    delay: float = 0.2,
) -> pd.DataFrame:
    """Download data for all discovered metro stations."""

    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOADING DATA FROM ALL METRO STATIONS")
    logger.info("=" * 70)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Stations to download: {len(stations)}")
    logger.info(f"Parameters: {list(PARAMETERS.keys())}")

    all_data = []
    successful = 0

    # Sort by parameter count (most params first)
    sorted_stations = sorted(stations.items(), key=lambda x: -x[1]['total_param_count'])

    for i, (station_id, station_info) in enumerate(sorted_stations):
        station_name = station_info['name']
        n_params = station_info['total_param_count']

        logger.info(f"\n[{i+1}/{len(stations)}] {station_name} (ID: {station_id}, {n_params} params)")

        result = download_metro_station(station_id, station_info, start_date, end_date, delay)

        if result[0] is not None and len(result[0]) > 0:
            df, params_downloaded = result
            all_data.append(df)
            successful += 1
            logger.info(f"  Downloaded {params_downloaded} params, {len(df)} records")
        else:
            logger.warning(f"  No data retrieved")

    if not all_data:
        logger.error("No data downloaded!")
        return pd.DataFrame()

    # Combine all stations
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values(['station_name', 'date'])

    # Reorder columns
    first_cols = ['date', 'station_id', 'station_name', 'latitude', 'longitude', 'elevation']
    param_cols = list(PARAMETERS.keys())
    available_cols = first_cols + [c for c in param_cols if c in combined_df.columns]
    combined_df = combined_df[available_cols]

    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Stations downloaded: {successful}/{len(stations)}")
    logger.info(f"Total records: {len(combined_df):,}")
    logger.info(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    logger.info(f"Output: {output_path}")

    # Coverage summary
    logger.info("\nParameter Coverage:")
    for param in param_cols:
        if param in combined_df.columns:
            non_null = combined_df[param].notna().sum()
            pct = non_null / len(combined_df) * 100
            logger.info(f"  {param:15}: {non_null:>8,} records ({pct:5.1f}%)")

    return combined_df


def main():
    parser = argparse.ArgumentParser(
        description='Download SMHI data from ALL multi-parameter stations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover stations with 3+ parameters (including snow)
  python download_smhi_metro_all.py --discover-only

  # Download from all stations with 3+ parameters
  python download_smhi_metro_all.py --output data/raw/smhi_metro_all.csv

  # Stricter: require 5+ parameters
  python download_smhi_metro_all.py --output data/raw/smhi_metro_strict.csv --min-params 5

  # Include stations without snow (all multi-param stations)
  python download_smhi_metro_all.py --output data/raw/smhi_all_metro.csv --no-require-snow

  # Save discovered stations to JSON
  python download_smhi_metro_all.py --discover-only --save-stations stations.json
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/smhi_metro_all.csv',
                        help='Output file path')
    parser.add_argument('--start-date', type=str, default='2015-01-01',
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2025-12-31',
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--min-params', type=int, default=3,
                        help='Minimum number of parameters a station must have (default: 3)')
    parser.add_argument('--no-require-snow', action='store_true',
                        help='Include stations without snow depth parameter')
    parser.add_argument('--delay', type=float, default=0.2,
                        help='Delay between API requests (seconds)')
    parser.add_argument('--discover-only', action='store_true',
                        help='Only discover stations, do not download data')
    parser.add_argument('--save-stations', type=str,
                        help='Save discovered stations to JSON file')

    args = parser.parse_args()

    # Discover stations
    stations = discover_metro_stations(
        min_params=args.min_params,
        require_snow=not args.no_require_snow
    )

    if not stations:
        logger.error("No stations found matching criteria!")
        return

    # Print discovered stations
    print_discovered_stations(stations)

    # Save stations to JSON if requested
    if args.save_stations:
        with open(args.save_stations, 'w') as f:
            # Convert to serializable format
            stations_json = {str(k): v for k, v in stations.items()}
            json.dump(stations_json, f, indent=2)
        logger.info(f"\nStations saved to: {args.save_stations}")

    # Download data if not discover-only
    if not args.discover_only:
        df = download_all_metro_stations(
            stations=stations,
            output_path=args.output,
            start_date=args.start_date,
            end_date=args.end_date,
            delay=args.delay,
        )

        if len(df) > 0:
            print(f"\nDownload complete!")
            print(f"  Total records: {len(df):,}")
            print(f"  Stations: {df['station_name'].nunique()}")
            print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
            print(f"  Output: {args.output}")


if __name__ == '__main__':
    main()
