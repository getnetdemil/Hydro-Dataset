# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Hydro-Dataset is a modular, script-driven data pipeline that fuses Nordic meteorological, hydrological, and satellite data into a research-grade benchmark dataset. It is developed for the **HydroImaging 2026** workshop. The final output is Xarray-compatible NetCDF files following CF Metadata Conventions, intended for Foundation Model training on snow hydrology, water resources, and water quality.

## Commands

**Setup**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in API keys and paths
```

**Pipeline (run from `pipelines/`)**
```bash
make extract-all       # run all extraction scripts
make extract-smhi      # individual provider ingestion
make build-dataset     # processing + derivation (stub, extend as needed)
make clean             # wipe data/interim/ and data/processed/
```

**Tests and Linting**
```bash
pytest                          # run all tests
pytest tests/test_specific.py   # run a single test file
pytest --cov=src                # with coverage
black src/                      # format
flake8 src/                     # lint
```

## Architecture

The pipeline is a strict 4-phase linear flow:

```
Extraction → Interim → Processing → Derivation → Output
```

| Phase | Location | Responsibility |
|---|---|---|
| Extraction | `src/extraction/` | One class/script per provider: `fetch_smhi.py`, `fetch_fmi.py`, `fetch_mesan.py`, `fetch_syke.py` |
| Processing | `src/processing/` | `alignment.py` (temporal resample, spatial warp to LAEA), `quality_control.py` (outlier flagging, gap-fill) |
| Derivation | `src/derivation/` | Research-grade parameter logic: `hydrological_parameters.py` (SWE via Sturm 2010, runoff potential) |
| Common | `src/common/` | `config.py` (reads `.env`, exposes `RAW_DIR`/`INTERIM_DIR`/`PROCESSED_DIR`), `geo_utils.py` (WGS84 → LAEA EPSG:3035), `io.py` (CSV and NetCDF I/O), `logging_utils.py` |

**Canonical projection**: ETRS89/LAEA Europe (EPSG:3035). All spatial data must be projected to this CRS before processing.

**Storage tiers**: `data/raw/` → `data/interim/` → `data/processed/`. Never skip tiers. `data/sample/` holds tiny test fixtures only.

## Data Sources

| Provider | API style | Key variables |
|---|---|---|
| SMHI MetObs | REST/JSON | Air temp, precip, snow depth, water level |
| MESAN | GRIB2 download | 2.5 km gridded reanalysis |
| FMI | WFS + H-SAF/MODIS | Station obs, satellite snow cover, soil moisture |
| Syke | OData | Discharge, nutrients (N, P), turbidity |
| ERA5-Land / MODIS | CDS API / GEE | Cross-validation and gap-filling |

API keys go in `.env` (`SMHI_API_KEY`, `FMI_API_KEY`, `SYKE_API_KEY`); `src/common/config.py` loads them.

## Branching Rules

This project uses a **three-tier model** (`main` → `experiment` → `feature/*`):

- Never push directly to `main` or `experiment`.
- All feature PRs target `experiment`, not `main`.
- `main` receives PRs only from `experiment` when a stable milestone is reached.
- Branch naming: `feature/name-of-task` (e.g., `feature/derive-swe-model`).

## Adding New Modules

- **New data source**: add `src/extraction/fetch_<provider>.py`, register a `make extract-<provider>` target in `pipelines/Makefile`, document variables in `docs/DATA_SOURCES.md`.
- **New derivation**: add to `src/derivation/`, include formula citation and CF-compliant `attrs` on all output variables, document in `docs/DERIVATION_METHODS.md`.
- Never mix extraction logic with derivation logic in the same script.
- Never commit `.env` files; update `.env.example` for any new keys.
- Never commit raw data files (`.csv`, `.grib`, `.nc`) to git.
