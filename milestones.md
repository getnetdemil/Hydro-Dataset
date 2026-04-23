# Project Timeline & Milestones: Hydro-Dataset (HydroImaging 2026)

**Submission Deadline**: May 13, 2026  
**Workshop Dates**: September 13–17, 2026 (Tampere, Finland)

---

## 📅 Roadmap Overview

This timeline focuses on the high-intensity period leading up to the paper submission.

### Phase 1: Data Infrastructure & Integration (April 23 – April 30)
*Focus: Completing the modular pipeline to ensure high-fidelity multi-modal ingestion.*

| Milestone | Key Tasks | Target Date |
| :--- | :--- | :--- |
| **M1: Source Readiness** | Finalize extraction logic for SMHI (MetObs, HydObs, HYPE), FMI (Weather, Marine), Syke, and MESAN. | April 26 |
| **M2: Harmonization** | Implement standardized reprojection to ETRS89-LAEA and temporal alignment. | April 28 |
| **M3: Initial Merge** | Successful generation of a single versioned NetCDF file for a pilot region. | April 30 |

### Phase 2: Parameter Derivation & Mining (May 01 – May 07)
*Focus: Deriving novel research variables using data mining and imaging-in-situ fusion.*

| Milestone | Key Tasks | Target Date |
| :--- | :--- | :--- |
| **M4: SWE Derivation** | Implement and validate the Sturm et al. SWE model across the Nordic domain. | May 03 |
| **M5: Water Quality Proxy** | Integrate FMI satellite turbidity with Syke field nutrient data. | May 05 |
| **M6: Dataset Version 1.0** | Finalize the full 2015-2024 dataset for benchmarking. | May 07 |

### Phase 3: Validation & Paper Drafting (May 08 – May 13)
*Focus: Empirical verification and final workshop submission.*

| Milestone | Key Tasks | Target Date |
| :--- | :--- | :--- |
| **M7: Benchmarking** | Calculate RMSE/KGE scores against field "Gold Standards." | May 09 |
| **M8: Visual Analytics** | Generate high-resolution spatial maps and time-series figures for the paper. | May 11 |
| **M9: Submission** | Finalize LaTeX/PDF and submit to HydroImaging 2026. | **May 13** |

---

## 🛠️ Critical Success Factors
1.  **Reproducibility**: Ensure all scripts run via `make build-dataset` by the M6 deadline.
2.  **Modularity**: Adhere to the `feature/*` branching strategy to prevent merge conflicts during Phase 2.
3.  **Data Integrity**: Continuous validation of NetCDF metadata against CF conventions.

---
**Status**: ACTIVE  
**Last Updated**: April 23, 2026
