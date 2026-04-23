# Data Sources (Phase 1)

This project fuses multiple data streams from the Nordic region.

## Swedish Meteorological and Hydrological Institute (SMHI)
- **API**: [SMHI Open Data API](https://opendata.smhi.se/apidocs/metobs/index.html) (REST, JSON).
- **Data types**: In-situ meteorological station observations (Temperature, Precipitation, Snow Depth).
- **Update Frequency**: Real-time or batch downloads depending on parameter.

## MESAN (Meteorological Analysis)
- **Format**: [GRIB2 files](https://opendata.smhi.se/apidocs/mesan/index.html).
- **Resolution**: High-resolution 2.5km grid over Sweden.
- **Role**: Serves as the primary "imaging" reanalysis source for spatial modeling.

## Finnish Meteorological Institute (FMI)
- **API**: [FMI Open Data WFS API](https://en.ilmatieteenlaitos.fi/open-data) (WFS, XML).
- **Data types**: Meteorological observations and satellite-derived snow products.
- **Update Frequency**: Daily or real-time.

## Finnish Environment Institute (Syke)
- **API**: [Syke OData API](https://www.syke.fi/en-US/Open_information) (OData).
- **Data types**: Hydrological discharge (Q), lake and river water levels, and water quality parameters.
- **Role**: Provides the primary ground-truth for catchment-scale hydrological research.
