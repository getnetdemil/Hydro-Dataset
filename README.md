# Hydro-Dataset

**Nordic Regional Hydrological and Environmental Dataset**

A modular, script-driven pipeline for creating a comprehensive dataset for snow hydrology, water resource, and water quality research in the Nordic region. This project is developed for the [Workshop on Mining Imaging Data for Hydrological and Environmental Modelling (HydroImaging 2026)](https://hydroimaging.github.io/).

## Overview

The Hydro-Dataset project aims to unify diverse data sources from the Nordic region to derive new research-grade parameters. Phase 1 focuses on:
- **SMHI (Sweden)**: Station data and reanalysis.
- **MESAN (Sweden)**: Reanalyzed meteorological data.
- **FMI (Finland)**: Station observations and satellite data.
- **Syke (Finland)**: Hydrological and water quality field observations.

## Project Structure

```text
Hydro-Dataset/
├── data/                 # Data storage (Raw, Interim, Processed)
├── docs/                 # Detailed architecture and source documentation
├── notebooks/            # EDA and quick prototyping
├── pipelines/            # Pipeline orchestration (Makefiles)
├── src/                  # Core processing logic
│   ├── extraction/       # Data downloaders
│   ├── processing/       # Data cleaning
│   └── derivation/       # Parameter derivation
├── tests/                # Automated verification
└── .env.example          # Template for local environment configuration
```

## Getting Started

1. **Setup Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure Paths**:
   Copy `.env.example` to `.env` and adjust the `DATA_DIR` and any API keys required.
3. **Run Pipeline**:
   The project uses a Makefile for orchestration.
   ```bash
   cd pipelines
   make extract-all
   make build-dataset
   ```

## Documentation

- [Architecture Design](docs/ARCHITECTURE.md)
- [Data Source Details](docs/DATA_SOURCES.md)
- [Derivation Methodologies](docs/DERIVATION_METHODS.md)
- [Contributing Guidelines](docs/CONTRIBUTING.md)
