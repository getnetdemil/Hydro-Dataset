#!/usr/bin/env python3
"""
Download ERA5 cloud cover for Finnish station locations via the Copernicus CDS API.

ERA5 is used exclusively to fill the two atmospheric features that are not
available from FMI station observations: total cloud cover (cloud_cover).
Visibility for Finnish stations is derived from the FMI WAWA weather
phenomenon code in download_fmi_hourly.py, so ERA5 is only needed for cloud.

ERA5 dataset:    reanalysis-era5-single-levels
Variable:        total_cloud_cover  (fraction 0–1 → converted to %)
Resolution:      0.25° × 0.25° (~25 km)
Time:            daily value at 12:00 UTC (representative of daily conditions)
Area:            Finland bounding box (59–71°N, 18–32°E)

Prerequisites:
    1. Register at https://cds.climate.copernicus.eu/
    2. Install CDS API key in ~/.cdsapirc:
         url: https://cds.climate.copernicus.eu/api/v2
         key: <your-uid>:<your-api-key>
    3. pip install cdsapi xarray cfgrib netcdf4

Usage:
    # Download cloud cover for all Finnish stations, Oct 2015 – Apr 2024
    python scripts/download_era5_finland.py \
        --station-file data/raw/fmi_station_metadata.csv

    # Single winter season
    python scripts/download_era5_finland.py \
        --station-file data/raw/fmi_station_metadata.csv \
        --start-year 2023 --end-year 2024

    # Test: 2024
    python scripts/download_era5_finland.py \
        --station-file data/raw/fmi_station_metadata.csv \
        --start-year 2023 --end-year 2024
"""

import argparse
import sys
from pathlib import Path
from datetime import date
from typing import List, Tuple, Optional
import logging

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WINTER_MONTHS = [10, 11, 12, 1, 2, 3, 4]
ERA5_AREA     = [71, 18, 59, 32]   # [north, west, south, east]


def _check_cdsapi():
    try:
        import cdsapi
        return cdsapi
    except ImportError:
        logger.error(
            "cdsapi not installed. Run: pip install cdsapi\n"
            "Also ensure ~/.cdsapirc is configured with your CDS API key.\n"
            "Register at: https://cds.climate.copernicus.eu/"
        )
        sys.exit(1)


def build_year_month_list(start_year: int, end_year: int) -> List[Tuple[int, int]]:
    """
    Build list of (year, month) tuples for winter months only.

    E.g., start_year=2015, end_year=2024 →
        (2015,10), (2015,11), (2015,12), (2016,1), ..., (2024,4)
    """
    pairs = []
    for y in range(start_year, end_year + 1):
        for m in WINTER_MONTHS:
            if m >= 10:
                if y < end_year:
                    pairs.append((y, m))
            else:
                if y <= end_year:
                    pairs.append((y, m))
    return pairs


def download_era5_month(
    year: int,
    month: int,
    raw_dir: Path,
    cdsapi_client,
    area: List[float] = ERA5_AREA,
) -> Optional[Path]:
    """
    Download ERA5 total_cloud_cover for a single year-month.

    Downloads as NetCDF to raw_dir/era5_cloud_{YYYY}{MM:02d}.nc.
    Returns the file path or None on failure.
    """
    import calendar
    _, n_days = calendar.monthrange(year, month)
    days = [f"{d:02d}" for d in range(1, n_days + 1)]

    out_file = raw_dir / f"era5_cloud_{year}{month:02d}.nc"
    if out_file.exists():
        logger.info(f"  {out_file.name} already exists — skipping download")
        return out_file

    logger.info(f"  Downloading ERA5 cloud cover {year}-{month:02d} ...")
    try:
        cdsapi_client.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "variable":     ["total_cloud_cover"],
                "year":         str(year),
                "month":        f"{month:02d}",
                "day":          days,
                "time":         "12:00",
                "area":         area,
                "format":       "netcdf",
            },
            str(out_file),
        )
        return out_file
    except Exception as e:
        logger.error(f"  ERA5 download failed for {year}-{month:02d}: {e}")
        return None


def extract_cloud_at_stations(
    nc_file: Path,
    stations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract total cloud cover at each station's nearest ERA5 grid cell.

    Args:
        nc_file:   Path to ERA5 NetCDF file
        stations:  DataFrame with columns [station_id, latitude, longitude]

    Returns:
        DataFrame with columns [date, station_id, cloud_cover]
        cloud_cover is in percent (0–100).
    """
    try:
        import xarray as xr
    except ImportError:
        logger.error("xarray not installed. Run: pip install xarray netcdf4")
        sys.exit(1)

    ds = xr.open_dataset(nc_file)

    # ERA5 variable name may be 'tcc' or 'total_cloud_cover'
    tcc_var = 'tcc' if 'tcc' in ds else 'total_cloud_cover'
    if tcc_var not in ds:
        available = list(ds.data_vars)
        logger.warning(f"Cloud cover variable not found. Available: {available}")
        ds.close()
        return pd.DataFrame()

    tcc = ds[tcc_var]  # dims: (valid_time, latitude, longitude)
    lats = ds['latitude'].values
    lons = ds['longitude'].values
    time_dim = 'valid_time' if 'valid_time' in ds.coords else 'time'
    times = pd.to_datetime(ds[time_dim].values)

    records = []
    for _, row in stations.iterrows():
        # Nearest ERA5 grid point
        lat_idx = int(np.argmin(np.abs(lats - row['latitude'])))
        lon_idx = int(np.argmin(np.abs(lons - row['longitude'])))

        values = tcc.isel(latitude=lat_idx, longitude=lon_idx).values  # fraction 0-1

        for t, v in zip(times, values):
            records.append({
                'date':        t.date(),
                'station_id':  row['station_id'],
                'cloud_cover': float(v) * 100.0 if not np.isnan(v) else np.nan,
            })

    ds.close()
    return pd.DataFrame(records)


def download_era5_finland(
    station_file: str = "data/raw/fmi_station_metadata.csv",
    output_path: str = "data/raw/era5_finland_cloud.csv",
    raw_dir: str = "data/raw/era5_cloud",
    start_year: int = 2015,
    end_year: int = 2024,
    area: List[float] = ERA5_AREA,
) -> pd.DataFrame:
    """
    Download ERA5 cloud cover for all Finnish stations and save to CSV.

    Args:
        station_file: Path to FMI station metadata CSV
        output_path:  Output CSV path
        raw_dir:      Directory for intermediate NetCDF files
        start_year:   First winter year
        end_year:     Last year (April is the last month downloaded)
        area:         ERA5 bounding box [north, west, south, east]

    Returns:
        DataFrame with columns [date, station_id, cloud_cover]
    """
    cdsapi = _check_cdsapi()

    stations_path = Path(station_file)
    if not stations_path.exists():
        logger.error(f"Station file not found: {station_file}")
        logger.error("Run download_fmi_stations.py first.")
        sys.exit(1)

    stations = pd.read_csv(stations_path)
    logger.info(f"Loaded {len(stations)} stations from {station_file}")

    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume: load existing
    existing_frames = []
    covered_months = set()
    if output_path.exists():
        try:
            existing_df = pd.read_csv(output_path, parse_dates=['date'])
            existing_df['date'] = existing_df['date'].dt.date
            # Determine which (year, month) pairs are already covered
            existing_df['ym'] = existing_df['date'].apply(lambda d: (d.year, d.month))
            covered_months = set(existing_df['ym'].unique())
            existing_df = existing_df.drop(columns=['ym'])
            existing_frames.append(existing_df)
            logger.info(f"Resuming: {len(covered_months)} year-month pairs already done")
        except Exception as e:
            logger.warning(f"Could not load existing file: {e}")

    client = cdsapi.Client()
    year_months = build_year_month_list(start_year, end_year)
    todo = [(y, m) for y, m in year_months if (y, m) not in covered_months]
    logger.info(f"Year-month pairs to download: {len(todo)}")

    new_frames = []
    for i, (y, m) in enumerate(todo, 1):
        logger.info(f"[{i}/{len(todo)}] {y}-{m:02d}")
        nc_file = download_era5_month(y, m, raw_path, client, area=area)
        if nc_file is None:
            continue
        df_month = extract_cloud_at_stations(nc_file, stations)
        if not df_month.empty:
            new_frames.append(df_month)
            logger.info(f"  Extracted {len(df_month)} rows from {nc_file.name}")

    parts = existing_frames + new_frames
    if not parts:
        logger.error("No data to save.")
        return pd.DataFrame()

    combined = pd.concat(parts, ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date']).dt.date
    combined = combined.drop_duplicates(subset=['date', 'station_id'], keep='last')
    combined = combined.sort_values(['station_id', 'date']).reset_index(drop=True)

    combined.to_csv(output_path, index=False)
    logger.info(f"\nSaved {len(combined):,} rows → {output_path}")
    logger.info(f"  Stations: {combined['station_id'].nunique()}")
    logger.info(f"  Dates:    {combined['date'].nunique()}")

    return combined


def main():
    parser = argparse.ArgumentParser(
        description='Download ERA5 cloud cover for Finnish stations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisites:
  1. pip install cdsapi xarray netcdf4
  2. Register at https://cds.climate.copernicus.eu/ and set up ~/.cdsapirc

Examples:
  python scripts/download_era5_finland.py \\
      --station-file data/raw/fmi_station_metadata.csv

  python scripts/download_era5_finland.py \\
      --station-file data/raw/fmi_station_metadata.csv \\
      --start-year 2023 --end-year 2024
        """
    )

    parser.add_argument('--station-file', type=str, default='data/raw/fmi_station_metadata.csv')
    parser.add_argument('--output', type=str, default='data/raw/era5_finland_cloud.csv')
    parser.add_argument('--raw-dir', type=str, default='data/raw/era5_cloud')
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2024)

    args = parser.parse_args()

    df = download_era5_finland(
        station_file=args.station_file,
        output_path=args.output,
        raw_dir=args.raw_dir,
        start_year=args.start_year,
        end_year=args.end_year,
    )

    if df.empty:
        print("ERROR: No data saved.", file=sys.stderr)
        sys.exit(1)
    print(f"\nDone! {len(df):,} rows → {args.output}")


if __name__ == '__main__':
    main()
