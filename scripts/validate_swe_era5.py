"""
validate_swe_era5.py — M4 validation

Compares Sturm et al. (2010) station SWE against ERA5-Land snow_depth
(= SWE in m water equivalent) bilinearly interpolated to station locations.

Output:
  - Metrics table (RMSE, Bias, Pearson R, KGE) printed to stdout
  - Scatter plot saved to docs/figures/swe_vs_era5_dalarna.png

Prerequisite: ~/.cdsapirc with a valid CDS API key.
  See https://cds.climate.copernicus.eu/how-to-api for setup instructions.
"""

import sys
import logging
import os
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import RegularGridInterpolator

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from common.config import RAW_DIR, PROCESSED_DIR
from derivation.hydrological_parameters import calculate_swe_sturm

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('validate_swe_era5')

PILOT_NC   = PROCESSED_DIR / 'pilot' / 'dalarna_tier0_2023_2024.nc'
ERA5_PATH  = RAW_DIR / 'era5' / 'dalarna_sd_2023_2024.nc'
FIGURE_DIR = Path(__file__).resolve().parent.parent / 'docs' / 'figures'
FIGURE_OUT = FIGURE_DIR / 'swe_vs_era5_dalarna.png'
SNOW_CLASS = 'taiga'

# Dalarna bounding box: N, W, S, E for CDS API
ERA5_AREA = [61.5, 13.0, 60.0, 16.0]


def _check_cdsapi():
    """Exit with a clear message if CDS API is not configured."""
    cdsapirc = Path.home() / '.cdsapirc'
    if not cdsapirc.exists():
        logger.error(
            'CDS API key not found. Create ~/.cdsapirc with:\n'
            '  url: https://cds.climate.copernicus.eu/api\n'
            '  key: <your-key>\n'
            'See: https://cds.climate.copernicus.eu/how-to-api'
        )
        sys.exit(1)


def download_era5(out_path: Path) -> None:
    """Download ERA5-Land daily snow_depth for Dalarna 2023-10 to 2024-04."""
    import cdsapi
    out_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f'Downloading ERA5-Land snow_depth → {out_path}')
    c = cdsapi.Client()
    c.retrieve(
        'reanalysis-era5-land',
        {
            'variable': 'snow_depth',
            'product_type': 'reanalysis',
            'year': ['2023', '2024'],
            'month': ['10', '11', '12', '01', '02', '03', '04'],
            'day': [f'{d:02d}' for d in range(1, 32)],
            'time': '12:00',
            'format': 'netcdf',
            'area': ERA5_AREA,   # N, W, S, E
        },
        str(out_path),
    )
    logger.info('ERA5-Land download complete')


def _kge(obs: np.ndarray, sim: np.ndarray) -> float:
    """Kling-Gupta Efficiency (KGE; Gupta et al. 2009)."""
    r = np.corrcoef(obs, sim)[0, 1]
    alpha = np.std(sim) / np.std(obs)
    beta  = np.mean(sim) / np.mean(obs)
    return float(1.0 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2))


def main():
    logger.info('=== ERA5-Land SWE Validation ===')
    _check_cdsapi()

    # 1. Download ERA5-Land if not cached
    if ERA5_PATH.exists():
        logger.info(f'Using cached ERA5-Land file: {ERA5_PATH}')
    else:
        download_era5(ERA5_PATH)

    # 2. Load ERA5-Land
    era5 = xr.open_dataset(ERA5_PATH)
    # Variable may be named 'sd' or 'snow_depth' depending on ERA5 version
    sd_var = 'sd' if 'sd' in era5 else 'snow_depth'
    era5_swe_mm = era5[sd_var] * 1000.0   # m water equiv → mm
    logger.info(f'ERA5-Land loaded: {era5_swe_mm.shape}, variable={sd_var}')

    # ERA5-Land lat may be descending — normalize to ascending for interpolator
    lats_era5 = era5['latitude'].values.astype(float)
    lons_era5 = era5['longitude'].values.astype(float)
    times_era5 = pd.DatetimeIndex(era5['time'].values).normalize()

    ascending = lats_era5[0] < lats_era5[-1]
    if not ascending:
        lats_era5 = lats_era5[::-1]
        era5_swe_mm = era5_swe_mm.isel(latitude=slice(None, None, -1))

    # 3. Load station pilot data and compute Sturm SWE
    logger.info(f'Loading pilot NetCDF: {PILOT_NC}')
    ds = xr.open_dataset(PILOT_NC)
    swe_ds = calculate_swe_sturm(ds, ds, snow_class=SNOW_CLASS)

    station_lats = ds['lat'].values.astype(float)
    station_lons = ds['lon'].values.astype(float)
    times_pilot  = pd.DatetimeIndex(ds['time'].values).normalize()

    # 4. Find common dates
    common_dates = sorted(set(times_pilot) & set(times_era5))
    if not common_dates:
        logger.error('No overlapping dates between ERA5-Land and pilot data. Exiting.')
        sys.exit(1)
    logger.info(f'{len(common_dates)} common dates found')

    # 5. Bilinear interpolation of ERA5-Land SWE to station locations
    records = []
    for date in common_dates:
        t_idx_era5 = list(times_era5).index(date)
        t_idx_pilot = list(times_pilot).index(date)

        era5_slice = era5_swe_mm.isel(time=t_idx_era5).values   # shape: (lat, lon)
        interp = RegularGridInterpolator(
            (lats_era5, lons_era5), era5_slice, method='linear', bounds_error=False, fill_value=np.nan
        )
        era5_at_stations = interp(np.column_stack([station_lats, station_lons]))

        sturm_at_stations = swe_ds['swe'].isel(time=t_idx_pilot).values
        snow_depth        = ds['snow_depth'].isel(time=t_idx_pilot).values

        for s_idx in range(len(station_lats)):
            records.append({
                'date':       date,
                'station_id': int(ds['station_id'].values[s_idx]),
                'swe_sturm':  sturm_at_stations[s_idx],
                'swe_era5':   era5_at_stations[s_idx],
                'snow_depth': snow_depth[s_idx],
            })

    df = pd.DataFrame(records)

    # 6. Filter to snow-present days (snow_depth > 0) and both values non-NaN
    mask = (df['snow_depth'] > 0) & df['swe_sturm'].notna() & df['swe_era5'].notna()
    df_snow = df[mask].copy()
    logger.info(f'Valid (snow-present) pairs: {len(df_snow)} / {len(df)}')

    if df_snow.empty:
        logger.error('No valid pairs to compare. Check ERA5-Land variable and date overlap.')
        sys.exit(1)

    obs  = df_snow['swe_era5'].values
    sim  = df_snow['swe_sturm'].values

    rmse = float(np.sqrt(np.mean((sim - obs) ** 2)))
    bias = float(np.mean(sim - obs))
    r    = float(np.corrcoef(obs, sim)[0, 1])
    kge  = _kge(obs, sim)

    # 7. Print metrics
    print()
    print('=== SWE Validation: Sturm (2010, taiga) vs ERA5-Land ===')
    print(f'  Domain   : Dalarna, Sweden (lat 60–61.5°N, lon 13–16°E)')
    print(f'  Period   : 2023-10-01 to 2024-04-30 (snow-present days only)')
    print(f'  N pairs  : {len(df_snow)} station-day pairs')
    print(f'  RMSE     : {rmse:.1f} mm')
    print(f'  Bias     : {bias:+.1f} mm (Sturm − ERA5-Land)')
    print(f'  Pearson R: {r:.3f}')
    print(f'  KGE      : {kge:.3f}')
    print()

    # 8. Scatter plot
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        FIGURE_DIR.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.scatter(obs, sim, alpha=0.3, s=10, color='steelblue')
        lim = max(obs.max(), sim.max()) * 1.05
        ax.plot([0, lim], [0, lim], 'k--', lw=0.8, label='1:1 line')
        ax.set_xlabel('ERA5-Land SWE (mm)')
        ax.set_ylabel('Sturm et al. (2010) SWE (mm)')
        ax.set_title(f'Dalarna 2023-24  |  RMSE={rmse:.1f} mm  KGE={kge:.3f}  R={r:.3f}')
        ax.set_xlim(0, lim); ax.set_ylim(0, lim)
        ax.legend()
        fig.tight_layout()
        fig.savefig(FIGURE_OUT, dpi=150)
        plt.close(fig)
        logger.info(f'Scatter plot saved → {FIGURE_OUT}')
    except ImportError:
        logger.warning('matplotlib not available — skipping scatter plot')


if __name__ == '__main__':
    main()
