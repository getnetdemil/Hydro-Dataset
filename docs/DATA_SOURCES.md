# Data Sources (Comprehensive Nordic Hydrology)

This project leverages the full open data portals of the Swedish and Finnish national institutes to create a multi-modal, research-ready dataset.

## SMHI (Swedish Meteorological and Hydrological Institute)
*   **Portal**: [SMHI Open Data Explorer](https://www.smhi.se/data/sok-oppna-data-i-utforskaren)
*   **MetObs**: Real-time and historical station observations (Temperature, Precip, Snow).
*   **HydObs**: Water level and discharge from Swedish gauging stations.
*   **HYPE Model**: Outputs from the Hydrological Predictions for the Environment model, including flow, nitrogen, and phosphorus transport.
*   **MESAN/STRÅNG**: Gridded reanalysis for meteorological and radiation parameters.
*   **Climate Scenarios**: Regional climate model projections (Rossby Centre).

## FMI (Finnish Meteorological Institute)
*   **Portal**: [FMI Open Data](https://en.ilmatieteenlaitos.fi/open-data)
*   **Observations**: WFS-based weather, marine (sea level/waves), and air quality data.
*   **Satellite Products**: H-SAF and MODIS-based snow cover and soil moisture products.
*   **Radar**: High-resolution gridded precipitation data.
*   **METIS**: Curated research datasets with persistent DOIs.

## Syke (Finnish Environment Institute)
*   **Type**: In-situ hydrological and water quality observations.
*   **Access**: OData API.
*   **Variables**: Catchment discharge, water temperature, and detailed nutrient profiles.

## ECMWF/Copernicus (Secondary)
*   **ERA5-Land**: Used for cross-validation and filling gaps in low-density station areas.
*   **MODIS**: Direct ingestion of thermal and optical bands for snow mapping verification.
