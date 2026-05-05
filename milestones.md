# Project Timeline & Milestones: Hydro-Dataset (HydroImaging 2026)

**Submission Deadline**: May 13, 2026
**Workshop Dates**: September 13–17, 2026 (Tampere, Finland)

---

## Roadmap Overview

### Phase 1: Data Infrastructure & Integration (April 23 – April 30)

| Milestone | Key Tasks | Target | Status |
|:---|:---|:---|:---|
| **M1: Source Readiness** | SMHI MetObs, HydObs, FMI, Syke, MESAN extraction scripts | Apr 26 | Complete |
| **M2: Harmonization** | LAEA reprojection, daily temporal normalization, QC | Apr 28 | Complete |
| **M3: Initial Merge** | `dalarna_tier0_2023_2024.nc` — 22 stations, 213 days, CF-1.9 | Apr 30 | **Complete** |

### Phase 2: Parameter Derivation & Mining (May 01 – May 07)

| Milestone | Key Tasks | Target | Status |
|:---|:---|:---|:---|
| **M4: SWE Derivation** | Sturm (2010) SWE model + Kriging upscale + ERA5-Land validation | May 03 | **Complete** |
| **M5: Water Quality Proxy** | FMI satellite turbidity + Syke nutrient integration | May 05 | Pending |
| **M6: Dataset Version 1.0** | `nordic_tier0_2015_2024.nc` — 582 stations, 9 seasons; derived params | May 07 | **Complete** |

### Phase 3: Validation & Paper Drafting (May 08 – May 13)

| Milestone | Key Tasks | Target | Status |
|:---|:---|:---|:---|
| **M7: Benchmarking** | RMSE/KGE vs field gold standards; DDM/phenology validation | May 09 | Pending |
| **M8: Visual Analytics** | Spatial maps + time-series figures for paper | May 11 | Pending |
| **M9: Submission** | Finalize LaTeX/PDF → HydroImaging 2026 | **May 13** | Pending |

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
- **Seasons**: Nine winters (2015–16 through 2023–24), 3135 days
- **Size**: 58 MB, version `1.0`
- **HydObs extractor**: `src/extraction/fetch_smhi_hydobs.py` (run `make extract-hydobs`)

### Derived Parameters (all in `src/derivation/hydrological_parameters.py`)

| Parameter | Function | Key Result |
|---|---|---|
| SWE + snow density | `calculate_swe_sturm` | Taiga model, R=0.78 vs ERA5 |
| Snow phenology | `calculate_snow_phenology` | Onset DOY ~30, duration ~161 days |
| Melt/accum rates | `calculate_snowmelt_dynamics` | Mean melt 6.2 mm/day |
| Degree-day factor | `calculate_degree_day_factor` | 2.5–4.1 mm/°C/day |
| Rain-on-snow flag | `detect_rain_on_snow` | 35 events (Dalarna pilot) |
| Freeze-thaw cycles | `calculate_freeze_thaw_cycles` | Mean 4, max 34 |
| Cold content | `calculate_cold_content` | Max 18.3 MJ/m² |
| Runoff potential | `calculate_runoff_potential` | API method, mean RC 0.23 |

**Test suite**: 53 tests passing (`pytest`)

---

## Branch Strategy

| Branch | Purpose |
|---|---|
| `feature/snow-parameters` | Getnet — snow derivation, Nordic dataset (current) |
| `feature/water-quality-pipeline` | Collaborator — M5 water quality track |
| `experiment` | Stable integration; `v1.0` tag to be applied after M6 merge |
| `main` | Release-only; receives PRs from `experiment` at stable milestones |

---

**Last Updated**: 2026-04-30
