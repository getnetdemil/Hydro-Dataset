"""
build_pilot_netcdf.py — M3 deliverable

Assembles Dalarna pilot NetCDF from SMHI station CSVs produced by fetch_smhi.py.
Output: data/processed/pilot/dalarna_tier0_2023_2024.nc (CF-1.9 compliant)

Tier 0 variables: snow_depth, temp_mean, precip, frozen_precip (derived)
Domain: Dalarna county, Sweden (lat 60.0–61.5°N, lon 13.0–16.0°E)
Period: 2023-10-01 to 2024-04-30 (2023–24 winter season)
"""

import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from common.config import RAW_DIR, PROCESSED_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("build_pilot_netcdf")

# --- Configuration ---
LAT_MIN, LAT_MAX = 60.0, 61.5
LON_MIN, LON_MAX = 13.0, 16.0
START_DATE = "2023-10-01"
END_DATE   = "2024-04-30"
OUTPUT_PATH = PROCESSED_DIR / 'pilot' / 'dalarna_tier0_2023_2024.nc'

SMHI_DIR = RAW_DIR / 'smhi'


def load_and_filter(csv_path: Path, data_col: str) -> pd.DataFrame:
    """Load a SMHI parameter CSV and apply geographic + temporal filters."""
    if not csv_path.exists():
        logger.warning(f"  Missing: {csv_path} — {data_col} will be all NaN")
        return pd.DataFrame(columns=['date', 'station_id', 'station_name', 'lat', 'lon', data_col])

    df = pd.read_csv(csv_path, parse_dates=['date'])
    original = len(df)

    # Geographic filter
    df = df[(df['lat'] >= LAT_MIN) & (df['lat'] <= LAT_MAX) &
            (df['lon'] >= LON_MIN) & (df['lon'] <= LON_MAX)]

    # Temporal filter
    df = df[(df['date'] >= START_DATE) & (df['date'] <= END_DATE)]

    cols = ['date', 'station_id', 'station_name', 'lat', 'lon', data_col]
    df = df[[c for c in cols if c in df.columns]]

    logger.info(f"  {csv_path.name}: {original} rows → {len(df)} after filter "
                f"({df['station_id'].nunique()} stations)")
    return df.reset_index(drop=True)


def build_dataset(df: pd.DataFrame) -> xr.Dataset:
    """Convert merged DataFrame to CF-compliant xarray Dataset."""
    # Station metadata: one row per station
    station_meta = (
        df.groupby('station_id')
        .agg(station_name=('station_name', 'first'),
             lat=('lat', 'first'),
             lon=('lon', 'first'))
        .reset_index()
    )

    # Pivot to (station_id × date) grid
    data_cols = ['snow_depth', 'temp_mean', 'precip', 'frozen_precip']
    pivot_cols = [c for c in data_cols if c in df.columns]

    df_idx = df.set_index(['station_id', 'date'])[pivot_cols]
    ds = df_idx.to_xarray()
    ds = ds.rename({'date': 'time'})

    # Attach station metadata as coordinates
    station_ids = station_meta['station_id'].values
    # Ensure coordinate order matches xarray dimension
    meta_indexed = station_meta.set_index('station_id').reindex(ds['station_id'].values)

    ds = ds.assign_coords({
        'station_name': ('station_id', meta_indexed['station_name'].to_numpy(dtype=str)),
        'lat': ('station_id', meta_indexed['lat'].values.astype(float)),
        'lon': ('station_id', meta_indexed['lon'].values.astype(float)),
    })

    # --- CF variable attributes ---
    var_attrs = {
        'snow_depth': {
            'standard_name': 'surface_snow_thickness',
            'long_name': 'Snow depth',
            'units': 'm',
            'source': 'SMHI MetObs Open Data, parameter 8',
            '_FillValue': float('nan'),
        },
        'temp_mean': {
            'standard_name': 'air_temperature',
            'long_name': 'Daily mean air temperature at 2 m',
            'units': 'degC',
            'source': 'SMHI MetObs Open Data, parameter 2',
            '_FillValue': float('nan'),
        },
        'precip': {
            'standard_name': 'precipitation_amount',
            'long_name': 'Daily precipitation',
            'units': 'mm',
            'source': 'SMHI MetObs Open Data, parameter 5',
            '_FillValue': float('nan'),
        },
        'frozen_precip': {
            'long_name': 'Binary frozen precipitation flag',
            'comment': '1 = frozen (precip>0 and temp_mean<0), 0 = liquid, NaN = missing input',
            'units': '1',
            'source': 'Derived: precip > 0 and temp_mean < 0',
            '_FillValue': float('nan'),
        },
    }
    coord_attrs = {
        'lat': {'standard_name': 'latitude',  'long_name': 'Station latitude',  'units': 'degrees_north'},
        'lon': {'standard_name': 'longitude', 'long_name': 'Station longitude', 'units': 'degrees_east'},
        'station_name': {'long_name': 'Station name'},
        'time': {'long_name': 'Time', 'axis': 'T'},
    }

    for var, attrs in var_attrs.items():
        if var in ds:
            ds[var].attrs = attrs
    for coord, attrs in coord_attrs.items():
        if coord in ds.coords:
            ds[coord].attrs = attrs

    # --- Global attributes ---
    ds.attrs = {
        'title': 'NordHydro Pilot: Dalarna 2023-24 Season, Tier 0',
        'institution': 'Hydro-Dataset / HydroImaging 2026',
        'source': 'SMHI MetObs Open Data API v1.0',
        'Conventions': 'CF-1.9',
        'history': f'Created {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} by build_pilot_netcdf.py',
        'geospatial_lat_min': LAT_MIN,
        'geospatial_lat_max': LAT_MAX,
        'geospatial_lon_min': LON_MIN,
        'geospatial_lon_max': LON_MAX,
        'time_coverage_start': START_DATE,
        'time_coverage_end': END_DATE,
        'license': 'CC0 (SMHI Open Data)',
        'version': '0.1-pilot',
    }

    return ds


def main():
    logger.info("=== NordHydro Pilot NetCDF Builder ===")
    logger.info(f"Domain : lat [{LAT_MIN}, {LAT_MAX}], lon [{LON_MIN}, {LON_MAX}]")
    logger.info(f"Period : {START_DATE} – {END_DATE}")

    # Load and filter each parameter
    logger.info("Loading SMHI CSVs...")
    snow   = load_and_filter(SMHI_DIR / 'smhi_snow_depth.csv', 'snow_depth')
    temp   = load_and_filter(SMHI_DIR / 'smhi_temp_mean.csv',  'temp_mean')
    precip = load_and_filter(SMHI_DIR / 'smhi_precip.csv',     'precip')

    if snow.empty:
        logger.error("No snow depth data found for Dalarna. Run fetch_smhi.py first.")
        sys.exit(1)

    # Merge: snow stations as reference; left-join temp and precip
    logger.info("Merging parameters...")
    df = snow.merge(
        temp[['date', 'station_id', 'temp_mean']],
        on=['date', 'station_id'], how='left'
    )
    df = df.merge(
        precip[['date', 'station_id', 'precip']],
        on=['date', 'station_id'], how='left'
    )

    # Derive frozen_precip
    valid = df['precip'].notna() & df['temp_mean'].notna()
    df['frozen_precip'] = np.where(
        valid,
        ((df['precip'] > 0) & (df['temp_mean'] < 0)).astype(float),
        float('nan')
    )

    logger.info(f"Merged: {len(df)} rows, {df['station_id'].nunique()} stations, "
                f"{df['date'].nunique()} days")

    # Build xarray Dataset
    logger.info("Building xarray Dataset...")
    ds = build_dataset(df)

    # Save with CF-compliant time encoding
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    encoding = {
        'time': {'units': f'days since {START_DATE}', 'dtype': 'float64'},
    }
    ds.to_netcdf(OUTPUT_PATH, format='NETCDF4', engine='netcdf4', encoding=encoding)

    logger.info(f"Saved → {OUTPUT_PATH}")
    logger.info(f"Dataset summary:\n{ds}")


if __name__ == "__main__":
    main()
