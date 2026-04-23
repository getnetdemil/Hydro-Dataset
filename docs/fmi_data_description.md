# FMI Data Integration: Complete Technical Description

**Finnish Meteorological Institute (FMI) Open Data for Nordic Snow Monitoring**

---

## Table of Contents

1. [Overview and Motivation](#1-overview-and-motivation)
2. [FMI Open Data Infrastructure](#2-fmi-open-data-infrastructure)
3. [Data Sources Used](#3-data-sources-used)
4. [Station Network](#4-station-network)
5. [API: Stored Queries and Parameters](#5-api-stored-queries-and-parameters)
6. [Wire Format: gmlcov:MultiPointCoverage](#6-wire-format-gmlcovmultipointcoverage)
7. [Feature Mapping: FMI → Model Inputs](#7-feature-mapping-fmi--model-inputs)
8. [Integration Architecture](#8-integration-architecture)
9. [Comparison with Swedish SMHI/MESAN Pipeline](#9-comparison-with-swedish-smsimesan-pipeline)
10. [How Finnish Data Helps the Model](#10-how-finnish-data-helps-the-model)
11. [Data Preparation Principles](#11-data-preparation-principles)
12. [Derived Features](#12-derived-features)
13. [Known Challenges and Mitigations](#13-known-challenges-and-mitigations)
14. [Data Quality and Coverage](#14-data-quality-and-coverage)
15. [Limitations and Caveats](#15-limitations-and-caveats)
16. [Download Pipeline Reference](#16-download-pipeline-reference)

---

## 1. Overview and Motivation

### Why Finnish data?

The model title claims *Nordic region* snow monitoring, but the original training data
covers **Sweden only** (SMHI stations, 55–70°N, 10–25°E). Finland is the second-largest
Nordic country by area, occupies 60–70°N (overlapping the Swedish latitude range), and
has a distinct **continental snow climate** that differs from Sweden's more oceanic west
coast regime. Adding Finnish stations:

1. **Substantiates the "Nordic" claim** — from 602 Swedish to ~760 combined stations.
2. **Extends geographic diversity** — Finnish stations cover longitudes 20–31°E, a
   region not represented in current training.
3. **Introduces a second snow climatology** — Finnish winters are colder and more
   continental east of the Scandinavian mountains; snowpacks form earlier, last
   longer, and reach greater depths than in comparable Swedish latitudes.
4. **Enlarges training data** — ~820K sequences vs. current 635K (+29%), directly
   improving generalisation.
5. **Adds new anomaly examples** — Finnish extreme snowfall events (e.g., eastern
   Finland lake-effect snows, Arctic intrusions) enrich the tail of the severity
   distribution.
6. **Enables country-stratified evaluation** — the geographic fairness analysis can
   be extended from north/south Sweden to Sweden vs. Finland vs. northern Finland,
   providing a richer picture of spatial equity.

### Why FMI specifically?

FMI (Finnish Meteorological Institute / Ilmatieteen laitos) is the national
meteorological authority for Finland. Its open data portal provides free, no-login
access to historical station observations going back at least to 2010, via a
standardised OGC Web Feature Service (WFS) API. This is the direct Finnish analogue
of SMHI's Open Data API used for Swedish stations.

---

## 2. FMI Open Data Infrastructure

| Component | Details |
|-----------|---------|
| **Organisation** | Finnish Meteorological Institute (FMI), Helsinki |
| **Portal** | https://en.ilmatieteenlaitos.fi/open-data |
| **API type** | OGC Web Feature Service (WFS) 2.0.0 |
| **WFS endpoint** | `https://opendata.fmi.fi/wfs` |
| **License** | Creative Commons Attribution 4.0 (CC-BY 4.0) |
| **Authentication** | None required; fully open |
| **Historical depth** | Observations available from ~2010; some stations from earlier |
| **Python library** | `fmiopendata` (pip install fmiopendata) |

### Service characteristics

- Maximum time window per WFS request: ~100 days (practical; not formally documented).
  Requests for longer windows time out or return empty bodies. The download scripts
  use 90-day chunks for daily and 30-day chunks for hourly data.
- The WFS endpoint returns XML in the GML/INSPIRE namespace family.
- No rate limiting is documented, but requests are throttled at 1-second intervals
  in our scripts to be a polite API consumer.
- All timestamps are UTC; Finnish local time is UTC+2 (UTC+3 in summer DST).

---

## 3. Data Sources Used

Finnish data requires **three separate API queries** because no single FMI endpoint
provides all 12 model input features:

| Source | FMI Query | Features Provided | Coverage |
|--------|-----------|------------------|----------|
| **FMI daily** | `fmi::observations::weather::daily::multipointcoverage` | snow depth, precip, mean/min/max temp | ~269 stations per query |
| **FMI hourly** | `fmi::observations::weather::hourly::multipointcoverage` | temperature, humidity, wind speed, precip, weather phenomena | ~201 stations per query |
| **ERA5 reanalysis** | Copernicus CDS API (`reanalysis-era5-single-levels`) | total cloud cover | Global, 0.25° |

> **Note on station counts:** The number of stations returned varies by query and
> time period because not all stations measure every parameter and some stations
> are inactive for certain periods. The daily query returns ~269 stations over
> Finland for January 2024; the hourly query returns ~201 (hourly obs require
> automated stations with tipping-bucket rain gauges and anemometers). Across
> 2015–2024, the effective station pool is approximately 160–200 after the
> coverage filter.

---

## 4. Station Network

### Coverage from `fmi::ef::stations` (WFS station registry)

| Metric | Value |
|--------|-------|
| Total stations in Finland bbox (18–32°E, 59–71°N) | **440** |
| Latitude range | 59.25°N – 70.08°N |
| Longitude range | 19.13°E – 31.04°E |
| Elevation range | 0 m (coastal) to ~650 m (Lapland fells); not in WFS metadata |

**Distribution by latitude band:**

| Band | Stations | Climate Zone |
|------|----------|-------------|
| 59–62°N | 221 (50%) | Southern Finland: oceanic-continental transition, lowest snow baseline |
| 62–64°N | 108 (25%) | Central Finland: continental, reliable winter snow |
| 64–66°N |  56 (13%) | Northern Ostrobothnia: boreal, deep snowpacks |
| 66–68°N |  34  (8%) | Lapland south: subarctic, snow Oct–May |
| 68–70°N |  20  (5%) | Lapland north: deep subarctic, permafrost edge |
| 70°N+   |   1  (<1%) | Utsjoki: northernmost point of Finland |

> **Comparison with Sweden:** The Swedish SMHI network used in training has
> 602 stations concentrated between 55–70°N. Finnish stations extend coverage
> further east (up to 31°E) and add more stations in the 60–65°N range.

### Station types

FMI operates several station types, all returning data through the same WFS API:
- **Automatic Weather Stations (AWS)**: hourly and daily obs; 1-minute sampling aggregated
- **Synoptic stations**: manual + automatic; aligned with WMO observation times
- **Road weather stations** (via Fintraffic): temperature, precipitation; no snow depth
- **Research stations**: specialized; some have long historical records

For our purposes, only stations reporting `snow` (depth in cm) in the daily query
are useful for training. After filtering, the effective training set is approximately
160–200 stations.

---

## 5. API: Stored Queries and Parameters

### 5.1 Daily observations (ground truth + basic met)

```
GET https://opendata.fmi.fi/wfs
  ?service=WFS
  &version=2.0.0
  &request=GetFeature
  &storedquery_id=fmi::observations::weather::daily::multipointcoverage
  &bbox=18,59,32,71
  &starttime=2024-01-01T00:00:00Z
  &endtime=2024-01-03T00:00:00Z
  &parameters=snow,rrday,tday,tmin,tmax,TG_PT12H_min
```

**Parameters returned:**

| FMI Name | Description | Unit | Notes |
|----------|-------------|------|-------|
| `snow` | Daily snow depth (ground truth) | cm | Primary target variable |
| `rrday` | Daily precipitation total | mm | -1.0 = trace (<0.5 mm), converted to 0.0 |
| `tday` | Daily mean air temperature | °C | Mean of 24-hour observations |
| `tmin` | Daily minimum air temperature | °C | Used to derive `frozen_precip` |
| `tmax` | Daily maximum air temperature | °C | Cross-check for plausibility |
| `TG_PT12H_min` | 12-h minimum ground temperature | °C | Proxy for soil freeze state |

**Missing value encoding:** `NaN` (literal string "NaN" in the XML data block).
The value -1.0 specifically for `rrday` means trace precipitation (< 0.5 mm detection
threshold), not a missing value — this is treated as 0.0 in our pipeline.

### 5.2 Hourly observations (atmospheric features)

```
GET https://opendata.fmi.fi/wfs
  ?service=WFS
  &version=2.0.0
  &request=GetFeature
  &storedquery_id=fmi::observations::weather::hourly::multipointcoverage
  &bbox=18,59,32,71
  &starttime=2024-01-01T00:00:00Z
  &endtime=2024-01-01T23:59:59Z
  &parameters=TA_PT1H_AVG,RH_PT1H_AVG,WS_PT1H_AVG,PRA_PT1H_ACC,WAWA_PT1H_RANK
```

**Parameters returned:**

| FMI Name | Description | Unit | Daily Aggregation |
|----------|-------------|------|-------------------|
| `TA_PT1H_AVG` | Hourly mean air temperature | °C | Daily mean (≥6 valid hours) |
| `RH_PT1H_AVG` | Hourly mean relative humidity | % | Daily mean (≥6 valid hours) |
| `WS_PT1H_AVG` | Hourly mean wind speed | m/s | Daily mean (≥6 valid hours) |
| `PRA_PT1H_ACC` | Hourly precipitation accumulation | mm | Daily sum |
| `WAWA_PT1H_RANK` | Hourly weather phenomenon rank | WMO code | → visibility (km) |

**Minimum observation requirement:** A daily aggregate is considered valid only if
at least 6 of the 24 hourly values are non-NaN. Days with fewer observations are
set to NaN. This threshold prevents unreliable daily means from sparse data.

### 5.3 ERA5 cloud cover (supplement)

```python
cdsapi.Client().retrieve(
    "reanalysis-era5-single-levels",
    {
        "product_type": "reanalysis",
        "variable":     ["total_cloud_cover"],
        "year":         year,
        "month":        month,
        "day":          days,
        "time":         "12:00",          # representative midday value
        "area":         [71, 18, 59, 32], # [N, W, S, E]
        "format":       "netcdf",
    },
    output_file
)
```

| ERA5 Variable | Unit | Resolution | Notes |
|---------------|------|-----------|-------|
| `total_cloud_cover` (tcc) | fraction (0–1) → converted to % | 0.25° × 0.25° (~25 km) | Single value at 12:00 UTC per day |

ERA5 is used only for `cloud_cover` because FMI station observations do not include
a cloud amount measurement in the standard WFS queries. The 0.25° resolution is
coarser than the MESAN 2.5 km grid used for Swedish cloud data, which introduces a
minor representativeness mismatch (discussed in Section 13).

---

## 6. Wire Format: gmlcov:MultiPointCoverage

Understanding the FMI XML response structure is essential for correct data parsing.
The FMI WFS returns observations as an OGC `gmlcov:MultiPointCoverage` — a coverage
encoding where space-time positions and data values are stored as parallel flat arrays.

### 6.1 Response structure (simplified)

```xml
<wfs:FeatureCollection>
  <wfs:member>
    <omso:GridSeriesObservation>

      <!-- Station registry: fmisid → name, lat/lon -->
      <om:featureOfInterest>
        <sams:SF_SpatialSamplingFeature>
          <sam:sampledFeature>
            <target:LocationCollection>
              <target:Location gml:id="obsloc-fmisid-101786-pos">
                <gml:identifier>101786</gml:identifier>
                <gml:name>Oulu lentoasema</gml:name>
                <target:representativePoint xlink:href="#point-101786"/>
              </target:Location>
              ...
            </target:LocationCollection>
          </sam:sampledFeature>

          <!-- Point positions with gml:id = "point-{fmisid}" -->
          <sams:shape>
            <gml:MultiPoint>
              <gml:pointMember>
                <gml:Point gml:id="point-101786">
                  <gml:name>Oulu lentoasema</gml:name>
                  <gml:pos>64.93503 25.33920</gml:pos>
                </gml:Point>
              </gml:pointMember>
              ...
            </gml:MultiPoint>
          </sams:shape>
        </sams:SF_SpatialSamplingFeature>
      </om:featureOfInterest>

      <!-- Coverage: domain (positions) + range (values) -->
      <om:result>
        <gmlcov:MultiPointCoverage>

          <!-- DOMAIN: each row is (lat lon unix_timestamp) -->
          <gml:domainSet>
            <gmlcov:SimpleMultiPoint
                srsName="...compoundCRS.php?crs=4258&time=unixtime"
                srsDimension="3">
              <gmlcov:positions>
                64.93503 25.33920 1704067200   <!-- station A, day 1 -->
                64.93503 25.33920 1704153600   <!-- station A, day 2 -->
                64.93503 25.33920 1704240000   <!-- station A, day 3 -->
                64.14263 25.42335 1704067200   <!-- station B, day 1 -->
                ...
              </gmlcov:positions>
            </gmlcov:SimpleMultiPoint>
          </gml:domainSet>

          <!-- RANGE: one tuple per position row, values per swe:field -->
          <gml:rangeSet>
            <gml:DataBlock>
              <gml:doubleOrNilReasonTupleList>
                NaN  NaN  -25.4    <!-- station A, day 1: snow=NaN, rrday=NaN, tday=-25.4 -->
                48.0 -1.0 -32.7    <!-- station A, day 2: snow=48, rrday=trace, tday=-32.7 -->
                ...
              </gml:doubleOrNilReasonTupleList>
            </gml:DataBlock>
          </gml:rangeSet>

          <!-- FIELD NAMES: order matches tuple columns -->
          <gmlcov:rangeType>
            <swe:DataRecord>
              <swe:field name="snow" .../>
              <swe:field name="rrday" .../>
              <swe:field name="tday" .../>
            </swe:DataRecord>
          </gmlcov:rangeType>

        </gmlcov:MultiPointCoverage>
      </om:result>
    </omso:GridSeriesObservation>
  </wfs:member>
</wfs:FeatureCollection>
```

### 6.2 Parsing algorithm

The parser in `download_fmi_snow.py` and `download_fmi_hourly.py` implements:

**Step 1 — Build station ID lookup:**
```
For each gml:Point where gml:id starts with "point-":
    station_id = id[6:]             # "point-101786" → "101786"
    (lat, lon) = parse gml:pos
    coord_to_id[(round(lat,5), round(lon,5))] = (station_id, name)
```

**Step 2 — Parse positions:**
```
tokens = gmlcov:positions.text.split()
positions = [(lat, lon, datetime.utcfromtimestamp(unix_ts))
             for i in range(0, len(tokens), 3)]
```

**Step 3 — Parse data values:**
```
tokens = gml:doubleOrNilReasonTupleList.text.split()
values = [nan if tok == "NaN" else float(tok) for tok in tokens]
arr = reshape(values, (n_positions, n_fields))
```

**Step 4 — Build tidy DataFrame:**
```
For each (lat, lon, timestamp) in positions:
    station_id = coord_to_id[(lat, lon)]
    row = {date, station_id, field_0=arr[i,0], field_1=arr[i,1], ...}
```

**Key parsing constraints:**
- Position rows are ordered: all time-steps for station 1, then station 2, etc.
  (i.e., station-major ordering, not time-major).
- The `gml:DataBlock` element's `.text` is empty; the data is in its child
  `gml:doubleOrNilReasonTupleList`. Searching for `DataBlock` and taking its `.text`
  was a bug that returned empty strings — the parser must specifically find
  `gml:doubleOrNilReasonTupleList`.
- Floating-point rounding in station coordinates: positions use 5 decimal place
  precision; the lookup uses `round(float, 5)` to avoid key mismatches.
- The `NaN` string (not IEEE NaN float) is used for missing values in the XML text.
  Python's `float("NaN")` correctly handles this.

---

## 7. Feature Mapping: FMI → Model Inputs

The model requires 12 features per day per station. The table below shows the source
and transformation for each feature when applied to Finnish stations.

| # | Feature Name | Swedish Source (MESAN) | Finnish Source (FMI) | Transformation |
|---|-------------|----------------------|---------------------|----------------|
| 1 | `snow_depth_cm` | SMHI station obs (param 8) | FMI daily `snow` | Direct (cm) |
| 2 | `temperature` | MESAN `t` (K→°C) | FMI hourly `TA_PT1H_AVG` | Daily mean of 24h obs |
| 3 | `precipitation` | MESAN `prec24h` (mm) | FMI hourly `PRA_PT1H_ACC` | Daily sum; fallback: FMI daily `rrday` |
| 4 | `wind_speed` | MESAN `u`,`v` → √(u²+v²) | FMI hourly `WS_PT1H_AVG` | Daily mean |
| 5 | `humidity` | MESAN `r` (fraction→%) | FMI hourly `RH_PT1H_AVG` | Daily mean |
| 6 | `frozen_precip` | MESAN `frsn24h` (cm) | **Derived** | see Section 12.1 |
| 7 | `visibility` | MESAN `vis` (m→km) | **Derived from WAWA** | see Section 12.2 |
| 8 | `cloud_cover` | MESAN `tcc` (fraction→%) | **ERA5** `tcc` | Nearest grid cell × 100 |
| 9 | `day_sin` | Computed | Computed | sin(2π×doy/365.25) |
| 10 | `day_cos` | Computed | Computed | cos(2π×doy/365.25) |
| 11 | `latitude` | Station metadata | FMI WFS station metadata | Degrees N |
| 12 | `elevation` | Station metadata | **Defaults to 0 m** | see Section 13.4 |

### Feature resolution comparison

| Feature | Sweden (MESAN) | Finland (FMI) | Resolution difference |
|---------|---------------|---------------|----------------------|
| Temperature | 2.5 km grid analysis | Station observation | Grid analysis vs point obs |
| Precipitation | 2.5 km grid analysis | Station tipping bucket | Grid analysis vs gauge |
| Wind speed | 2.5 km grid analysis | Station anemometer | Grid analysis vs point obs |
| Humidity | 2.5 km grid analysis | Station psychrometer | Grid analysis vs point obs |
| Cloud cover | 2.5 km grid analysis | 25 km ERA5 reanalysis | 10× coarser for Finland |
| Snow depth | Station observation | Station observation | Equivalent |

The most significant quality difference is that MESAN provides **spatially consistent
gridded analysis fields** (gap-filled, physically constrained), whereas FMI provides
**raw point observations** that may have gaps, calibration offsets, and measurement
noise. This is the primary source of feature heterogeneity between the two countries.

---

## 8. Integration Architecture

### 8.1 Pipeline overview

```
                  SWEDEN                         FINLAND
                  ──────                         ───────

  SMHI API ──→ param_08_snow_depth.csv      FMI WFS ──→ fmi_snow_daily.csv
                   (snow depth)                            (snow + basic met)

  SMHI Grid ──→ MESAN GRIB files            FMI WFS ──→ fmi_hourly_daily.csv
  Archive         ↓                                       (temp, humidity, wind,
               process_mesan_to_daily.py                   precipitation, visibility)
                   ↓
  mesan_station_daily.csv                   ERA5 CDS ──→ era5_finland_cloud.csv
  (12 atmospheric features)                               (cloud cover only)
                                                ↓
                                          merge_fmi_features.py
                                                ↓
                                          fmi_features_daily.csv
                                          (all 12 features, FI stations)
                                                ↓
                   ────────────────────────────┴──────────────────────────
                                               ↓
                            merge_features_groundtruth.py
                              --extra-features fmi_features_daily.csv
                                               ↓
                            training_data_nordic.csv
                            (SE + FI, all 12 features + snow depth target)
                                               ↓
                            prepare_dataset.py
                                               ↓
                            {train,val,test}_sequences.npz  (nordic)
                                               ↓
                            train.py --config multitask_mesan_nordic.yaml
```

### 8.2 Merge logic

The `merge_features_groundtruth.py` script handles the heterogeneous sources via a
**stack-then-join** pattern when `--extra-features` is provided:

1. Load MESAN features for Swedish stations → add `country='SE'`
2. Load FMI feature table for Finnish stations → already has `country='FI'`
3. Align columns: any column present in one table but not the other is added with NaN
4. **Concatenate** (row-wise): combined feature table now has all stations
5. Load SMHI snow depth (Swedish) + FMI snow depth (Finnish) → concatenate
6. **Left-join** on (station_id, date): features ← snow depth
7. Apply coverage filter, interpolation, sequence creation — **identical logic** for both

This means Finnish and Swedish data flow through the same preprocessing, normalisation,
and sequence construction steps. No country-specific code paths exist downstream.

### 8.3 The `country` column

A `country` column (`'SE'` or `'FI'`) is carried through to `training_data_nordic.csv`.
It is **not** used as a model input feature, but is used during evaluation to compute
country-stratified metrics:
- Sweden N/S recall ratio
- Finland N/S recall ratio
- Sweden vs. Finland overall recall
- Cross-country geographic fairness analysis

---

## 9. Comparison with Swedish SMHI/MESAN Pipeline

| Aspect | Sweden (SMHI + MESAN) | Finland (FMI) |
|--------|----------------------|---------------|
| **Observation type** | Grid analysis (MESAN, 2.5 km) + station obs | Station observations |
| **Spatial coverage** | Continuous grid → gap-free for every station | Only at station locations |
| **Atmospheric features** | All 11 from MESAN grid (high quality) | 9 from station obs + 2 derived/ERA5 |
| **Snow depth source** | SMHI station observations | FMI station observations |
| **Coverage constraint** | MESAN covers Sweden only (approx. 10–25°E) | FMI covers Finland (19–31°E) |
| **Data format** | GRIB2 grid files → station extraction | WFS XML → direct station download |
| **Download time** | Heavy (GRIB files, ~GBs) | Lightweight (XML per chunk) |
| **Gap filling** | MESAN physically fills most gaps | Station gaps remain; 5-day interpolation |
| **Wind direction** | Vector components u, v from MESAN | Single speed WS_PT1H_AVG, no direction |
| **Frozen precip** | Measured `frsn24h` from MESAN | Derived from tmin/precip |
| **Cloud cover** | MESAN `tcc`, 2.5 km | ERA5 `tcc`, 25 km |
| **Visibility** | MESAN `vis`, 2.5 km | Derived from WAWA code |

### Why MESAN was not used for Finland

SMHI's MESAN product is a regional meteorological analysis covering Scandinavia.
Its eastern boundary is approximately 25–28°E, matching the Swedish-Finnish border
in the south but not extending across the Finnish mainland (which reaches 32°E).
This was confirmed by inspecting the MESAN GRIB grid coordinate arrays:

```python
# MESAN GRIB grid extent (actual values from our data)
lat_range: 55.0 – 70.0 °N
lon_range: 10.0 – 25.0 °E   ← Finland not covered
```

Finnish stations at longitudes 25–31°E would fall outside the MESAN domain, causing
the nearest-neighbor grid lookup to assign edge-of-domain values — physically
meaningless and potentially highly biased. Therefore, MESAN was **not extended** to
Finnish stations, and a separate feature source was required.

---

## 10. How Finnish Data Helps the Model

### 10.1 Increased training data volume

| Dataset | Stations | Winter days | Sequences (est.) |
|---------|----------|-------------|-----------------|
| Sweden only (current) | 305–425 | 2015–2022, Oct–Apr | 635,000 |
| Finland addition (estimated) | 160–200 | 2015–2022, Oct–Apr | ~180,000 |
| **Nordic combined** | **~550–600** | 2015–2022, Oct–Apr | **~820,000** |

More sequences directly reduce overfitting risk on the rare Extreme class (~3.9%),
which translates to better anomaly recall.

### 10.2 Climatological diversity

Finnish snow regimes differ from Swedish ones in several ways relevant to the model:

| Characteristic | Sweden (west) | Finland (east) |
|----------------|--------------|----------------|
| Snowpack onset | Nov–Dec (south), Oct (north) | Oct–Nov (south), Oct (north) |
| Max snow depth | 30–80 cm (north) | 50–100 cm (north) |
| Melt period | Mar–Apr (south), May (north) | Apr–May (south), May–Jun (north) |
| Rain-on-snow frequency | Higher (Atlantic influence) | Lower (continental, colder) |
| Lake-effect snow events | Rare | Common (Ladoga, Saimaa, Oulu) |
| Wind-compaction events | West coast (Bothnian coast) | Less frequent |

This diversity trains the shared encoder to learn more general snow physics
representations that are not overfit to the specific statistical patterns of
Swedish Atlantic-influenced snowfall.

### 10.3 Addressing the "Nordic region" claim

The paper's title and abstract claim *Nordic region* coverage. Restricting to Sweden
is a scientific weakness that reviewers at IGARSS or IEEE GRSL would likely flag.
Finnish data:
- Adds 160–200 stations from the second-largest Nordic country
- Extends the study domain eastward by 6 degrees of longitude
- Enables the geographic fairness analysis to demonstrate multi-country operation

### 10.4 Extended anomaly diversity

Finnish extreme snow events include patterns not well-represented in Swedish data:
- **Lake-effect snowbands** from Lakes Ladoga, Saimaa, and Oulu
- **Arctic outbreaks** into eastern Finland (colder, drier than Swedish equivalents)
- **Spring flooding snows**: late snowfall on already-deep snowpacks (significant
  snow-water equivalent events)

Training on these events improves the encoder's ability to detect thermodynamically
diverse pathways to "Extreme" class, not just the Atlantic storm-track patterns
dominant in Swedish training data.

### 10.5 Improved geographic fairness baseline

The current geographic oversampling strategy targets stations below 63°N. Southern
Finland (60–63°N) experiences an even weaker baseline snow climate than southern
Sweden — brief winters with episodic, short-duration snowfall. Including these
stations naturally tests and improves the model's ability to detect anomalies in
low-baseline climates, the very regime where the original model failed most severely
(recall = 0.124 for southern Sweden without oversampling).

---

## 11. Data Preparation Principles

### 11.1 Winter-month filtering

Both Swedish and Finnish sequences are restricted to **October–April** (7 months):
- Eliminates summer months with zero snow probability
- Matches the MESAN processing window
- Reduces dataset size by ~42% while retaining all snow-relevant observations

### 11.2 Temporal chunking for API downloads

**Daily query (90-day chunks):**
```
Oct 1 – Dec 29   (90 days)
Dec 30 – Mar 28  (90 days)
Mar 29 – Apr 30  (33 days)
```
Winter 2015-16 through 2023-24 = 9 winters × 3 chunks = 27 requests.

**Hourly query (30-day chunks):**
More granular because hourly responses are ~10× larger (24 values/day vs 1).
One winter season (7 months) = ~7 requests.

### 11.3 Resume capability

Both download scripts implement **checkpointing**: if the output CSV already exists,
the set of already-downloaded dates is read from it and only missing chunks are
fetched. This allows interrupted downloads to continue without restarting.

### 11.4 Coverage filtering

A Finnish station is retained only if it has snow depth observations on ≥30% of
its winter days (Oct–Apr). This threshold is lower than the Swedish 50% threshold
because:
- FMI station obs have more instrument gaps than the SMHI snow network
- Finnish coastal stations (southern Archipelago Sea) may have snow-free winters
  in mild years, legitimately producing <50% coverage
- The 30% threshold was chosen to balance data quality against station count

After coverage filtering, ~160–200 of the 440 raw FMI stations are retained.

### 11.5 Gap interpolation

After merging, snow depth gaps ≤5 consecutive days are linearly interpolated
per station. This is identical to the Swedish pipeline and prevents artificial
sequence breaks in the sliding-window construction.

### 11.6 Normalisation

A single `StandardScaler` (mean/variance) is fit on the **combined Nordic training
set** (2015–2022, SE + FI). This ensures:
- Swedish and Finnish features share the same normalisation space
- Feature distributions from different sources (MESAN grid vs. FMI station obs)
  are standardised together
- The model does not see raw distribution differences between countries at inference

Potential issue: if MESAN and FMI have systematically different biases for the same
physical quantity (e.g., different rain gauge designs → different precipitation
totals), normalisation will compress but not eliminate this bias. This is an
acceptable limitation for a first Nordic extension (see Section 15).

---

## 12. Derived Features

Two features are not directly observed by FMI instruments and must be derived.
One additional feature (elevation) uses a default value.

### 12.1 Frozen Precipitation Indicator

**Swedish source:** MESAN `frsn24h` — 24-hour frozen precipitation accumulation (cm),
physically modelled from temperature and precipitation fields.

**Finnish derivation:**
```python
frozen_precip = 1.0 if (precipitation > 0 AND temp_min < 0°C) else 0.0
```

**Rationale:** Precipitation is frozen when temperature is below 0°C. Using `temp_min`
(daily minimum temperature) rather than the mean is more conservative and
physically appropriate: even if the daily mean is slightly above 0°C, sub-zero
minimum temperatures indicate freezing conditions during the coldest part of the
day when most snowfall events occur.

**Limitations:**
- The MESAN feature is a continuous accumulation (cm of frozen water); the derived
  feature is binary (0/1). This changes the feature semantics — the model receives
  "yes/no frozen precip" for Finland vs. "how much frozen precip" for Sweden.
- Mixed-phase precipitation (sleet) at temperatures of -1°C to +1°C is ambiguous.
- Rain-on-snow events (positive temperature + snow depth > 0) are not explicitly
  captured by this binary derivation.

**Mitigation:** Normalisation partially compensates for the scale difference
(MESAN values are cm; Finnish binary is 0/1). The shared encoder must learn to use
both representations. In future work, a categorical variable encoding precipitation
phase derived from WAWA codes could replace this binary approximation.

### 12.2 Visibility

**Swedish source:** MESAN `vis` — gridded visibility analysis (m → km, capped at 100 km).

**Finnish derivation from WAWA weather phenomenon rank:**

The WAWA (WMO Table 4677 / BUFR 020003) code encodes the dominant weather phenomenon
at an observation station. The mapping used:

| WAWA Code Range | Phenomenon | Derived Visibility |
|-----------------|------------|-------------------|
| 40–49 | Fog (continuous or intermittent) | 0.2 km |
| 50–69 | Drizzle and/or rain | 2.0 km |
| 70–79 | Snow (falling or blowing) | 2.0 km |
| 80–99 | Showers (rain, snow, hail) | 2.0 km |
| 10–19 | Haze, dust, smoke | 5.0 km |
| 20–39 | Precipitation within past hour (obs time) | 4.0 km |
| all others | Clear / not observed | 10.0 km (default) |

**Daily visibility:** Mean of hourly WAWA-derived visibility values.

**Observed distribution (Jan 2024, 3-day test):**
- Min: 2.0 km, Max: 10.0 km, Mean: 8.3 km, Std: 2.7 km
- 100% of daily rows have a valid visibility value (WAWA is well-observed)

**Limitations:**
- WAWA codes provide only categorical visibility classes; the Swedish MESAN field
  provides continuous visibility analysis. This creates a feature that is inherently
  more discretised for Finnish stations.
- WAWA is missing or unreported at some automatic stations; the default 10.0 km
  is assigned, which slightly over-represents clear conditions.
- WAWA reports the dominant phenomenon, not necessarily a direct visibility measurement.
  True visibility instruments (transmissometers) are deployed at major airports only.

### 12.3 Elevation

**Swedish source:** Station metadata from SMHI API (field `height`, metres).

**Finnish source:** Elevation is **not provided** by the FMI `fmi::ef::stations`
WFS query. All Finnish stations are assigned `elevation = 0.0` as a default.

**Impact:** Elevation is one of 12 features used for spatial context. In Sweden,
elevation ranges from 0 to ~600 m and helps the model distinguish coastal/lowland
from upland/fell snow regimes. Setting Finnish elevation to 0 removes this
contextual signal for Finnish stations.

**Mitigation options (not yet implemented):**
1. Download SRTM or GTOPO30 DEM and look up elevation by station lat/lon
2. Use ERA5 orography (`z` field / 9.80665 → metres) as a proxy
3. Query the FMI station database via a different API endpoint

For the current implementation, elevation=0 is acceptable because:
- Elevation is a static feature (constant per station)
- Its effect is captured partially through latitude (correlated with snow regime)
- Finnish topography is relatively flat compared to Sweden (max ~650 m in
  Finnish Lapland vs. ~2000 m in Swedish Fjells)

---

## 13. Known Challenges and Mitigations

### 13.1 Feature heterogeneity (grid vs. station observations)

**Challenge:** Swedish features come from MESAN's 2.5 km gridded analysis (spatially
interpolated, physically consistent, gap-free). Finnish features come from raw point
observations (sparse, gappy, instrument-dependent).

**Consequence:** The encoder sees two systematically different data generating
processes for the same 12 features. This can cause the model to learn
country-specific patterns rather than generalising.

**Mitigations:**
- Joint normalisation ensures features have the same mean/variance regardless of source
- The shared encoder's compact size (d=64) limits its capacity to memorise
  country-specific patterns
- The geographic oversampling strategy (Section 14) ensures both countries contribute
  proportionally to training batches
- In the paper: the feature source heterogeneity is explicitly acknowledged in the
  Data section as a limitation

**Longer-term solution:** Replace MESAN with ERA5 for all stations (both SE + FI)
to achieve a consistent gridded analysis source across the full Nordic domain.
This would require re-extracting all Swedish features from ERA5, which is a
significant but tractable pipeline change.

### 13.2 WFS request limits and pagination

**Challenge:** The FMI WFS service does not document maximum request sizes, but
empirically, time windows > ~100 days return empty responses or connection timeouts.
Downloading 2015–2024 at daily resolution for all Finnish stations requires
~27 requests (for daily) and ~63 requests (for hourly).

**Mitigation:**
- 90-day chunks for daily (confirmed to work)
- 30-day chunks for hourly (more data per chunk)
- Retry logic with exponential back-off (3 attempts, 5/10/15 second delays)
- Resume capability avoids re-downloading on partial failures

**Estimated download time:**
- Daily query (all winters 2015–2024): ~5 minutes
- Hourly query (all winters 2015–2024): ~45–60 minutes (63 requests × ~60 seconds each)

### 13.3 Station availability over time

**Challenge:** Not all 440 FMI stations were operational throughout 2015–2024.
Some stations opened after 2015; some closed; some changed instrumentation.
The effective station pool varies by year.

**Evidence:** The daily query returns 269 stations for Jan 2024 but the station
registry has 440 entries. The difference (~170) includes inactive stations,
stations measuring different parameters, and road weather stations without snow obs.

**Mitigation:**
- Coverage filter (≥30% winter-day snow observations) automatically excludes
  stations with insufficient data
- Temporal train/val/test split means stations must have consistent coverage
  across 2015–2022 (train), 2023 (val), 2024 (test) to contribute to all phases

### 13.4 ERA5 cloud cover resolution mismatch

**Challenge:** Finnish cloud cover uses ERA5 at 0.25° (~25 km resolution) while
Swedish cloud cover uses MESAN at 2.5 km. The 10× resolution difference means:
- Convective clouds (mesoscale) are not resolved in ERA5 for Finnish stations
- ERA5 cloud cover is a domain average rather than a point observation

**Consequence:** Cloud cover has reduced discriminative power for Finnish stations
compared to Swedish ones. Cloud cover is used as a proxy for snow condition context
(overcast skies during snowfall events), so reduced resolution is acceptable.

**Mitigation:** ERA5 total cloud cover at midday (12:00 UTC) provides a daily-scale
signal that is relevant for the model's 30-day context window.

### 13.5 Missing precipitation for some Finnish stations

**Observed rate:** In the 3-day test (Jan 2024), `precipitation` was available for
only 59% of daily station-rows from the hourly query. This is because not all
Finnish weather stations have tipping-bucket gauges (which are needed for the
`PRA_PT1H_ACC` parameter).

**Fallback strategy:** When hourly precipitation is NaN, the pipeline falls back to
the `rrday` value from the daily query (which has broader station coverage).

**Coverage after fallback:** Expected ~75–80% non-NaN (based on daily query coverage
observed in initial tests).

### 13.6 WAWA code interpretation

**Challenge:** The WAWA `PT1H_RANK` parameter encodes "the most significant weather
phenomenon in the past hour" on a WMO ordinal scale. This is not a direct
visibility measurement. The mapping from WAWA codes to visibility classes (km) is
an approximation based on WMO definitions.

**Key ambiguity:** WAWA code 0 or NaN means "no significant weather phenomenon
observed" — which is mapped to 10.0 km (default clear). This is generally appropriate
but will over-estimate visibility during light overcast or thin haze conditions.

---

## 14. Data Quality and Coverage

### 14.1 Snow depth coverage (Jan 2024 snapshot)

| Metric | Value |
|--------|-------|
| Stations returning snow data | 269 |
| Snow depth non-NaN | 67% (905/1,345 station-days) |
| Snow depth range | 0–72 cm |
| Mean (non-zero days) | 38.8 cm |
| Standard deviation | 13.6 cm |

The 33% NaN rate for snow depth is expected: southern Finnish stations (below 62°N)
frequently have 0 snow depth in January 2024 due to the mild winter, but some return
NaN when there is genuinely no measurement on that day.

### 14.2 Atmospheric feature coverage (Jan 2024, 3-day test)

| Feature | Non-NaN Rate | Source |
|---------|-------------|--------|
| temperature | 66% | FMI hourly |
| humidity | 66% | FMI hourly |
| wind_speed | 55% | FMI hourly |
| precipitation | 59% | FMI hourly |
| visibility | 100% | WAWA-derived |
| cloud_cover | ~100% | ERA5 |
| frozen_precip | ~60% | Derived (needs temp_min + precip) |

The ~65% feature completeness for atmospheric variables from hourly queries
is lower than MESAN's ~95% (the grid analysis fills most gaps). After gap
interpolation (≤5 days), the effective coverage should rise to ~80–85% for
the training set.

### 14.3 Effective training contribution (estimated)

After coverage filtering (≥30% winter days with snow):
- Expected to retain: **160–200 Finnish stations**
- Contributing training sequences: ~180,000 (2015–2022, Oct–Apr, 30-day windows)
- This represents ~28% more data than the current Swedish-only dataset

---

## 15. Limitations and Caveats

1. **Feature heterogeneity is a known limitation** that should be explicitly
   acknowledged in the paper's Data section. The different sources (MESAN grid vs.
   FMI station obs) mean that the model must learn to use slightly different feature
   representations for Swedish vs. Finnish stations.

2. **Elevation defaults to 0** for Finnish stations. This removes one contextual
   feature that is otherwise informative for Swedish upland stations (>300 m).

3. **Frozen precipitation is binary** for Finnish stations vs. a continuous
   accumulation for Swedish stations. This is the most significant semantic
   difference between the two feature sets.

4. **ERA5 cloud cover is coarser** (25 km) than MESAN cloud cover (2.5 km). The
   practical impact on model performance is expected to be small since cloud cover
   is a supporting feature, not the primary signal.

5. **FMI does not cover Norway** — the Nordic region strictly includes Norway,
   Denmark, and Iceland. The current extension covers Sweden + Finland only.
   Norwegian data could be added from MET Norway's WFS (similar API).

6. **Historical FMI data availability:** FMI's WFS provides historical observations
   going back to ~2010 for most stations. The 2015–2024 period used in this study
   should be fully covered, but data gaps in early years (2015–2017) may be more
   frequent for automatic stations.

7. **Anomaly label derivation for Finnish stations** uses the same threshold rules
   as Swedish stations (7-day rolling max snow depth + meteorological indicators).
   These thresholds were calibrated to SMHI warning levels. FMI uses a different
   warning system (class I–IV vs. SMHI class I–III). The severity class distribution
   for Finnish stations may differ from Swedish ones.

---

## 16. Download Pipeline Reference

### Scripts (in execution order)

```bash
# 1. Station metadata (fast, ~1 second)
python scripts/download_fmi_stations.py \
    --output data/raw/fmi_station_metadata.csv

# 2. Daily snow + basic met (Oct 2015 – Apr 2024, ~5 minutes)
python scripts/download_fmi_snow.py \
    --output data/raw/fmi_snow_daily.csv

# 3. Hourly atmospheric features, aggregated to daily (~45–60 minutes)
python scripts/download_fmi_hourly.py \
    --output data/raw/fmi_hourly_daily.csv

# 4. ERA5 cloud cover [requires CDS API key in ~/.cdsapirc]
pip install cdsapi xarray netcdf4
python scripts/download_era5_finland.py \
    --station-file data/raw/fmi_station_metadata.csv \
    --output data/raw/era5_finland_cloud.csv

# 5. Merge FMI sources into feature table
python scripts/merge_fmi_features.py \
    --snow-file    data/raw/fmi_snow_daily.csv \
    --hourly-file  data/raw/fmi_hourly_daily.csv \
    --cloud-file   data/raw/era5_finland_cloud.csv \
    --station-file data/raw/fmi_station_metadata.csv \
    --output       data/processed/fmi_features_daily.csv

# 6. Combine with Swedish data for Nordic training set
python scripts/merge_features_groundtruth.py \
    --extra-features data/processed/fmi_features_daily.csv \
    --output data/processed/training_data_nordic.csv

# 7. Build sequence NPZ files
python scripts/prepare_dataset.py \
    --input  data/processed/training_data_nordic.csv \
    --output data/processed/nordic

# 8. Train Nordic model
python train.py --config configs/multitask_mesan_nordic.yaml
```

### Key configuration

File: `configs/multitask_mesan_nordic.yaml`

- Training data: `data/processed/training_data_nordic.csv`
- Architecture: identical to MTL-Severity (encoder_hidden=64, 89K params)
- Geographic oversampling: `south_anomaly_oversample_factor: 8.0` (lat < 63°N, both countries)
- Loss weights: `[spatial=1.0, temporal=0.1, anomaly=2.0]` (unchanged)
- Class weights: `[1.0, 17.8, 23.6]` (recomputed from Nordic class distribution if needed)

### ERA5 prerequisite

Register at https://cds.climate.copernicus.eu/ and configure `~/.cdsapirc`:
```
url: https://cds.climate.copernicus.eu/api/v2
key: <uid>:<api-key>
```

ERA5 requests are processed asynchronously (queue-based); each month takes ~2–10 minutes
to be fulfilled depending on server load. For 9 winters × 7 months = 63 month-level
requests, expect total ERA5 download time of 2–10 hours.

---

*Last updated: 2026-04-16*
*Data source: Finnish Meteorological Institute (FMI) Open Data (CC-BY 4.0)*
*ERA5 data: Copernicus Climate Change Service (C3S), ECMWF*
