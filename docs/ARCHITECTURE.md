# System Architecture

## Pipeline Flow

```
Raw APIs → data/raw/ → data/interim/ → data/processed/
              ↑                               ↓
         Extraction                     Derivation → NetCDF
```

Four strictly ordered phases — never skip tiers, never mix extraction with derivation.

---

## Module Map

### `src/extraction/` — one script per provider

| Script | Provider | Output |
|---|---|---|
| `fetch_smhi.py` | SMHI MetObs (snow depth, temp, precip) | `data/raw/smhi/smhi_*.csv` |
| `fetch_smhi_hydobs.py` | SMHI HydObs (discharge m³/s) | `data/raw/smhi/smhi_discharge.csv` |
| `fetch_fmi.py` | FMI station observations | `data/raw/fmi/` |
| `fetch_mesan.py` | MESAN 2.5 km GRIB2 reanalysis | `data/raw/mesan/` |
| `fetch_syke.py` | Syke water quality / discharge | `data/raw/syke/` |

### `src/processing/` — spatial and temporal harmonization

| Function | File | Description |
|---|---|---|
| `harmonize_point_to_grid()` | `alignment.py` | Ordinary Kriging: stations → 2.5 km LAEA grid |
| `resample_temporal()` | `alignment.py` | Standardize time resolution (sub-daily → daily) |
| `align_spatially_to_laea()` | `alignment.py` | Stub: rioxarray reproject for gridded inputs |
| `flag_physical_outliers()` | `quality_control.py` | NaN values outside physical bounds |
| `impute_missing_linear()` | `quality_control.py` | Linear gap-fill, max gap = 3 days |

### `src/derivation/hydrological_parameters.py` — all research-grade parameters

| Function | Inputs | Outputs |
|---|---|---|
| `calculate_swe_sturm()` | snow_depth | swe [mm], snow_density [g/cm³] |
| `calculate_snow_phenology()` | snow_depth (+ swe) | onset/melt-out DOY, duration, peak SWE |
| `calculate_snowmelt_dynamics()` | swe | snowmelt_rate, swe_accumulation_rate [mm/day] |
| `calculate_degree_day_factor()` | swe, temp_mean | degree_day_factor [mm/°C/day] |
| `detect_rain_on_snow()` | snow_depth, temp_mean, precip | rain_on_snow flag (0/1) |
| `calculate_freeze_thaw_cycles()` | temp_mean | freeze_thaw_count per station |
| `calculate_cold_content()` | snow_depth, temp_mean | cold_content [MJ/m²] |
| `calculate_runoff_potential()` | precip, soil_moisture | runoff_potential [mm/day], runoff_coeff, api |

### `src/common/` — shared utilities

| Module | Key exports |
|---|---|
| `config.py` | `RAW_DIR`, `INTERIM_DIR`, `PROCESSED_DIR` (from .env) |
| `geo_utils.py` | `get_laea_transformer()`, `project_points_to_laea()` |
| `io.py` | `save_to_csv()`, `save_to_netcdf()` |
| `logging_utils.py` | `setup_logger()` |

---

## Driver Scripts (`scripts/`)

| Script | Purpose | Output |
|---|---|---|
| `build_pilot_netcdf.py` | Dalarna 2023–24 pilot (M3) | `pilot/dalarna_tier0_2023_2024.nc` |
| `build_swe_grid.py` | Kriging upscale of pilot SWE (M4) | `pilot/dalarna_swe_gridded_2023_2024.nc` |
| `validate_swe_era5.py` | ERA5-Land SWE cross-validation (M4) | metrics + scatter plot |
| `build_nordic_netcdf.py` | Full Nordic 2015–2024 (M6) | `nordic/nordic_tier0_2015_2024.nc` |

---

## Canonical Projection

All spatial data uses **ETRS89/LAEA Europe (EPSG:3035)** with 2.5 km grid spacing
(matches MESAN). Point-source observations in WGS84 are reprojected via
`get_laea_transformer()` (pyproj, always_xy=True: input lon/lat, output x/y in metres).

---

## Output Format

All final datasets are **CF-1.9 compliant NetCDF4** files readable with `xarray.open_dataset()`.

Mandatory global attributes: `title`, `institution`, `source`, `Conventions`, `history`,
`geospatial_lat_min/max`, `geospatial_lon_min/max`, `time_coverage_start/end`, `license`, `version`.

---

## Makefile Targets (`pipelines/Makefile`)

```bash
make extract-smhi      # Download SMHI MetObs CSVs
make extract-hydobs    # Download SMHI HydObs discharge CSV
make extract-fmi       # Download FMI data
make extract-syke      # Download Syke data
make pilot-netcdf      # Build Dalarna pilot NetCDF
make swe-grid          # Kriging upscale → gridded SWE
make validate-swe      # ERA5-Land cross-validation
make nordic-netcdf     # Build full Nordic 2015–2024 NetCDF
make clean             # Wipe data/interim/ and data/processed/
```

---

## Test Suite

```bash
pytest                          # all 53 tests
pytest tests/test_swe_sturm.py  # Sturm SWE model (16 tests)
pytest tests/test_kriging.py    # Kriging upscale (8 tests)
pytest tests/test_snow_derived_params.py  # Phenology + process params (28 tests)
pytest --cov=src                # with coverage
```
