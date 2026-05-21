"""
generate_pipeline_arch.py — Publication-quality system architecture figure.

Generates pipeline_arch.svg: a proper architecture diagram (not a flowchart).
Design: outer frame, labelled sections (A/B/C), full-width vertical pipeline
stages, source tiles with type icons, output product cards, statistics banner.

Intended for two-column journal (IEEE ICIP / GMD / RSE format).

Outputs:
    docs/figures/pipeline_arch.svg
    Overleaf_manuscript/figures/pipeline_arch.svg

Usage:
    python scripts/generate_pipeline_arch.py
    make pipeline-figure
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = [
    ROOT / 'docs' / 'figures' / 'pipeline_arch.svg',
    ROOT / 'Overleaf_manuscript' / 'figures' / 'pipeline_arch.svg',
]

# ─── Canvas & font ────────────────────────────────────────────────────────────
VW, VH = 820, 540
F      = "Arial, Helvetica, sans-serif"

# ─── Colour palette ───────────────────────────────────────────────────────────
# Frame / title
FRAME      = "#0d2137"
TITLE_BAR  = "#0d2137"

# Section backgrounds
SEC_A_BG   = "#eef4fb"    # data sources — blue tint
SEC_B_BG   = "#fafcff"    # pipeline     — near white
SEC_C_BG   = "#f0f9f4"    # outputs      — green tint

SEC_A_BR   = "#b8cfe8"
SEC_B_BR   = "#c8d8ec"
SEC_C_BR   = "#9ecdb8"

# Pipeline stage headers and fills
STG = [
    # (badge_bg,  header_bg,  fill,      accent,    label     )
    ("#154a7a",  "#154a7a",  "#e8f4fd", "#2e86c1", "EXTRACTION"),
    ("#0a4d3c",  "#0a4d3c",  "#edf7f2", "#1e8449", "PROCESSING"),
    ("#3b1f5e",  "#3b1f5e",  "#f3eefb", "#7d3c98", "DERIVATION"),
]

# Source tile colours  (border, fill)
SRC_C = [
    ("#1a5276", "#d6eaf8"),   # SMHI MetObs   — blue
    ("#1a5276", "#c8def5"),   # SMHI HydObs   — blue (slightly darker)
    ("#0b5345", "#d5f5e3"),   # FMI WFS       — green
    ("#515a5a", "#f2f3f4"),   # MESAN 2.5 km  — gray
    ("#a04000", "#fdebd0"),   # ERA5-Land †   — amber, dashed
]

# Output product colours  (header, fill, border)
TIER0  = ("#0a4d3c", "#e6f7ee", "#1e8449")
TIER1  = ("#0f3460", "#dbeafe", "#2e86c1")

# Stats bar
STAT_F = "#fef9e7"
STAT_B = "#d4ac0d"
STAT_T = "#7e5109"

WHITE  = "#ffffff"
DARK   = "#1a202c"
MID    = "#4a5568"
LIGHT  = "#718096"


# ─── Geometry ─────────────────────────────────────────────────────────────────
PAD   = 10    # section inner padding
MRG   = 6     # outer margin

# Outer frame — FX/FY/FW fixed; FH depends on final VH (computed below)
FX, FY, FW = MRG, MRG, VW - 2*MRG

# Title bar inside outer frame
TBAR_H = 34
TX, TY = FX, FY
TW, TH = FW, TBAR_H

# Section A — data sources
SA_Y = TY + TH + 8
SA_H = 68
SA_X, SA_W = FX + 8, FW - 16

# Section B — pipeline  (3 stages × 50px + 2 arrows × 18px + header 22 + pad)
STAGE_H = 50       # height of each pipeline stage box
ARROW_H = 16       # gap between stages
SB_INNER_H = 3 * STAGE_H + 2 * ARROW_H + 20   # ~186
SB_Y = SA_Y + SA_H + 8
SB_H = SB_INNER_H + 22   # 22px for section label
SB_X, SB_W = SA_X, SA_W

# Section C — outputs
SC_Y = SB_Y + SB_H + 8
SC_H = 100
SC_X, SC_W = SA_X, SA_W

# Stats banner
ST_Y = SC_Y + SC_H + 8
ST_H = 30
ST_X, ST_W = SA_X, SA_W

# Actual canvas height needed — VH and FH both finalised here
NEEDED_H = ST_Y + ST_H + 12
VH = NEEDED_H
FH = VH - 2*MRG


# ─── Minimal SVG helper ───────────────────────────────────────────────────────
class SVG:
    def __init__(self):
        self._b = []
        self._markers = set()

    def raw(self, s):   self._b.append(s)

    def rect(self, x, y, w, h, rx=4, fill=WHITE, stroke="#aaa", sw=1,
             dash="", opacity=1):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        op = f' opacity="{opacity}"' if opacity != 1 else ""
        self.raw(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}{op}/>'
        )

    def path_top_cap(self, x, y, w, h, rx=5, fill=FRAME):
        """Rounded top, flat bottom — used for box headers."""
        self.raw(
            f'<path d="M{x+rx},{y} H{x+w-rx} Q{x+w},{y} {x+w},{y+rx} '
            f'V{y+h} H{x} V{y+rx} Q{x},{y} {x+rx},{y}" fill="{fill}"/>'
        )

    def path_frame_title(self, x, y, w, h, rx=8, fill=FRAME):
        """Full frame rounded top; flat bottom corners match inner content."""
        self.raw(
            f'<path d="M{x+rx},{y} H{x+w-rx} Q{x+w},{y} {x+w},{y+rx} '
            f'V{y+h} H{x} V{y+rx} Q{x},{y} {x+rx},{y}" fill="{fill}"/>'
        )

    def text(self, x, y, s, anchor="middle", size=10, weight="normal",
             fill=DARK, italic=False, ls=""):
        sty = "font-style:italic;" if italic else ""
        lsa = f' letter-spacing="{ls}"' if ls else ""
        self.raw(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
            f'font-family="{F}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" style="{sty}"{lsa}>{s}</text>'
        )

    def line(self, x1, y1, x2, y2, stroke="#aaa", sw=1, dash=""):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{da}/>'
        )

    def _marker(self, uid, color, pw=8, ph=6):
        if uid not in self._markers:
            self._markers.add(uid)
            pts = f"0 0, {pw} {ph/2:.1f}, 0 {ph}"
            self.raw(
                f'<defs><marker id="{uid}" markerWidth="{pw}" markerHeight="{ph}" '
                f'refX="{pw-1}" refY="{ph/2:.1f}" orient="auto">'
                f'<polygon points="{pts}" fill="{color}"/></marker></defs>'
            )

    def arrow_d(self, x, y1, y2, color="#555", sw=1.8, dash=""):
        uid = f"ad_{int(x)}_{int(y1)}"
        self._marker(uid, color)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.raw(
            f'<line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2-2:.1f}" '
            f'stroke="{color}" stroke-width="{sw}"{da} marker-end="url(#{uid})"/>'
        )

    def arrow_r(self, x1, y, x2, color="#555", sw=1.8):
        uid = f"ar_{int(x1)}_{int(y)}"
        self._marker(uid, color)
        self.raw(
            f'<line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2-2:.1f}" y2="{y:.1f}" '
            f'stroke="{color}" stroke-width="{sw}" marker-end="url(#{uid})"/>'
        )

    def render(self):
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {VW} {VH}" width="{VW}" height="{VH}">\n'
            + "\n".join(self._b)
            + "\n</svg>"
        )


# ─── Drawing components ───────────────────────────────────────────────────────

def draw_outer_frame(s: SVG):
    """Outer frame with dark title bar."""
    s.rect(FX, FY, FW, FH, rx=8, fill=WHITE, stroke=FRAME, sw=1.8)
    s.path_frame_title(TX, TY, TW, TH, rx=8, fill=TITLE_BAR)
    cx = TX + TW / 2
    s.text(cx - 60, TY + 14, "Hydro-Dataset v1.1",
           size=13, weight="bold", fill=WHITE)
    s.text(cx - 60, TY + 28, "System Architecture",
           size=9, fill="#a8c8e8", italic=True)
    # Right-side subtitle
    s.text(TX + TW - 12, TY + 22,
           "Reproducible pipeline · 582 stations · 9 winters · CF-1.9",
           anchor="end", size=8, fill="#7fb3d3", italic=True)


def draw_section_label(s: SVG, x, y, letter, label, color="#4a5568"):
    """Section header: 'A  DATA SOURCES' style."""
    s.rect(x, y, 20, 13, rx=3, fill=color, stroke="none", sw=0)
    s.text(x + 10, y + 10, letter,
           size=8, weight="bold", fill=WHITE)
    s.text(x + 26, y + 10, label,
           anchor="start", size=8, weight="bold", fill=color, ls="0.5")


def draw_source_tile(s: SVG, x, y, w, h, name, desc, bc, fc,
                     dashed=False, icon_type="circle"):
    """Data source tile with coloured top tab and icon."""
    dash = "6,3" if dashed else ""
    TAB_H = 5
    # Tile body
    s.rect(x, y, w, h, rx=5, fill=fc, stroke=bc, sw=1.2, dash=dash)
    # Coloured top tab
    s.raw(
        f'<path d="M{x+5},{y} H{x+w-5} Q{x+w},{y} {x+w},{y+5} '
        f'V{y+TAB_H+2} H{x} V{y+5} Q{x},{y} {x+5},{y}" fill="{bc}"/>'
    )
    cx = x + w / 2
    # Small geometric icon
    ico_y = y + TAB_H + 10
    if icon_type == "circle":
        s.raw(f'<circle cx="{cx}" cy="{ico_y}" r="4" fill="{bc}" opacity="0.4"/>')
        s.raw(f'<circle cx="{cx}" cy="{ico_y}" r="2" fill="{bc}"/>')
    elif icon_type == "grid":
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                s.raw(f'<rect x="{cx+dx-1}" y="{ico_y+dy-1}" '
                      f'width="2" height="2" rx="0.4" fill="{bc}" opacity="0.5"/>')
    # Text
    s.text(cx, y + TAB_H + 21, name, size=8.5, weight="bold", fill=DARK)
    s.text(cx, y + TAB_H + 32, desc, size=7.5, fill=MID, italic=True)


def draw_pipeline_stage(s: SVG, x, y, w, h, number, label, subpath,
                        items, hdr_color, fill, accent, tier_label=""):
    """Full-width pipeline stage with number badge, header, bullet items."""
    BADGE_W = 44
    HDR_H   = h   # entire height is "header + content" combined

    # Background
    s.rect(x, y, w, h, rx=5, fill=fill, stroke=accent, sw=1.2)

    # Left badge strip
    s.raw(
        f'<path d="M{x+5},{y} H{x+BADGE_W} V{y+h} H{x} V{y+5} '
        f'Q{x},{y} {x+5},{y}" fill="{hdr_color}"/>'
    )
    # Badge number
    s.text(x + BADGE_W/2, y + h/2 - 6, number,
           size=14, weight="bold", fill=WHITE)
    s.text(x + BADGE_W/2, y + h/2 + 8, "▸", size=10, fill=WHITE, weight="bold")

    # Stage label (right of badge)
    lx = x + BADGE_W + 12
    s.text(lx, y + 15, label,
           anchor="start", size=10.5, weight="bold", fill=hdr_color)
    s.text(lx, y + 28, subpath,
           anchor="start", size=7.5, fill=LIGHT, italic=True)

    # Items as a comma-joined inline list (fits better in a shallow box)
    item_str = "  ·  ".join(items)
    s.text(lx, y + 43, item_str,
           anchor="start", size=8.5, fill=MID)

    # Right side tier label
    if tier_label:
        tx = x + w - 8
        s.text(tx, y + h/2 + 4, tier_label,
               anchor="end", size=7.5, fill=accent, italic=True)


def draw_output_card(s: SVG, x, y, w, h, title, fname, lines,
                     hdr, fill, border, primary=False):
    """Output product card."""
    HDR_H = 26
    sw    = 2.2 if primary else 1.3
    s.rect(x + 2, y + 2, w, h, rx=6, fill="#c8d0da", stroke="none", sw=0)  # shadow
    s.rect(x, y, w, h, rx=6, fill=fill, stroke=border, sw=sw)
    s.path_top_cap(x, y, w, HDR_H, rx=6, fill=hdr)

    if primary:
        s.raw(
            f'<text x="{x+w-8}" y="{y+HDR_H-8}" text-anchor="end" '
            f'font-family="{F}" font-size="7" fill="{WHITE}" '
            f'font-weight="bold" letter-spacing="0.5">★ ZENODO PRIMARY</text>'
        )
    s.text(x + w/2, y + HDR_H/2 + 5, title, size=9, weight="bold", fill=WHITE)
    s.text(x + w/2, y + HDR_H + 16, fname, size=8.8, weight="bold", fill=DARK)
    for i, ln in enumerate(lines):
        s.text(x + w/2, y + HDR_H + 30 + i*14, ln, size=8.3, fill=MID)


# ─── Main build ───────────────────────────────────────────────────────────────

def build() -> str:
    s = SVG()

    # ── Background ─────────────────────────────────────────────────────────
    s.rect(0, 0, VW, VH, rx=0, fill="#f4f7fb", stroke="none", sw=0)

    # ── Outer frame + title bar ─────────────────────────────────────────────
    draw_outer_frame(s)

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION A — DATA SOURCES
    # ═══════════════════════════════════════════════════════════════════════
    s.rect(SA_X, SA_Y, SA_W, SA_H, rx=6,
           fill=SEC_A_BG, stroke=SEC_A_BR, sw=1)
    draw_section_label(s, SA_X + 8, SA_Y + 6, "A", "DATA SOURCES", color="#1a4a7a")

    # 5 source tiles inside section A
    # 4 obs tiles + 1 ERA5 tile (slightly separated)
    N_OBS = 4
    OBS_GAP  = 8
    ERA5_GAP = 18   # visual separation for ERA5
    TILE_H   = SA_H - 22
    TILE_Y   = SA_Y + 22

    # Available width for all 5 tiles
    TOTAL_W = SA_W - 2*PAD - ERA5_GAP
    # 4 obs tiles equally spaced, then ERA5 tile after a bigger gap
    OBS_W  = (TOTAL_W * 0.72 - 3*OBS_GAP) / 4
    ERA5_W = TOTAL_W * 0.24

    tile_x = SA_X + PAD
    TILES = [
        ("SMHI MetObs",  "snow·temp·precip", SRC_C[0], "circle"),
        ("SMHI HydObs",  "discharge",        SRC_C[1], "circle"),
        ("FMI WFS",      "temp·snow·precip", SRC_C[2], "circle"),
        ("MESAN 2.5 km", "LAEA ref. grid",   SRC_C[3], "grid"),
    ]
    tile_centers = []
    for bc, fc, ic in [(t[2][0], t[2][1], t[3]) for t in TILES]:
        idx = [t[2] for t in TILES].index((bc, fc))
        # Actually iterate properly:
        pass

    obs_tiles_x = []
    for i, (name, desc, (bc, fc), ic) in enumerate(TILES):
        tx = SA_X + PAD + i * (OBS_W + OBS_GAP)
        draw_source_tile(s, tx, TILE_Y, OBS_W, TILE_H,
                         name, desc, bc, fc, icon_type=ic)
        obs_tiles_x.append(tx + OBS_W / 2)

    era5_x = SA_X + PAD + 4 * (OBS_W + OBS_GAP) + ERA5_GAP - OBS_GAP
    draw_source_tile(s, era5_x, TILE_Y, ERA5_W, TILE_H,
                     "ERA5-Land †", "cross-val only",
                     SRC_C[4][0], SRC_C[4][1],
                     dashed=True, icon_type="grid")

    # Vertical separator before ERA5
    sep_x = era5_x - ERA5_GAP/2
    s.line(sep_x, SA_Y + 18, sep_x, SA_Y + SA_H - 6,
           stroke=SEC_A_BR, sw=0.8, dash="4,3")

    # ═══════════════════════════════════════════════════════════════════════
    # Connection from Section A to Section B (collector line + arrow)
    # ═══════════════════════════════════════════════════════════════════════
    GAP_AB   = SB_Y - (SA_Y + SA_H)   # 8px
    COLL_Y   = SA_Y + SA_H + 4
    # Extraction stage top-center
    EX_CX = SB_X + SB_W / 2
    EX_TOP = SB_Y + 22   # top of first stage (below section label)

    # Stems from each obs tile center down to collector
    for cx in obs_tiles_x:
        s.line(cx, TILE_Y + TILE_H, cx, COLL_Y,
               stroke=SRC_C[0][0], sw=1.1)
    # Horizontal collector bar
    s.line(obs_tiles_x[0], COLL_Y, obs_tiles_x[-1], COLL_Y,
           stroke=SRC_C[0][0], sw=1.1)
    # Arrow from collector mid into Section B
    coll_mid = (obs_tiles_x[0] + obs_tiles_x[-1]) / 2
    s.line(coll_mid, COLL_Y, EX_CX, COLL_Y,
           stroke="#5b8abf", sw=1, dash="3,2")
    s.arrow_d(EX_CX, COLL_Y, EX_TOP, color="#3d6b9a", sw=1.6)

    # ERA5 dashed stem (separate path, goes to right side of pipeline)
    era5_cx = era5_x + ERA5_W / 2
    era5_end_y = SB_Y + 22 + STAGE_H + ARROW_H + STAGE_H * 0.5
    s.arrow_d(era5_cx, TILE_Y + TILE_H, era5_end_y,
              color=SRC_C[4][0], sw=1.2, dash="5,3")
    # Small annotation
    s.rect(era5_cx - 34, era5_end_y + 2, 68, 15, rx=3,
           fill=SRC_C[4][1], stroke=SRC_C[4][0], sw=0.8, dash="4,2")
    s.text(era5_cx, era5_end_y + 12,
           "cross-validation", size=7, fill=SRC_C[4][0], italic=True)

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION B — PIPELINE
    # ═══════════════════════════════════════════════════════════════════════
    s.rect(SB_X, SB_Y, SB_W, SB_H, rx=6,
           fill=SEC_B_BG, stroke=SEC_B_BR, sw=1)
    draw_section_label(s, SB_X + 8, SB_Y + 6, "B", "PROCESSING PIPELINE", color="#1a3a5c")

    STAGE_X = SB_X + PAD
    STAGE_W = SB_W - 2*PAD

    stage_data = [
        ("01", "EXTRACTION",  "src / extraction /",
         ["fetch_smhi.py", "fetch_smhi_hydobs.py",
          "fetch_fmi.py", "fetch_mesan.py", "fetch_syke.py"],
         *STG[0][:-1], "→ data/raw/"),

        ("02", "PROCESSING",  "src / processing /",
         ["LAEA reproject (EPSG:3035)", "Temporal normalisation",
          "QC outlier flagging", "Gap-fill ≤ 3 d", "Kriging 2.5 km"],
         *STG[1][:-1], "→ data/interim/"),

        ("03", "DERIVATION",  "src / derivation /",
         ["SWE (Sturm 2010)", "Phenology",
          "Melt &amp; accum. rates", "DDM", "Rain-on-snow", "Freeze-thaw"],
         *STG[2][:-1], "→ data/processed/"),
    ]

    stage_tops = []
    sy = SB_Y + 22   # top of first stage (inside section B, below label)
    for num, lbl, subpath, items, badge, hdr, fill, accent, tier in stage_data:
        draw_pipeline_stage(s, STAGE_X, sy, STAGE_W, STAGE_H,
                            num, lbl, subpath, items,
                            hdr, fill, accent, tier_label=tier)
        stage_tops.append(sy)
        if num != "03":
            # Down arrow between stages
            arr_x  = STAGE_X + STAGE_W / 2
            arr_y1 = sy + STAGE_H
            arr_y2 = sy + STAGE_H + ARROW_H
            s.arrow_d(arr_x, arr_y1, arr_y2, color=accent, sw=1.5)
            sy += STAGE_H + ARROW_H
        else:
            sy += STAGE_H

    # ─── Arrows from pipeline stages to output cards ───────────────────────
    # Processing → Tier 0 (anchor to left output card center)
    # Derivation → Tier 1 (anchor to right output card center)
    # These go downward with a small bend.
    PH2_TOP = stage_tops[1]
    PH3_TOP = stage_tops[2]
    PH2_BOT = PH2_TOP + STAGE_H
    PH3_BOT = PH3_TOP + STAGE_H

    TIER0_W = SC_W * 0.40
    TIER1_W = SC_W * 0.57
    TIER0_X = SC_X + PAD
    TIER1_X = TIER0_X + TIER0_W + 10

    TIER0_CX = TIER0_X + TIER0_W / 2
    TIER1_CX = TIER1_X + TIER1_W / 2

    # Path: Derivation center → down to Tier 1 top
    DV_CX = STAGE_X + STAGE_W / 2

    # We route as an elbow:  stage_bottom → midpoint y → tier_top
    MID_Y = SC_Y + 2
    # Extraction (01) → draw straight down to Tier0 (via bend)
    # Processing (02) → Tier 0
    # Derivation (03) → Tier 1

    # Vertical line + bend for Processing → Tier 0
    s.line(STAGE_X + STAGE_W * 0.25, PH2_BOT,
           STAGE_X + STAGE_W * 0.25, MID_Y,
           stroke=TIER0[2], sw=1.2)
    s.line(STAGE_X + STAGE_W * 0.25, MID_Y, TIER0_CX, MID_Y,
           stroke=TIER0[2], sw=1.2)
    s.arrow_d(TIER0_CX, MID_Y, SC_Y + 2, color=TIER0[2], sw=1.5)

    # Straight arrow for Derivation → Tier 1
    s.arrow_d(TIER1_CX, PH3_BOT, SC_Y + 2, color=TIER1[2], sw=1.5)

    # Script labels on arrows
    s.text(STAGE_X + STAGE_W * 0.25 + 4, PH2_BOT + 10,
           "build_nordic_netcdf.py", anchor="start",
           size=7, fill=LIGHT, italic=True)
    s.text(TIER1_CX + 4, PH3_BOT + 10,
           "enrich_nordic_netcdf.py", anchor="start",
           size=7, fill=LIGHT, italic=True)

    # ═══════════════════════════════════════════════════════════════════════
    # SECTION C — OUTPUTS
    # ═══════════════════════════════════════════════════════════════════════
    s.rect(SC_X, SC_Y, SC_W, SC_H, rx=6,
           fill=SEC_C_BG, stroke=SEC_C_BR, sw=1)
    draw_section_label(s, SC_X + 8, SC_Y + 6, "C", "DATASET PRODUCTS", color="#0a4d3c")

    CARD_Y  = SC_Y + 20
    CARD_H  = SC_H - 28

    draw_output_card(
        s, TIER0_X, CARD_Y, TIER0_W, CARD_H,
        title="Tier 0 — Raw Observations",
        fname="nordic_tier0_2015_2024.nc",
        lines=["582 st. × 3 135 days · 58 MB",
               "4 vars: snow_depth · temp · precip"],
        hdr=TIER0[0], fill=TIER0[1], border=TIER0[2],
    )

    # Tier 0 → Tier 1 enrichment arrow
    s.arrow_r(TIER0_X + TIER0_W + 1, CARD_Y + CARD_H/2,
              TIER1_X - 1, color=TIER1[2], sw=1.8)
    s.text((TIER0_X + TIER0_W + TIER1_X) / 2,
           CARD_Y + CARD_H/2 - 6,
           "+ 6 derived", size=7.5, fill=TIER1[2], italic=True)

    draw_output_card(
        s, TIER1_X, CARD_Y, TIER1_W, CARD_H,
        title="Tier 1 — Derived Dataset",
        fname="nordic_tier1_2015_2024.nc",
        lines=["582 st. × 3 135 days · 133 MB",
               "SWE · Phenology · Melt · DDM · ROS · FT  |  CF-1.9"],
        hdr=TIER1[0], fill=TIER1[1], border=TIER1[2],
        primary=True,
    )

    # ═══════════════════════════════════════════════════════════════════════
    # STATISTICS BANNER
    # ═══════════════════════════════════════════════════════════════════════
    s.rect(ST_X, ST_Y, ST_W, ST_H, rx=5,
           fill=STAT_F, stroke=STAT_B, sw=1.2)

    stats = [
        ("582", "stations"),
        ("9", "winters  2015–2024"),
        ("1.8 M", "annotated station-days"),
        ("6", "derived parameters"),
        ("CF-1.9", "NetCDF standard"),
        ("Zenodo", "open archive"),
    ]
    seg = ST_W / len(stats)
    for i, (num, lbl) in enumerate(stats):
        sx = ST_X + seg * (i + 0.5)
        if i > 0:
            s.line(ST_X + seg * i, ST_Y + 5,
                   ST_X + seg * i, ST_Y + ST_H - 5,
                   stroke=STAT_B, sw=0.7)
        s.text(sx - 2, ST_Y + 13, num,
               anchor="end", size=10, weight="bold", fill=STAT_T)
        s.text(sx + 2, ST_Y + 13, lbl,
               anchor="start", size=8.2, fill=MID)

    # Footnote inside outer frame, below stats
    fn_y = ST_Y + ST_H + 10
    s.text(SA_X, fn_y,
           "† ERA5-Land: cross-validation only. "
           "Pearson R = 0.78, bias = −262 mm (ERA5-Land overestimates SWE "
           "in Scandinavian boreal terrain).",
           anchor="start", size=7, fill=LIGHT, italic=True)

    return s.render()


def main():
    svg_str = build()
    for out in OUTPUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg_str, encoding="utf-8")
        kb = len(svg_str.encode()) / 1024
        print(f"Saved ({kb:.0f} kB): {out}")


if __name__ == "__main__":
    main()
