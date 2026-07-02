**# 𝑯𝒀𝑫𝑹𝑶-𝑫𝑨𝑻𝑨𝑺𝑬𝑻 v1.1: 𝑨 𝑴𝒖𝒍𝒕𝒊-𝑴𝒐𝒅𝒂𝒍 𝑶𝒑𝒆𝒏-𝑺𝒐𝒖𝒓𝒄𝒆 𝑷𝒊𝒑𝒆𝒍𝒊𝒏𝒆 𝒇𝒐𝒓 𝑵𝒐𝒓𝒅𝒊𝒄 𝑯𝒚𝒅𝒓𝒐𝒍𝒐𝒈𝒊𝒄𝒂𝒍 𝑹𝒆𝒔𝒆𝒂𝒓𝒄𝒉 𝒂𝒏𝒅 𝑭𝒐𝒖𝒏𝒅𝒂𝒕𝒊𝒐𝒏 𝑴𝒐𝒅𝒆𝒍 𝑩𝒆𝒏𝒄𝒉𝒎𝒂𝒓𝒌𝒊𝒏𝒈**
**Multi-Modal Open-Source Pipeline for Nordic Hydrological Research and Foundation Model Benchmarking**

Dataset: [https://zenodo.org/records/20287300](https://zenodo.org/records/20287300)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Workshop](https://img.shields.io/badge/Workshop-HydroImaging_2026-orange?style=flat-square)](https://hydroimaging.github.io/)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square)](https://www.python.org/)
[![CF-1.9](https://img.shields.io/badge/NetCDF-CF--1.9-green?style=flat-square)](https://cfconventions.org/)

---

## Overview

Hydro-Dataset v1.1 is a reproducible, script-driven pipeline that fuses Nordic meteorological and hydrological station observations into a research-grade benchmark dataset. It harmonizes **582 SMHI MetObs stations** across **nine hydrological winters (2015–2024)** into a unified CF-1.9 NetCDF product annotated with six derived snow parameters — providing **1.8 million annotated station-days** ready for Hydrological Foundation Model training.

Cross-validation against ERA5-Land confirms station-anchored SWE is more credible ground truth than reanalysis (Pearson R = 0.78, bias = −262 mm; ERA5-Land systematically overestimates SWE in Scandinavian boreal terrain).

---

## Output Products

| Product | Filename | Size | Contents |
| :--- | :--- | :--- | :--- |
| **Tier 0** | `nordic_tier0_2015_2024.nc` | 58 MB | Raw harmonised observations (4 variables) |
| **Tier 1** | `nordic_tier1_2015_2024.nc` | 133 MB | Tier 0 + 6 derived snow parameters |

Both products are CF-1.9 compliant and loadable with `xarray.open_dataset()`. Zenodo archive (DOI forthcoming upon publication).

---

## Data Sources

| Provider | Type | Key Variables |
| :--- | :--- | :--- |
| **SMHI MetObs** | Station | Air temperature, precipitation, snow depth |
| **SMHI HydObs** | Station | Discharge (m³/s) |
| **FMI** | Station | Air temperature, precipitation, snow depth |
| **MESAN** | 2.5 km Reanalysis | Meteorological fields (Kriging reference grid) |
| **ERA5-Land** | Reanalysis | SWE — cross-validation only |

---

## Derived Snow Parameters

| Parameter | Method | Units |
| :--- | :--- | :--- |
| Snow Water Equivalent (SWE) | Sturm et al. (2010) taiga density model | mm |
| Snow phenology | Onset DOY, melt-out DOY, duration, peak SWE day | days |
| Melt & accumulation rates | SWE finite differences | mm day⁻¹ |
| Degree-day melt factor (DDM) | Hock (2003) temperature-index | mm °C⁻¹ day⁻¹ |
| Rain-on-snow flag | Depth + temperature + precipitation threshold | binary |
| Freeze-thaw cycles | Sign changes in daily temperature series | count |

---

## Pipeline Architecture

```
DATA SOURCES → EXTRACTION → PROCESSING → DERIVATION → OUTPUT
               src/extraction/  src/processing/  src/derivation/
               data/raw/        data/interim/    data/processed/
```

Four strictly ordered phases — never skip tiers, never mix extraction with derivation.

| Phase | Module | Key Operations |
| :--- | :--- | :--- |
| Extraction | `src/extraction/` | Provider-specific fetchers (SMHI, FMI, MESAN) |
| Processing | `src/processing/` | LAEA reproject (EPSG:3035), QC outlier flags, linear gap-fill, Kriging 2.5 km |
| Derivation | `src/derivation/` | SWE (Sturm 2010), phenology, melt dynamics, DDM, rain-on-snow, freeze-thaw |
| Common | `src/common/` | Config, geo-utils (WGS84→LAEA), CF-1.9 NetCDF I/O, logging |

---

## Getting Started

```bash
git clone <repo-url>
cd Hydro-Dataset
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add SMHI / FMI / CDS API keys
```

```bash
cd pipelines
make extract-smhi             # download 582 SMHI station CSVs
make nordic-netcdf            # build Tier 0 NetCDF (58 MB)
make enrich-netcdf            # embed derived parameters → Tier 1 (133 MB)
make validate-swe             # ERA5-Land cross-validation
make benchmark                # 9-season interannual benchmarking
make figures                  # generate manuscript figures
```

---

## Tests

```bash
pytest                                      # all 53 tests
pytest tests/test_swe_sturm.py             # Sturm SWE model — 16 tests
pytest tests/test_kriging.py               # Kriging upscale — 8 tests
pytest tests/test_snow_derived_params.py   # Derived parameters — 28 tests
pytest --cov=src                           # with coverage report
```

---

## Repository Structure

```
Hydro-Dataset/
├── src/
│   ├── extraction/       # Provider-specific API fetchers
│   ├── processing/       # Spatial alignment, QC, Kriging
│   ├── derivation/       # Snow parameter logic
│   └── common/           # Config, geo-utils, I/O, logging
├── scripts/              # Driver scripts (build NetCDF, validate, benchmark, figures)
├── pipelines/            # Makefile orchestration
├── tests/                # 53 automated tests (pytest)
├── data/                 # raw/ → interim/ → processed/ (not committed)
└── .env.example          # environment template
```

---

## License

MIT. Raw input data are openly accessible via the [SMHI Open Data API](https://opendata.smhi.se) and [FMI Open Data portal](https://en.ilmatieteenlaitos.fi/open-data); no registration required.
