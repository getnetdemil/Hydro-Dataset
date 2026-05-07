"""
generate_figures.py — M8 deliverable

Generates manuscript-quality figures from the Nordic dataset and M7 benchmark
outputs. All figures saved to docs/figures/.

Requires:
    data/processed/nordic/nordic_tier0_2015_2024.nc
    data/processed/nordic/benchmark_results.json
    data/processed/nordic/ddm_per_season.csv
    data/processed/nordic/peak_swe_per_season.csv

Usage:
    python scripts/generate_figures.py

Outputs (docs/figures/):
    mean_peak_swe_map.png        — spatial map of 9yr mean peak SWE per station
    swe_anomaly_timeseries.png   — bar chart of Nordic-mean SWE anomaly per season
    ddm_boxplot.png              — per-season DDM distribution (582 stations)
    ros_frequency_map.png        — spatial map of total ROS events per station
"""

import sys
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

sys.path.append(str(Path(__file__).resolve().parent.parent / 'src'))
from common.config import PROCESSED_DIR
from derivation.hydrological_parameters import detect_rain_on_snow

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('generate_figures')

NORDIC_NC   = PROCESSED_DIR / 'nordic' / 'nordic_tier0_2015_2024.nc'
OUT_JSON    = PROCESSED_DIR / 'nordic' / 'benchmark_results.json'
OUT_DDM_CSV = PROCESSED_DIR / 'nordic' / 'ddm_per_season.csv'
OUT_SWE_CSV = PROCESSED_DIR / 'nordic' / 'peak_swe_per_season.csv'
FIG_DIR     = Path(__file__).resolve().parent.parent / 'docs' / 'figures'

SEASON_LABELS = [f'{y}-{y+1}' for y in range(2015, 2024)]

# Shared style
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 10,
    'figure.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.dpi': 150,
})


def check_inputs():
    missing = [p for p in [NORDIC_NC, OUT_JSON, OUT_DDM_CSV, OUT_SWE_CSV] if not p.exists()]
    if missing:
        for p in missing:
            logger.error(f'Missing: {p}')
        logger.error('Run benchmark_snow_params.py first.')
        sys.exit(1)


# ---------------------------------------------------------------------------
# Figure 1 — Spatial map: 9yr mean peak SWE
# ---------------------------------------------------------------------------

def fig_mean_peak_swe(ds: xr.Dataset, swe_df: pd.DataFrame):
    """Scatter map coloured by 9-season mean peak SWE."""
    logger.info('Generating Figure 1: mean peak SWE map')

    lat = ds['lat'].values
    lon = ds['lon'].values
    mean_swe = swe_df.mean(axis=1, skipna=True).values  # (n_stations,)

    valid = ~np.isnan(mean_swe)
    fig, ax = plt.subplots(figsize=(8, 7))

    sc = ax.scatter(
        lon[valid], lat[valid],
        c=mean_swe[valid],
        cmap='YlOrRd',
        s=12,
        alpha=0.85,
        linewidths=0.2,
        edgecolors='0.4',
        vmin=0,
        vmax=np.nanpercentile(mean_swe[valid], 95),
    )
    cbar = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Mean peak SWE [mm]', fontsize=9)

    ax.set_xlabel('Longitude [°E]')
    ax.set_ylabel('Latitude [°N]')
    ax.set_title('9-Season Mean Peak SWE — Nordic Domain (2015–2024)\n'
                 f'Sturm et al. (2010) taiga model, {valid.sum()} SMHI stations', pad=8)
    ax.set_xlim(9.5, 31)
    ax.set_ylim(54.5, 71)
    ax.grid(True, linestyle=':', linewidth=0.5, alpha=0.6)

    out = FIG_DIR / 'mean_peak_swe_map.png'
    fig.savefig(out)
    plt.close(fig)
    logger.info(f'  Saved: {out}')


# ---------------------------------------------------------------------------
# Figure 2 — SWE anomaly time-series (bar chart)
# ---------------------------------------------------------------------------

def fig_swe_anomaly(benchmark: dict):
    """Bar chart of per-season Nordic-mean SWE anomaly."""
    logger.info('Generating Figure 2: SWE anomaly timeseries')

    anomaly = benchmark['anomaly_summary']
    seasons = [a['season'] for a in anomaly]
    values  = [a['mean_swe_anomaly_mm'] for a in anomaly]
    stds    = [a['std_swe_anomaly_mm']  for a in anomaly]

    colors = ['#d73027' if v > 0 else '#4575b4' for v in values]
    x = np.arange(len(seasons))

    fig, ax = plt.subplots(figsize=(10, 4.5))
    bars = ax.bar(x, values, color=colors, width=0.65, yerr=stds,
                  error_kw={'elinewidth': 1.2, 'ecolor': '0.35', 'capsize': 4},
                  zorder=3)
    ax.axhline(0, color='black', linewidth=0.8, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace('-', '\n') for s in seasons], fontsize=9)
    ax.set_xlabel('Winter Season')
    ax.set_ylabel('Mean Peak SWE Anomaly [mm]')
    ax.set_title('Interannual SWE Anomaly — Nordic Domain (2015–2024)\n'
                 'Departure from 9-season mean (bars = Nordic-mean; error = 1σ across stations)', pad=8)
    ax.grid(axis='y', linestyle=':', linewidth=0.5, alpha=0.6, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Label bars
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (5 if v >= 0 else -12),
                f'{v:+.0f}',
                ha='center', va='bottom', fontsize=8)

    out = FIG_DIR / 'swe_anomaly_timeseries.png'
    fig.savefig(out)
    plt.close(fig)
    logger.info(f'  Saved: {out}')


# ---------------------------------------------------------------------------
# Figure 3 — DDM boxplot per season
# ---------------------------------------------------------------------------

def fig_ddm_boxplot(ddm_df: pd.DataFrame):
    """Boxplot of per-station DDM distribution for each season."""
    logger.info('Generating Figure 3: DDM boxplot')

    seasons = [c for c in SEASON_LABELS if c in ddm_df.columns]
    data    = [ddm_df[s].dropna().values for s in seasons]
    data    = [d[d > 0] for d in data]   # keep only calibrated stations

    fig, ax = plt.subplots(figsize=(10, 4.5))
    bp = ax.boxplot(
        data,
        tick_labels=[s.replace('-', '\n') for s in seasons],
        patch_artist=True,
        medianprops={'color': 'black', 'linewidth': 1.5},
        whiskerprops={'linewidth': 1.0},
        flierprops={'marker': 'o', 'markersize': 2, 'alpha': 0.4, 'markerfacecolor': '0.6'},
        notch=False,
    )
    for patch in bp['boxes']:
        patch.set_facecolor('#a1c9f4')
        patch.set_alpha(0.8)

    ax.set_xlabel('Winter Season')
    ax.set_ylabel('Degree-Day Melt Factor [mm °C⁻¹ day⁻¹]')
    ax.set_title('Degree-Day Melt Factor Distribution — Nordic Domain (2015–2024)\n'
                 'Per-station DDM calibrated from SWE finite differences; stations with ≥3 melt days', pad=8)
    ax.axhline(3.0, color='#e34a33', linestyle='--', linewidth=0.9, label='Literature midpoint (3.0)')
    ax.legend(fontsize=8)
    ax.grid(axis='y', linestyle=':', linewidth=0.5, alpha=0.6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Annotate sample sizes
    for i, (s, d) in enumerate(zip(seasons, data)):
        ax.text(i + 1, ax.get_ylim()[0] + 0.05,
                f'n={len(d)}', ha='center', va='bottom', fontsize=7, color='0.4')

    out = FIG_DIR / 'ddm_boxplot.png'
    fig.savefig(out)
    plt.close(fig)
    logger.info(f'  Saved: {out}')


# ---------------------------------------------------------------------------
# Figure 4 — Spatial map: ROS event frequency
# ---------------------------------------------------------------------------

def fig_ros_frequency(ds: xr.Dataset):
    """Scatter map coloured by total ROS events per station over 2015–2024."""
    logger.info('Generating Figure 4: ROS frequency map (computing ROS over full period...)')

    ros_ds    = detect_rain_on_snow(ds, ds, ds)
    ros_count = ros_ds['rain_on_snow'].values.sum(axis=1)   # (n_stations,)

    lat = ds['lat'].values
    lon = ds['lon'].values

    fig, ax = plt.subplots(figsize=(8, 7))

    # Background: all stations as faint grey
    ax.scatter(lon, lat, c='0.85', s=6, linewidths=0, zorder=1)

    # ROS stations coloured
    mask = ros_count > 0
    sc = ax.scatter(
        lon[mask], lat[mask],
        c=ros_count[mask],
        cmap='Oranges',
        s=18,
        alpha=0.9,
        linewidths=0.3,
        edgecolors='0.3',
        norm=mcolors.LogNorm(vmin=1, vmax=max(ros_count[mask].max(), 2)),
        zorder=3,
    )
    cbar = plt.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Total ROS station-days (log scale)', fontsize=9)

    n_affected = int(mask.sum())
    ax.set_xlabel('Longitude [°E]')
    ax.set_ylabel('Latitude [°N]')
    ax.set_title(
        f'Rain-on-Snow Event Frequency — Nordic Domain (2015–2024)\n'
        f'{n_affected} of {len(ros_count)} stations with ≥1 ROS event '
        f'(snow_depth > 1 cm, T > 0°C, precip > 0.5 mm/d)',
        pad=8,
    )
    ax.set_xlim(9.5, 31)
    ax.set_ylim(54.5, 71)
    ax.grid(True, linestyle=':', linewidth=0.5, alpha=0.6)

    out = FIG_DIR / 'ros_frequency_map.png'
    fig.savefig(out)
    plt.close(fig)
    logger.info(f'  Saved: {out}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    check_inputs()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f'Loading datasets...')
    ds      = xr.open_dataset(NORDIC_NC)
    swe_df  = pd.read_csv(OUT_SWE_CSV, index_col='station_id')
    ddm_df  = pd.read_csv(OUT_DDM_CSV, index_col='station_id')
    with open(OUT_JSON) as f:
        benchmark = json.load(f)

    fig_mean_peak_swe(ds, swe_df)
    fig_swe_anomaly(benchmark)
    fig_ddm_boxplot(ddm_df)
    fig_ros_frequency(ds)

    logger.info(f'\nAll figures saved to {FIG_DIR}/')
    print('\nFigures written:')
    for p in sorted(FIG_DIR.glob('*.png')):
        print(f'  {p}')


if __name__ == '__main__':
    main()
