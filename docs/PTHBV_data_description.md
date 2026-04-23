**PTHBV – Gridded Daily Temperature and Precipitation over Sweden (since 1961)**

- **Keywords**: Meteorology, model data, air temperature, precipitation amount  
- **Dataset name**: PTHBV (Precipitation & Temperature, Hydrological Agency’s Water Model)

---

### Overview

PTHBV is a climate database developed with a particular focus on **hydrological model calculations**. It contains **daily values of precipitation and air temperature** over Sweden and is primarily used as input to hydrological models such as **S-HYPE** and **HBV**.

- **Spatial representation**: Nationwide grid, **4 × 4 km** resolution  
- **Temporal coverage**: From **1961-01-01** to **ongoing**  
- **Main use cases**: Forcing data for hydrological and climate-related modelling and analysis

PTHBV is constructed by interpolating observations from SMHI’s meteorological station network (and, in border regions, selected stations from the Norwegian Meteorological Institute) to a regular grid over Sweden.

---

### Status and Versioning

- **Data update status**: Data is **continuously updated**  
- **Operational update cycle**:  
  - Updated on the **first day of each month**  
  - Each update revises the previous **three months**, with a **one‑month lag**  
  - Example: On 1 December, values for **September and October** are updated

- **Metadata dates** (example SMHI metadata):
  - **Created**: 2022‑12‑06  
  - **Published**: 2022‑12‑06  
  - **Revised**: 2025‑02‑24  
  - **Last updated**: 2025‑03‑04

*(Adjust these dates if you maintain your own internal versioning.)*

---

### Data Formats

Data can be distributed in several standard formats:

- **NetCDF** (`application/netcdf`)  
- **CSV** (`text/csv`)  
- **JSON** (`application/json`)

---

### Access and Links

- **Product information (SMHI PTHBV / PT-HBV)**:  
  `https://www.smhi.se/data/nedladdning-av-data/`

- **Data download interface (gridded precipitation and temperature)**:  
  `https://www.smhi.se/data/meteorologi/nederbord-och-temperatur/griddade-nederbords-och-temperaturdata`

- **API documentation (PTHBV API)**:  
  `https://opendata.smhi.se/pthbv/api`

*(URLs may change over time; check SMHI’s website if links are outdated.)*

---

### License and Restrictions

By downloading and using the data you accept SMHI’s license terms:

- **License / terms of use**:  
  `https://www.smhi.se/data/om-smhis-data/villkor-for-anvandning`

When possible, **cite SMHI as the data source** in publications and reports.

---

### Spatial and Temporal Coverage

- **Geographical coverage**: Sweden  

| Parameter          | Value  |
|--------------------|--------|
| Longitude (West)   | 5.51   |
| Longitude (East)   | 28.60  |
| Latitude (North)   | 69.85  |
| Latitude (South)   | 53.89  |

- **Time interval**:  
  - **Start date**: 1961‑01‑01  
  - **End date**: Ongoing (continuously extended)

---

### About Gridded Data

Because the climate cannot be observed at every location, **gridded analysis models** are used. In such models, the region of interest (here, slightly larger than Sweden) is divided into grid boxes (4 × 4 km for PTHBV).

For each grid box and each day:

- A value is computed using **all available observations** and  
- A **geostatistical interpolation method** is applied, incorporating:
  - Station coordinates  
  - Station elevation  
  - Grid box characteristics (e.g. elevation)  

This results in **complete spatial coverage**: every grid cell has data for every time step within the covered period.

---

### Interpolation Method in PTHBV

Data from SMHI’s meteorological stations are interpolated to the PTHBV grid using a **geostatistical method called optimal interpolation**. The method explicitly takes into account:

- The **distance** between stations and the grid box being estimated  
- The **mutual correlation** between stations  
- **Topography** (e.g. elevation)  
- Typical **wind direction and wind speed** in different parts of the country

Technical details of the interpolation are described in:

- Johansson (2000)  
- Johansson and Chen (2003, 2005)

---

### Precipitation Corrections

Observed precipitation is corrected for **measurement losses**, which are mainly due to precipitation being blown past the gauge (especially in windy and snowy conditions).

The corrections:

- Are calculated using the methods specified by **Alexandersson (2003)**  
- Take into account:
  - How **wind‑exposed** the station is  
  - Whether the precipitation falls as **snow or rain** (determined from temperature)

---

### Station Network and Homogeneity

The PTHBV database is based primarily on observations from:

- **Swedish meteorological stations** in SMHI’s station network  
- Additional stations in the **Norwegian Meteorological Institute’s** network along the Swedish–Norwegian border

SMHI performs an annual review (typically in **April**) of:

- Changes in the station network (closures, new stations, relocations)  
- Consequent effects on data homogeneity

After this review, the database is updated and, where necessary, **recalculated values** are produced:

- For previous years (if network changes impact historical consistency)  
- For the period January–February of the current year  

Note that **station closures or openings** can, in some cases, introduce **inhomogeneities** in the time series, even after adjustments.

---

### Summary

PTHBV provides **long-term, high‑resolution, gridded daily precipitation and temperature data** for Sweden, specifically tailored for **hydrological and climate applications**. Through optimal interpolation, measurement corrections, and continuous updates, it offers a consistent and spatially complete dataset suitable for driving models like **S‑HYPE** and **HBV** and for research on Nordic hydrology and climate.