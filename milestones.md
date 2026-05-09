# Project Timeline & Milestones: Hydro-Dataset (HydroImaging 2026)

**Submission Deadline**: May 13, 2026
**Workshop Dates**: September 13–17, 2026 (Tampere, Finland)

---

## Roadmap Overview

### Phase 1: Data Infrastructure & Integration (April 23 – April 30)

| Milestone | Key Tasks | Target | Status |
|:---|:---|:---|:---|
| **M1: Source Readiness** | SMHI MetObs, HydObs, FMI, Syke, MESAN extraction scripts | Apr 26 | **Complete** |
| **M2: Harmonization** | LAEA reprojection, daily temporal normalization, QC | Apr 28 | **Complete** |
| **M3: Initial Merge** | `dalarna_tier0_2023_2024.nc` — 22 stations, 213 days, CF-1.9 | Apr 30 | **Complete** |

### Phase 2: Parameter Derivation & Mining (May 01 – May 07)

| Milestone | Key Tasks | Target | Status |
|:---|:---|:---|:---|
| **M4: SWE Derivation** | Sturm (2010) SWE model + Kriging upscale + ERA5-Land validation | May 03 | **Complete** |
| **M5: Water Quality Proxy** | FMI satellite turbidity + Syke nutrient integration | — | **Separate paper** |
| **M6: Dataset Version 1.0** | `nordic_tier0_2015_2024.nc` — 582 stations, 9 seasons; derived params | May 07 | **Complete** |

### Phase 3: Validation & Paper Drafting (May 08 – May 13)

| Milestone | Key Tasks | Target | Status |
|:---|:---|:---|:---|
| **M7: Benchmarking** | Interannual SWE anomaly + DDM calibration across 9 seasons | May 09 | **Complete** |
| **M8: Visual Analytics** | Spatial maps + time-series figures for paper | May 11 | **Complete** |
| **M9: Submission** | Finalize LaTeX/PDF → HydroImaging 2026 | **May 13** | In Progress |

---

## Completed Deliverables

### M3 — Dalarna Pilot NetCDF
- **File**: `data/processed/pilot/dalarna_tier0_2023_2024.nc`
- **Coverage**: 22 SMHI stations, 60–61.5°N, 13–16°E, Oct 2023 – Apr 2024
- **Variables**: `snow_depth`, `temp_mean`, `precip`, `frozen_precip`
- **Format**: CF-1.9 Xarray-compatible NetCDF4

### M4 — SWE Derivation & Validation
- **Kriging grid**: `data/processed/pilot/dalarna_swe_gridded_2023_2024.nc`
  — 58 × 68 LAEA cells at 2.5 km, peak SWE 185 mm
- **ERA5-Land validation** (`scripts/validate_swe_era5.py`):
  - N = 2 770 snow-present station-day pairs
  - RMSE = 293 mm, Bias = −262 mm (ERA5 overestimates), Pearson R = 0.78, KGE = −0.13
- **Manuscript**: `Overleaf_manuscript/` updated with actual results

### M6 — Full Nordic Dataset v1.0
- **File**: `data/processed/nordic/nordic_tier0_2015_2024.nc`
- **Coverage**: 582 SMHI stations, 55–70°N, 10–30°E, Oct 2015 – Apr 2024
- **Seasons**: Nine winters (2015–16 through 2023–24), 3 135 days
- **Size**: 58 MB, version `1.0`
- **HydObs extractor**: `src/extraction/fetch_smhi_hydobs.py` (`make extract-hydobs`)

### Derived Parameters (all in `src/derivation/hydrological_parameters.py`)

| Parameter | Function | Nordic v1.0 Result |
|---|---|---|
| SWE + snow density | `calculate_swe_sturm` | 9yr mean peak 94.7 mm; R=0.78 vs ERA5 |
| Snow phenology | `calculate_snow_phenology` | Mean duration 123.7 days across 9 seasons |
| Melt/accum rates | `calculate_snowmelt_dynamics` | Mean melt 6.2 mm/day (pilot) |
| Degree-day factor | `calculate_degree_day_factor` | Median 2.26–3.53 mm/°C/day across seasons |
| Rain-on-snow flag | `detect_rain_on_snow` | 398–721 station-days/season; peak 2023–24 |
| Freeze-thaw cycles | `calculate_freeze_thaw_cycles` | Mean 23.9 cycles/station across 9 seasons |
| Cold content | `calculate_cold_content` | Max 18.3 MJ/m² (pilot) |
| Runoff potential | `calculate_runoff_potential` | Mean RC 0.23 (pilot) |

**Test suite**: 53 tests passing (`pytest`)

### M7 — Benchmarking
- **Script**: `scripts/benchmark_snow_params.py` (`make benchmark`)
- **Outputs**: `data/processed/nordic/benchmark_results.json`, `ddm_per_season.csv`, `peak_swe_per_season.csv`
- **Key results** (582 stations, 9 seasons):

| Season | Peak SWE (mm) | Anomaly (mm) | Duration (d) | DDM | ROS events | FT cycles |
|---|---|---|---|---|---|---|
| 2015–16 | 83.7 | −12.3 | 108.3 | 2.89 | 678 | 21.5 |
| 2016–17 | 72.5 | −21.7 | 136.9 | 3.21 | 581 | 29.2 |
| 2017–18 | 131.6 | +36.8 | 128.9 | 2.95 | 621 | 21.2 |
| 2018–19 | 102.0 | +6.8 | 101.7 | 2.42 | 483 | 24.8 |
| 2019–20 | 75.7 | −22.7 | 118.6 | 2.43 | 398 | 23.0 |
| 2020–21 | 98.9 | +6.1 | 104.9 | 2.54 | 479 | 18.3 |
| 2021–22 | 87.2 | −6.6 | 129.3 | 2.26 | 461 | 28.8 |
| 2022–23 | 92.3 | −1.7 | 135.7 | 2.76 | 541 | 26.1 |
| 2023–24 | 108.8 | +16.5 | 148.6 | 3.53 | 721 | 22.0 |
| **Mean** | **94.7** | — | **123.7** | **2.78** | **551** | **23.9** |

### M8 — Visual Analytics
- **Script**: `scripts/generate_figures.py` (`make figures`)
- **Outputs** (`docs/figures/` + `Overleaf_manuscript/figures/`):
  - `mean_peak_swe_map.png` — spatial distribution of 9yr mean peak SWE across 582 stations
  - `swe_anomaly_timeseries.png` — interannual SWE anomaly bar chart (±1σ)
  - `ddm_boxplot.png` — per-season DDM distribution across calibrated stations
  - `ros_frequency_map.png` — total ROS event frequency per station
- All four figures embedded in manuscript (`sections/05_results.tex`)

---

## Branch Strategy

| Branch | Purpose |
|---|---|
| `feature/snow-parameters` | Getnet — snow derivation, Nordic dataset (current) |
| `feature/water-quality-pipeline` | Collaborator — water quality track (separate paper) |
| `experiment` | Stable integration; `v1.0` tag to be applied after M6 merge |
| `main` | Release-only; receives PRs from `experiment` at stable milestones |

---

## Remaining Work

| Item | Owner | Deadline | Notes |
|---|---|---|---|
| M5: Water quality | Collaborator | TBD | Scoped to separate paper — out of scope for this submission |
| M9: Manuscript final proofread + PDF | Getnet | May 13 | LaTeX compiles; figures embedded; needs final read |
| M9: Zenodo dataset archive | Getnet | May 13 | Nordic v1.0 + code DOI for submission |
| M9: Submit to HydroImaging 2026 | Getnet | May 13 | |

---

**Last Updated**: 2026-05-07
