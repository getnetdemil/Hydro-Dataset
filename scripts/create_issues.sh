#!/bin/bash

# Array of issues to be created. Format: "Title;Body;Labels"
issues=(
    # --- Category: Data Extraction (Extraction) ---
    "SMHI API: Implement station data downloader for temperature and precipitation;Create a robust downloader for SMHI meteorological observations using their REST API. Handle rate limiting and pagination.;extraction,smhi"
    "SMHI API: Implement hydrological level downloader;Fetch water level data for Swedish rivers and lakes. Standardize output to CSV.;extraction,smhi"
    "MESAN: Implement GRIB2 to NetCDF converter for reanalysis;Develop a module to convert raw MESAN GRIB2 files into Xarray-compatible NetCDF files for easier processing.;extraction,mesan,processing"
    "MESAN: Automated downloader for latest reanalysis cycles;Create a script to fetch the most recent 2.5km MESAN grids from SMHI Open Data servers.;extraction,mesan"
    "FMI API: Implement WFS downloader for station observations;Use FMI's WFS API to fetch Finnish meteorological station data. Handle multi-point requests.;extraction,fmi"
    "FMI Satellite: Ingest snow cover extent products;Download and preprocess FMI's satellite-derived snow products (H-SAF or similar).;extraction,fmi,imaging"
    "Syke OData: Implement discharge data extractor;Develop a client for Syke's OData API to fetch discharge (Q) measurements from Finnish catchments.;extraction,syke"
    "Syke OData: Ingest lake and river water quality parameters;Fetch nutrient (N, P), turbidity, and temperature data from Syke's monitoring stations.;extraction,syke"
    "Data Source: Research and document Norwegian (MET Norway) API for Phase 2;Identify key endpoints for Norwegian meteorological data to expand the Nordic coverage.;extraction,research"
    "Data Source: Research and document Danish (DMI) API for Phase 2;Explore DMI's open data for potential inclusion in the next phase of the project.;extraction,research"

    # --- Category: Harmonization & Processing (Processing) ---
    "Coordinate System: Implement ETRS89-LAEA projection for all spatial data;Standardize all gridded and point data to the ETRS89 Lambert Azimuthal Equal Area projection (EPSG:3035).;processing,geo"
    "Temporal Alignment: Implement hourly-to-daily resampling logic;Develop a common utility to aggregate hourly observations into daily averages/sums for hydrological modeling.;processing"
    "Missing Values: Implement gap-filling for station observations;Apply linear interpolation or nearest-neighbor methods to handle short gaps in sensor data.;processing"
    "Metadata: Implement CF-convention compliance for NetCDF outputs;Ensure all processed datasets follow Climate and Forecast (CF) Metadata Conventions.;processing,standard"
    "Spatial Alignment: Create a common 2.5km Nordic grid mask;Develop a mask to clip and align all imaging data (MESAN, FMI) to a unified study area.;processing,geo"
    "Unit Standardization: Convert all precipitation to mm and temperature to Celsius;Ensure strict unit consistency across SMHI, FMI, and Syke data streams.;processing"
    "Data Quality: Implement outlier detection for sensor data;Develop scripts to flag and remove physically impossible values (e.g., -90C in summer).;processing,qc"

    # --- Category: Parameter Derivation (Derivation) ---
    "SWE Model: Implement Sturm empirical formula for snow density;Use snow depth and temperature history to estimate snow density and derive SWE.;derivation,snow"
    "SWE Model: Develop a machine learning regressor for SWE downscaling;Train a model to interpolate sparse SWE station data using MESAN imaging features.;derivation,ml,snow"
    "Runoff: Implement catchment-scale water balance scripts;Calculate runoff potential by fusing Syke discharge with MESAN precipitation data.;derivation,hydrology"
    "Water Quality: Develop a satellite-based turbidity index;Create a proxy for water quality using FMI satellite imagery to supplement Syke observations.;derivation,imaging"
    "Derivation: Implement Snowmelt degree-day factor calculation;Derive snowmelt rates based on temperature cubes and historical melt patterns.;derivation,snow"
    "Derivation: Create a Nordic Soil Moisture proxy;Estimate soil moisture status by integrating precipitation history and temperature patterns.;derivation,hydrology"

    # --- Category: Validation & Quality Control (Validation) ---
    "Validation: Benchmark derived SWE against FMI satellite products;Compare our derived SWE estimates with FMI's official satellite-based SWE products.;validation,snow"
    "Sanity Check: Cross-validate border stations between SMHI and FMI;Check for consistency in readings from weather stations near the SE-FI border.;validation,qc"
    "Visualization: Create temporal profile plots for key catchments;Develop a notebook to visualize precipitation vs. discharge for top 10 catchments.;validation,notebook"
    "Spatial Validation: Generate error maps for MESAN vs. Station data;Visualize the spatial distribution of reanalysis errors to identify bias.;validation,imaging"

    # --- Category: Foundation Model Ready Benchmarking (Foundation) ---
    "Benchmark: Create a 'Gold Standard' dataset for Nordic SWE;Curate a high-quality subset of validated SWE data for ML benchmarking.;foundation,ml"
    "LLM Prep: Document dataset schema for LLM ingestion;Create detailed JSON-LD or Markdown schema to help LLMs understand the dataset structure.;foundation,documentation"
    "VLM Prep: Generate multi-modal image-text pairs;Create paired samples of satellite imagery and hydrological descriptions for VLM training.;foundation,imaging,ml"
    "Benchmark: Implement leaderboard scripts for model evaluation;Develop scripts to calculate RMSE, MAE, and KGE scores for external model submissions.;foundation"

    # --- Category: Infrastructure & CI/CD (Infrastructure) ---
    "GitHub Actions: Implement automated linting and type checking;Set up a workflow to run Black, Flake8, and Mypy on every push.;infrastructure,ci"
    "GitHub Actions: Set up unit test runner;Automatically run Pytest on feature branch PRs.;infrastructure,ci"
    "DVC: Initialize Data Version Control for raw data tracking;Set up DVC to track large binary files (GRIB2/NetCDF) without bloating Git.;infrastructure,data"
    "Environment: Create a Dockerfile for reproducible processing;Provide a containerized environment with all geospatial libraries (GDAL, PROJ) pre-installed.;infrastructure"
    "Logging: Implement a centralized logging module in src/common;Ensure all pipeline scripts log to both console and a file for debugging.;infrastructure"
    "Config: Implement secret management for API keys;Use GitHub Secrets and local .env files to securely handle SMHI/FMI keys.;infrastructure,security"

    # --- Category: Documentation & Paper (Documentation) ---
    "Tutorial: Create a 'Getting Started' Jupyter Notebook;Provide an end-to-end example of fetching data and deriving one parameter.;documentation,notebook"
    "Paper: Draft the 'Methodology' section for HydroImaging 2026;Document the data fusion and processing steps in LaTeX/Markdown.;documentation,paper"
    "Paper: Generate high-resolution figures for the workshop paper;Create maps and charts showing the study area and preliminary results.;documentation,paper"
    "Proposal: Refine 'Expected Impact' section with team feedback;Finalize the research impact statement in proposal.md.;documentation,paper"

    # --- Category: Community & Collaboration (Collaboration) ---
    "Templates: Add GitHub Issue and Pull Request templates;Standardize how issues are reported and how code is reviewed.;collaboration"
    "LICENSE: Research and add appropriate Open Science license;Choose between MIT, Apache 2.0, or CC-BY for the dataset and code.;collaboration"
    "CODE_OF_CONDUCT: Add project code of conduct;Establish basic rules for professional interaction in the repository.;collaboration"
    "Tutorial: Document how to add a new data source;Create a guide for external researchers in docs/CONTRIBUTING.md.;collaboration,documentation"

    # --- Category: Final Integration (Integration) ---
    "Integration: Implement a unified 'make build-dataset' command;Finalize the Makefile to run all steps from extraction to derivation sequentially.;integration"
    "Integration: Create a final NetCDF packaging script;Aggregate all derived parameters into a single versioned NetCDF file for release.;integration"
    "Project: Perform a dry run of the entire pipeline;Verify that a fresh clone can generate the processed dataset from scratch.;integration,qc"
    "Workshop: Prepare the presentation deck for HydroImaging 2026;Create a slide deck summarizing the Nordic Hydro-Dataset and its benchmarks.;paper,workshop"
)

# Create issues sequentially
for issue in "${issues[@]}"; do
    IFS=";" read -r title body labels <<< "$issue"
    echo "Creating issue: $title"
    gh issue create --title "$title" --body "$body" --label "$labels"
done
