# Parameter Derivation Methodologies

All derivation functions live in `src/derivation/hydrological_parameters.py`.
Every output variable carries CF-compliant `attrs` (standard_name, units, source).

---

## Implemented Derivations

### 1. Snow Water Equivalent (SWE)
**Function**: `calculate_swe_sturm(snow_depth_ds, temp_history_ds, snow_class='taiga')`

Sturm et al. (2010) seasonal density model applied to observed snow depth:

```
ρ(h, DOS) = (ρ_max − ρ_0) × [1 − exp(−k₁·h_cm − k₂·DOS)] + ρ_0
SWE [mm]  = ρ [g/cm³] × h [m] × 1000
```

- DOS = days since Oct 1 (season start)
- Six snow climate classes supported; **taiga** used for Nordic boreal domain
- Taiga constants: ρ₀ = 0.217, ρ_max = 0.490 g/cm³, k₁ = 0.0, k₂ = 0.015

**Outputs**: `swe` [mm], `snow_density` [g/cm³]
**Citation**: Sturm et al. (2010), J. Hydrometeorology 11(6), 1380–1394

**Pilot validation (Dalarna 2023–24)**: RMSE = 293 mm vs ERA5-Land, Pearson R = 0.78,
Bias = −262 mm (ERA5-Land overestimates SWE in Scandinavia — see Mudryk et al. 2015)

---

### 2. Gridded SWE / Snow Depth (Kriging Upscale)
**Function**: `harmonize_point_to_grid(station_ds, variable, grid_resolution_m=2500.0)`
(in `src/processing/alignment.py`)

Ordinary Kriging with a spherical variogram interpolates station-point observations onto a
regular LAEA EPSG:3035 grid. Time steps with fewer than 3 valid stations are filled with NaN.

- Grid extent: station bounding box + 10 km padding
- Default resolution: 2500 m (matches MESAN)
- Pilot output: 58 × 68 grid (3 944 cells), peak SWE 185 mm, peak depth 0.848 m

**Outputs**: gridded `snow_depth` and `swe` on (y, x, time) LAEA grid
**Script**: `scripts/build_swe_grid.py`

---

### 3. Snow Phenology
**Function**: `calculate_snow_phenology(snow_depth_ds, depth_threshold=0.01, min_consecutive=3)`

Per-station seasonal metrics derived from the snow_depth time series:

| Output variable | Description | Units |
|---|---|---|
| `snow_onset_doy` | Day-of-season of first persistent snow (Oct 1 = 0) | days |
| `melt_out_doy` | Day-of-season of last snow day | days |
| `snow_cover_duration` | Days from onset to melt-out inclusive | days |
| `peak_swe` | Maximum SWE during season (requires `swe` in input) | mm |
| `peak_swe_doy` | Day-of-season of peak SWE | days |

**Pilot results (Dalarna 2023–24, 22 stations)**:
- Onset: DOY 29–33 (late October)
- Melt-out: DOY 166–207 (mid-March to late April)
- Duration: 156–178 days (mean 161)
- Peak SWE: 70–187 mm (mean 120 mm) at DOY ~124 (late January)

---

### 4. Snowmelt and Accumulation Rates
**Function**: `calculate_snowmelt_dynamics(swe_ds)`

Daily finite differences of SWE, split into melt and accumulation signals:

```
snowmelt_rate [mm/day]         = max(0, −dSWE/dt)   on melt days, else NaN
swe_accumulation_rate [mm/day] = max(0, +dSWE/dt)   on accum days, else NaN
```

**Pilot results (Dalarna 2023–24)**:
- 955 melt station-days, mean melt rate 6.2 mm/day, max 50 mm/day
- Mean accumulation rate 3.2 mm/day

---

### 5. Degree-Day Melt Factor (DDM)
**Function**: `calculate_degree_day_factor(swe_ds, temp_ds, min_melt_rate=0.5)`

Calibrated temperature-index melt parameter:

```
DDM = snowmelt_rate / temp_mean    [mm °C⁻¹ day⁻¹]
```

Computed as the per-station median over days where `snowmelt_rate ≥ 0.5 mm/day`
and `temp_mean > 0°C`. Requires ≥ 3 qualifying days.

**Pilot results (Dalarna 2023–24)**: DDM 2.5–4.1 mm/°C/day (3 of 22 stations had
sufficient warm melt days in this short pilot window; full range expected with 2015–2024 data).

---

### 6. Rain-on-Snow Detection
**Function**: `detect_rain_on_snow(snow_depth_ds, temp_ds, precip_ds)`

Binary event flag raised when all three conditions hold simultaneously:

```
snow_depth > 0.01 m  AND  temp_mean > 0°C  AND  precip > 0.5 mm/day
```

Thresholds are configurable. ROS events are high-impact for flood risk and snowpack
metamorphism; they serve as rare-event labels for Foundation Model training.

**Pilot results (Dalarna 2023–24)**: 35 ROS station-days detected.

---

### 7. Freeze-Thaw Cycles
**Function**: `calculate_freeze_thaw_cycles(temp_ds)`

Count of 0°C sign changes in the daily `temp_mean` time series per station.
NaN days are skipped; exact-zero days inherit the previous day's sign.

**Pilot results (Dalarna 2023–24)**: mean 4, max 34 crossings per station over the season.

---

### 8. Snowpack Cold Content
**Function**: `calculate_cold_content(snow_depth_ds, temp_ds)`

Energy deficit required to bring the snowpack to 0°C:

```
CC = ρ_ice × c_ice × h_snow × |min(T_air, 0)|    [MJ m⁻²]
```

ρ_ice = 917 kg m⁻³, c_ice = 2090 J kg⁻¹ K⁻¹. Air temperature is used as a
bulk snow temperature proxy (valid for cold continental taiga snowpacks).
Returns zero where snow_depth = 0.

**Pilot results (Dalarna 2023–24)**: max 18.3 MJ/m², mean (snow-present) 2.6 MJ/m².

---

### 9. Runoff Potential (API Method)
**Function**: `calculate_runoff_potential(precip_ds, soil_moisture_ds)`

Antecedent Precipitation Index (API) daily runoff estimation:

```
API_t = k × API_{t−1} + P_t      (k = 0.85 recession constant)
RC_t  = API_t / (API_t + S)       (S = 50 mm saturation deficit)
Q_t   = P_t × RC_t                [mm/day]
```

If `soil_moisture_ds` contains direct soil moisture measurements, they nudge the
API at available time steps. Both k and S are configurable.

**Outputs**: `runoff_potential` [mm/day], `runoff_coeff` [-], `api` [mm]
**Nordic subset results**: mean RC 0.23, max daily runoff 51 mm — physically plausible.

---

## Implementation Standards

- All functions accept `xr.Dataset` with `(station_id, time)` dims and return an augmented dataset.
- Variable names in the pilot dataset: `snow_depth` [m], `temp_mean` [°C], `precip` [mm].
- Phenology, DDM, freeze-thaw, and peak-SWE functions return per-station scalars (station_id dim only).
- Time-series functions (melt dynamics, ROS, cold content) return (station_id, time) arrays.
- All output variables include: `long_name`, `units`, `source` in attrs.

## Citation Requirements

Any derivation added to this module must include:
- Formula with variable definitions and units
- Citation to original paper (full reference in `Overleaf_manuscript/references.bib`)
- Input variable requirements (name, units, resolution)
