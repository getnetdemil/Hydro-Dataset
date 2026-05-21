"""
enrich_nordic_netcdf.py
=======================
Loads the Tier 0 Nordic dataset (raw harmonised observations) and embeds
six time-varying derived snow parameters, producing a self-contained Tier 1
NetCDF suitable for Zenodo archiving.

Input:  data/processed/nordic/nordic_tier0_2015_2024.nc  (4 variables, ~56 MB)
Output: data/processed/nordic/nordic_tier1_2015_2024.nc  (10 variables, ~130 MB)

Derived variables added (all dims: station_id × time):
    swe                   [mm]      — Snow Water Equivalent (Sturm 2010, taiga)
    snow_density          [g cm-3]  — Bulk snow density (Sturm 2010)
    snowmelt_rate         [mm day-1]— Daily SWE decrease; NaN on non-melt days
    swe_accumulation_rate [mm day-1]— Daily SWE increase; NaN on non-accum days
    rain_on_snow          [int8]    — Event flag (1 = ROS, 0 = no event)
    cold_content          [MJ m-2]  — Snowpack energy deficit to 0 °C

Season-level scalars (phenology, DDM, freeze-thaw) are already in the
companion CSV files produced by benchmark_snow_params.py and are not
repeated here.

Note on rain_on_snow: the flag requires temp_mean > 0 °C. Since temp_mean
is only available at ~12% of station-days (snow-depth stations without a
co-located temperature sensor yield NaN), the flag is conservatively set to
0 wherever temperature is missing — correct behaviour because ROS cannot be
confirmed without a temperature observation.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

import numpy as np
import xarray as xr

from common.config import PROCESSED_DIR
from common.io import save_to_netcdf
from derivation.hydrological_parameters import (
    calculate_swe_sturm,
    calculate_snowmelt_dynamics,
    detect_rain_on_snow,
    calculate_cold_content,
)

INPUT  = PROCESSED_DIR / 'nordic' / 'nordic_tier0_2015_2024.nc'
OUTPUT = PROCESSED_DIR / 'nordic' / 'nordic_tier1_2015_2024.nc'


def _mb(ds: xr.Dataset) -> float:
    """Uncompressed size of all data variables in MB."""
    return sum(ds[v].nbytes for v in ds.data_vars) / 1e6


def main() -> None:
    print(f'Loading Tier 0 dataset: {INPUT}')
    ds = xr.open_dataset(INPUT)
    print(f'  Dimensions : {dict(ds.sizes)}')
    print(f'  Variables  : {list(ds.data_vars)}')
    print(f'  Size       : {_mb(ds):.1f} MB (uncompressed)')

    # ------------------------------------------------------------------
    # Step 1 — SWE and snow density  (Sturm et al. 2010, taiga class)
    # ------------------------------------------------------------------
    print('\n[1/4] Deriving SWE and snow density (Sturm 2010, taiga)...')
    swe_ds = calculate_swe_sturm(ds, ds, snow_class='taiga')
    n_swe = int(np.isfinite(swe_ds['swe'].values).sum())
    print(f'      Valid SWE values : {n_swe:,}')

    # ------------------------------------------------------------------
    # Step 2 — Melt and accumulation rates (SWE finite differences)
    # ------------------------------------------------------------------
    print('[2/4] Deriving melt and accumulation rates...')
    melt_ds = calculate_snowmelt_dynamics(swe_ds)
    n_melt  = int(np.isfinite(melt_ds['snowmelt_rate'].values).sum())
    n_accum = int(np.isfinite(melt_ds['swe_accumulation_rate'].values).sum())
    print(f'      Melt days  : {n_melt:,}   Accumulation days : {n_accum:,}')

    # ------------------------------------------------------------------
    # Step 3 — Rain-on-snow flag
    # Note: flag = 0 where temp_mean is NaN (no temperature available)
    # ------------------------------------------------------------------
    print('[3/4] Detecting rain-on-snow events...')
    ros_ds    = detect_rain_on_snow(ds, ds, ds)
    n_ros     = int(ros_ds['rain_on_snow'].values.sum())
    print(f'      Total ROS station-days : {n_ros:,}  '
          f'(expected ~4963 from 9-season benchmark)')

    # ------------------------------------------------------------------
    # Step 4 — Cold content
    # ------------------------------------------------------------------
    print('[4/4] Deriving snowpack cold content...')
    cc_ds  = calculate_cold_content(ds, ds)
    cc_max = float(np.nanmax(cc_ds['cold_content'].values))
    print(f'      Max cold content : {cc_max:.2f} MJ m-2')

    # ------------------------------------------------------------------
    # Assemble enriched dataset
    # ------------------------------------------------------------------
    print('\nAssembling Tier 1 dataset...')
    enriched = ds.copy()

    # Time-varying derived variables
    enriched['swe']                   = swe_ds['swe']
    enriched['snow_density']          = swe_ds['snow_density']
    enriched['snowmelt_rate']         = melt_ds['snowmelt_rate']
    enriched['swe_accumulation_rate'] = melt_ds['swe_accumulation_rate']
    enriched['rain_on_snow']          = ros_ds['rain_on_snow']
    enriched['cold_content']          = cc_ds['cold_content']

    # Update global attributes
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
    enriched.attrs['version'] = '1.1'
    enriched.attrs['title'] = (
        'NordHydro: Full Nordic Domain 2015\u20132024, Tier 1 (with derived parameters)'
    )
    enriched.attrs['history'] = (
        ds.attrs.get('history', '') +
        f'; {now}: Derived variables added by enrich_nordic_netcdf.py'
        f' (swe, snow_density, snowmelt_rate, swe_accumulation_rate,'
        f' rain_on_snow, cold_content; Sturm 2010 taiga class)'
    )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    print(f'Saving Tier 1 dataset: {OUTPUT}')
    save_to_netcdf(enriched, OUTPUT)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    ds_out = xr.open_dataset(OUTPUT)
    import os
    disk_mb = os.path.getsize(OUTPUT) / 1e6
    print('\n=== Tier 1 dataset summary ===')
    print(f'  Variables  : {list(ds_out.data_vars)}')
    print(f'  Dimensions : {dict(ds_out.dims)}')
    print(f'  Size (disk): {disk_mb:.1f} MB')
    print(f'  Output     : {OUTPUT}')
    print('\nDone.')


if __name__ == '__main__':
    main()
