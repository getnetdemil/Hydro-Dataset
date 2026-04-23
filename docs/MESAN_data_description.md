**Meteorological Analysis Model MESAN (AROME) – Historical Analysis Data**

- **Keywords**: HVD, meteorology, model data, air temperature, cloud amount, precipitation amount, relative humidity, visibility, wind speed, wind direction  
- **Dataset name**: MESAN (AROME) – historical analysis

---

### Overview

The MESAN (AROME) historical analysis dataset contains **archived MESAN analysis data** up to and including the **day before** the data extraction takes place.

- **Data available from**: **December 2014**  
- **Earlier period**: Prior to this, corresponding analysis data were delivered from MESAN based on **HIRLAM**  
- **Model type**: Meteorological **analysis model** describing the **current weather situation** in grid squares  
- **Update frequency**: **Hourly** two‑dimensional analyses of common weather parameters

The fields mainly describe:

- Air temperature  
- Precipitation  
- Cloud cover  
- Visibility  
- Relative humidity  
- Wind speed and direction  
- Snow‑related variables

The analysis domain covers:

- **Scandinavia**  
- The **British Isles**  
- The **northern part of continental Europe**  
- The **Baltic states**

MESAN is tightly linked to the numerical weather prediction model **AROME**, which provides the first‑guess background field.

---

### Status and Versioning

- **Data update status**: Data is **continuously updated**  

Metadata (example from SMHI):

- **Created**: 2016‑05‑24  
- **Published**: 2016‑05‑24  
- **Revised**: 2024‑05‑03  
- **Last updated**: 2025‑04‑22  

*(Adjust these dates if you use a specific snapshot/version internally.)*

---

### Spatial Coverage and Grid

The MESAN analysis covers a fixed grid over northern Europe.

- **Horizontal grid resolution**: **2.5 × 2.5 km**

**Domain corners (approximate):**

| Corner     | Latitude | Longitude |
|-----------|----------|-----------|
| Southwest | 52.4° N  | 2.0° W    |
| Northwest | 71.5° N  | 9.5° W    |
| Northeast | 71.2° N  | 39.7° E   |
| Southeast | 52.3° N  | 27.8° E   |

**Region description**:

- Sweden and Scandinavia  
- The British Isles  
- Northern continental Europe  
- The Baltic states

**Time coverage in this archive**:

- **Start date**: 2015‑08‑01 (per SMHI grid archive metadata)  
- **End date**: Ongoing

---

### Data Usage

At SMHI, MESAN data are used to:

- Produce **weather maps** that meteorologists use as a basis for **forecasting**  
- Provide **analysis fields** that can replace missing observations in some cases  
- Serve as **input** to other models, for example:
  - Hydrological models to calculate **runoff** in rivers and catchments  
  - Models and indices mapping **forest and land fire risk**  

For your project, MESAN can be used as a **high‑resolution reanalysis** of atmospheric conditions over Sweden and surrounding regions.

---

### Data Format

MESAN analysis data are distributed in **GRIB** format.

- **Format**: **GRIB** (binary grid format defined by WMO)  
- A GRIB file contains encoded gridded fields together with codes that are combined with external metadata to interpret the dataset correctly.

**GRIB format information and documentation**:

- General GRIB description and usage help:  
  `https://www.smhi.se/data/temperatur-och-vind/temperatur/historisk-data-i-grib-format/sa-fungerar-grib-format`

---

### Access and Links

- **API feed for download (grid archive)**:  
  `https://opendata-download-grid-archive.smhi.se/feed/6`

- **GUI / web interface for MESAN historical data (GRIB)**:  
  `https://www.smhi.se/data/temperatur-och-vind/temperatur/historisk-data-i-grib-format/mesan-a`

- **WMS viewing service for MESAN (AROME)**:  
  `https://opendata-view.smhi.se/grid-archive/mesanA_extent/wms?service=WMS&request=GetCapabilities`

- **Information about the GRIB format** (for developers):  
  `https://www.smhi.se/data/temperatur-och-vind/temperatur/historisk-data-i-grib-format/sa-fungerar-grib-format`

- **Grid archive / model API documentation**:  
  `https://opendata.smhi.se/gridarchive/index_met`

**Download notes**:

- You can specify a **time period** and download data in files that typically contain **24 hours** of data per file.  
- These files can be large; SMHI recommends downloading **a few days at a time**.  
- A maximum of **7 days** can usually be downloaded per request.

---

### License and Restrictions

By downloading and using MESAN data you accept SMHI’s license terms:

- **License / terms of use**:  
  `https://www.smhi.se/data/om-smhis-data/villkor-for-anvandning`

When possible, **cite SMHI as the data source** in publications, reports, or derived products.

---

### Analysis Method and Data Sources

The MESAN analysis uses a combination of:

- Observations from **standard weather stations**  
- Stations operated by the **Swedish Transport Administration**  
- **Weather radar** data  
- **Satellite** observations  

As a **first guess (background)**, MESAN typically uses a forecast from the numerical weather prediction model **AROME** at the relevant analysis time. This background field:

- Is itself based on previous observations and forecasts  
- Is then **adjusted** within MESAN to better fit current observations

The analysis uses a method known as **Optimal Interpolation (OI)**, which:

- Is based on statistical relationships describing how the **information content** of observations decreases with **distance** from each station  
- Allows several observations to be **weighted and combined** into an average value representative of a **grid square**  
- In MESAN/AROME, these grid squares are **2.5 × 2.5 km**

---

### Related Models and Context

For context within SMHI’s modelling system:

- **NEMO NSBS01**: Oceanographic forecasting model describing sea state (in use since 2020‑11, replacing NEMO NS01, which replaced HIROMB BS01 in 2016‑10).  
- **MESAN (GRIDPP)**: Current version of the MESAN analysis system (in use since 2024‑02), replacing the earlier MesanA and, before that, Mesan.  
- **AROME**: Numerical weather prediction model describing the **evolution** of weather in time and space (in use since 2014‑03, replacing HIRLAM E11).

The MESAN analysis fields you use are strongly connected to **AROME** as the background model, and to the **MESAN (GRIDPP)** system for later periods.

---

### Summary

The MESAN (AROME) historical analysis dataset provides **high‑resolution (2.5 km), hourly meteorological analysis fields** over Scandinavia and surrounding regions, from the mid‑2010s onwards. Combining dense observational networks (stations, radar, satellite) with **Optimal Interpolation** on top of **AROME** forecasts, it yields spatially consistent fields of key weather variables suitable for **hydrological modelling**, **climate analysis**, and other environmental applications in northern Europe.