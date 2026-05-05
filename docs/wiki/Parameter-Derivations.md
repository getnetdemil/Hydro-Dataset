# Parameter Derivations

All functions are in `src/derivation/hydrological_parameters.py` and accept
`xr.Dataset` with `(station_id, time)` dims. See `docs/DERIVATION_METHODS.md`
for full formulas and pilot results.

---

## Snow Water Equivalent (SWE)
**`calculate_swe_sturm(snow_depth_ds, temp_history_ds, snow_class='taiga')`**

Sturm et al. (2010) seasonal density model. Six snow classes; **taiga** is
the default for Nordic boreal domain (ρ₀ = 0.217, ρ_max = 0.490 g/cm³).

Outputs: `swe` [mm], `snow_density` [g/cm³]

Pilot (Dalarna 2023–24): peak SWE 185 mm; R = 0.78 vs ERA5-Land.

---

## Gridded SWE / Snow Depth
**`harmonize_point_to_grid(station_ds, variable, grid_resolution_m=2500.0)`**
(in `src/processing/alignment.py`)

Ordinary Kriging with spherical variogram onto 2.5 km LAEA EPSG:3035 grid.
Time steps with < 3 valid stations → NaN.

Script: `scripts/build_swe_grid.py`

---

## Snow Phenology
**`calculate_snow_phenology(snow_depth_ds)`**

Per-station seasonal scalars: `snow_onset_doy`, `melt_out_doy`,
`snow_cover_duration` [days], `peak_swe` [mm], `peak_swe_doy`.

Pilot: onset DOY ~30, melt-out ~189, duration ~161 days, peak SWE 120 mm mean.

---

## Snowmelt and Accumulation Rates
**`calculate_snowmelt_dynamics(swe_ds)`**

Daily SWE finite differences split by sign:
- `snowmelt_rate` [mm/day] — positive on melt days, NaN otherwise
- `swe_accumulation_rate` [mm/day] — positive on accumulation days, NaN otherwise

Pilot: mean melt rate 6.2 mm/day, max 50 mm/day.

---

## Degree-Day Melt Factor (DDM)
**`calculate_degree_day_factor(swe_ds, temp_ds)`**

`DDM = snowmelt_rate / temp_mean` [mm °C⁻¹ day⁻¹], per-station median
over qualifying melt days (melt ≥ 0.5 mm/day, temp > 0°C).

Pilot: DDM 2.5–4.1 mm/°C/day. Bridges temperature forcing to melt prediction.

---

## Rain-on-Snow Detection
**`detect_rain_on_snow(snow_depth_ds, temp_ds, precip_ds)`**

Flag = 1 when: snow depth > 0.01 m AND temp > 0°C AND precip > 0.5 mm/day.
High-impact for flood risk; rare-event label for Foundation Model training.

Pilot: 35 ROS station-days in Dalarna 2023–24.

---

## Freeze-Thaw Cycles
**`calculate_freeze_thaw_cycles(temp_ds)`**

Count of 0°C sign changes in daily `temp_mean` per station.
Proxy for snowpack metamorphism rate and ice lens formation.

Pilot: mean 4, max 34 crossings per station over the season.

---

## Snowpack Cold Content
**`calculate_cold_content(snow_depth_ds, temp_ds)`**

`CC = ρ_ice × c_ice × h_snow × |min(T_air, 0)|` [MJ m⁻²]

Controls when melt can begin; zero when no snow or T_air > 0°C.

Pilot: max 18.3 MJ/m², mean (snow-present) 2.6 MJ/m².

---

## Runoff Potential
**`calculate_runoff_potential(precip_ds, soil_moisture_ds)`**

API recession model:
```
API_t = 0.85 × API_{t-1} + P_t
RC_t  = API_t / (API_t + 50 mm)
Q_t   = P_t × RC_t
```

Outputs: `runoff_potential` [mm/day], `runoff_coeff` [-], `api` [mm].
Direct soil moisture measurements nudge API when available.

---

## Planned (M7+)
- **Interannual SWE anomaly** — requires multi-year baseline (2015–2024 data now available)
- **Hypsometric SWE distribution** — needs DEM (SRTM/Copernicus)
- **Snow cover fraction validation** — FMI H-SAF vs kriged SWE extent
- **Snowmelt-runoff lag** — melt rate + HydObs discharge (extractor ready)
- **Water Quality Index** — Syke nutrients + FMI turbidity (M5)
