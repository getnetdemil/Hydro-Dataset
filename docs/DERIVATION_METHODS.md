# Parameter Derivation Methodologies

## Methodology Overview

The Hydro-Dataset project derives new parameters for snow hydrology, water resources, and water quality by fusing multi-modal data.

## Proposed Derivations

1. **Snow Water Equivalent (SWE)**
   - **Input**: SMHI/FMI Snow Depth + MESAN Temperature history + Syke Snow density samples.
   - **Method**: Empirical formulas (e.g., Sturm et al., 2010) or ML-based regression.

2. **Surface Runoff Coefficients**
   - **Input**: MESAN Precipitation + Syke Discharge + Land cover data.
   - **Method**: Water balance modeling at catchments.

3. **Water Quality Index**
   - **Input**: Syke Nutrient levels + FMI Satellite turbidity estimates.
   - **Method**: Spatio-temporal kriging and normalization.

## Implementation Standard

All derivation scripts must include:
- A clear description of the formula or model used.
- Citations to the original research/paper.
- Input data requirements (variables, units, resolution).
