"""
benchmark_snow_params.py — M7 deliverable

Computes interannual SWE anomaly and per-season statistics (DDM, phenology,
rain-on-snow, freeze-thaw) across all 9 winter seasons (2015–2024) using
the full Nordic dataset.

Usage:
    python scripts/benchmark_snow_params.py

Outputs:
    data/processed/nordic/benchmark_results.json  — full metrics per season
    data/processed/nordic/ddm_per_season.csv      — per-station DDM matrix (stations × seasons)
    data/processed/nordic/peak_swe_per_season.csv — per-station peak SWE matrix
"""

import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from common.config import PROCESSED_DIR
from derivation.hydrological_parameters import (
    calculate_swe_sturm,
    calculate_snow_phenology,
    calculate_degree_day_factor,
    detect_rain_on_snow,
    calculate_freeze_thaw_cycles,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('benchmark_snow_params')

NORDIC_NC   = PROCESSED_DIR / 'nordic' / 'nordic_tier0_2015_2024.nc'
OUT_JSON    = PROCESSED_DIR / 'nordic' / 'benchmark_results.json'
OUT_DDM_CSV = PROCESSED_DIR / 'nordic' / 'ddm_per_season.csv'
OUT_SWE_CSV = PROCESSED_DIR / 'nordic' / 'peak_swe_per_season.csv'

# Nine hydrological winters: Oct Y → Apr Y+1
SEASONS = [(f'{y}-{y+1}', f'{y}-10-01', f'{y+1}-04-30') for y in range(2015, 2024)]


def season_label(t: pd.Timestamp) -> str | None:
    """Return 'YYYY-YYYY' season label for a timestamp; None for summer months."""
    if t.month >= 10:
        return f'{t.year}-{t.year + 1}'
    if t.month <= 4:
        return f'{t.year - 1}-{t.year}'
    return None  # May–Sep excluded


def _fmt(v, spec='>10.1f'):
    return f'{v:{spec}}' if v is not None else f"{'N/A':>10}"


def benchmark_season(ds: xr.Dataset, swe_ds: xr.Dataset, label: str) -> dict:
    """Compute all benchmark metrics for one winter season slice."""
    logger.info(f'  Season {label}: {ds.sizes["station_id"]} stations × {ds.sizes["time"]} days')

    # --- SWE / Peak SWE ---
    peak_swe = swe_ds['swe'].max(dim='time').values          # (station_id,)
    valid_peak = peak_swe[~np.isnan(peak_swe) & (peak_swe > 0)]

    # --- Phenology ---
    pheno     = calculate_snow_phenology(swe_ds)
    duration  = pheno['snow_cover_duration'].values
    onset_arr = pheno['snow_onset_doy'].values
    melt_arr  = pheno['melt_out_doy'].values

    # --- DDM ---
    ddm_ds  = calculate_degree_day_factor(swe_ds, ds)
    ddm_arr = ddm_ds['degree_day_factor'].values
    valid_ddm = ddm_arr[~np.isnan(ddm_arr) & (ddm_arr > 0)]
    n_days_arr = ddm_ds['ddm_n_days'].values

    # --- Rain-on-snow ---
    ros_ds    = detect_rain_on_snow(ds, ds, ds)
    ros_total = int(ros_ds['rain_on_snow'].values.sum())
    ros_sta   = int((ros_ds['rain_on_snow'].values.sum(axis=1) > 0).sum())

    # --- Freeze-thaw ---
    ft_ds  = calculate_freeze_thaw_cycles(ds)
    ft_arr = ft_ds['freeze_thaw_count'].values.astype(float)
    ft_arr[ft_arr == 0] = np.nan  # stations with no crossings → NaN for stats

    return {
        'season': label,
        'n_stations': int(ds.sizes['station_id']),
        'n_days':     int(ds.sizes['time']),
        'swe': {
            'mean_peak_swe_mm': float(np.nanmean(valid_peak)) if len(valid_peak) else None,
            'max_peak_swe_mm':  float(np.nanmax(valid_peak))  if len(valid_peak) else None,
            'n_snow_stations':  int(len(valid_peak)),
        },
        'phenology': {
            'mean_onset_doy':    float(np.nanmean(onset_arr))   if not np.all(np.isnan(onset_arr)) else None,
            'mean_meltout_doy':  float(np.nanmean(melt_arr))    if not np.all(np.isnan(melt_arr))  else None,
            'mean_duration_days': float(np.nanmean(duration[~np.isnan(duration)])) if not np.all(np.isnan(duration)) else None,
        },
        'ddm': {
            'median_ddm':              float(np.nanmedian(valid_ddm))        if len(valid_ddm) else None,
            'q25_ddm':                 float(np.nanpercentile(valid_ddm, 25)) if len(valid_ddm) else None,
            'q75_ddm':                 float(np.nanpercentile(valid_ddm, 75)) if len(valid_ddm) else None,
            'n_calibrated_stations':   int(len(valid_ddm)),
            'mean_qualifying_days':    float(n_days_arr[n_days_arr > 0].mean()) if (n_days_arr > 0).any() else None,
        },
        'rain_on_snow': {
            'total_events':       ros_total,
            'affected_stations':  ros_sta,
        },
        'freeze_thaw': {
            'mean_cycles': float(np.nanmean(ft_arr)) if not np.all(np.isnan(ft_arr)) else None,
            'max_cycles':  float(np.nanmax(ft_arr))  if not np.all(np.isnan(ft_arr)) else None,
        },
        # Raw arrays stored separately (for figures); placeholder here
        '_ddm_array':      ddm_arr.tolist(),
        '_peak_swe_array': peak_swe.tolist(),
    }


def main():
    if not NORDIC_NC.exists():
        logger.error(f'Nordic NetCDF not found: {NORDIC_NC}')
        logger.error('Run: python scripts/build_nordic_netcdf.py')
        sys.exit(1)

    logger.info(f'Loading {NORDIC_NC}')
    ds_full = xr.open_dataset(NORDIC_NC)
    logger.info(f'Full dataset: {dict(ds_full.sizes)}')

    station_ids = ds_full['station_id'].values
    times       = pd.DatetimeIndex(ds_full['time'].values)
    labels_all  = np.array([season_label(t) for t in times])

    results       = []
    ddm_matrix    = {}   # season_label -> np.ndarray (n_stations,)
    peak_swe_mat  = {}   # season_label -> np.ndarray (n_stations,)

    logger.info('Running per-season benchmarks...')
    for lbl, t_start, t_end in SEASONS:
        mask = labels_all == lbl
        if mask.sum() == 0:
            logger.warning(f'  No time steps for {lbl} — skipping')
            continue

        ds_s   = ds_full.isel(time=mask)
        swe_ds = calculate_swe_sturm(ds_s, ds_s, snow_class='taiga')

        metrics = benchmark_season(ds_s, swe_ds, lbl)

        # Stash arrays before writing to JSON (pop internal keys)
        ddm_matrix[lbl]   = np.array(metrics.pop('_ddm_array'))
        peak_swe_mat[lbl] = np.array(metrics.pop('_peak_swe_array'))

        results.append(metrics)

    # --- Interannual SWE anomaly ---
    logger.info('Computing interannual SWE anomaly...')
    season_order = [r['season'] for r in results]
    swe_stack    = np.stack([peak_swe_mat[lbl] for lbl in season_order], axis=0)  # (n_seasons, n_stations)
    baseline_mu  = np.nanmean(swe_stack, axis=0)                                  # (n_stations,)

    anomaly_summary = []
    for i, r in enumerate(results):
        lbl   = r['season']
        anom  = peak_swe_mat[lbl] - baseline_mu
        entry = {
            'season':               lbl,
            'mean_swe_anomaly_mm':  float(np.nanmean(anom)),
            'std_swe_anomaly_mm':   float(np.nanstd(anom)),
            'fraction_positive':    float(np.nanmean(anom > 0)),
        }
        anomaly_summary.append(entry)
        r['swe_anomaly'] = entry

    # --- Print summary table ---
    print('\n=== M7 Benchmark Results — Nordic Snow Parameters (2015–2024) ===\n')
    hdr = (
        f"{'Season':<12}  {'PeakSWE':>10}  {'Anomaly':>11}  {'Duration':>9}  "
        f"{'DDM med':>7}  {'ROS events':>10}  {'FT cycles':>9}"
    )
    print(hdr)
    print('─' * len(hdr))
    for r in results:
        peak = r['swe'].get('mean_peak_swe_mm')
        anom = r['swe_anomaly'].get('mean_swe_anomaly_mm')
        dur  = r['phenology'].get('mean_duration_days')
        ddm  = r['ddm'].get('median_ddm')
        ros  = r['rain_on_snow']['total_events']
        ft   = r['freeze_thaw'].get('mean_cycles')
        print(
            f"{r['season']:<12}  "
            f"{_fmt(peak, '>10.1f')}  "
            f"{_fmt(anom, '>+11.1f')}  "
            f"{_fmt(dur,  '>9.1f')}  "
            f"{_fmt(ddm,  '>7.2f')}  "
            f"{ros:>10d}  "
            f"{_fmt(ft,   '>9.1f')}"
        )

    # --- Save CSVs (per-station matrices) ---
    ddm_df = pd.DataFrame(
        {lbl: ddm_matrix[lbl] for lbl in season_order},
        index=station_ids,
    )
    ddm_df.index.name = 'station_id'
    ddm_df.to_csv(OUT_DDM_CSV)
    logger.info(f'DDM matrix saved: {OUT_DDM_CSV}')

    swe_df = pd.DataFrame(
        {lbl: peak_swe_mat[lbl] for lbl in season_order},
        index=station_ids,
    )
    swe_df.index.name = 'station_id'
    swe_df.to_csv(OUT_SWE_CSV)
    logger.info(f'Peak SWE matrix saved: {OUT_SWE_CSV}')

    # --- Save JSON ---
    output = {
        'generated':       datetime.now(timezone.utc).isoformat(),
        'dataset':         str(NORDIC_NC),
        'n_seasons':       len(results),
        'n_stations':      int(ds_full.sizes['station_id']),
        'baseline_mean_peak_swe_mm': float(np.nanmean(baseline_mu)),
        'seasons':         results,
        'anomaly_summary': anomaly_summary,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, 'w') as f:
        json.dump(output, f, indent=2)
    logger.info(f'Benchmark results saved: {OUT_JSON}')
    print(f'\nOutputs written to {OUT_JSON.parent}/')


if __name__ == '__main__':
    main()
