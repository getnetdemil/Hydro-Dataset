# Project Proposal: Hydro-Dataset (Nordic Region)

**Title**: Mining Multi-Modal Imaging and In-Situ Data for Scalable Nordic Hydrological Modelling  
**Target Venue**: [Workshop on Mining Imaging Data for Hydrological and Environmental Modelling (HydroImaging 2026)](https://hydroimaging.github.io/)  
**Primary Research Areas**: Snow Hydrology, Multi-Sensor Fusion, Physics-Informed ML, Water Quality  
**Geographic Focus**: Nordic Region (Sweden, Finland, and surrounding areas)

---

## 1. Executive Summary
The Nordic region is a critical frontier for understanding climate-driven hydrological shifts. However, the integration of high-resolution Earth Observation (EO) imaging with heterogeneous in-situ observations remains a significant bottleneck. This project, **Hydro-Dataset**, proposes an open-source, reproducible framework designed to "mine" and fuse multi-modal data from SMHI, MESAN, FMI, and Syke. By harmonizing satellite-derived imaging products with high-resolution reanalysis (MESAN) and ground-truth station data, we create a **foundation-model-ready benchmark** for snow hydrology and water quality research, directly addressing the HydroImaging 2026 call for scalable, observation-driven environmental modelling.

## 2. Research Context & Motivation
### 2.1 Bridging Earth Observation and Hydrology
Traditional hydrological models often lack the spatial granularity provided by modern imaging sensors. Conversely, computer vision models for EO often lack the physical constraints provided by in-situ hydrological observations. Our project bridges this gap by:
*   **Integrating Multi-Sensor Imaging**: Leveraging FMI satellite snow products and MESAN gridded reanalysis (2.5km) as "imaging" inputs for spatial modeling.
*   **Mining Large-Scale Reanalysis**: Using data mining techniques to extract spatio-temporal features from MESAN's multi-decadal meteorological cubes.
*   **Physics-Informed Data Fusion**: Ensuring that derived parameters (like SWE) respect the physical water balance while benefiting from the high resolution of imaging data.

## 3. Objectives & Phase 1 Scope
### 3.1 Primary Objectives (HydroImaging Alignment)
1.  **Multi-Modal Ingestion & Alignment**: Synchronize disparate data streams into a unified spatio-temporal grid (ETRS89-LAEA).
    *   **Imaging/Gridded**: MESAN (Meteorological cubes), FMI (Satellite snow products).
    *   **In-Situ/Tabular**: SMHI (Station obs), Syke (Water quality/Discharge).
2.  **Benchmark Creation**: Develop a curated, "clean" dataset specifically designed for training and validating **Foundation Models (LLMs/VLMs)** in the hydrological domain.
3.  **Advanced Parameter Derivation**: Apply "Mining" techniques to derive:
    *   **Downscaled SWE**: Using imaging-based proxies to interpolate sparse station data.
    *   **Gap-Filled Water Quality**: Utilizing satellite turbidity "images" to fill temporal gaps in Syke's field observations.

## 4. Methodology & Technical Approach
### 4.1 Scalable Pipeline & Data Mining
*   **Spatial-Temporal Fusion**: Using `Xarray` and `RioXarray` to stack 2D imaging data with point-source observations, creating 4D (x, y, z, t) environmental cubes.
*   **Feature Engineering**: Extraction of morphological and topological features from terrain imaging to improve runoff predictions.
*   **Reproducibility**: A Makefile-driven orchestration ensures that the entire "data mining" process—from raw API ingestion to final NetCDF generation—is verifiable and extensible.

## 5. Timeline & Milestones (HydroImaging 2026)
| Milestone | Description | Deadline |
| :--- | :--- | :--- |
| **M1: Data Scaffolding** | Modular extraction for SMHI, MESAN, FMI, and Syke. | April 30, 2026 |
| **M2: Imaging-InSitu Fusion** | Spatio-temporal alignment of MESAN cubes with station data. | May 05, 2026 |
| **M3: Paper Submission** | Submission to ICIP 2026 / HydroImaging Workshop. | May 13, 2026 |
| **M4: Validation** | Benchmarking derived SWE against independent EO products. | June 2026 |
| **M5: Workshop** | Presentation in Tampere, Finland. | Sept 13-17, 2026 |

## 6. Impact & Future "Foundation" Vision
This project serves as a cornerstone for the development of **Hydrological Foundation Models**. By providing a high-quality, multi-modal Nordic benchmark, we enable the community to move beyond site-specific models toward generalizable, imaging-driven environmental forecasting.

