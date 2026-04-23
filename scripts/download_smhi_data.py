#!/usr/bin/env python3
"""
Download multiple meteorological parameters from SMHI Open Data API.

Downloads and merges data for:
- Snow depth (parameter 8)
- Temperature (parameter 2 - daily mean)
- Precipitation (parameter 5 - daily sum)
- Wind speed (parameter 4 - hourly, aggregated to daily)
- Humidity (parameter 6 - hourly, aggregated to daily)

SMHI API Documentation: https://opendata.smhi.se/apidocs/metobs/

Usage:
    # Download all parameters for model training
    python scripts/download_smhi_data.py --output data/raw/smhi_data.csv

    # Download specific parameters only
    python scripts/download_smhi_data.py --parameters snow,temp,precip --output data/raw/smhi_subset.csv

    # Download for specific date range
    python scripts/download_smhi_data.py --start-date 2020-01-01 --end-date 2025-12-31
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

# Parameter definitions
# Format: {name: (parameter_id, unit, description, aggregation_method)}
# Aggregation: 'mean', 'sum', 'max', 'min', 'last' (for hourly -> daily conversion)

# Core parameters for snow monitoring model
CORE_PARAMETERS = {
    'snow': (8, 'm', 'Snow depth', 'last'),
    'temp': (2, '°C', 'Air temperature (daily mean)', 'mean'),
    'precip': (14, 'mm', 'Precipitation (daily sum)', 'sum'),
    'wind': (4, 'm/s', 'Wind speed (10-min avg)', 'mean'),
    'humidity': (29, '%', 'Relative humidity', 'mean'),
}

# All available SMHI parameters (from smhi_parameters.csv)
ALL_PARAMETERS = {
    # Temperature
    'temp_instant': (1, '°C', 'Air temperature (instantaneous, hourly)', 'mean'),
    'temp': (2, '°C', 'Air temperature (daily mean)', 'mean'),
    'temp_min': (19, '°C', 'Air temperature (daily min)', 'min'),
    'temp_max': (20, '°C', 'Air temperature (daily max)', 'max'),
    'temp_min_12h': (26, '°C', 'Air temperature min (twice daily)', 'min'),
    'temp_max_12h': (27, '°C', 'Air temperature max (twice daily)', 'max'),
    'temp_monthly': (22, '°C', 'Air temperature (monthly mean)', 'mean'),
    'dew_point': (39, '°C', 'Dew point temperature (hourly)', 'mean'),

    # Wind
    'wind_dir': (3, '°', 'Wind direction (10-min mean, hourly)', 'mean'),
    'wind': (4, 'm/s', 'Wind speed (10-min mean, hourly)', 'mean'),
    'wind_gust': (21, 'm/s', 'Wind gust max (hourly)', 'max'),
    'wind_max_3h': (25, 'm/s', 'Max of mean wind speed (3-hour)', 'max'),

    # Precipitation
    'precip': (14, 'mm', 'Precipitation (daily sum)', 'sum'),
    'precip_intensity': (15, 'mm/h', 'Precipitation intensity (15-min max)', 'max'),
    'precip_12h': (17, 'mm', 'Precipitation (twice daily 06/18)', 'sum'),
    'precip_18': (18, 'mm', 'Precipitation (daily at 18 UTC)', 'sum'),
    'precip_monthly': (23, 'mm', 'Precipitation (monthly sum)', 'sum'),
    'precip_intensity_mean': (38, 'mm/h', 'Precipitation intensity (15-min mean max)', 'max'),

    # Snow
    'snow': (8, 'm', 'Snow depth (daily at 06 UTC)', 'last'),

    # Humidity & Pressure
    'humidity': (29, '%', 'Relative humidity (hourly)', 'mean'),
    'pressure': (9, 'hPa', 'Sea-level pressure (hourly)', 'mean'),

    # Radiation & Sunshine
    'sunshine': (10, 'h', 'Sunshine duration (hourly sum)', 'sum'),
    'irradiance_sw': (11, 'W/m²', 'Global irradiance shortwave (hourly)', 'mean'),
    'irradiance_lw': (24, 'W/m²', 'Longwave irradiance (hourly)', 'mean'),

    # Visibility & Clouds
    'visibility': (12, 'm', 'Horizontal visibility (hourly)', 'mean'),
    'cloud_cover': (16, '%', 'Total cloud cover (hourly)', 'mean'),
    'cloud_base_1': (28, 'm', 'Cloud base layer 1 (hourly)', 'mean'),
    'cloud_base_2': (30, 'm', 'Cloud base layer 2 (hourly)', 'mean'),
    'cloud_base_3': (32, 'm', 'Cloud base layer 3 (hourly)', 'mean'),
    'cloud_base_4': (34, 'm', 'Cloud base layer 4 (hourly)', 'mean'),
    'cloud_base_low': (36, 'm', 'Cloud base lowest (hourly)', 'min'),
    'cloud_base_high': (37, 'm', 'Cloud base highest (hourly)', 'max'),

    # Weather codes
    'weather_type_1': (31, 'code', 'Weather type 1 (hourly)', 'last'),
    'weather_type_2': (33, 'code', 'Weather type 2 (hourly)', 'last'),
    'weather_type_3': (35, 'code', 'Weather type 3 (hourly)', 'last'),

    # Ground state
    'ground_state': (40, 'code', 'Ground state code (daily)', 'last'),
}

# Recommended parameters for snow monitoring (subset of ALL_PARAMETERS)
RECOMMENDED_PARAMETERS = [
    'snow',           # Primary target
    'temp',           # Daily mean temperature
    'temp_min',       # Daily min (freeze/thaw cycles)
    'temp_max',       # Daily max (melt potential)
    'precip',         # Precipitation
    'wind',           # Wind speed
    'humidity',       # Relative humidity
    'pressure',       # Atmospheric pressure (weather patterns)
    'dew_point',      # Dew point (freeze prediction)
    'sunshine',       # Sunshine hours (melt)
    'irradiance_sw',  # Solar radiation (melt)
    'cloud_cover',    # Cloud cover (insulation)
    'ground_state',   # Ground condition code
]

# For backwards compatibility
PARAMETERS = CORE_PARAMETERS
ADDITIONAL_PARAMETERS = {k: v for k, v in ALL_PARAMETERS.items() if k not in CORE_PARAMETERS}


class SMHIDownloader:
    """Download meteorological data from SMHI Open Data API."""

    def __init__(
        self,
        min_lat: float = 55.0,
        max_lat: float = 70.0,
        min_lon: float = 10.0,
        max_lon: float = 25.0,
        start_date: str = "2015-01-01",
        end_date: str = "2025-12-31",
        delay: float = 0.2
    ):
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.delay = delay

    def get_stations_for_parameter(self, parameter_id: int) -> List[Dict]:
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

            if self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon:
                stations.append({
                    'id': s.get('key'),
                    'name': s.get('name'),
                    'latitude': lat,
                    'longitude': lon,
                    'height': s.get('height', None),
                    'active': s.get('active', False)
                })

        return stations

    def download_station_parameter(
        self,
        station_id: str,
        parameter_id: int,
        period: str = "corrected-archive"
    ) -> Optional[pd.DataFrame]:
        """Download data for a specific station and parameter."""
        url = f"{BASE_URL}/parameter/{parameter_id}/station/{station_id}/period/{period}/data.csv"

        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                return None

            content = resp.text
            lines = content.split('\n')

            # Find header line (starts with "Datum")
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
            df = df[(df['date'] >= self.start_date) & (df['date'] <= self.end_date)]

            return df if len(df) > 0 else None

        except Exception as e:
            logger.debug(f"Error downloading station {station_id}, param {parameter_id}: {e}")
            return None

    def aggregate_to_daily(
        self,
        df: pd.DataFrame,
        method: str = 'mean'
    ) -> pd.DataFrame:
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

    def download_parameter(
        self,
        param_name: str,
        param_info: Tuple[int, str, str, str]
    ) -> pd.DataFrame:
        """Download all data for a single parameter across all stations."""
        param_id, unit, description, agg_method = param_info
        logger.info(f"Downloading {description} (parameter {param_id})...")

        stations = self.get_stations_for_parameter(param_id)
        logger.info(f"  Found {len(stations)} stations")

        all_data = []
        successful = 0

        for i, station in enumerate(stations):
            if (i + 1) % 50 == 0:
                logger.info(f"  Processing station {i + 1}/{len(stations)}")

            df = self.download_station_parameter(station['id'], param_id)

            if df is not None and len(df) > 0:
                # Aggregate to daily if needed (for hourly parameters)
                df = self.aggregate_to_daily(df, agg_method)

                # Add station info
                df['station_id'] = station['id']
                df['station_name'] = station['name']
                df['latitude'] = station['latitude']
                df['longitude'] = station['longitude']
                df['elevation'] = station['height']

                # Rename value column
                df = df.rename(columns={'value': param_name})

                all_data.append(df)
                successful += 1

            time.sleep(self.delay)

        logger.info(f"  Downloaded from {successful}/{len(stations)} stations")

        if not all_data:
            return pd.DataFrame()

        combined = pd.concat(all_data, ignore_index=True)
        return combined

    def download_all_parameters(
        self,
        parameters: List[str] = None
    ) -> pd.DataFrame:
        """Download and merge all requested parameters."""
        if parameters is None:
            parameters = ['snow', 'temp', 'precip', 'wind', 'humidity']

        # Handle special parameter sets
        if len(parameters) == 1:
            if parameters[0] == 'core':
                parameters = list(CORE_PARAMETERS.keys())
            elif parameters[0] == 'recommended':
                parameters = RECOMMENDED_PARAMETERS.copy()
            elif parameters[0] == 'all':
                parameters = list(ALL_PARAMETERS.keys())

        # Validate parameters
        valid_params = []
        for p in parameters:
            if p in ALL_PARAMETERS:
                valid_params.append(p)
            else:
                logger.warning(f"Unknown parameter: {p}")

        if not valid_params:
            logger.error("No valid parameters specified!")
            return pd.DataFrame()

        logger.info(f"Downloading parameters: {valid_params}")
        logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")

        # Download each parameter
        param_dfs = {}
        for param_name in valid_params:
            param_info = ALL_PARAMETERS[param_name]
            df = self.download_parameter(param_name, param_info)
            if len(df) > 0:
                param_dfs[param_name] = df
                logger.info(f"  {param_name}: {len(df)} records from {df['station_name'].nunique()} stations")

        if not param_dfs:
            logger.error("No data downloaded!")
            return pd.DataFrame()

        # Find common stations across parameters
        # Use the first parameter as base (usually snow)
        base_param = valid_params[0]
        if base_param not in param_dfs:
            base_param = list(param_dfs.keys())[0]

        result = param_dfs[base_param].copy()
        merge_keys = ['date', 'station_id']

        # Merge other parameters
        for param_name, df in param_dfs.items():
            if param_name == base_param:
                continue

            # Keep only the parameter value column for merging
            merge_cols = merge_keys + [param_name]
            df_merge = df[merge_cols].drop_duplicates()

            result = result.merge(
                df_merge,
                on=merge_keys,
                how='left'
            )

        # Sort by station and date
        result = result.sort_values(['station_name', 'date'])

        # Reorder columns
        first_cols = ['date', 'station_id', 'station_name', 'latitude', 'longitude', 'elevation']
        param_cols = [p for p in valid_params if p in result.columns]
        other_cols = [c for c in result.columns if c not in first_cols + param_cols]
        result = result[first_cols + param_cols + other_cols]

        return result


def download_separate_files(
    output_dir: str,
    parameters: List[str],
    start_date: str,
    end_date: str,
    **kwargs
) -> Dict[str, pd.DataFrame]:
    """Download each parameter to a separate file (useful for large datasets)."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Handle special parameter sets
    if len(parameters) == 1:
        if parameters[0] == 'core':
            parameters = list(CORE_PARAMETERS.keys())
        elif parameters[0] == 'recommended':
            parameters = RECOMMENDED_PARAMETERS.copy()
        elif parameters[0] == 'all':
            parameters = list(ALL_PARAMETERS.keys())

    downloader = SMHIDownloader(
        start_date=start_date,
        end_date=end_date,
        **kwargs
    )

    results = {}
    total = len(parameters)
    for i, param_name in enumerate(parameters):
        if param_name not in ALL_PARAMETERS:
            logger.warning(f"Unknown parameter: {param_name}")
            continue

        logger.info(f"\n[{i+1}/{total}] Downloading {param_name}...")
        param_info = ALL_PARAMETERS[param_name]
        df = downloader.download_parameter(param_name, param_info)

        if len(df) > 0:
            file_path = output_path / f"smhi_{param_name}.csv"
            df.to_csv(file_path, index=False)
            logger.info(f"Saved {param_name} to {file_path} ({len(df):,} records)")
            results[param_name] = df

    return results


def list_available_parameters():
    """Print all available parameters."""
    print("\n" + "=" * 80)
    print("SMHI AVAILABLE PARAMETERS")
    print("=" * 80)

    # Group parameters by category
    categories = {
        'Temperature': ['temp_instant', 'temp', 'temp_min', 'temp_max', 'temp_min_12h',
                       'temp_max_12h', 'temp_monthly', 'dew_point'],
        'Wind': ['wind_dir', 'wind', 'wind_gust', 'wind_max_3h'],
        'Precipitation': ['precip', 'precip_intensity', 'precip_12h', 'precip_18',
                         'precip_monthly', 'precip_intensity_mean'],
        'Snow': ['snow'],
        'Humidity & Pressure': ['humidity', 'pressure'],
        'Radiation & Sunshine': ['sunshine', 'irradiance_sw', 'irradiance_lw'],
        'Visibility & Clouds': ['visibility', 'cloud_cover', 'cloud_base_1', 'cloud_base_2',
                                'cloud_base_3', 'cloud_base_4', 'cloud_base_low', 'cloud_base_high'],
        'Weather & Ground': ['weather_type_1', 'weather_type_2', 'weather_type_3', 'ground_state'],
    }

    for category, param_names in categories.items():
        print(f"\n--- {category} ---")
        print(f"{'Name':<20} {'ID':<4} {'Unit':<8} {'Description'}")
        print("-" * 75)
        for name in param_names:
            if name in ALL_PARAMETERS:
                pid, unit, desc, _ = ALL_PARAMETERS[name]
                recommended = "⭐" if name in RECOMMENDED_PARAMETERS else "  "
                print(f"{recommended}{name:<18} {pid:<4} {unit:<8} {desc}")

    print("\n" + "=" * 80)
    print("PARAMETER SETS")
    print("=" * 80)
    print(f"\n--parameters core        : {list(CORE_PARAMETERS.keys())}")
    print(f"--parameters recommended : {RECOMMENDED_PARAMETERS}")
    print(f"--parameters all         : All {len(ALL_PARAMETERS)} parameters")
    print("\n⭐ = Recommended for snow monitoring model")


def main():
    parser = argparse.ArgumentParser(
        description='Download SMHI meteorological data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download core parameters (snow, temp, precip, wind, humidity)
  python download_smhi_data.py --parameters core --output data/raw/smhi_core.csv

  # Download recommended parameters for snow model (13 parameters)
  python download_smhi_data.py --parameters recommended --output data/raw/smhi_recommended.csv

  # Download ALL 37 parameters (takes a long time!)
  python download_smhi_data.py --parameters all --separate --output-dir data/raw/all_params/

  # Download specific parameters
  python download_smhi_data.py --parameters snow,temp,precip,pressure --output data/raw/subset.csv

  # Download to separate files (recommended for large downloads)
  python download_smhi_data.py --parameters recommended --separate --output-dir data/raw/

  # List all available parameters
  python download_smhi_data.py --list-parameters

Parameter sets:
  core        : 5 basic parameters (snow, temp, precip, wind, humidity)
  recommended : 13 parameters optimized for snow monitoring
  all         : All 37 SMHI parameters
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/smhi_data.csv',
                        help='Output file path (for merged data)')
    parser.add_argument('--output-dir', type=str, default='data/raw',
                        help='Output directory (for separate files)')
    parser.add_argument('--parameters', type=str, default='core',
                        help='Parameters to download: "core", "recommended", "all", or comma-separated list')
    parser.add_argument('--separate', action='store_true',
                        help='Save each parameter to a separate file')
    parser.add_argument('--start-date', type=str, default='2015-01-01',
                        help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2025-12-31',
                        help='End date (YYYY-MM-DD)')
    parser.add_argument('--min-lat', type=float, default=55.0)
    parser.add_argument('--max-lat', type=float, default=70.0)
    parser.add_argument('--min-lon', type=float, default=10.0)
    parser.add_argument('--max-lon', type=float, default=25.0)
    parser.add_argument('--delay', type=float, default=0.2,
                        help='Delay between API requests (seconds)')
    parser.add_argument('--list-parameters', action='store_true',
                        help='List all available parameters and exit')

    args = parser.parse_args()

    if args.list_parameters:
        list_available_parameters()
        return

    parameters = [p.strip() for p in args.parameters.split(',')]

    if args.separate:
        # Download to separate files
        results = download_separate_files(
            output_dir=args.output_dir,
            parameters=parameters,
            start_date=args.start_date,
            end_date=args.end_date,
            min_lat=args.min_lat,
            max_lat=args.max_lat,
            min_lon=args.min_lon,
            max_lon=args.max_lon,
            delay=args.delay
        )

        print(f"\nDownload complete!")
        print(f"  Parameters downloaded: {list(results.keys())}")
        print(f"  Output directory: {args.output_dir}")

    else:
        # Download and merge all parameters
        downloader = SMHIDownloader(
            min_lat=args.min_lat,
            max_lat=args.max_lat,
            min_lon=args.min_lon,
            max_lon=args.max_lon,
            start_date=args.start_date,
            end_date=args.end_date,
            delay=args.delay
        )

        df = downloader.download_all_parameters(parameters)

        if len(df) > 0:
            # Save to file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)

            print(f"\nDownload complete!")
            print(f"  Total records: {len(df):,}")
            print(f"  Stations: {df['station_name'].nunique()}")
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"  Parameters: {[p for p in parameters if p in df.columns]}")
            print(f"  Output: {args.output}")

            # Print data coverage summary
            print(f"\nData coverage:")
            for param in parameters:
                if param in df.columns:
                    non_null = df[param].notna().sum()
                    total = len(df)
                    pct = 100 * non_null / total if total > 0 else 0
                    print(f"  {param}: {non_null:,}/{total:,} ({pct:.1f}%)")
        else:
            print("No data downloaded!")
            sys.exit(1)


if __name__ == '__main__':
    main()
