"""
generate_pipeline_figure.py — Methodology section architecture figure

Renders a publication-quality pipeline diagram showing the five-phase
Hydro-Dataset architecture, data sources, and key contributions.

Outputs (saved to both locations):
    docs/figures/pipeline_architecture.png
    Overleaf_manuscript/figures/pipeline_architecture.png

Usage:
    python scripts/generate_pipeline_figure.py
    make pipeline-figure
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
NAVY    = '#1f4e79'
LBLUE   = '#dce6f1'
AMBER   = '#fff2cc'
AMBER_B = '#f0c040'      # amber border
WHITE   = '#ffffff'
DARK    = '#2c2c2c'

# Source-specific colours (left column)
SRC_COLORS = {
    'SMHI MetObs': '#c9daf8',
    'SMHI HydObs': '#a8c7fa',
    'FMI WFS':     '#d9ead3',
    'MESAN GRIB2': '#efefef',
    'ERA5-Land':   '#fff2cc',
}

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------
COLUMNS = [
    {
        'label':   'DATA SOURCES',
        'sources': [
            ('SMHI MetObs',  'snow_depth, T, precip'),
            ('SMHI HydObs',  'discharge'),
            ('FMI WFS',      'T, precip, snow'),
            ('MESAN GRIB2',  '2.5 km reanalysis'),
            ('ERA5-Land',    'validation only'),
        ],
    },
    {
        'label': 'EXTRACTION',
        'lines': [
            'fetch_smhi.py',
            'fetch_smhi_hydobs.py',
            'fetch_fmi.py',
            'fetch_mesan.py',
            'fetch_syke.py',
        ],
        'tier': 'data/raw/',
    },
    {
        'label': 'PROCESSING',
        'lines': [
            'LAEA reproject',
            'EPSG:3035',
            'Temporal normalise',
            '(daily resolution)',
            'QC outlier flags',
            'Linear gap-fill ≤3d',
        ],
        'tier': 'data/interim/',
    },
    {
        'label': 'DERIVATION',
        'lines': [
            'SWE  (Sturm 2010)',
            'Snow phenology',
            'Melt / accum rates',
            'Degree-day factor',
            'Rain-on-snow flag',
            'Freeze-thaw cycles',
        ],
        'tier': 'data/processed/',
    },
    {
        'label': 'OUTPUT',
        'outputs': [
            ('Tier 0 NetCDF', 'nordic_tier0_*.nc\n58 MB · raw obs'),
            ('Tier 1 NetCDF', 'nordic_tier1_*.nc\n133 MB · +6 params'),
        ],
        'tier': 'Zenodo DOI',
    },
]

CONTRIBUTIONS = [
    'KEY CONTRIBUTIONS',
    '582 SMHI stations · Nordic domain (55–70°N)',
    '9 hydrological winters  2015–2024',
    '1.8 M annotated station-days',
    '6 co-registered derived snow parameters',
    'CF-1.9 compliant · Zenodo archive',
]

# ---------------------------------------------------------------------------
# Layout geometry (in axes-fraction units, xlim=ylim=[0,1])
# ---------------------------------------------------------------------------
COL_CENTERS = [0.09, 0.26, 0.46, 0.66, 0.86]
COL_W       = 0.155          # column width
HDR_H       = 0.07           # header box height
BODY_TOP    = 0.82           # top of content boxes
BODY_BOT    = 0.18           # bottom of content boxes (above tier label)
TIER_Y      = 0.10           # y position of storage tier label
ARROW_Y     = (BODY_TOP + BODY_BOT) / 2


def _bbox(ax, cx, top, height, width, color, edgecolor='#7a9cbf', lw=0.8, radius=0.012):
    """Draw a rounded rectangle and return its patch."""
    x = cx - width / 2
    patch = FancyBboxPatch(
        (x, top - height), width, height,
        boxstyle=f'round,pad=0,rounding_size={radius}',
        linewidth=lw, edgecolor=edgecolor,
        facecolor=color, zorder=2,
        transform=ax.transAxes, clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def _text(ax, x, y, s, **kw):
    defaults = dict(transform=ax.transAxes, zorder=3, clip_on=False,
                    ha='center', va='center')
    defaults.update(kw)
    ax.text(x, y, s, **defaults)


# ---------------------------------------------------------------------------
# Main drawing function
# ---------------------------------------------------------------------------
def draw_pipeline(ax):
    for i, col in enumerate(COLUMNS):
        cx = COL_CENTERS[i]

        # --- Header ---
        _bbox(ax, cx, BODY_TOP + HDR_H, HDR_H, COL_W,
              color=NAVY, edgecolor=NAVY, radius=0.015)
        _text(ax, cx, BODY_TOP + HDR_H / 2, col['label'],
              color=WHITE, fontsize=9.5, fontweight='bold')

        # --- Body box ---
        body_h = BODY_TOP - BODY_BOT
        _bbox(ax, cx, BODY_TOP, body_h, COL_W,
              color=LBLUE, edgecolor='#7a9cbf', lw=0.9)

        # --- Tier label below body ---
        tier = col.get('tier', '')
        if tier:
            _text(ax, cx, TIER_Y, tier,
                  fontsize=7.5, color='#444', style='italic')

        # --- Column-specific content ---
        if 'sources' in col:
            # Left column: stacked source boxes
            n = len(col['sources'])
            slot_h = body_h / n
            for j, (name, desc) in enumerate(col['sources']):
                sy = BODY_TOP - j * slot_h
                bg = SRC_COLORS.get(name, LBLUE)
                _bbox(ax, cx, sy, slot_h * 0.88, COL_W * 0.90,
                      color=bg, edgecolor='#888', lw=0.5, radius=0.008)
                _text(ax, cx, sy - slot_h * 0.30,
                      name, fontsize=7.8, fontweight='bold', color=DARK)
                _text(ax, cx, sy - slot_h * 0.60,
                      desc, fontsize=6.8, color='#555')

        elif 'outputs' in col:
            # Right column: two output blocks
            n = len(col['outputs'])
            slot_h = body_h / n
            colors = ['#c6efce', '#c9daf8']
            edge_c = ['#5a9e5a', '#4472c4']
            for j, (name, desc) in enumerate(col['outputs']):
                sy = BODY_TOP - j * slot_h
                _bbox(ax, cx, sy, slot_h * 0.88, COL_W * 0.90,
                      color=colors[j], edgecolor=edge_c[j], lw=0.8, radius=0.010)
                _text(ax, cx, sy - slot_h * 0.25,
                      name, fontsize=8, fontweight='bold', color=DARK)
                _text(ax, cx, sy - slot_h * 0.62,
                      desc, fontsize=7, color='#333')

        else:
            # Middle columns: simple bulleted lines
            lines = col.get('lines', [])
            step = body_h / (len(lines) + 1)
            for k, line in enumerate(lines):
                y = BODY_TOP - (k + 1) * step
                weight = 'bold' if line.startswith('→') else 'normal'
                col_   = '#1a5276' if line.startswith('→') else DARK
                _text(ax, cx, y, line, fontsize=7.8, color=col_, fontweight=weight)

    # --- Arrows between columns ---
    for i in range(len(COLUMNS) - 1):
        x_start = COL_CENTERS[i] + COL_W / 2
        x_end   = COL_CENTERS[i + 1] - COL_W / 2
        ax.annotate(
            '', xy=(x_end, ARROW_Y), xytext=(x_start, ARROW_Y),
            xycoords='axes fraction', textcoords='axes fraction',
            arrowprops=dict(arrowstyle='->', color='#333',
                            lw=1.8, mutation_scale=18),
            zorder=4,
        )

    # --- Contributions callout (bottom-centre) ---
    cont_cx = 0.48
    cont_cy = 0.045
    cont_w  = 0.64
    cont_h  = 0.10
    patch = FancyBboxPatch(
        (cont_cx - cont_w / 2, cont_cy - cont_h / 2), cont_w, cont_h,
        boxstyle='round,pad=0,rounding_size=0.015',
        linewidth=1.5, edgecolor=AMBER_B,
        facecolor=AMBER, zorder=2,
        transform=ax.transAxes, clip_on=False,
    )
    ax.add_patch(patch)

    # Title line
    _text(ax, cont_cx, cont_cy + cont_h * 0.33,
          CONTRIBUTIONS[0],
          fontsize=8.5, fontweight='bold', color='#7d6608')
    # Detail lines in two groups side by side
    left_lines  = CONTRIBUTIONS[1:4]
    right_lines = CONTRIBUTIONS[4:]
    for k, line in enumerate(left_lines):
        _text(ax, cont_cx - cont_w * 0.27, cont_cy + cont_h * 0.05 - k * cont_h * 0.27,
              f'• {line}', fontsize=7.5, ha='center', color=DARK)
    for k, line in enumerate(right_lines):
        _text(ax, cont_cx + cont_w * 0.27, cont_cy + cont_h * 0.05 - k * cont_h * 0.27,
              f'• {line}', fontsize=7.5, ha='center', color=DARK)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    ROOT     = Path(__file__).resolve().parent.parent
    FIG_DOCS = ROOT / 'docs' / 'figures'
    FIG_TEX  = ROOT / 'Overleaf_manuscript' / 'figures'
    FIG_DOCS.mkdir(parents=True, exist_ok=True)
    FIG_TEX.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(16, 8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    fig.suptitle(
        'Hydro-Dataset Pipeline Architecture',
        fontsize=14, fontweight='bold', y=0.97, color=DARK,
    )

    draw_pipeline(ax)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    for out in [FIG_DOCS / 'pipeline_architecture.png',
                FIG_TEX  / 'pipeline_architecture.png']:
        fig.savefig(out, dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        print(f'Saved: {out}')

    plt.close(fig)


if __name__ == '__main__':
    main()
