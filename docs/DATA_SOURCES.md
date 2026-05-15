# Data Sources — Nordic Hydrology Dataset

## SMHI (Swedish Meteorological and Hydrological Institute)

**Portal**: [SMHI Open Data Explorer](https://www.smhi.se/data)

### MetObs (Meteorological Observations)
- **API**: REST/JSON — `https://opendata-download-metobs.smhi.se/api/version/1.0`
- **Extractor**: `src/extraction/fetch_smhi.py`
- **Raw output**: `data/raw/smhi/smhi_{snow_depth,temp_mean,precip}.csv`
- **Status**: Active — full Nordic archive downloaded (55–70°N, 10–30°E)

| Parameter | SMHI ID | Variable name | Units |
|---|---|---|---|
| Snow depth | 8 | `snow_depth` | m |
| Daily mean temperature | 2 | `temp_mean` | °C |
| Daily precipitation | 5 | `precip` | mm |

### HydObs (Hydrological Observations)
- **API**: REST/JSON — `https://opendata-download-hydobs.smhi.se/api/version/1.0`
- **Extractor**: `src/extraction/fetch_smhi_hydobs.py`
- **Raw output**: `data/raw/smhi/smhi_discharge.csv`
- **Status**: Extractor implemented; run `make extract-hydobs` to download

| Parameter | SMHI ID | Variable name | Units |
|---|---|---|---|
| Discharge (Vattenföring) | 1 | `discharge` | m³/s |

### MESAN (Gridded Reanalysis)
- **Format**: GRIB2 — `https://opendata.smhi.se/apidocs/mesan/`
- **Extractor**: `src/extraction/fetch_mesan.py`
- **Resolution**: 2.5 km grid over Sweden
- **Role**: Target grid for Kriging upscale; LAEA EPSG:3035 compatible

---

## FMI (Finnish Meteorological Institute)

**Portal**: [FMI Open Data](https://en.ilmatieteenlaitos.fi/open-data)

- **API**: WFS (XML) — `https://opendata.fmi.fi/wfs`
- **Extractors**: `src/extraction/fetch_fmi.py`, `scripts/download_fmi_*.py`
- **Status**: Station download scripts implemented; satellite products planned for M7

| Data type | Variables | Notes |
|---|---|---|
| Station observations | Temperature, precip, snow depth | WFS parameter queries |
| H-SAF snow cover | Snow cover fraction | Satellite, daily |
| Soil moisture | Surface soil moisture | H-SAF ASCAT product |

---

## Syke (Finnish Environment Institute)

- **API**: OData — `https://www.syke.fi/en-US/Open_information`
- **Extractor**: `src/extraction/fetch_syke.py`
- **Status**: Extractor implemented; discharge used for runoff calibration. Nutrient and turbidity variables are scoped to a companion water quality paper.

| Variable | Units | Role |
|---|---|---|
| Discharge (Q) | m³/s | Runoff coefficient calibration |
| Total nitrogen (TN) | µg/L | Companion paper |
| Total phosphorus (TP) | µg/L | Companion paper |
| Turbidity | FTU | Companion paper |

---

## ERA5-Land (ECMWF/Copernicus)

- **API**: CDS API v2 — `https://cds.climate.copernicus.eu/api`
- **Script**: `scripts/validate_swe_era5.py`, `scripts/download_era5_*.py`
- **Raw output**: `data/raw/era5/dalarna_sd_2023_2024.nc`
- **Status**: Downloaded for Dalarna pilot; used for SWE cross-validation only

| Variable | ERA5 name | Units | Notes |
|---|---|---|---|
| Snow depth water equiv. | `sde` | m w.e. | = SWE; multiply by 1000 for mm |

**Key finding**: ERA5-Land overestimates SWE in Scandinavia by ~262 mm on average
(Dalarna 2023–24 pilot). Our station-anchored SWE is more credible as ground truth
for Foundation Model training (Pearson R = 0.78 with ERA5 confirms temporal agreement).

---

## Processed Datasets

| File | Description | Dimensions | Size |
|---|---|---|---|
| `data/processed/pilot/dalarna_tier0_2023_2024.nc` | Dalarna pilot, 1 season (raw obs) | 22 stations × 213 days | ~150 kB |
| `data/processed/pilot/dalarna_swe_gridded_2023_2024.nc` | Kriged SWE/depth grid | 58 × 68 × 213 (LAEA) | ~13 MB |
| `data/processed/nordic/nordic_tier0_2015_2024.nc` | Full Nordic, 9 seasons (raw obs only) | 582 stations × 3135 days | 58 MB |
| `data/processed/nordic/nordic_tier1_2015_2024.nc` | **Zenodo primary**: Tier 0 + 6 derived parameters | 582 stations × 3135 days × 10 vars | 133 MB |

Tier 1 derived variables: `swe` [mm], `snow_density` [g cm⁻³], `snowmelt_rate` [mm day⁻¹],
`swe_accumulation_rate` [mm day⁻¹], `rain_on_snow` [int8 flag], `cold_content` [MJ m⁻²].
Script: `scripts/enrich_nordic_netcdf.py` (`make enrich-netcdf`).

All processed files follow CF-1.9 conventions. Raw data files (CSV, GRIB, NC) are
excluded from git via `.gitignore`.
