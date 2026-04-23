# Parameter Derivations

The core of this project is deriving new parameters from multi-modal inputs.

## Snow Water Equivalent (SWE)
- **Input**: SMHI/FMI Snow Depth + MESAN Temperature history + Syke Snow density samples.
- **Model**: Fusing gridded reanalysis with point-source measurements.

## Surface Runoff Coefficients
- **Input**: MESAN Precipitation + Syke Discharge measurements + Terrain elevation data.
- **Goal**: Create a spatial map of runoff potential across major catchments.

## Water Quality Index (WQI)
- **Input**: Syke Nutrient levels (N, P, Turbidity) + FMI Satellite imagery.
- **Goal**: Interpolate point-source nutrients to a grid for continuous monitoring.
