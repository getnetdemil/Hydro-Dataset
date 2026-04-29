# Nordic Hydrology Dataset (NordHydro)
## A Multi-Modal, Research-Ready Benchmark for Snow, Water Resources, and Water Quality

**Short name**: NordHydro  
**Target Venue**: [Workshop on Mining Imaging Data for Hydrological and Environmental Modelling (HydroImaging 2026)](https://hydroimaging.github.io/)  
**Primary Research Areas**: Snow Hydrology, Water Resources, Water Quality, Multi-Sensor Fusion, Physics-Informed ML  
**Geographic Focus**: Nordic Region — Sweden and Finland (core); Scandinavian margins (supplementary)  
**Submission Deadline**: May 13, 2026  
**Workshop**: Tampere, Finland, September 13–17, 2026

---

## 1. Executive Summary

Nordic researchers studying snow hydrology, water resources, and water quality face a shared bottleneck: the underlying data exists — SMHI, FMI, Syke, and MESAN all maintain world-class monitoring infrastructure — but it is siloed across agencies in incompatible formats (GRIB2, WFS/XML, OData, REST/JSON), different coordinate systems, and varying temporal resolutions. A researcher wanting to model snowmelt-driven runoff in a catchment straddling the Swedish-Finnish border currently needs to operate four separate data pipelines, reproject three different coordinate reference systems, and hand-derive Snow Water Equivalent from scratch. The result: 80% of research time on data engineering, 20% on science.

**NordHydro** eliminates this bottleneck. It is an open, reproducible dataset — not just a pipeline — that delivers pre-harmonized, physics-expanded Nordic hydrology data in a single format ready for immediate research use. Researchers download one dataset; they get everything they need.

The dataset spans **2015–2024**, covers **Sweden and Finland** at a uniform **2.5 km spatial resolution** in **CF-compliant NetCDF4** format projected to **ETRS89/LAEA Europe (EPSG:3035)**. It fuses three data modalities — in-situ station observations, gridded meteorological reanalysis, and satellite-derived imaging products — and expands the parameter space beyond what any single agency provides by deriving research-critical variables (Snow Water Equivalent, snowmelt rates, runoff potential, water quality indices) that are not operationally available but are routinely needed by the research community.

This dataset directly addresses the **HydroImaging 2026** call for scalable, imaging-driven environmental benchmarks and serves as a **Foundation Model pretraining corpus** for next-generation hydrological AI.

---

## 2. The Problem: Data Abundance, Research Inaccessibility

### 2.1 The Multi-Agency Silo Problem

Nordic hydrology data is abundant but structurally inaccessible:

| Agency | Data type | Format | API | Projection |
|---|---|---|---|---|
| SMHI MetObs | Station obs (T, precip, snow depth) | REST/JSON | `opendata-download-metobs.smhi.se` | WGS84 point |
| SMHI HydObs | Discharge gauges | REST/JSON | same portal | WGS84 point |
| MESAN | Gridded reanalysis (2.5 km, hourly) | GRIB2 | grid archive API | Rotated lat/lon |
| FMI WFS | Finnish station obs | OGC WFS / GML-XML | `opendata.fmi.fi/wfs` | WGS84 point |
| FMI H-SAF | Satellite snow products | HDF5 / NetCDF | FTP / EUMETSAT | Lambert conformal |
| Syke | Finnish discharge + nutrients | OData | odata.syke.fi | WGS84 point |
| MODIS | Optical/thermal EO imagery | HDF4 | NASA / GEE | Sinusoidal |
| ERA5-Land | Global reanalysis | NetCDF | CDS API | Regular lat/lon |

No single researcher should need to master eight different APIs and six projection systems to study one catchment. **NordHydro resolves this**: one dataset, one format, one projection.

### 2.2 The Parameter Gap

Agencies publish raw measurements. Critical research parameters are absent:

| Parameter | Needed for | Why not available |
|---|---|---|
| Snow Water Equivalent (SWE) | Snowmelt modeling, flood forecasting | Snow depth is measured; density requires derivation |
| Snow density | SWE derivation, avalanche risk | Not directly observed at most stations |
| Snowmelt rate | Runoff timing, spring flood prediction | Requires temperature history + land cover |
| Accumulated degree-days | Phenology, melt onset | Trivial to compute but never pre-packaged |
| Water Quality Index | Lake monitoring, ecosystem health | Requires fusion of satellite turbidity + field nutrients |

**NordHydro derives these parameters** from the raw agency data and publishes them as first-class dataset variables alongside the original observations.

---

## 3. The Dataset

### 3.1 What Researchers Get

| Property | Value |
|---|---|
| **Format** | CF-compliant NetCDF4 (Xarray-compatible), Parquet (station metadata) |
| **Projection** | ETRS89/LAEA Europe (EPSG:3035), 2.5 km × 2.5 km grid |
| **Temporal coverage** | 2015–2024, daily |
| **Primary season** | October–April (winter, 7 months) — full year for auxiliary variables |
| **Geographic extent** | Sweden + Finland; 55–71°N, 10–32°E |
| **Station count** | ~600 Nordic stations (425 Swedish SMHI + ~175 Finnish FMI) |
| **Sequences (ML-ready)** | ~810,000 station-season 30-day sliding windows |
| **Tracks** | Snow & Water Resources; Water Quality |
| **License** | CC-BY 4.0 (FMI-derived), CC0 (SMHI, ERA5-derived) |
| **Access** | `data/processed/` — one NetCDF per year per track; `make build-dataset` |

### 3.2 Three-Tier Variable Structure

**Tier 0 — Observed** (raw agency data, harmonized to EPSG:3035 and daily resolution):
Station snow depth, air temperature (2m, min, max), precipitation, discharge, turbidity, and all MESAN gridded fields.

**Tier 1 — Derived** (new parameters computed from Tier 0 — the value-add):
Snow Water Equivalent, snow density, accumulated degree-days, snowmelt rate, runoff potential, runoff coefficient, water quality index.

**Tier 2 — ML-Ready** (normalized sequences for Foundation Model training):
30-day windows per station with cyclical day-of-year encoding, anomaly class labels, and country/climate-class metadata.

---

## 4. Data Sources

NordHydro fuses data from eleven sources across three modalities. All data is openly licensed.

### 4.1 In-Situ Station Observations

| Source | Provider | Variables | Stations | Period |
|---|---|---|---|---|
| **SMHI MetObs** | SMHI, Sweden | Snow depth, air temperature (min/max/mean), precipitation, wind speed, humidity | ~500 active | 1881–present (systematic: 1945) |
| **SMHI HydObs** | SMHI, Sweden | River discharge (m³/s), water level | ~250 gauges | 1900–present |
| **FMI WFS (daily)** | FMI, Finland | Snow depth, precipitation, air temperature (min/max/mean), ground temperature | ~269 active | 2010–present |
| **FMI WFS (hourly)** | FMI, Finland | Air temperature, humidity, wind speed, precipitation accumulation, weather phenomena (WAWA) | ~201 active | 2010–present |
| **Syke OData** | SYKE, Finland | River discharge, water temperature, N, P, turbidity | Catchment network | 2000–present |

**API access notes**:
- SMHI MetObs: REST/JSON, no authentication, CC0, 2–5 req/sec limit
- FMI WFS: OGC WFS 2.0, no authentication, CC-BY 4.0, chunk requests to ≤90 days (daily) / ≤30 days (hourly)
- Syke: OData REST, no authentication, CC-BY 4.0

### 4.2 Gridded Reanalysis & Climate Data

| Source | Provider | Variables | Resolution | Period |
|---|---|---|---|---|
| **MESAN AROME** | SMHI, Sweden | Air temp, precip, frozen precip fraction, humidity, wind (u/v), visibility, cloud cover, surface pressure | 2.5 km, hourly | 2015–present |
| **PTHBV** | SMHI, Sweden | Daily precipitation (wind-corrected), daily air temperature | 4 km, daily | 1961–present |
| **SMHI HYPE** | SMHI, Sweden | Streamflow, nitrogen transport, phosphorus transport (modelled) | Catchment-scale | 2000–present |
| **ERA5-Land** | ECMWF / C3S | SWE, snow depth, 2m temperature, precipitation, cloud cover, soil moisture | 0.1° (~9 km), hourly | 1950–present |

**Download notes**:
- MESAN GRIB2: grid archive API, chunk by ≤7 days per request; ~GB/day; `cfgrib` for parsing
- PTHBV: SMHI API, NetCDF/CSV/JSON, monthly update cycle (1-month lag)
- ERA5-Land: CDS API (`cdsapi`), requires `~/.cdsapirc` registration; asynchronous queue, 2–10 hours for multi-year downloads

### 4.3 Satellite & Earth Observation (Imaging Inputs)

| Source | Provider | Variables | Resolution | Period |
|---|---|---|---|---|
| **FMI H-SAF** | EUMETSAT / FMI | Snow cover probability, passive microwave SWE, soil moisture | 0.1° (~10 km) | 2008–present |
| **MODIS Terra** | NASA / GEE | Snow cover extent (MOD10A1), LST thermal (MOD11A1), surface reflectance | 500 m (snow), 1 km (LST) | 2000–present |
| **CGLS Land Cover** | Copernicus | Land cover class (forest, open, urban, water) | 100 m → 2.5 km aggregated | Annual |

**Imaging access notes**:
- MODIS: accessed via Google Earth Engine (`earthengine-api`); 500 m optical patches for spatial context
- H-SAF: EUMETSAT Data Store, free registration required
- Cloud contamination handling: 5-day maximum snow cover composite; LST provides secondary signal under cloud cover

---

## 5. Parameter Derivation — Expanding the Agency Parameter Space

The core scientific contribution of NordHydro is computing parameters that agencies do not provide operationally. Every derivation is implemented in `src/derivation/`, documented with its formula, citation, and CF-compliant output attributes.

### 5.1 Snow & Water Resources Track

| Derived Parameter | From | Method | Reference |
|---|---|---|---|
| Snow Water Equivalent (SWE, mm) | Snow depth + MESAN T | Sturm et al. (2010) empirical density model with Nordic climate classes | Sturm et al., JHydromet 2010 |
| Snow density (kg/m³) | Snow depth + MESAN T + DOY | Intermediate in SWE derivation | Sturm et al. (2010) |
| Cold Degree-Days (CDD, °C·day) | MESAN / PTHBV T | Cumulative T deficit below 0°C from Oct 1 | Standard hydrological practice |
| Thawing Degree-Days (TDD, °C·day) | MESAN / PTHBV T | Cumulative T excess above 0°C from Mar 1 | Standard hydrological practice |
| Snowmelt rate (mm/day) | MESAN T + CGLS land cover | Degree-day model with land-cover-specific DDF values | Hock (2003) |
| Runoff potential (mm/day) | Snowmelt + liquid precip | Simplified water balance (Snowmelt + P_liquid) | Lindström et al. (1997) |
| Runoff coefficient (Q/P) | SMHI HydObs Q + MESAN P | Ratio at catchment scale | Standard |
| Frozen precip indicator (FI) | FMI T_min + precip | Binary: 1 if precip > 0 and T_min < 0°C | Derived; flags where SWE accretes |

### 5.2 Water Quality Track (collaborator-owned)

| Derived Parameter | From | Method |
|---|---|---|
| Spatio-temporal Water Quality Index | Syke nutrients (N, P) + FMI satellite turbidity | Kriging + multi-variable normalization |
| Gap-filled nutrient time series | Syke field obs + satellite turbidity proxy | Satellite-guided temporal interpolation |

---

## 6. Research Tracks

### Track 1: Snow Hydrology + Water Resources
**Branch**: `feature/snow-parameters`  
**Owner**: Getnet Demil  
**Data sources**: SMHI MetObs, SMHI HydObs, SMHI HYPE, MESAN, PTHBV, FMI WFS, FMI H-SAF, MODIS, ERA5-Land  
**Output**: `data/processed/snow/snow_nordic_<YYYY>.nc` — gridded SWE, snowmelt, runoff, and all Tier 0 snow + hydrology parameters

### Track 2: Water Quality
**Branch**: `feature/water-quality-pipeline`  
**Owner**: Collaborator  
**Data sources**: Syke OData, FMI WFS, FMI satellite turbidity, ERA5-Land  
**Output**: `data/processed/wq/water_quality_nordic_<YYYY>.nc` — water quality index, gap-filled nutrients, turbidity

### Integration
Both tracks merge into the `experiment` branch where a unified 4D (x, y, z, t) environmental cube is assembled. Integration is scoped post-May 7 (M6), estimated for late May 2026.

---

## 7. Technical Approach

### 7.1 Modular Pipeline (Means, Not the End)

The pipeline is the machinery; the dataset is the product. The four-phase pipeline:

```
Extraction → Interim (QC + align) → Derivation → Output (NetCDF)
```

- **Extraction** (`src/extraction/`): One module per provider. Handles API chunking, retry logic, and raw data storage in `data/raw/`.
- **Processing** (`src/processing/`): Spatial reprojection to EPSG:3035, temporal resampling to daily, physical QC (hard bounds + z-score flags), gap interpolation (linear, ≤5 days).
- **Derivation** (`src/derivation/`): Research-grade parameters computed from processed Tier 0 fields.
- **Output**: CF-compliant NetCDF4 with mandatory global attributes (`Conventions`, `institution`, `source`, `references`, `grid_mapping`).

### 7.2 Reproducibility

```bash
make build-dataset   # runs full extraction → derivation for all providers
make extract-smhi    # individual extraction targets
pytest --cov=src     # test coverage
```

All outputs are deterministic given the same API responses. Raw data is stored in `data/raw/` (never committed to git); processed outputs in `data/processed/`.

### 7.3 Foundation Model Readiness

- **Format**: Xarray-native NetCDF4 opens with `xr.open_dataset()` — no preprocessing required
- **Sequences**: Prebuilt 30-day sliding windows as compressed `.npz` arrays (NumPy)
- **Features**: 12 features per station per day (matches the feature set documented in `docs/fmi_data_description.md §7`)
- **Labels**: SWE anomaly class (Normal / High / Extreme / Drought) for classification pretraining
- **Multi-modal pairing**: Each station sequence can be paired with a co-located MESAN 2D image stack and MODIS optical patch for CNN/ViT fusion pretraining

---

## 8. Timeline & Milestones

| Milestone | Deliverable | Deadline |
|---|---|---|
| **M1: Source Readiness** | SMHI, MESAN, FMI, Syke extraction scripts verified; first raw data in `data/raw/` | April 30, 2026 |
| **M2: Pilot Dataset** | Single-season (2023–24), single sub-domain (Dalarna pilot tile) NetCDF with Tier 0 variables | April 30, 2026 |
| **M3: SWE Derivation** | Full Sturm SWE + CDD/TDD + snowmelt over pilot domain; validated against ERA5-Land | May 5, 2026 |
| **M4: Dataset v1.0** | Full 2015–2024, all Nordic domain, both tracks, Tier 0 + Tier 1 complete | May 7, 2026 |
| **M5: Validation** | RMSE/KGE scores vs ERA5-Land and H-SAF; spatial maps and time series figures | May 11, 2026 |
| **M6: Paper Submission** | LaTeX/PDF submitted to HydroImaging 2026 | **May 13, 2026** |
| **M7: Public Release** | DOI (Zenodo), GitHub release tag, dataset documentation | July 2026 |
| **M8: Workshop** | Poster/talk presentation, Tampere, Finland | **Sept 13–17, 2026** |

---

## 9. Impact & Vision

### 9.1 Immediate Research Value

NordHydro gives the Nordic research community a dataset that:
- Eliminates 80% of data engineering overhead per project
- Provides physically consistent, agency-quality variables augmented with derived parameters that are routinely re-derived in isolation across research groups
- Covers both countries (Sweden + Finland) in a single, consistent format — the first dataset to do so at this resolution

### 9.2 Foundation Model Pretraining Corpus

The ~810,000 station-season sequences covering diverse snow regimes (tundra, boreal, maritime, continental) across the Nordic domain constitute a high-quality pretraining corpus for:
- **Hydrological Foundation Models** — spatial and temporal generalization across Nordic catchments
- **Vision-Language Models (VLMs) for EO** — paired station sequences + MESAN image stacks enable joint language-image pretraining on environmental data
- **Anomaly Detection** — SWE Extreme/Drought class labels provide supervision signal for rare-event modeling

### 9.3 Community Infrastructure

NordHydro is designed to grow. New data sources (Norway via MET Norway WFS, Denmark via DMI) can be added by implementing a new `src/extraction/fetch_<provider>.py` module following the existing pattern. The dataset format is stable (CF NetCDF4) and versioned.

---

## 10. References

- Sturm, M., et al. (2010). Estimating snow water equivalent using snow depth data and climate classes. *Journal of Hydrometeorology, 11*(6), 1380–1394.
- Hock, R. (2003). Temperature index melt modelling in mountain areas. *Journal of Hydrology, 282*(1–4), 104–115.
- Lindström, G., et al. (1997). Development and test of the distributed HBV-96 hydrological model. *Journal of Hydrology, 201*(1–4), 272–288.
- Johansson, B. (2000). Areal precipitation and temperature in the Swedish mountains. *SMHI Reports Hydrology, 57*.
- Alexandersson, H. (2003). Wind corrected manual precipitation observations. *SMHI Technical Report, RMK No. 97*.
- Gupta, H. V., et al. (2009). Decomposition of the mean squared error and NSE performance criteria. *Journal of Hydrology, 377*(1–2), 80–91.
- Lundberg, A., & Koivusalo, H. (2003). Estimating winter evaporation in boreal forests with operational snow course data. *Hydrological Processes, 17*(8), 1479–1493.

---

*Last updated*: April 29, 2026  
*Status*: ACTIVE — M1/M2 deadline April 30, 2026
