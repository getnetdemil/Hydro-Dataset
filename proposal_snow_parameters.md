# NordHydro — Track 1: Snow Hydrology & Water Resources

**Derived from**: `proposal.md` (NordHydro master proposal)  
**Track owner**: Getnet Demil (`feature/snow-parameters`)  
**Branch**: `feature/snow-parameters` → merges to `experiment`  
**Companion track**: Water Quality (`feature/water-quality-pipeline`, collaborator)  
**Venue**: HydroImaging 2026 Workshop — Tampere, Finland, Sept 13–17, 2026  
**Submission deadline**: May 13, 2026

---

## Dataset Card

This card summarizes what a researcher receives when they use this track of NordHydro. Full methodology is in §§6–8.

| Property | Value |
|---|---|
| **Who is this for** | Snow hydrologists, water resources researchers, ML engineers pretraining hydrological Foundation Models |
| **What is the gap filled** | No operational product provides gridded SWE at <5 km for Sweden+Finland 2015–2024. Researchers currently re-derive SWE independently from 4 separate data sources. |
| **Period** | 2015–2024, daily; primary season Oct–Apr (7 months) |
| **Geography** | Sweden + Finland; 55–71°N, 10–32°E |
| **Grid** | ETRS89/LAEA Europe (EPSG:3035), 2.5 km × 2.5 km |
| **Format** | CF-compliant NetCDF4, Xarray-compatible |
| **Station coverage** | ~600 Nordic stations (~425 Swedish SMHI + ~175 Finnish FMI after QC) |
| **ML sequences** | ~810,000 station-season 30-day sliding windows |
| **File location** | `data/processed/snow/snow_nordic_<YYYY>.nc` (1 file/year) |
| **Station metadata** | `data/processed/snow/station_metadata_nordic.parquet` |
| **License** | CC-BY 4.0 (FMI-derived components); CC0 (SMHI, ERA5) |
| **Key derived variables** | SWE, snow density, CDD, TDD, snowmelt rate, runoff potential, runoff coefficient |

---

## 1. Executive Summary

Snow hydrology and water resources in the Nordic region share a common observational bottleneck: **Snow Water Equivalent (SWE) — the volume of liquid water stored in a snowpack — is never directly measured at scale.** SMHI and FMI provide snow depth observations at ~600 stations, but depth alone is insufficient for runoff modeling, flood forecasting, or Foundation Model pretraining. Converting depth to SWE requires snow density, which varies nonlinearly with temperature history, age, and regional snow climate class. No agency provides this derivation; every research group re-invents it in isolation.

This track delivers a **research-ready Nordic SWE field** at 2.5 km spatial resolution and daily temporal resolution, covering the full Sweden + Finland domain for 2015–2024. It fuses station snow depth observations from SMHI and FMI with MESAN gridded temperature history to implement the Sturm et al. (2010) empirical density model — extended with Nordic-specific snow climate class assignments. Alongside SWE, the track delivers accumulated degree-days, snowmelt rates, runoff potential, and streamflow from SMHI HydObs, providing the complete set of variables needed for snowmelt-driven water resources modeling without visiting any external data portal.

### Why not just use ERA5-Land?

| Property | ERA5-Land | This track (NordHydro Snow) |
|---|---|---|
| SWE spatial resolution | 0.1° ≈ 9 km | 2.5 km (3.6× finer) |
| Snow depth anchor | Modeled (no station assimilation) | Station-anchored (SMHI/FMI ground truth) |
| Mountain terrain bias | Systematic underestimate (documented) | Corrected via Sturm density classes per climate zone |
| Nordic domain coverage | Global (consistent) | Sweden + Finland specifically optimized |
| Swedish/Finnish station data | Not assimilated | Core input — ground truth for every grid cell |
| Water resources variables | Precipitation only | Discharge (HydObs) + runoff potential |

ERA5-Land is used in this track as a **validation benchmark** and for **Finnish cloud cover** (where MESAN does not reach), but not as the primary SWE source.

---

## 2. Scientific Background

### 2.1 The Snowpack as the Nordic Water Tower

Over 70% of annual runoff in northern Sweden and Finland originates from snowmelt (Lundberg & Koivusalo, 2003). Snowpacks accumulate throughout October–April and release water over a compressed melt window (March–June), driving hydropower generation, spring flood risk, and stream chemistry across the entire Nordic watershed system.

Despite this centrality, the research community lacks a unified Nordic SWE product at actionable resolution. This gap has three consequences:
1. **Redundant effort**: Each research group independently derives SWE using different methods, making results non-comparable.
2. **Model uncertainty**: Without a ground-truth-anchored SWE field, snowmelt models are calibrated on ERA5 alone, which underestimates deep snowpacks in fjell terrain.
3. **AI inaccessibility**: Foundation Models require large, clean, consistently formatted corpora. No such corpus exists for Nordic snow hydrology.

### 2.2 The Multi-Scale Observation Problem

| Scale | Source | Provides | Missing |
|---|---|---|---|
| Point (station) | SMHI MetObs, FMI WFS | Precise depth and temperature at ~600 stations | Spatial continuity; density |
| Gridded (reanalysis) | MESAN 2.5 km, PTHBV 4 km | Spatially consistent atmospheric fields | No snow depth or density |
| Satellite (EO imaging) | FMI H-SAF, MODIS | Areal snow cover extent | No depth or SWE; cloud gaps |
| Discharge (hydrology) | SMHI HydObs, Syke | Streamflow as integrated catchment signal | Not spatially distributed |

The scientific contribution of this track is **fusion across all four scales**: satellite snow cover constrains spatial extent; MESAN temperature history drives density evolution; station depths provide ground-truth anchoring; and HydObs discharge validates the downstream runoff signal.

### 2.3 Alignment with HydroImaging 2026

The HydroImaging 2026 call targets *imaging + in-situ data mining for hydrological modelling*. This track is a direct instantiation:

- **Imaging inputs**: MESAN 2.5 km meteorological cubes (multi-channel image stacks); FMI H-SAF satellite snow cover grids; MODIS 500 m optical patches.
- **In-situ inputs**: SMHI station snow depth (point obs, ~425 stations); FMI daily snow network (~175 stations after QC); SMHI HydObs discharge gauges.
- **Derived targets**: Gridded SWE at 2.5 km — the result of fusing imaging and in-situ data using physics-informed methods.

---

## 3. Research Objectives

### 3.1 Primary Objectives

1. **Build a unified daily snow depth + temperature archive** (2015–2024, Oct–Apr, ~600 stations) in CF-compliant NetCDF, projected to EPSG:3035 — the first research-ready pan-Nordic snow observation dataset.

2. **Derive gridded SWE at 2.5 km** using Sturm et al. (2010) forced by MESAN temperature history, with station depths as ground-truth anchor via kriging upscale.

3. **Deliver accumulated degree-days (CDD/TDD) and snowmelt rates** from MESAN temperature fields — mechanistic forcing variables ready for ML model input.

4. **Integrate SMHI HydObs discharge and SMHI HYPE streamflow** as water resources variables, linking snowmelt output to observed catchment response.

5. **Validate derived SWE** against ERA5-Land (independent reanalysis) and FMI H-SAF passive microwave products, reporting RMSE, KGE, and bias decomposition per snow climate class.

### 3.2 Secondary Objectives

- Produce a clean station metadata Parquet file (station ID, lat/lon, elevation, country, active period, climate class) usable as geographic embeddings for Foundation Models.
- Assign Nordic snow climate classes (Sturm 1995) to every grid cell as a static variable in the output dataset.
- Document every derivation formula with citation, CF-compliant output attributes, and input specification per `docs/DERIVATION_METHODS.md` standards.

---

## 4. Input Data Inventory

### 4.1 SMHI MetObs — Swedish Station Snow & Meteorology

| Item | Detail |
|---|---|
| **Endpoint** | `https://opendata-download-metobs.smhi.se/api/version/1.0` |
| **Parameters** | Snow depth (param 8, cm), air temperature (param 1, °C), daily precip (param 5/14, mm), T_min, T_max |
| **Stations** | ~500 active; northern Sweden priority for snow |
| **Coverage** | Some since 1881; systematic since ~1945; param 8 (snow) from ~1960s at most stations |
| **Quality codes** | G (approved) used for derivation; Y (suspect) for exploratory QC |
| **Script** | `src/extraction/fetch_smhi.py`, `scripts/download_smhi_snow.py` |

**Priority stations** (high-elevation / high-latitude):

| Station | ID | Lat | Lon | Elev (m) | Since | Why |
|---|---|---|---|---|---|---|
| Abisko Aut | 156820 | 68.35°N | 18.82°E | 392 | 1986 | Subarctic tundra baseline |
| Kiruna | 180960 | 67.85°N | 20.25°E | 519 | 1898 | Longest high-latitude record |
| Östersund-Frösön | 134110 | 63.20°N | 14.49°E | 376 | 1944 | Mountain transition zone |
| Falun-Lugnet | 105370 | 60.62°N | 15.66°E | 161 | 1881 | Representative boreal |

### 4.2 SMHI HydObs & HYPE — Swedish Water Resources

| Item | Detail |
|---|---|
| **HydObs** | Discharge (m³/s) and water level from ~250 Swedish river gauging stations |
| **HYPE model** | SMHI S-HYPE outputs: modelled streamflow, nitrogen transport, phosphorus transport at catchment scale |
| **Period** | HydObs: 1900–present; HYPE: 2000–present |
| **Use in this track** | HydObs discharge is Tier 0 ground truth for validating runoff potential derivation; HYPE provides modelled N/P transport as supplementary water quality input passed to the collaborator track |
| **Script** | `src/extraction/fetch_smhi.py` (HydObs endpoint) |

### 4.3 MESAN AROME — Swedish Gridded Reanalysis

| Item | Detail |
|---|---|
| **Format** | GRIB2 (read via `cfgrib`) |
| **Resolution** | 2.5 × 2.5 km, hourly |
| **Domain** | 52–71°N, 2°W–40°E |
| **Coverage** | 2015-08-01 to present (AROME-based); pre-2015 via HIRLAM |
| **Snow-relevant fields** | `t` (2m air temp, K), `frsn1h` (frozen precip cm/hr), `spp` (frozen fraction 0–1), `prec1h`/`prec3h` (mm), `r` (humidity %), `vis` (visibility m), `tcc` (cloud cover), `msl` (surface pressure hPa) |
| **Method** | Optimal Interpolation on top of AROME NWP background |
| **Script** | `src/extraction/fetch_mesan.py`, `scripts/download_mesan_bulk.py` |

> **Boundary note**: MESAN domain ends at ~25–28°E. Eastern Finnish stations (25–31°E) must use FMI WFS + ERA5 for atmospheric fields.

### 4.4 PTHBV — Long-Term Swedish Climate Grid

| Item | Detail |
|---|---|
| **Resolution** | 4 × 4 km, daily |
| **Coverage** | 1961-01-01 to present |
| **Variables** | Daily precipitation (wind-undercatch corrected, Alexandersson 2003), daily air temperature |
| **Interpolation** | Optimal Interpolation with topographic correction (Johansson 2000; Johansson & Chen 2003) |
| **Use** | Historical degree-day baseline (1961–2014 climatology); independent precipitation cross-check vs MESAN |

### 4.5 FMI WFS — Finnish Station Observations

| Item | Detail |
|---|---|
| **API** | OGC WFS 2.0 at `https://opendata.fmi.fi/wfs`, CC-BY 4.0 |
| **Stations** | 440 in Finland bbox; ~160–200 retained after snow coverage filter (≥30% winter days) |
| **Daily query** | `fmi::observations::weather::daily::multipointcoverage` → snow depth, `rrday`, `tday`, `tmin`, `tmax`, `TG_PT12H_min` |
| **Hourly query** | `fmi::observations::weather::hourly::multipointcoverage` → `TA_PT1H_AVG`, `RH_PT1H_AVG`, `WS_PT1H_AVG`, `PRA_PT1H_ACC`, `WAWA_PT1H_RANK` |
| **Chunking** | 90 days/request (daily), 30 days/request (hourly) |
| **Scripts** | `scripts/download_fmi_snow.py`, `scripts/download_fmi_hourly.py`, `scripts/download_fmi_stations.py` |

**Parsing note**: FMI XML uses `gml:doubleOrNilReasonTupleList` for data values (not `gml:DataBlock.text` which is empty). Missing values = literal string `"NaN"`. Station-major ordering in position array.

### 4.6 FMI H-SAF / MODIS — Satellite Imaging Inputs

| Source | Variables | Resolution | Use |
|---|---|---|---|
| **FMI H-SAF** | Snow cover probability, passive microwave SWE, soil moisture | 0.1° (~10 km) | Spatial extent constraint for SWE; validation |
| **MODIS Terra (MOD10A1)** | Snow cover extent (optical), LST (thermal) | 500 m / 1 km | High-res snow cover imaging; cloud-masked 5-day composites |
| **CGLS Land Cover** | Forest, open, urban, water classes | 100 m → aggregated to 2.5 km | Degree-day factor (DDF) assignment for snowmelt derivation |

Cloud contamination strategy: 5-day maximum snow cover composite (optical); LST provides secondary signal under persistent cloud cover.

### 4.7 ERA5-Land — Validation & Finnish Atmospheric Gap-Fill

| Item | Detail |
|---|---|
| **Resolution** | 0.1° × 0.1° (~9 km), hourly → daily |
| **Variables** | SWE, snow depth, 2m temperature, precipitation, total cloud cover |
| **Coverage** | 1950–present |
| **Use** | (1) Independent SWE validation benchmark; (2) Finnish cloud cover where MESAN domain ends; (3) Historical T for pre-2015 degree-day baseline |
| **Access** | CDS API (`cdsapi`); `~/.cdsapirc` registration required |

---

## 5. Variable Catalog

All output variables comply with **CF Metadata Conventions v1.9**. Each variable carries `standard_name`, `long_name`, `units`, `grid_mapping`, and `source` attributes.

### 5.1 Tier 0 — Directly Observed (Snow & Atmosphere)

| CF Standard Name | Short Name | Source | Units | Grid |
|---|---|---|---|---|
| `surface_snow_thickness` | `snow_depth` | SMHI MetObs, FMI daily | cm | Station → 2.5 km |
| `air_temperature` | `t2m` | MESAN `t` (K→°C), FMI `TA_PT1H_AVG` | °C | 2.5 km (SE) / station (FI) |
| `air_temperature minimum` | `t2m_min` | SMHI MetObs, FMI `tmin` | °C | Station |
| `air_temperature maximum` | `t2m_max` | SMHI MetObs, FMI `tmax` | °C | Station |
| `precipitation_flux` | `precip` | MESAN `prec24h`, FMI `rrday` | mm | 2.5 km (SE) / station (FI) |
| `snowfall_flux` | `frozen_precip` | MESAN `frsn1h` sum, FMI derived | cm (SE) / binary (FI) | 2.5 km / station |
| `relative_humidity` | `rh` | MESAN `r`, FMI `RH_PT1H_AVG` | % | 2.5 km / station |
| `wind_speed` | `ws` | MESAN √(u²+v²), FMI `WS_PT1H_AVG` | m/s | 2.5 km / station |
| `visibility_in_air` | `vis` | MESAN `vis`, FMI WAWA-derived | km | 2.5 km / categorical |
| `cloud_area_fraction` | `tcc` | MESAN, ERA5 (FI fallback) | % | 2.5 km / 25 km |
| `surface_air_pressure` | `msl` | MESAN `msl` | hPa | 2.5 km |

### 5.2 Tier 0 — Directly Observed (Water Resources)

| CF Standard Name | Short Name | Source | Units | Grid |
|---|---|---|---|---|
| `water_volume_transport_in_river_channel` | `discharge` | SMHI HydObs | m³/s | Gauge station |
| `river_water_level` | `water_level` | SMHI HydObs | m | Gauge station |
| `water_temperature` | `water_temp` | Syke / SMHI HydObs | °C | Station |

### 5.3 Tier 1 — Derived & Expanded Parameters

| CF Standard Name | Short Name | Method | Units | Grid | Reference |
|---|---|---|---|---|---|
| `liquid_water_content_of_surface_snow` | `swe` | Sturm et al. (2010) density model | mm | 2.5 km | Sturm 2010 |
| `snow_density` | `rho_snow` | Intermediate in Sturm 2010 | kg/m³ | 2.5 km | Sturm 2010 |
| `CDD` | `cdd` | Cumulative T deficit below 0°C from Oct 1 | °C·day | 2.5 km / station | Standard |
| `TDD` | `tdd` | Cumulative T excess above 0°C from Mar 1 | °C·day | 2.5 km / station | Standard |
| `snowmelt_flux` | `snowmelt` | Degree-day model, land-cover DDF | mm/day | 2.5 km | Hock (2003) |
| `surface_runoff_flux` | `runoff_potential` | Snowmelt + liquid precip (simplified HBV) | mm/day | Station / catchment | Lindström (1997) |
| `runoff_coefficient` | `runoff_coeff` | Q_observed / P_catchment at gauge scale | dimensionless | Gauge catchment | Standard |
| `frozen_precip_indicator` | `frozen_flag` | FI-only: 1 if precip>0 and T_min<0°C | binary | Station | Derived |

### 5.4 Tier 2 — ML-Ready Variables

| Variable | Content | Notes |
|---|---|---|
| `doy_sin` | sin(2π × doy / 365.25) | Cyclical season encoding |
| `doy_cos` | cos(2π × doy / 365.25) | Cyclical season encoding |
| `swe_anomaly_class` | Normal / High / Extreme / Drought | SWE vs. 1961–2014 PTHBV-based climatology |
| `climate_class` | Tundra / Boreal / Maritime / Continental | Sturm 1995, static per grid cell |
| `country` | `'SE'` or `'FI'` | For country-stratified evaluation |
| `elevation` | m above sea level | SMHI metadata (SE); SRTM lookup planned (FI) |

### 5.5 Spatial Metadata

| Variable | Content | Source |
|---|---|---|
| `station_id` | SMHI station ID or FMI FMISID | Station registry |
| `latitude` / `longitude` | WGS84 decimal degrees | Station metadata |
| `x_laea` / `y_laea` | EPSG:3035 projected coordinates (m) | `src/common/geo_utils.py` |

---

## 6. Derivation Methodology

### 6.1 Snow Water Equivalent — Sturm et al. (2010)

**Citation**: Sturm, M., Taras, B., Liston, G. E., Derksen, C., Jonas, T., & Lea, J. (2010). Estimating snow water equivalent using snow depth data and climate classes. *Journal of Hydrometeorology, 11*(6), 1380–1394.

**Model**:
```
ρ(h, DOY) = (ρ_max - ρ_0) × [1 - exp(-k1 × h - k2 × (DOY - DOY_start))] + ρ_0

SWE [mm] = h [m] × ρ(h, DOY) [kg/m³]
```

Where `h` = snow depth (m), `DOY` = day of year, `DOY_start` = first accumulation date.

**Nordic climate class coefficients** (Sturm 1995):

| Region | Class | ρ_max (kg/m³) | ρ_0 (kg/m³) | k1 | k2 |
|---|---|---|---|---|---|
| N. Sweden / Finnish Lapland (>65°N) | Tundra | 217 | 173 | 0.0333 | 0.0583 |
| Central/Boreal Sweden & Finland (60–65°N) | Boreal/Taiga | 217 | 217 | 0.0333 | 0.0 |
| Southern Sweden / S. Finland (<60°N) | Maritime | 500 | 150 | 0.0150 | 0.0 |
| Mountain fjell (Swedish fjell) | Alpine | 500 | 200 | 0.0200 | 0.0 |

> **Current stub** in `src/derivation/hydrological_parameters.py:19` uses flat `rho = 200 kg/m³`. Full implementation replaces this with climate-class lookup + DOY-driven exponential.

**Inputs**:
- Snow depth (m): SMHI/FMI stations kriged to 2.5 km MESAN grid
- MESAN `t`: daily mean (K→°C), 2.5 km
- Climate class raster: Sturm 1995 (NSIDC GeoTIFF), reprojected to EPSG:3035
- DOY: from Xarray time coordinate

### 6.2 Accumulated Degree-Days

```
CDD(t) = Σ max(0, 0°C - T_mean(i))   from Oct 1 to day t   [proxy: snow compaction]
TDD(t) = Σ max(0, T_mean(i) - 0°C)   from Mar 1 to day t   [proxy: melt intensity]
```

Climatological baseline uses PTHBV (1961–2014). Anomaly = current season CDD/TDD minus 1961–2014 median.

### 6.3 Snowmelt Rate — Hock (2003)

```
M [mm/day] = max(0, DDF × (T_mean - 0°C))
```

**DDF values** (Hock 2003, Table 2):

| Land cover | DDF (mm °C⁻¹ day⁻¹) |
|---|---|
| Open snowfield | 4.1 ± 1.5 |
| Forested areas | 2.7 ± 1.0 |
| Glacier / permanent ice | 7.4 ± 2.8 |

Land cover from CGLS 100 m, aggregated to 2.5 km by dominant class.

### 6.4 Runoff Potential & Runoff Coefficient

**Simplified water balance** (M4 deadline):
```
Q_potential [mm/day] = Snowmelt + P_liquid
P_liquid = MESAN prec24h × (1 - spp)
```

**Full HBV-96 water balance** (M6 enhancement):
```
Q_potential = P_liquid + Snowmelt - ET_ref - ΔS_soil
```
ET_ref via Penman-Monteith (MESAN T, RH, wind). ΔS_soil from FMI H-SAF soil moisture.

**Runoff coefficient** (where HydObs discharge available):
```
C_r = Q_observed [m³/s] / (P_catchment [mm/day] × A_catchment [m²])
```

### 6.5 Finnish Frozen Precipitation (Derived)

MESAN `frsn24h` does not cover eastern Finland (>25°E). Binary approximation:
```python
frozen_flag = 1 if (precip_mm > 0 and t2m_min < 0.0) else 0
```

Semantic difference vs. MESAN (binary vs. continuous cm) is documented in output `source` attribute; `country` column flags this for post-hoc bias correction.

---

## 7. Technical Pipeline

### 7.1 Extraction → `data/raw/`

| Data | Script | Output |
|---|---|---|
| SMHI snow depth | `scripts/download_smhi_snow.py` | `data/raw/smhi_snow_depth.csv` |
| SMHI temperature | `scripts/download_smhi_temp.py` | `data/raw/smhi_temperature.csv` |
| SMHI HydObs discharge | `src/extraction/fetch_smhi.py` (HydObs endpoint) | `data/raw/smhi_discharge.csv` |
| MESAN GRIB2 (daily chunks) | `scripts/download_mesan_bulk.py` | `data/raw/mesan/<YYYY-MM-DD>.grib2` |
| FMI station metadata | `scripts/download_fmi_stations.py` | `data/raw/fmi_station_metadata.csv` |
| FMI daily snow + met | `scripts/download_fmi_snow.py` | `data/raw/fmi_snow_daily.csv` |
| FMI hourly atmospheric | `scripts/download_fmi_hourly.py` | `data/raw/fmi_hourly_daily.csv` |
| ERA5-Land (FI cloud + validation) | `scripts/download_era5_finland.py` | `data/raw/era5_finland_cloud.csv` |
| MODIS snow patches | `scripts/download_modis_patches.py` | `data/raw/modis/` |

### 7.2 Processing → `data/interim/`

**QC bounds** (`src/processing/quality_control.py`):

| Parameter | Hard bounds | Soft threshold |
|---|---|---|
| `snow_depth` | 0–500 cm | z-score > 4 flagged |
| `t2m` | −60 to +40°C | z-score > 5 flagged |
| `precip` | 0–300 mm/day | z-score > 5 flagged |
| `discharge` | ≥ 0 m³/s | — |
| `swe` (derived) | 0–2000 mm | z-score > 4 flagged |
| `rho_snow` (derived) | 50–550 kg/m³ | — |

**Spatial alignment** (`src/processing/alignment.py`):
- Project station lat/lon → EPSG:3035 via `src/common/geo_utils.py`
- Upscale station snow depth to 2.5 km: bilinear (dense southern networks), ordinary kriging (sparse northern networks)
- Reproject MODIS to EPSG:3035 using `rioxarray.reproject`

**Temporal harmonization**:
- Resample to daily at 06:00 UTC
- Season filter: Oct 1 – Apr 30
- Linear gap interpolation: ≤5 consecutive days

### 7.3 Derivation → `data/processed/snow/`

Execution order in `src/derivation/hydrological_parameters.py`:

1. `calculate_swe_sturm(snow_depth_ds, temp_history_ds, climate_class_map)` → `swe_nordic_<YYYY>.nc`
2. `calculate_cumulative_degree_days(temp_ds, season_start)` → `cdd_<YYYY>.nc`, `tdd_<YYYY>.nc`
3. `calculate_snowmelt(temp_ds, land_cover_ds)` → `snowmelt_<YYYY>.nc`
4. `calculate_runoff_potential(precip_ds, frozen_frac_ds, snowmelt_ds)` → `runoff_potential_<YYYY>.nc`
5. `calculate_runoff_coefficient(discharge_ds, precip_ds, catchment_area)` → `runoff_coeff_<YYYY>.nc`

### 7.4 Output Format

```
data/processed/snow/
  snow_nordic_2015.nc
  ...
  snow_nordic_2024.nc
  station_metadata_nordic.parquet
```

Mandatory global NetCDF attributes:
```
Conventions      = "CF-1.9"
title            = "NordHydro Snow & Water Resources Track, 2015–2024"
institution      = "Hydro-Dataset Project (HydroImaging 2026)"
source           = "SMHI MetObs, SMHI HydObs, MESAN, FMI WFS, ERA5-Land, MODIS"
references       = "Sturm et al. (2010); Hock (2003); Lindström et al. (1997)"
geospatial_lat_min = 55.0
geospatial_lat_max = 71.5
grid_mapping_name  = "lambert_azimuthal_equal_area"
```

---

## 8. Quality Control & Validation

### 8.1 Internal Consistency Checks

- **Melt-out check**: snow depth must be 0 if T_mean > +4°C for 5 consecutive days
- **SWE physical bound**: 0 ≤ SWE ≤ snow_depth × 550 kg/m³
- **Monotonicity**: SWE non-decreasing when T_mean < 0°C and frozen_precip > 0
- **Cross-country border**: adjacent grid cells at the Swedish-Finnish border (~25°E) must have consistent snow depth gradients

### 8.2 External Validation Targets

| Comparison | Metric | Target |
|---|---|---|
| Derived SWE vs. ERA5-Land SWE | RMSE, KGE | RMSE < 50 mm; KGE > 0.6 |
| Derived SWE vs. FMI H-SAF passive microwave | Correlation per climate class | r > 0.7 (tundra/boreal) |
| Held-out SMHI snow depth (10%) | MAE | < 5 cm |
| Held-out FMI snow depth (15%) | MAE | < 8 cm |
| Runoff potential vs. SMHI HydObs discharge | KGE per catchment | KGE > 0.5 |

KGE = Kling-Gupta Efficiency (Gupta et al., 2009). Scores reported per climate class and latitude band (below/above 63°N).

---

## 9. Geographic Scope

### 9.1 Domain (EPSG:3035)

```
x_min: 2,600,000 m  (~9°E)     x_max: 5,000,000 m  (~32°E)
y_min: 6,000,000 m  (~53°N)    y_max: 8,300,000 m  (~71°N)
```

### 9.2 Station Network

| Country | Snow stations (post-QC) | Discharge gauges | Sequences (est.) |
|---|---|---|---|
| Sweden | ~425 | ~250 (HydObs) | ~630,000 |
| Finland | ~160–200 | — (Syke: water quality track) | ~180,000 |
| **Total** | **~580–625** | **~250** | **~810,000** |

### 9.3 Regional Priority Order

1. Northern Fennoscandia (>65°N) — deepest snowpacks, tundra class, longest records
2. Boreal core (62–65°N) — highest station density, SE/FI continental comparison
3. Mountain fjell (~63°N, Swedish Jämtland) — elevation gradients, Sturm model most sensitive
4. Southern transition (<62°N) — episodic snowpacks, lowest baseline, highest anomaly challenge

---

## 10. Foundation Model Readiness

**Sequence construction**: 30-day sliding windows, 12 features/day, daily frequency.

**Multi-modal pairing**: each sequence links to:
- MESAN 2D image stack (T, precip, frozen_frac channels at 2.5 km) → CNN/ViT fusion
- MODIS optical patch (500 m) at co-located tile → satellite-context pretraining

**Anomaly class distribution** (SWE vs. PTHBV 1961–2014 climatology):

| Class | Criteria | Estimated frequency |
|---|---|---|
| Normal | Within ±1σ | ~75% |
| High | > 90th percentile | ~18% |
| Extreme | > 99th percentile | ~3–5% |
| Drought | < 10th percentile | ~2–4% |

Oversampling: geographic (southern stations 4–8×) + class-level (Extreme and Drought).

---

## 11. Timeline

Today: **April 29, 2026**.

### Phase 1: Data Infrastructure (Critical Path — April 30 deadline)

| Task | Status | Deadline | Notes |
|---|---|---|---|
| SMHI snow + temperature extraction | In progress | Apr 29 | `fetch_smhi.py` working for 5 stations; extend to full network |
| MESAN GRIB download + cfgrib parsing | In progress | Apr 29 | Verify `download_mesan_bulk.py` end-to-end |
| FMI daily snow download (27 WFS chunks) | In progress | **Apr 30** | ~5 min total download time |
| FMI hourly atmospheric download | To do | **Apr 30** | ~45–60 min; daily query sufficient for M2 if hourly lags |
| **Pilot NetCDF** (Dalarna tile, 2023–24, Tier 0) | **Critical path** | **Apr 30** | Proves pipeline end-to-end; minimum viable M2 output |

### Phase 2: Derivation & Water Resources (May 1–7)

| Task | Deadline | Blocker |
|---|---|---|
| Full Sturm SWE formula (replace stub) | May 2 | Climate class raster download (NSIDC) |
| Kriging upscale of station depths to 2.5 km grid | May 2 | `alignment.py:harmonize_point_to_grid` stub |
| SWE validation vs ERA5-Land (pilot region) | May 3 | CDS API registration + ERA5 download |
| CDD / TDD derivation | May 3 | MESAN availability |
| Degree-day snowmelt + CGLS land cover | May 4 | CGLS download |
| SMHI HydObs discharge extraction + runoff coefficient | May 4 | HydObs endpoint integration |
| Runoff potential (simplified) | May 5 | Depends on snowmelt |
| **Dataset v1.0 — full 2015–2024, all Nordic domain** | **May 7** | All above complete |

### Phase 3: Validation & Paper (May 8–13)

| Task | Deadline | Paper output |
|---|---|---|
| RMSE/KGE benchmarking vs ERA5-Land + H-SAF | May 9 | §Results validation table |
| Spatial SWE maps (2023–24, 3 dates) | May 11 | Figure 2 |
| Station time series (Kiruna, Falun, Oulu) | May 11 | Figure 3 |
| Runoff correlation plot (HydObs vs derived) | May 11 | Figure 4 |
| Overleaf sections finalized | **May 13** | `Overleaf_manuscript/sections/` |

### Post-Submission (June–September 2026)

| Target | Description | Date |
|---|---|---|
| Full validation report | All sub-domains, all climate classes | June 2026 |
| Dataset public release | Zenodo DOI + GitHub release | July 2026 |
| Workshop presentation | HydroImaging 2026, Tampere | Sept 13–17, 2026 |

---

## 12. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| MESAN downloads slow (~GB/day, 10 years) | High | Pilot tile (Dalarna, 2023–24) sufficient for M2; full download continues post-submission |
| Sturm 1995 climate class raster not yet downloaded | Medium | NSIDC GeoTIFF; register and download this week. Fallback: latitude-band class assignment |
| FMI hourly download (~45–60 min) incomplete by Apr 30 | Medium | Daily query (5 min) covers snow depth for M2; hourly deferred to M3 |
| Kriging artifacts in sparse northern networks | Medium | Nearest-neighbor fallback for regions with <3 stations within 100 km; validate against MESAN T gradient |
| SMHI HydObs endpoint not yet integrated | Low | HydObs uses same `fetch_smhi.py` pattern; add HydObs parameter endpoint |
| ERA5-Land SWE underestimates mountain terrain | Low | Known, documented bias; cited as validation limitation; H-SAF provides independent check |
| FMI station elevation defaults to 0 | Low | SRTM lookup via `rasterio` planned for M3; flag `elevation_source=default` in metadata |

---

## 13. Integration with Water Quality Track

The snow + water resources track produces shared artifacts consumed by the collaborator's water quality track:

| Artifact | Produced by (snow track) | Consumed by (water quality track) |
|---|---|---|
| Station metadata Parquet | `data/processed/snow/station_metadata_nordic.parquet` | Spatial join with Syke discharge stations |
| Runoff potential field | `data/processed/snow/runoff_potential_<YYYY>.nc` | Snowmelt runoff = primary N/P transport vector into Finnish lakes |
| MESAN daily temperature | `data/interim/mesan_t2m_<YYYY>.nc` | Water temperature modeling in Syke catchments |
| SMHI HYPE N/P transport | `data/raw/smhi_hype_np.csv` | Supplementary nutrient load signal |

Integration: both tracks target `data/processed/` by May 7 (M4 dataset v1.0). Unified 4D cube (snow SWE + water quality index) assembled in `experiment` branch — estimated late May 2026.

---

## 14. References

- Sturm, M., et al. (2010). Estimating snow water equivalent using snow depth data and climate classes. *Journal of Hydrometeorology, 11*(6), 1380–1394.
- Hock, R. (2003). Temperature index melt modelling in mountain areas. *Journal of Hydrology, 282*(1–4), 104–115.
- Lindström, G., et al. (1997). Development and test of the distributed HBV-96 hydrological model. *Journal of Hydrology, 201*(1–4), 272–288.
- Johansson, B. (2000). Areal precipitation and temperature in the Swedish mountains. *SMHI Reports Hydrology, 57*.
- Johansson, B., & Chen, D. (2003). The influence of wind and topography on precipitation distribution in Sweden. *International Journal of Climatology, 23*(12), 1523–1535.
- Alexandersson, H. (2003). Wind corrected manual precipitation observations. *SMHI Technical Report, RMK No. 97*.
- Gupta, H. V., et al. (2009). Decomposition of the mean squared error and NSE performance criteria. *Journal of Hydrology, 377*(1–2), 80–91.
- Lundberg, A., & Koivusalo, H. (2003). Estimating winter evaporation in boreal forests with operational snow course data. *Hydrological Processes, 17*(8), 1479–1493.

---

*Branch*: `feature/snow-parameters`  
*Parent proposal*: `proposal.md`  
*Last updated*: April 29, 2026  
*Status*: ACTIVE — Pilot NetCDF deadline April 30, 2026
