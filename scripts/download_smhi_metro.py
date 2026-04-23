#!/usr/bin/env python3
"""
Download SMHI data for meteorological stations only.

These 15 stations have both snow depth AND meteorological parameters
(wind, humidity, pressure, dew point, cloud cover, and some have precipitation).

This gives a complete dataset for model training with all features.

Usage:
    python scripts/download_smhi_metro.py --output data/raw/smhi_metro.csv
    python scripts/download_smhi_metro.py --output data/raw/smhi_metro.csv --start-date 2018-01-01
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

# Meteorological stations with good multi-parameter coverage
# These stations have snow + multiple meteorological parameters
METRO_STATIONS = {
    # Station Name: (station_id, latitude, longitude, elevation, parameters_available)
    'Abisko Aut': (188790, 68.3538, 18.8164, 392.24, 7),           # 7 params including precip
    'Arjeplog A': (167710, 66.0513, 17.8396, 430.84, 7),           # 7 params including precip
    'Norrköping-SMHI': (86340, 58.5828, 16.1470, 40.33, 7),        # 7 params including precip
    'Enköping': (97380, 59.6406, 17.0655, 14.31, 6),               # 6 params
    'Falsterbo': (52230, 55.3837, 12.8167, 1.54, 6),               # 6 params (southernmost)
    'Linköping-Malmslätt': (85240, 58.3980, 15.5230, 94.00, 6),    # 6 params
    'Luleå-Kallax Flygplats': (162860, 65.5430, 22.1240, 19.90, 6), # 6 params
    'Ronneby-Bredåkra': (65160, 56.2670, 15.2650, 58.20, 6),       # 6 params
    'Såtenäs': (82260, 58.4280, 12.7110, 55.10, 6),                # 6 params
    'Vidsel': (160960, 65.8728, 20.1485, 180.06, 6),               # 6 params
    'Katterjåkk A': (188850, 68.4202, 18.1680, 514.25, 5),         # 5 params including precip
    'Stockholm-Observatoriekullen': (98210, 59.3417, 18.0549, 43.13, 5),  # 5 params
    'Katterjåkk': (188820, 68.4207, 18.1670, 513.91, 4),           # 4 params
    'Svenska Högarna': (99270, 59.4439, 19.5028, 10.14, 4),        # 4 params (island)
    'Uppsala Aut': (97510, 59.8471, 17.6320, 23.54, 4),            # 4 params
}

# Parameters to download
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
    station_name: str,
    station_info: tuple,
    start_date: str,
    end_date: str,
    delay: float = 0.2
) -> Optional[pd.DataFrame]:
    """Download all parameters for a single meteorological station."""
    station_id, lat, lon, elev, _ = station_info

    logger.info(f"  Downloading {station_name} (ID: {station_id})...")

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
            logger.debug(f"    {param_name}: {len(daily_df)} records")
        else:
            # Add empty column
            if param_name not in station_df.columns:
                station_df[param_name] = np.nan

    logger.info(f"    Downloaded {params_downloaded}/{len(PARAMETERS)} parameters")

    # Remove rows where ALL parameters are NaN (keep rows with at least some data)
    param_cols = list(PARAMETERS.keys())
    station_df = station_df.dropna(subset=param_cols, how='all')

    return station_df if len(station_df) > 0 else None


def download_all_metro_stations(
    output_path: str,
    start_date: str = "2015-01-01",
    end_date: str = "2023-12-31",
    delay: float = 0.2,
    stations: List[str] = None
) -> pd.DataFrame:
    """Download data for all meteorological stations."""

    logger.info("=" * 60)
    logger.info("SMHI METEOROLOGICAL STATIONS DOWNLOAD")
    logger.info("=" * 60)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Parameters: {list(PARAMETERS.keys())}")

    # Filter stations if specified
    if stations:
        station_dict = {k: v for k, v in METRO_STATIONS.items() if k in stations}
    else:
        station_dict = METRO_STATIONS

    logger.info(f"Stations to download: {len(station_dict)}")

    all_data = []
    successful = 0

    for i, (station_name, station_info) in enumerate(station_dict.items()):
        logger.info(f"\n[{i+1}/{len(station_dict)}] {station_name}")

        df = download_metro_station(station_name, station_info, start_date, end_date, delay)

        if df is not None and len(df) > 0:
            all_data.append(df)
            successful += 1
            logger.info(f"    Total records: {len(df)}")

    if not all_data:
        logger.error("No data downloaded!")
        return pd.DataFrame()

    # Combine all stations
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values(['station_name', 'date'])

    # Reorder columns
    first_cols = ['date', 'station_id', 'station_name', 'latitude', 'longitude', 'elevation']
    param_cols = list(PARAMETERS.keys())
    combined_df = combined_df[first_cols + param_cols]

    # Save to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_path, index=False)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Stations downloaded: {successful}/{len(station_dict)}")
    logger.info(f"Total records: {len(combined_df):,}")
    logger.info(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    logger.info(f"Output: {output_path}")

    # Coverage summary
    logger.info("\nParameter Coverage:")
    for param in param_cols:
        non_null = combined_df[param].notna().sum()
        pct = non_null / len(combined_df) * 100
        logger.info(f"  {param:15}: {non_null:>6,} records ({pct:5.1f}%)")

    return combined_df


def list_stations():
    """Print available meteorological stations."""
    print("\n" + "=" * 80)
    print("AVAILABLE METEOROLOGICAL STATIONS")
    print("=" * 80)
    print(f"\n{'Station Name':<35} {'ID':<10} {'Lat':>8} {'Lon':>8} {'Elev':>8} {'Params':>6}")
    print("-" * 80)

    for name, (sid, lat, lon, elev, params) in sorted(METRO_STATIONS.items(), key=lambda x: -x[1][4]):
        print(f"{name:<35} {sid:<10} {lat:>8.4f} {lon:>8.4f} {elev:>8.2f} {params:>6}")

    print("\n" + "=" * 80)
    print("GEOGRAPHIC COVERAGE")
    print("=" * 80)
    lats = [v[1] for v in METRO_STATIONS.values()]
    lons = [v[2] for v in METRO_STATIONS.values()]
    elevs = [v[3] for v in METRO_STATIONS.values()]
    print(f"Latitude range:  {min(lats):.2f}°N to {max(lats):.2f}°N")
    print(f"Longitude range: {min(lons):.2f}°E to {max(lons):.2f}°E")
    print(f"Elevation range: {min(elevs):.0f}m to {max(elevs):.0f}m")

    print("\n" + "=" * 80)
    print("PARAMETERS DOWNLOADED")
    print("=" * 80)
    for name, (pid, unit, desc, _) in PARAMETERS.items():
        print(f"  {name:<15} (ID {pid:>2}): {desc}")


def main():
    parser = argparse.ArgumentParser(
        description='Download SMHI data for meteorological stations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all 15 meteorological stations
  python download_smhi_metro.py --output data/raw/smhi_metro.csv

  # Download specific date range
  python download_smhi_metro.py --output data/raw/smhi_metro.csv --start-date 2018-01-01 --end-date 2023-12-31

  # Download only the best stations (7 parameters including precip)
  python download_smhi_metro.py --output data/raw/smhi_metro_best.csv --best-only

  # List available stations
  python download_smhi_metro.py --list-stations
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/smhi_metro.csv',
                        help='Output file path')
    parser.add_argument('--start-date', type=str, default='2015-01-01',
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2023-12-31',
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--delay', type=float, default=0.2,
                        help='Delay between API requests (seconds)')
    parser.add_argument('--best-only', action='store_true',
                        help='Download only stations with 7 parameters (including precip)')
    parser.add_argument('--list-stations', action='store_true',
                        help='List available stations and exit')

    args = parser.parse_args()

    if args.list_stations:
        list_stations()
        return

    # Filter to best stations if requested
    stations = None
    if args.best_only:
        stations = [name for name, info in METRO_STATIONS.items() if info[4] >= 7]
        logger.info(f"Downloading best stations only: {stations}")

    df = download_all_metro_stations(
        output_path=args.output,
        start_date=args.start_date,
        end_date=args.end_date,
        delay=args.delay,
        stations=stations
    )

    if len(df) > 0:
        print(f"\nDownload complete!")
        print(f"  Total records: {len(df):,}")
        print(f"  Stations: {df['station_name'].nunique()}")
        print(f"  Output: {args.output}")


if __name__ == '__main__':
    main()
