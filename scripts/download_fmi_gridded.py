#!/usr/bin/env python3
"""
Download FMI gridded observations from public AWS S3 and extract pixel values
at all 440 FMI station locations.

S3 bucket : fmi-gridded-obs-daily-1km  (public, anonymous)
Variables  : Snow, Tday, Tmin, RRday, Rh
CRS        : UTM Zone 35N / ETRS89 (EPSG:3067); Lon=easting, Lat=northing (metres)
Strategy   : download each annual NetCDF to /tmp, extract station pixels, delete

Output: data/raw/fmi_gridded_daily.csv
Columns: station_id, date, snow_depth_grid, temperature_grid, tmin_grid,
         precipitation_grid, humidity_grid

Usage:
    python scripts/download_fmi_gridded.py
    python scripts/download_fmi_gridded.py --start-year 2015 --end-year 2024
    python scripts/download_fmi_gridded.py --output data/raw/fmi_gridded_daily.csv
"""

import argparse
import logging
import shutil
import tempfile
from pathlib import Path

import boto3
import numpy as np
import pandas as pd
import xarray as xr
from botocore import UNSIGNED
from botocore.config import Config
from pyproj import Transformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BUCKET = "fmi-gridded-obs-daily-1km"
REGION = "eu-west-1"

# S3 path pattern: Netcdf/<Dir>/<prefix>_YYYY.nc
# Variable name inside the NetCDF is the directory name (capitalized)
VARIABLES = {
    "snow_depth_grid":    ("Snow",  "snow"),
    "temperature_grid":   ("Tday",  "tday"),
    "tmin_grid":          ("Tmin",  "tmin"),
    "precipitation_grid": ("RRday", "rrday"),
    "humidity_grid":      ("Rh",    "rh"),
}

WINTER_MONTHS = {10, 11, 12, 1, 2, 3, 4}
DEFAULT_START = 2015
DEFAULT_END   = 2024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def s3_client():
    return boto3.client(
        "s3",
        config=Config(signature_version=UNSIGNED),
        region_name=REGION,
    )


def load_stations(metadata_path: Path) -> pd.DataFrame:
    df = pd.read_csv(metadata_path)
    df["station_id"] = df["station_id"].astype(str)
    # Transform WGS84 (lon, lat) → ETRS89/TM35FIN (easting, northing) in metres
    xformer = Transformer.from_crs("EPSG:4326", "EPSG:3067", always_xy=True)
    df["easting"], df["northing"] = xformer.transform(
        df["longitude"].values, df["latitude"].values
    )
    logger.info(f"Loaded {len(df)} stations from {metadata_path}")
    return df


def compute_grid_indices(ds: xr.Dataset, stations: pd.DataFrame):
    """Return (lat_idx, lon_idx) arrays for each station (computed once, reused)."""
    lons = ds["Lon"].values   # easting, ascending
    lats = ds["Lat"].values   # northing, descending
    lat_idx = np.array([np.argmin(np.abs(lats - n)) for n in stations["northing"].values])
    lon_idx = np.array([np.argmin(np.abs(lons - e)) for e in stations["easting"].values])
    return lat_idx, lon_idx


def extract_variable(
    nc_path: Path,
    col_name: str,
    dir_name: str,
    stations: pd.DataFrame,
    grid_indices: tuple | None,
) -> tuple[pd.DataFrame, tuple]:
    """
    Open a local NetCDF, extract (time, n_station) values at station grid cells,
    filter to winter months, return long-format DataFrame and cached grid_indices.
    """
    ds = xr.open_dataset(nc_path, engine="scipy")

    # Resolve variable name (dir_name, lowercase, or first variable)
    candidates = [dir_name, dir_name.lower(), dir_name.upper()]
    var_name = next((c for c in candidates if c in ds.data_vars), None)
    if var_name is None:
        var_name = list(ds.data_vars)[0]
        logger.warning(f"    Variable '{dir_name}' not found; using '{var_name}'")

    # Grid indices are the same across all years/variables — compute once
    if grid_indices is None:
        grid_indices = compute_grid_indices(ds, stations)
        logger.info(f"    Grid indices computed for {len(stations)} stations")

    lat_idx, lon_idx = grid_indices

    # Load full time × station slice
    times = pd.to_datetime(ds["Time"].values)
    data = ds[var_name].values[:, lat_idx, lon_idx]   # (n_time, n_stations)
    ds.close()

    # Filter to winter months
    winter_mask = np.array([t.month in WINTER_MONTHS for t in times])
    data_w = data[winter_mask]                         # (n_winter, n_stations)
    times_w = times[winter_mask]

    # Build long-format DataFrame (vectorized)
    dates = pd.to_datetime(times_w).date
    df_wide = pd.DataFrame(
        data_w,
        index=dates,
        columns=stations["station_id"].values,
    )
    df_long = df_wide.stack().reset_index()
    df_long.columns = ["date", "station_id", col_name]
    df_long["date"] = pd.to_datetime(df_long["date"])

    return df_long, grid_indices


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Download FMI gridded S3 data at station locations")
    parser.add_argument("--stations", default="data/raw/fmi_station_metadata.csv")
    parser.add_argument("--output",   default="data/raw/fmi_gridded_daily.csv")
    parser.add_argument("--start-year", type=int, default=DEFAULT_START)
    parser.add_argument("--end-year",   type=int, default=DEFAULT_END)
    parser.add_argument("--cache-dir",  default=None,
                        help="Local directory for temporary NetCDF downloads (default: system temp)")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    stations_path = base_dir / args.stations
    output_path   = base_dir / args.output

    stations = load_stations(stations_path)
    s3 = s3_client()

    # Load already-completed (year, col) pairs to support resume
    done = set()
    if output_path.exists():
        existing = pd.read_csv(output_path, usecols=["date"])
        # We track completion at the variable×year level via a sidecar set
        # (simple: if output exists, we check which (year, col) pairs contributed)
        logger.info(f"Existing output found: {len(existing):,} rows — will append new data")
        existing_full = pd.read_csv(output_path)
        # Mark years fully present for each variable
        existing_full["year"] = pd.to_datetime(existing_full["date"]).dt.year
        for col in VARIABLES:
            if col in existing_full.columns:
                for yr in existing_full["year"].unique():
                    done.add((int(yr), col))
    else:
        existing_full = pd.DataFrame()

    use_temp = args.cache_dir is None
    cache_dir = Path(tempfile.mkdtemp(prefix="fmi_grid_")) if use_temp else Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    all_frames = []
    grid_indices = None   # computed once from first file, reused

    years = range(args.start_year, args.end_year + 1)
    for year in years:
        year_frames = {}
        for col_name, (dir_name, file_prefix) in VARIABLES.items():
            if (year, col_name) in done:
                logger.info(f"[{year}] {col_name}: already done, skipping")
                continue

            s3_key    = f"Netcdf/{dir_name}/{file_prefix}_{year}.nc"
            nc_local  = cache_dir / f"{file_prefix}_{year}.nc"

            logger.info(f"[{year}] {col_name}: downloading s3://{BUCKET}/{s3_key}")
            try:
                s3.download_file(BUCKET, s3_key, str(nc_local))
            except Exception as e:
                logger.warning(f"[{year}] {col_name}: download failed — {e}")
                continue

            logger.info(f"[{year}] {col_name}: extracting {len(stations)} station pixels")
            try:
                df_var, grid_indices = extract_variable(
                    nc_local, col_name, dir_name, stations, grid_indices
                )
                year_frames[col_name] = df_var
                n_notnull = df_var[col_name].notna().sum()
                logger.info(f"[{year}] {col_name}: {len(df_var):,} rows, "
                            f"{n_notnull:,} non-NaN ({100*n_notnull/len(df_var):.1f}%)")
            except Exception as e:
                logger.error(f"[{year}] {col_name}: extraction failed — {e}")
            finally:
                nc_local.unlink(missing_ok=True)

        if not year_frames:
            continue

        # Join all variables for this year on (date, station_id)
        cols = list(year_frames.keys())
        df_year = year_frames[cols[0]]
        for col in cols[1:]:
            df_year = df_year.merge(year_frames[col], on=["date", "station_id"], how="outer")
        all_frames.append(df_year)
        logger.info(f"[{year}] merged: {len(df_year):,} rows")

    if use_temp:
        shutil.rmtree(cache_dir, ignore_errors=True)

    if not all_frames:
        logger.info("No new data to write.")
        return

    df_new = pd.concat(all_frames, ignore_index=True)
    df_new["station_id"] = df_new["station_id"].astype(str)

    # Combine with existing output
    if not existing_full.empty:
        df_out = pd.concat([existing_full, df_new], ignore_index=True)
        df_out = df_out.drop_duplicates(subset=["date", "station_id"]).sort_values(
            ["station_id", "date"]
        )
    else:
        df_out = df_new.sort_values(["station_id", "date"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False)
    logger.info(
        f"Saved {len(df_out):,} rows × {df_out.shape[1]} columns → {output_path}"
    )
    logger.info("Columns: " + ", ".join(df_out.columns.tolist()))
    logger.info("Stations: " + str(df_out["station_id"].nunique()))


if __name__ == "__main__":
    main()
