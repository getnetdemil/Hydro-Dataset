"""
build_nordic_netcdf.py — M6 deliverable

Assembles the full Nordic domain NetCDF from SMHI station CSVs produced by
fetch_smhi.py. Covers all SMHI stations in the Nordic bounding box over the
2015-16 through 2023-24 winter seasons.

Output: data/processed/nordic/nordic_tier0_2015_2024.nc (CF-1.9 compliant)

Tier 0 variables: snow_depth, temp_mean, precip, frozen_precip
Domain: Nordic (lat 55–70°N, lon 10–30°E)
Period: 2015-10-01 to 2024-04-30 (nine winter seasons)
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
logger = logging.getLogger('build_nordic_netcdf')

# --- Configuration ---
LAT_MIN, LAT_MAX = 55.0, 70.0
LON_MIN, LON_MAX = 10.0, 30.0
START_DATE = '2015-10-01'
END_DATE   = '2024-04-30'
OUTPUT_PATH = PROCESSED_DIR / 'nordic' / 'nordic_tier0_2015_2024.nc'
SMHI_DIR = RAW_DIR / 'smhi'

# Minimum data completeness: stations with fewer snow-depth days are excluded
MIN_SNOW_DAYS = 30


def load_and_filter(csv_path: Path, data_col: str) -> pd.DataFrame:
    """Load a SMHI parameter CSV and apply geographic + temporal filters."""
    if not csv_path.exists():
        logger.warning(f'Missing: {csv_path} — {data_col} will be all NaN')
        return pd.DataFrame(
            columns=['date', 'station_id', 'station_name', 'lat', 'lon', data_col]
        )

    df = pd.read_csv(csv_path, parse_dates=['date'])
    original = len(df)

    df = df[
        (df['lat'] >= LAT_MIN) & (df['lat'] <= LAT_MAX) &
        (df['lon'] >= LON_MIN) & (df['lon'] <= LON_MAX) &
        (df['date'] >= START_DATE) & (df['date'] <= END_DATE)
    ]

    cols = ['date', 'station_id', 'station_name', 'lat', 'lon', data_col]
    df = df[[c for c in cols if c in df.columns]].reset_index(drop=True)

    logger.info(
        f'  {csv_path.name}: {original:,} rows → {len(df):,} after filter '
        f'({df["station_id"].nunique()} stations)'
    )
    return df


def build_dataset(df: pd.DataFrame) -> xr.Dataset:
    """Convert merged DataFrame to CF-compliant xarray Dataset."""
    station_meta = (
        df.groupby('station_id')
        .agg(station_name=('station_name', 'first'),
             lat=('lat', 'first'),
             lon=('lon', 'first'))
        .reset_index()
    )

    data_cols = ['snow_depth', 'temp_mean', 'precip', 'frozen_precip']
    pivot_cols = [c for c in data_cols if c in df.columns]

    # Deduplicate: take mean of any same-day duplicate rows per station
    df_dedup = (
        df.groupby(['station_id', 'date'])[pivot_cols]
        .mean()
    )
    ds = df_dedup.to_xarray().rename({'date': 'time'})

    meta_indexed = station_meta.set_index('station_id').reindex(ds['station_id'].values)
    ds = ds.assign_coords({
        'station_name': ('station_id', meta_indexed['station_name'].to_numpy(dtype=str)),
        'lat':          ('station_id', meta_indexed['lat'].values.astype(float)),
        'lon':          ('station_id', meta_indexed['lon'].values.astype(float)),
    })

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
        'lat':          {'standard_name': 'latitude',  'long_name': 'Station latitude',  'units': 'degrees_north'},
        'lon':          {'standard_name': 'longitude', 'long_name': 'Station longitude', 'units': 'degrees_east'},
        'station_name': {'long_name': 'Station name'},
        'time':         {'long_name': 'Time', 'axis': 'T'},
    }
    for var, attrs in var_attrs.items():
        if var in ds:
            ds[var].attrs = attrs
    for coord, attrs in coord_attrs.items():
        if coord in ds.coords:
            ds[coord].attrs = attrs

    ds.attrs = {
        'title':                'NordHydro: Full Nordic Domain 2015–2024, Tier 0',
        'institution':          'Hydro-Dataset / HydroImaging 2026',
        'source':               'SMHI MetObs Open Data API v1.0',
        'Conventions':          'CF-1.9',
        'history':              f'Created {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} by build_nordic_netcdf.py',
        'geospatial_lat_min':   LAT_MIN,
        'geospatial_lat_max':   LAT_MAX,
        'geospatial_lon_min':   LON_MIN,
        'geospatial_lon_max':   LON_MAX,
        'time_coverage_start':  START_DATE,
        'time_coverage_end':    END_DATE,
        'license':              'CC0 (SMHI Open Data)',
        'version':              '1.0',
        'seasons':              '2015-16 through 2023-24 (nine winter seasons)',
    }
    return ds


def main():
    logger.info('=== NordHydro Full Nordic NetCDF Builder ===')
    logger.info(f'Domain : lat [{LAT_MIN}, {LAT_MAX}], lon [{LON_MIN}, {LON_MAX}]')
    logger.info(f'Period : {START_DATE} – {END_DATE}')

    logger.info('Loading SMHI CSVs...')
    snow   = load_and_filter(SMHI_DIR / 'smhi_snow_depth.csv', 'snow_depth')
    temp   = load_and_filter(SMHI_DIR / 'smhi_temp_mean.csv',  'temp_mean')
    precip = load_and_filter(SMHI_DIR / 'smhi_precip.csv',     'precip')

    if snow.empty:
        logger.error('No snow depth data. Run fetch_smhi.py first.')
        sys.exit(1)

    # Drop stations with too few observations to be useful
    station_counts = snow.groupby('station_id')['snow_depth'].count()
    active = station_counts[station_counts >= MIN_SNOW_DAYS].index
    snow = snow[snow['station_id'].isin(active)]
    logger.info(
        f'Stations after completeness filter (>={MIN_SNOW_DAYS} days): '
        f'{len(active)} / {station_counts.shape[0]}'
    )

    logger.info('Merging parameters...')
    df = snow.merge(temp[['date', 'station_id', 'temp_mean']],   on=['date', 'station_id'], how='left')
    df = df.merge(precip[['date', 'station_id', 'precip']],       on=['date', 'station_id'], how='left')

    valid = df['precip'].notna() & df['temp_mean'].notna()
    df['frozen_precip'] = np.where(
        valid,
        ((df['precip'] > 0) & (df['temp_mean'] < 0)).astype(float),
        float('nan'),
    )

    logger.info(
        f'Merged: {len(df):,} rows, {df["station_id"].nunique()} stations, '
        f'{df["date"].nunique()} days'
    )

    logger.info('Building xarray Dataset...')
    ds = build_dataset(df)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    encoding = {'time': {'units': f'days since {START_DATE}', 'dtype': 'float64'}}
    ds.to_netcdf(OUTPUT_PATH, format='NETCDF4', engine='netcdf4', encoding=encoding)

    logger.info(f'Saved → {OUTPUT_PATH}')
    logger.info(f'Dataset summary:\n{ds}')


if __name__ == '__main__':
    main()
