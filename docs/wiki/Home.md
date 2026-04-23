# Welcome to the Hydro-Dataset Wiki

This wiki serves as the central knowledge base for the **Hydro-Dataset** project, developed for the [Workshop on Mining Imaging Data for Hydrological and Environmental Modelling (HydroImaging 2026)](https://hydroimaging.github.io/).

## Overview
The Hydro-Dataset project aims to unify multi-modal data from the Nordic region (Sweden and Finland) to support advanced research in snow hydrology, water resources, and water quality.

### Core Goals
- **Harmonization**: Unify disparate data sources from SMHI, MESAN, FMI, and Syke.
- **Multi-Modal Fusion**: Bridge the gap between imaging sensors (satellite/reanalysis) and in-situ hydrological observations.
- **Foundation-Ready Benchmarking**: Create high-quality datasets for training next-generation LLMs and VLMs.

## Wiki Navigation
1.  **[Data Sources](Data-Sources.md)**: Details on APIs, formats (GRIB2, NetCDF, OData), and providers.
2.  **[Parameter Derivations](Parameter-Derivations.md)**: Methodology for Snow Water Equivalent (SWE), Runoff Potential, and more.
3.  **[Foundation Model Benchmarks](Foundation-Model-Benchmarks.md)**: How we curate data for ML-based research.
4.  **[Reproducibility Guide](Reproducibility-Guide.md)**: Instructions on running the script-driven pipeline.

## Collaboration
We follow a strict [GitHub Collaboration Rule](../../github_rule.md). All feature development should occur in `feature/*` branches and merge into `experiment` before reaching `main`.

---
**Get Involved**: Check our [50+ Open Issues](https://github.com/getnetdemil/Hydro-Dataset/issues) to start contributing!
