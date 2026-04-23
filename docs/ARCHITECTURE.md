# System Architecture

## Pipeline Overview

The pipeline is designed as a series of modular, script-based steps that ingest raw data from Nordic providers and output a research-ready dataset.

1. **Extraction Phase**: Downloads data from diverse APIs (SMHI, FMI, Syke) and file storage (MESAN).
2. **Interim Phase**: Standardizes varied data formats (CSV, GRIB2, NetCDF) into a common schema.
3. **Processing Phase**: Handles spatial and temporal alignment, missing values, and normalization.
4. **Derivation Phase**: Applies hydrological and environmental models to calculate new parameters.
5. **Output Phase**: Generates final, versioned datasets.

## Module Design

- `src/extraction/`: One script per source provider.
- `src/processing/`: Generalized and source-specific cleaning scripts.
- `src/derivation/`: Modular logic for each research-specific parameter.
- `src/common/`: Shared tools for spatial alignment, I/O, and configuration.

## Data Schema

We aim to use **Xarray-compatible NetCDF** as the primary format for the final processed dataset to support multi-dimensional environmental modeling.
