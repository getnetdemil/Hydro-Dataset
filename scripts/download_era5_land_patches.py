#!/usr/bin/env python3
"""
Download ERA5-Land patches (32x32 pixels per station) for Nordic snow monitoring.

This is Phase 1 / Month 1 of the multi-modal fusion project. Unlike
download_era5_finland.py (single variable, single grid-point scalar), this script
downloads 9 ERA5-Land variables and extracts a 32x32 pixel patch centred on each
station, producing per-station per-month NPZ shards ready for multi-modal fusion.

ERA5-Land dataset:  reanalysis-era5-land  (~9 km, 0.1 deg grid)
Variables (9):      2m_temperature, total_precipitation,
                    10m_u_component_of_wind, 10m_v_component_of_wind,
                    surface_solar_radiation_downwards,
                    snow_depth, snow_density, snowfall, skin_temperature
Area:               Nordic bbox (lat 55-71, lon 5-32) covers Sweden + Finland
Time:               12:00 UTC daily snapshot (pilot; accumulated-var handling
                    will be revisited when scaling beyond pilot)
Patch:              32x32 pixels centred on each station (nearest grid cell)

Output layout:
    data/raw/era5_land_nc/era5_land_YYYYMM.nc          (raw CDS downloads)
    data/processed/era5_land_patches/
        <station_id>/<YYYY-MM>.npz                     (per-station shards)
            keys: patch   (days, 32, 32, 9) float32
                  mask    (days, 32, 32)     uint8
                  dates   (days,)            |S10 (ISO YYYY-MM-DD)
                  channels (9,)              object (variable names)
                  station_id, latitude, longitude     scalars

Prerequisites:
    1. Register at https://cds.climate.copernicus.eu/
    2. Install CDS API key in ~/.cdsapirc
    3. pip install cdsapi xarray netcdf4

Usage:
    # Pilot: 10 stations, winter 2023-24
    python scripts/download_era5_land_patches.py \\
        --start-year 2023 --end-year 2024 --pilot 10

    # Full run (all 839 Nordic stations, 2015-2024 winters)
    python scripts/download_era5_land_patches.py \\
        --start-year 2015 --end-year 2024
"""

import argparse
import calendar
import logging
import sys
import time
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

WINTER_MONTHS = [10, 11, 12, 1, 2, 3, 4]

ERA5_LAND_VARS = [
    '2m_temperature',
    'total_precipitation',
    '10m_u_component_of_wind',
    '10m_v_component_of_wind',
    'surface_solar_radiation_downwards',
    'snow_depth',
    'snow_density',
    'snowfall',
    'skin_temperature',
]

ERA5_LAND_SHORT_NAMES = {
    '2m_temperature': 't2m',
    'total_precipitation': 'tp',
    '10m_u_component_of_wind': 'u10',
    '10m_v_component_of_wind': 'v10',
    'surface_solar_radiation_downwards': 'ssrd',
    'snow_depth': 'sde',
    'snow_density': 'rsn',
    'snowfall': 'sf',
    'skin_temperature': 'skt',
}

NORDIC_AREA = [71.0, 5.0, 55.0, 32.0]  # [north, west, south, east]


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


def load_station_metadata(
    smhi_file: Path,
    fmi_file: Path,
    pilot_n: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load and merge SMHI + FMI station metadata into a unified DataFrame.

    Keeps only the columns we need: station_id, latitude, longitude, source.
    Filters out stations with missing coordinates.

    Args:
        smhi_file: Path to SMHI station metadata CSV
        fmi_file:  Path to FMI station metadata CSV
        pilot_n:   If set, return only the first N stations (sorted by station_id)

    Returns:
        DataFrame with columns [station_id, latitude, longitude, source]
    """
    frames = []
    if smhi_file.exists():
        df_se = pd.read_csv(smhi_file, usecols=['station_id', 'latitude', 'longitude'])
        df_se['source'] = 'SMHI'
        frames.append(df_se)
        logger.info(f"Loaded {len(df_se)} SMHI stations from {smhi_file}")
    else:
        logger.warning(f"SMHI station file not found: {smhi_file}")

    if fmi_file.exists():
        df_fi = pd.read_csv(fmi_file, usecols=['station_id', 'latitude', 'longitude'])
        df_fi['source'] = 'FMI'
        frames.append(df_fi)
        logger.info(f"Loaded {len(df_fi)} FMI stations from {fmi_file}")
    else:
        logger.warning(f"FMI station file not found: {fmi_file}")

    if not frames:
        logger.error("No station metadata available. Aborting.")
        sys.exit(1)

    stations = pd.concat(frames, ignore_index=True)
    stations = stations.dropna(subset=['latitude', 'longitude'])
    stations = stations.drop_duplicates(subset=['station_id'])
    stations['station_id'] = stations['station_id'].astype(str)
    stations = stations.sort_values('station_id').reset_index(drop=True)

    if pilot_n is not None:
        stations = stations.head(pilot_n).reset_index(drop=True)
        logger.info(f"PILOT MODE: limited to first {pilot_n} stations")

    logger.info(f"Final station set: {len(stations)} stations "
                f"({(stations['source']=='SMHI').sum()} SE, "
                f"{(stations['source']=='FMI').sum()} FI)")
    return stations


def build_year_month_list(start_year: int, end_year: int) -> List[Tuple[int, int]]:
    """
    Build list of (year, month) tuples for winter months only.
    Matches logic in scripts/download_era5_finland.py for consistency.
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


def download_era5_land_month(
    year: int,
    month: int,
    raw_dir: Path,
    cdsapi_client,
    area: List[float] = NORDIC_AREA,
    max_retries: int = 3,
) -> Optional[Path]:
    """
    Download ERA5-Land multi-variable NetCDF for a single (year, month).

    Returns the file path or None on persistent failure. Skips if file exists.
    """
    _, n_days = calendar.monthrange(year, month)
    days = [f"{d:02d}" for d in range(1, n_days + 1)]

    out_file = raw_dir / f"era5_land_{year}{month:02d}.nc"
    if out_file.exists():
        logger.info(f"  {out_file.name} already exists - skipping download")
        return out_file

    request = {
        "variable": ERA5_LAND_VARS,
        "year":     str(year),
        "month":    f"{month:02d}",
        "day":      days,
        "time":     "12:00",
        "area":     area,
        "format":   "netcdf",
    }

    for attempt in range(1, max_retries + 1):
        logger.info(f"  Downloading ERA5-Land {year}-{month:02d} (attempt {attempt}/{max_retries})")
        try:
            cdsapi_client.retrieve("reanalysis-era5-land", request, str(out_file))
            return _unzip_if_needed(out_file)
        except Exception as e:
            logger.warning(f"  Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(60)
    logger.error(f"  ERA5-Land download failed permanently for {year}-{month:02d}")
    return None


def _unzip_if_needed(path: Path) -> Path:
    """
    CDS-Beta returns multi-variable ERA5-Land requests as a ZIP containing a
    single data_0.nc. If the downloaded file is a zip, extract the inner NetCDF
    in place (overwriting the zip with the extracted file contents).

    Returns the path to the usable NetCDF (same path as input).
    """
    if not zipfile.is_zipfile(path):
        return path
    logger.info(f"  {path.name} is a zip; extracting inner NetCDF")
    with zipfile.ZipFile(path) as z:
        members = z.namelist()
        nc_members = [m for m in members if m.endswith('.nc')]
        if not nc_members:
            raise RuntimeError(f"No .nc file found in zip {path}: {members}")
        inner_name = nc_members[0]
        tmp_dir = path.parent / f".{path.stem}_unzip"
        tmp_dir.mkdir(exist_ok=True)
        z.extract(inner_name, tmp_dir)
    extracted = tmp_dir / inner_name
    path.unlink()
    extracted.replace(path)
    tmp_dir.rmdir()
    return path


def _find_var_name(ds, candidates: List[str]) -> Optional[str]:
    """Return the first variable name from candidates that exists in the dataset."""
    for c in candidates:
        if c in ds.data_vars:
            return c
    return None


def extract_station_patches(
    nc_file: Path,
    stations: pd.DataFrame,
    patch_size: int = 32,
) -> dict:
    """
    Extract a patch_size x patch_size patch per station from an ERA5-Land NetCDF.

    Each station is placed at the centre of its patch (nearest grid cell).
    Patches that fall off the grid edge are padded with NaN (and masked).

    Returns:
        dict: station_id -> {
            'patch':   (days, H, W, C) float32,
            'mask':    (days, H, W)    uint8,
            'dates':   (days,)          list[str],
            'channels': list[str],
            'latitude', 'longitude': float,
        }
    """
    try:
        import xarray as xr
    except ImportError:
        logger.error("xarray not installed. Run: pip install xarray netcdf4")
        sys.exit(1)

    ds = xr.open_dataset(nc_file)

    time_dim = 'valid_time' if 'valid_time' in ds.coords else 'time'
    dates = pd.to_datetime(ds[time_dim].values)
    date_strs = [d.strftime('%Y-%m-%d') for d in dates]

    lats = ds['latitude'].values
    lons = ds['longitude'].values
    n_lat, n_lon = len(lats), len(lons)

    channels = []
    data_stack = []
    for long_name in ERA5_LAND_VARS:
        short = ERA5_LAND_SHORT_NAMES[long_name]
        varname = _find_var_name(ds, [short, long_name])
        if varname is None:
            logger.warning(f"Variable {long_name} ({short}) not found in {nc_file.name}; "
                           f"available: {list(ds.data_vars)}")
            continue
        arr = ds[varname].values  # (T, H, W)
        data_stack.append(arr)
        channels.append(short)

    if not data_stack:
        logger.error(f"No ERA5-Land variables could be extracted from {nc_file.name}")
        ds.close()
        return {}

    full = np.stack(data_stack, axis=-1).astype(np.float32)  # (T, H, W, C)
    ds.close()

    T, H, W, C = full.shape
    half = patch_size // 2
    result = {}

    for _, row in stations.iterrows():
        station_id = row['station_id']
        slat, slon = float(row['latitude']), float(row['longitude'])

        lat_idx = int(np.argmin(np.abs(lats - slat)))
        lon_idx = int(np.argmin(np.abs(lons - slon)))

        lat_start = lat_idx - half
        lat_end   = lat_idx + half
        lon_start = lon_idx - half
        lon_end   = lon_idx + half

        patch = np.full((T, patch_size, patch_size, C), np.nan, dtype=np.float32)
        mask = np.zeros((T, patch_size, patch_size), dtype=np.uint8)

        src_lat_lo = max(lat_start, 0)
        src_lat_hi = min(lat_end, n_lat)
        src_lon_lo = max(lon_start, 0)
        src_lon_hi = min(lon_end, n_lon)

        dst_lat_lo = src_lat_lo - lat_start
        dst_lat_hi = dst_lat_lo + (src_lat_hi - src_lat_lo)
        dst_lon_lo = src_lon_lo - lon_start
        dst_lon_hi = dst_lon_lo + (src_lon_hi - src_lon_lo)

        sub = full[:, src_lat_lo:src_lat_hi, src_lon_lo:src_lon_hi, :]
        patch[:, dst_lat_lo:dst_lat_hi, dst_lon_lo:dst_lon_hi, :] = sub

        valid = (~np.isnan(patch).any(axis=-1)).astype(np.uint8)
        mask[:, dst_lat_lo:dst_lat_hi, dst_lon_lo:dst_lon_hi] = valid[:, dst_lat_lo:dst_lat_hi, dst_lon_lo:dst_lon_hi]

        result[station_id] = {
            'patch':     patch,
            'mask':      mask,
            'dates':     date_strs,
            'channels':  channels,
            'latitude':  slat,
            'longitude': slon,
        }

    return result


def save_station_shards(
    patches: dict,
    shard_dir: Path,
    year: int,
    month: int,
) -> int:
    """Write one NPZ per station to shard_dir/<station_id>/<YYYY-MM>.npz."""
    written = 0
    ym = f"{year}-{month:02d}"
    for station_id, payload in patches.items():
        station_dir = shard_dir / str(station_id)
        station_dir.mkdir(parents=True, exist_ok=True)
        out_path = station_dir / f"{ym}.npz"
        np.savez_compressed(
            out_path,
            patch=payload['patch'],
            mask=payload['mask'],
            dates=np.array(payload['dates'], dtype='S10'),
            channels=np.array(payload['channels'], dtype=object),
            station_id=str(station_id),
            latitude=payload['latitude'],
            longitude=payload['longitude'],
        )
        written += 1
    return written


def all_shards_exist(
    stations: pd.DataFrame,
    shard_dir: Path,
    year: int,
    month: int,
) -> bool:
    """Return True iff every station already has a shard for this (year, month)."""
    ym = f"{year}-{month:02d}"
    for sid in stations['station_id']:
        if not (shard_dir / str(sid) / f"{ym}.npz").exists():
            return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Download ERA5-Land patches (32x32, 9 vars) for Nordic stations.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--smhi-station-file', type=str,
                        default='data/raw/station_metadata.csv')
    parser.add_argument('--fmi-station-file', type=str,
                        default='data/raw/fmi_station_metadata.csv')
    parser.add_argument('--raw-dir', type=str,
                        default='data/raw/era5_land_nc')
    parser.add_argument('--shard-dir', type=str,
                        default='data/processed/era5_land_patches')
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2024)
    parser.add_argument('--patch-size', type=int, default=32)
    parser.add_argument('--pilot', type=int, default=None,
                        help='If set, limit to first N stations (by sorted station_id)')
    args = parser.parse_args()

    cdsapi = _check_cdsapi()

    raw_dir = Path(args.raw_dir)
    shard_dir = Path(args.shard_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    shard_dir.mkdir(parents=True, exist_ok=True)

    stations = load_station_metadata(
        Path(args.smhi_station_file),
        Path(args.fmi_station_file),
        pilot_n=args.pilot,
    )

    year_months = build_year_month_list(args.start_year, args.end_year)
    logger.info(f"Year-month pairs to process: {len(year_months)}")

    client = cdsapi.Client()
    for i, (y, m) in enumerate(year_months, 1):
        logger.info(f"\n[{i}/{len(year_months)}] {y}-{m:02d}")

        if all_shards_exist(stations, shard_dir, y, m):
            logger.info(f"  All {len(stations)} station shards exist for {y}-{m:02d}; skipping")
            continue

        nc_file = download_era5_land_month(y, m, raw_dir, client)
        if nc_file is None:
            continue

        patches = extract_station_patches(nc_file, stations, patch_size=args.patch_size)
        if not patches:
            logger.warning(f"  No patches extracted from {nc_file.name}")
            continue

        n_written = save_station_shards(patches, shard_dir, y, m)
        logger.info(f"  Wrote {n_written} station shards to {shard_dir}")

    logger.info("\nDone.")


if __name__ == '__main__':
    main()
