"""
build_swe_grid.py — M4 deliverable

Kriging upscale: station snow_depth and SWE from the Dalarna pilot NetCDF
onto a 2.5 km LAEA EPSG:3035 grid.

Input:  data/processed/pilot/dalarna_tier0_2023_2024.nc  (22 stations × 213 days)
Output: data/processed/pilot/dalarna_swe_gridded_2023_2024.nc
"""

import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

import xarray as xr

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from common.config import PROCESSED_DIR
from common.io import save_to_netcdf
from derivation.hydrological_parameters import calculate_swe_sturm
from processing.alignment import harmonize_point_to_grid

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('build_swe_grid')

PILOT_NC   = PROCESSED_DIR / 'pilot' / 'dalarna_tier0_2023_2024.nc'
OUTPUT_NC  = PROCESSED_DIR / 'pilot' / 'dalarna_swe_gridded_2023_2024.nc'
GRID_RES_M = 2500.0
SNOW_CLASS  = 'taiga'


def main():
    logger.info('=== M4 SWE Grid Builder ===')
    logger.info(f'Input : {PILOT_NC}')
    logger.info(f'Output: {OUTPUT_NC}')

    # 1. Load station pilot data
    ds = xr.open_dataset(PILOT_NC)
    logger.info(f'Loaded: {ds.sizes["station_id"]} stations × {ds.sizes["time"]} days')

    # 2. Derive station-level SWE (Sturm 2010 taiga class)
    logger.info(f'Computing SWE (Sturm 2010, snow_class={SNOW_CLASS})...')
    swe_ds = calculate_swe_sturm(ds, ds, snow_class=SNOW_CLASS)
    logger.info(
        f'SWE range: {float(swe_ds["swe"].min()):.1f}–{float(swe_ds["swe"].max()):.1f} mm'
    )

    # 3. Krige snow_depth onto 2.5 km grid
    logger.info(f'Kriging snow_depth at {GRID_RES_M:.0f} m resolution...')
    grid_sd = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=GRID_RES_M)

    # 4. Krige SWE onto same grid
    logger.info(f'Kriging swe at {GRID_RES_M:.0f} m resolution...')
    grid_swe = harmonize_point_to_grid(swe_ds, variable='swe', grid_resolution_m=GRID_RES_M)

    # 5. Clip physical floor (kriging can produce small negatives at domain edges)
    grid_sd['snow_depth'] = grid_sd['snow_depth'].clip(min=0.0)
    grid_swe['swe'] = grid_swe['swe'].clip(min=0.0)

    # 7. Merge into one dataset
    out = xr.Dataset(
        {
            'snow_depth': grid_sd['snow_depth'],
            'swe':        grid_swe['swe'],
        },
        coords=grid_sd.coords,
    )
    out.attrs = {
        'title':        'NordHydro Pilot: Dalarna 2023-24, Gridded SWE (2.5 km LAEA)',
        'institution':  'Hydro-Dataset / HydroImaging 2026',
        'source':       'SMHI MetObs stations; Sturm et al. (2010) SWE model; OrdinaryKriging',
        'Conventions':  'CF-1.9',
        'history':      (
            f'Created {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")} '
            f'by build_swe_grid.py'
        ),
        'grid_mapping':      'EPSG:3035',
        'grid_resolution_m': GRID_RES_M,
        'snow_class':        SNOW_CLASS,
        'version':           '0.1-pilot',
    }

    # 8. Save
    OUTPUT_NC.parent.mkdir(parents=True, exist_ok=True)
    encoding = {'time': {'units': 'days since 2023-10-01', 'dtype': 'float64'}}
    out.to_netcdf(OUTPUT_NC, format='NETCDF4', engine='netcdf4', encoding=encoding)

    logger.info(f'Saved → {OUTPUT_NC}')
    logger.info(f'Grid shape: y={out.sizes["y"]}, x={out.sizes["x"]}, time={out.sizes["time"]}')
    logger.info(f'SWE grid max: {float(out["swe"].max()):.1f} mm')


if __name__ == '__main__':
    main()
