#!/usr/bin/env python3
"""
Download SMHI temperature data from all available stations.

Downloads temperature parameters:
- Parameter 2: Daily mean temperature (Lufttemperatur, dygnsmedelvärde)
- Parameter 19: Daily minimum temperature
- Parameter 20: Daily maximum temperature

Usage:
    python scripts/download_smhi_temp.py --output data/raw/smhi_temp.csv
    python scripts/download_smhi_temp.py --output data/raw/smhi_temp.csv --param temp_mean
    python scripts/download_smhi_temp.py --list-stations
"""

import requests
import pandas as pd
import numpy as np
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SMHI API configuration
BASE_URL = "https://opendata-download-metobs.smhi.se/api/version/1.0"

# Temperature parameters
TEMP_PARAMETERS = {
    'temp_mean': (2, '°C', 'Air temperature (daily mean)', 'mean'),
    'temp_min': (19, '°C', 'Air temperature (daily min)', 'min'),
    'temp_max': (20, '°C', 'Air temperature (daily max)', 'max'),
}

# Default date range
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE = "2025-12-31"


def get_stations_for_parameter(
    parameter_id: int,
    min_lat: float = 55.0,
    max_lat: float = 70.0,
    min_lon: float = 10.0,
    max_lon: float = 25.0
) -> List[Dict]:
    """Get list of stations that have data for a specific parameter."""
    url = f"{BASE_URL}/parameter/{parameter_id}.json"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch stations for parameter {parameter_id}: {e}")
        return []

    stations = []
    for s in data.get('station', []):
        lat = s.get('latitude', 0)
        lon = s.get('longitude', 0)

        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            stations.append({
                'id': s.get('key'),
                'name': s.get('name'),
                'latitude': lat,
                'longitude': lon,
                'elevation': s.get('height', None),
                'active': s.get('active', False),
                'from': s.get('measuringStations', {}).get('from', None) if isinstance(s.get('measuringStations'), dict) else None,
                'to': s.get('measuringStations', {}).get('to', None) if isinstance(s.get('measuringStations'), dict) else None,
            })

    return stations


def download_station_parameter(
    station_id: int,
    parameter_id: int,
    start_date: str,
    end_date: str,
    delay: float = 0.1
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
        df['date'] = pd.to_datetime(df['date'])

        # Filter by date range
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]

        # Aggregate to daily (in case of multiple readings)
        if len(df) > 0:
            daily = df.groupby('date')['value'].mean().reset_index()
            return daily

        return None

    except Exception as e:
        logger.debug(f"Error downloading station {station_id}, param {parameter_id}: {e}")
        return None


def download_temperature_data(
    output_path: str,
    parameters: List[str] = None,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    min_lat: float = 55.0,
    max_lat: float = 70.0,
    min_lon: float = 10.0,
    max_lon: float = 25.0,
    delay: float = 0.1,
    active_only: bool = False
) -> pd.DataFrame:
    """Download temperature data from all available stations."""

    if parameters is None:
        parameters = ['temp_mean', 'temp_min', 'temp_max']

    # Validate parameters
    valid_params = [p for p in parameters if p in TEMP_PARAMETERS]
    if not valid_params:
        logger.error(f"No valid parameters. Choose from: {list(TEMP_PARAMETERS.keys())}")
        return pd.DataFrame()

    logger.info("=" * 70)
    logger.info("SMHI TEMPERATURE DATA DOWNLOAD")
    logger.info("=" * 70)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Parameters: {valid_params}")
    logger.info(f"Geographic bounds: lat [{min_lat}, {max_lat}], lon [{min_lon}, {max_lon}]")

    all_data = []

    for param_name in valid_params:
        param_id, unit, desc, _ = TEMP_PARAMETERS[param_name]
        logger.info(f"\n{'='*60}")
        logger.info(f"Downloading {param_name} (Parameter {param_id}): {desc}")
        logger.info(f"{'='*60}")

        # Get stations for this parameter
        stations = get_stations_for_parameter(param_id, min_lat, max_lat, min_lon, max_lon)

        if active_only:
            stations = [s for s in stations if s.get('active', False)]

        logger.info(f"Found {len(stations)} stations")

        successful = 0
        for i, station in enumerate(stations):
            station_id = station['id']
            station_name = station['name']

            if (i + 1) % 50 == 0 or (i + 1) == len(stations):
                logger.info(f"  Processing station {i + 1}/{len(stations)}: {station_name}")

            df = download_station_parameter(station_id, param_id, start_date, end_date, delay)

            if df is not None and len(df) > 0:
                df['station_id'] = station_id
                df['station_name'] = station_name
                df['latitude'] = station['latitude']
                df['longitude'] = station['longitude']
                df['elevation'] = station['elevation']
                df['parameter'] = param_name
                df = df.rename(columns={'value': param_name})

                all_data.append(df)
                successful += 1

            time.sleep(delay)

        logger.info(f"  Downloaded from {successful}/{len(stations)} stations")

    if not all_data:
        logger.error("No data downloaded!")
        return pd.DataFrame()

    # Combine all data
    logger.info(f"\nCombining data...")
    combined_df = pd.concat(all_data, ignore_index=True)

    # Pivot to have parameters as columns
    if len(valid_params) > 1:
        # Group by station and date, then pivot
        pivot_dfs = []
        for param in valid_params:
            param_df = combined_df[combined_df['parameter'] == param].copy()
            if len(param_df) > 0:
                param_df = param_df.drop(columns=['parameter'])
                pivot_dfs.append(param_df)

        if pivot_dfs:
            # Merge all parameter dataframes
            result_df = pivot_dfs[0]
            for pdf in pivot_dfs[1:]:
                merge_cols = ['date', 'station_id']
                param_col = [c for c in pdf.columns if c in valid_params][0]
                result_df = result_df.merge(
                    pdf[merge_cols + [param_col]],
                    on=merge_cols,
                    how='outer'
                )
            combined_df = result_df
    else:
        combined_df = combined_df.drop(columns=['parameter'], errors='ignore')

    # Sort
    combined_df = combined_df.sort_values(['station_name', 'date'])

    # Reorder columns
    first_cols = ['date', 'station_id', 'station_name', 'latitude', 'longitude', 'elevation']
    param_cols = [p for p in valid_params if p in combined_df.columns]
    other_cols = [c for c in combined_df.columns if c not in first_cols + param_cols]
    combined_df = combined_df[[c for c in first_cols + param_cols + other_cols if c in combined_df.columns]]

    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)

    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total records: {len(combined_df):,}")
    logger.info(f"Stations: {combined_df['station_name'].nunique()}")
    logger.info(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    logger.info(f"Output: {output_path}")

    # Coverage summary
    logger.info("\nParameter Coverage:")
    for param in param_cols:
        non_null = combined_df[param].notna().sum()
        pct = non_null / len(combined_df) * 100
        logger.info(f"  {param:15}: {non_null:>8,} records ({pct:5.1f}%)")

    return combined_df


def list_stations(parameter: str = 'temp_mean'):
    """List all stations with temperature data."""
    if parameter not in TEMP_PARAMETERS:
        parameter = 'temp_mean'

    param_id = TEMP_PARAMETERS[parameter][0]
    stations = get_stations_for_parameter(param_id)

    print(f"\n{'='*90}")
    print(f"STATIONS WITH {parameter.upper()} DATA (Parameter {param_id})")
    print(f"{'='*90}")
    print(f"\n{'ID':<10} {'Name':<35} {'Lat':>8} {'Lon':>8} {'Elev':>8} {'Active':>8}")
    print("-" * 90)

    active_count = 0
    for s in sorted(stations, key=lambda x: -x['latitude']):
        active_str = "Yes" if s.get('active') else "No"
        if s.get('active'):
            active_count += 1
        elev = f"{s['elevation']:.1f}" if s['elevation'] else "N/A"
        print(f"{s['id']:<10} {s['name'][:34]:<35} {s['latitude']:>8.4f} {s['longitude']:>8.4f} {elev:>8} {active_str:>8}")

    print(f"\nTotal stations: {len(stations)} ({active_count} active)")

    print(f"\n{'='*90}")
    print("AVAILABLE TEMPERATURE PARAMETERS")
    print(f"{'='*90}")
    for name, (pid, unit, desc, _) in TEMP_PARAMETERS.items():
        n_stations = len(get_stations_for_parameter(pid))
        print(f"  {name:<15} (ID {pid:>2}): {desc} - {n_stations} stations")


def main():
    parser = argparse.ArgumentParser(
        description='Download SMHI temperature data from all stations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all temperature parameters (mean, min, max) from all stations
  python download_smhi_temp.py --output data/raw/smhi_temp.csv

  # Download only daily mean temperature
  python download_smhi_temp.py --param temp_mean --output data/raw/smhi_temp_mean.csv

  # Download with custom date range
  python download_smhi_temp.py --start-date 2018-01-01 --end-date 2023-12-31

  # Download only from active stations
  python download_smhi_temp.py --active-only --output data/raw/smhi_temp_active.csv

  # List available stations
  python download_smhi_temp.py --list-stations

Parameters:
  temp_mean : Daily mean temperature (Parameter 2)
  temp_min  : Daily minimum temperature (Parameter 19)
  temp_max  : Daily maximum temperature (Parameter 20)
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/smhi_temp.csv',
                        help='Output file path')
    parser.add_argument('--param', type=str, default='all',
                        help='Parameter to download: temp_mean, temp_min, temp_max, or "all"')
    parser.add_argument('--start-date', type=str, default=DEFAULT_START_DATE,
                        help=f'Start date (YYYY-MM-DD), default: {DEFAULT_START_DATE}')
    parser.add_argument('--end-date', type=str, default=DEFAULT_END_DATE,
                        help=f'End date (YYYY-MM-DD), default: {DEFAULT_END_DATE}')
    parser.add_argument('--min-lat', type=float, default=55.0)
    parser.add_argument('--max-lat', type=float, default=70.0)
    parser.add_argument('--min-lon', type=float, default=10.0)
    parser.add_argument('--max-lon', type=float, default=25.0)
    parser.add_argument('--delay', type=float, default=0.1,
                        help='Delay between API requests (seconds)')
    parser.add_argument('--active-only', action='store_true',
                        help='Download only from active stations')
    parser.add_argument('--list-stations', action='store_true',
                        help='List available stations and exit')

    args = parser.parse_args()

    if args.list_stations:
        list_stations()
        return

    # Determine parameters to download
    if args.param == 'all':
        parameters = ['temp_mean', 'temp_min', 'temp_max']
    else:
        parameters = [p.strip() for p in args.param.split(',')]

    df = download_temperature_data(
        output_path=args.output,
        parameters=parameters,
        start_date=args.start_date,
        end_date=args.end_date,
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        delay=args.delay,
        active_only=args.active_only
    )

    if len(df) > 0:
        print(f"\nDownload complete!")
        print(f"  Total records: {len(df):,}")
        print(f"  Stations: {df['station_name'].nunique()}")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"  Output: {args.output}")

        # Quick stats
        print(f"\nTemperature Statistics:")
        for param in ['temp_mean', 'temp_min', 'temp_max']:
            if param in df.columns and df[param].notna().sum() > 0:
                print(f"  {param}: min={df[param].min():.1f}°C, max={df[param].max():.1f}°C, mean={df[param].mean():.1f}°C")


if __name__ == '__main__':
    main()
