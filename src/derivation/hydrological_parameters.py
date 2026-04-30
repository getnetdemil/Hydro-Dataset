import numpy as np
import pandas as pd
import xarray as xr

# Sturm et al. (2010) Table 2 — snow class density model coefficients
# ρ in g/cm³, k1 in cm⁻¹, k2 in d⁻¹
# Sturm, M., Taras, B., Liston, G. E., Derksen, C., Jonas, T., & Lea, J. (2010).
# Estimating Snow Water Equivalent Using Snow Depth Data and Climate Classes.
# Journal of Hydrometeorology, 11(6), 1380–1394. https://doi.org/10.1175/2010JHM1202.1
STURM_CLASSES = {
    'alpine':    {'rho_0': 0.2497, 'rho_max': 0.5975, 'k1': 0.0012, 'k2': 0.0038},
    'maritime':  {'rho_0': 0.2579, 'rho_max': 0.5979, 'k1': 0.0010, 'k2': 0.0038},
    'prairie':   {'rho_0': 0.2578, 'rho_max': 0.5940, 'k1': 0.0016, 'k2': 0.0031},
    'tundra':    {'rho_0': 0.2172, 'rho_max': 0.3633, 'k1': 0.0000, 'k2': 0.0155},
    'taiga':     {'rho_0': 0.2172, 'rho_max': 0.2179, 'k1': 0.0000, 'k2': 0.0150},
    'ephemeral': {'rho_0': 0.2172, 'rho_max': 0.2400, 'k1': 0.0000, 'k2': 0.0019},
}

# Nordic boreal forest snowpack class (Dalarna, Sweden is predominantly Taiga)
NORDIC_SNOW_CLASS = 'taiga'


def _day_of_season(times: pd.DatetimeIndex, season_start_month: int = 10) -> np.ndarray:
    """Days elapsed since the most recent season-start month (Oct 1 by default), clipped ≥ 0."""
    dos = np.array([
        (t - pd.Timestamp(
            t.year if t.month >= season_start_month else t.year - 1,
            season_start_month, 1
        )).days
        for t in times
    ], dtype=float)
    return np.maximum(dos, 0.0)


def calculate_swe_sturm(
    snow_depth_ds: xr.Dataset,
    temp_history_ds: xr.Dataset,
    snow_class: str = NORDIC_SNOW_CLASS,
    season_start_month: int = 10,
) -> xr.Dataset:
    """
    Sturm et al. (2010) seasonal snow density model → SWE.

    Formula:
        ρ(h, DOS) = (ρ_max − ρ_0) × [1 − exp(−k1·h_cm − k2·DOS)] + ρ_0
        SWE (mm)  = ρ (g/cm³) × h (m) × 1000

    DOS = days elapsed since season start (season_start_month, day 1).
    temp_history_ds is accepted for API compatibility but unused here;
    seasonal compaction is captured by DOS alone per the Sturm formulation.

    Returns the input dataset with two new variables appended:
        swe          [mm]    — Snow Water Equivalent
        snow_density [g/cm³] — Modelled bulk snow density
    """
    if snow_class not in STURM_CLASSES:
        raise ValueError(
            f"Unknown snow class '{snow_class}'. Valid options: {list(STURM_CLASSES)}"
        )

    coeffs = STURM_CLASSES[snow_class]
    h_m = snow_depth_ds['snow_depth']   # DataArray (station_id × time), units: m
    h_cm = h_m * 100.0                  # m → cm (k1 coefficient is in cm⁻¹)

    times = pd.DatetimeIndex(snow_depth_ds['time'].values)
    dos = _day_of_season(times, season_start_month)
    dos_da = xr.DataArray(dos, coords={'time': snow_depth_ds['time']}, dims=['time'])

    rho_s = (
        (coeffs['rho_max'] - coeffs['rho_0'])
        * (1.0 - np.exp(-coeffs['k1'] * h_cm - coeffs['k2'] * dos_da))
        + coeffs['rho_0']
    )  # g/cm³, broadcasts (station_id × time) × (time,)

    swe_mm = rho_s * h_m * 1000.0  # g/cm³ × m × 1000 = mm

    swe_ds = snow_depth_ds.copy()

    swe_ds['swe'] = swe_mm
    swe_ds['swe'].attrs = {
        'standard_name': 'liquid_water_content_of_surface_snow',
        'long_name': 'Snow Water Equivalent (Sturm et al. 2010)',
        'units': 'mm',
        'source': (
            f'Derived: Sturm et al. (2010) J. Hydromet. 11(6), '
            f'snow_class={snow_class}, season_start_month={season_start_month}'
        ),
        '_FillValue': float('nan'),
    }

    swe_ds['snow_density'] = rho_s
    swe_ds['snow_density'].attrs = {
        'long_name': 'Modelled bulk snow density (Sturm et al. 2010)',
        'units': 'g cm-3',
        'source': (
            f'Derived: Sturm et al. (2010) J. Hydromet. 11(6), '
            f'snow_class={snow_class}'
        ),
        '_FillValue': float('nan'),
    }

    return swe_ds


def calculate_runoff_potential(precip_ds: xr.Dataset, soil_moisture_ds: xr.Dataset) -> xr.Dataset:
    """
    Stub for Runoff Potential calculation fusing precipitation and soil moisture.
    """
    # Placeholder: Runoff = Precip * Soil_Moisture_Factor
    return precip_ds


# ---------------------------------------------------------------------------
# Helper functions for phenology detection
# ---------------------------------------------------------------------------

def _first_persistent_snow_idx(snow_flag: np.ndarray, min_consecutive: int) -> int:
    """Index of first day in first persistent-snow run; -1 if none found."""
    n = len(snow_flag)
    for i in range(n - min_consecutive + 1):
        if np.all(snow_flag[i:i + min_consecutive]):
            return i
    return -1


def _last_snow_idx(snow_flag: np.ndarray) -> int:
    """Index of last True day in snow_flag; -1 if none."""
    idxs = np.where(snow_flag)[0]
    return int(idxs[-1]) if len(idxs) > 0 else -1


# ---------------------------------------------------------------------------
# Phenology — per-station seasonal scalars
# ---------------------------------------------------------------------------

def calculate_snow_phenology(
    snow_depth_ds: xr.Dataset,
    depth_threshold: float = 0.01,
    min_consecutive: int = 3,
) -> xr.Dataset:
    """
    Per-station seasonal snow phenology metrics.

    Args:
        snow_depth_ds:   Dataset with 'snow_depth' [m] and optionally 'swe' [mm];
                         dims (station_id, time).
        depth_threshold: Minimum snow depth (m) to classify a day as snow-covered.
        min_consecutive: Consecutive snow days required to confirm onset.

    Returns:
        Dataset indexed by station_id with:
            snow_onset_doy       — day-of-season of first persistent onset (Oct 1 = 0)
            melt_out_doy         — day-of-season of last snow day
            snow_cover_duration  — days from onset to melt-out inclusive
            peak_swe             — maximum SWE [mm]  (NaN if 'swe' absent)
            peak_swe_doy         — day-of-season of peak SWE (NaN if 'swe' absent)
    """
    times = pd.DatetimeIndex(snow_depth_ds['time'].values)
    n_stations = snow_depth_ds.sizes['station_id']
    station_ids = snow_depth_ds['station_id'].values
    dos = _day_of_season(times).astype(int)

    onset_doy    = np.full(n_stations, np.nan)
    meltout_doy  = np.full(n_stations, np.nan)
    duration     = np.full(n_stations, np.nan)
    peak_swe_val = np.full(n_stations, np.nan)
    peak_swe_doy = np.full(n_stations, np.nan)
    has_swe = 'swe' in snow_depth_ds

    for s in range(n_stations):
        depth = snow_depth_ds['snow_depth'].isel(station_id=s).values.astype(float)
        snow_flag = depth > depth_threshold

        onset_idx = _first_persistent_snow_idx(snow_flag, min_consecutive)
        last_idx  = _last_snow_idx(snow_flag)

        if onset_idx >= 0:
            onset_doy[s] = dos[onset_idx]
        if last_idx >= 0:
            meltout_doy[s] = dos[last_idx]
        if onset_idx >= 0 and last_idx >= onset_idx:
            duration[s] = last_idx - onset_idx + 1

        if has_swe:
            swe = snow_depth_ds['swe'].isel(station_id=s).values.astype(float)
            valid_swe = np.where(snow_flag, swe, np.nan)
            if not np.all(np.isnan(valid_swe)):
                peak_idx = int(np.nanargmax(valid_swe))
                peak_swe_val[s] = valid_swe[peak_idx]
                peak_swe_doy[s] = dos[peak_idx]

    out = xr.Dataset(
        {
            'snow_onset_doy':      ('station_id', onset_doy),
            'melt_out_doy':        ('station_id', meltout_doy),
            'snow_cover_duration': ('station_id', duration),
            'peak_swe':            ('station_id', peak_swe_val),
            'peak_swe_doy':        ('station_id', peak_swe_doy),
        },
        coords={'station_id': station_ids},
    )
    out['snow_onset_doy'].attrs = {
        'long_name': 'Day-of-season of first persistent snow cover onset',
        'units': 'days since season start (Oct 1)',
        'depth_threshold_m': depth_threshold,
        'min_consecutive_days': min_consecutive,
    }
    out['melt_out_doy'].attrs = {
        'long_name': 'Day-of-season of last snow cover day',
        'units': 'days since season start (Oct 1)',
    }
    out['snow_cover_duration'].attrs = {
        'long_name': 'Total snow cover duration (onset to melt-out, inclusive)',
        'units': 'days',
    }
    out['peak_swe'].attrs = {
        'long_name': 'Maximum Snow Water Equivalent during season',
        'units': 'mm',
    }
    out['peak_swe_doy'].attrs = {
        'long_name': 'Day-of-season of peak SWE',
        'units': 'days since season start (Oct 1)',
    }
    return out


# ---------------------------------------------------------------------------
# Melt dynamics — station × time series
# ---------------------------------------------------------------------------

def calculate_snowmelt_dynamics(swe_ds: xr.Dataset) -> xr.Dataset:
    """
    Daily snowmelt and accumulation rates from SWE finite differences.

    Both outputs are NaN on the first time step and on days when the signal
    moves in the opposite direction.

    Args:
        swe_ds: Dataset with 'swe' [mm]; dims (station_id, time).

    Returns:
        Input dataset augmented with:
            snowmelt_rate         [mm day-1] — positive on melt days, else NaN
            swe_accumulation_rate [mm day-1] — positive on accumulation days, else NaN
    """
    swe = swe_ds['swe'].values.astype(float)
    dswe = np.diff(swe, axis=1)   # shape (station_id, time-1)

    melt_rate  = np.full_like(swe, np.nan)
    accum_rate = np.full_like(swe, np.nan)

    melt_rate[:, 1:]  = np.where(dswe < 0, -dswe, np.nan)
    accum_rate[:, 1:] = np.where(dswe > 0,  dswe, np.nan)

    out = swe_ds.copy()
    out['snowmelt_rate'] = xr.DataArray(
        melt_rate, dims=swe_ds['swe'].dims,
        attrs={
            'long_name': 'Daily snowmelt rate (SWE decrease)',
            'units': 'mm day-1',
            'positive': 'melt (SWE loss)',
        },
    )
    out['swe_accumulation_rate'] = xr.DataArray(
        accum_rate, dims=swe_ds['swe'].dims,
        attrs={
            'long_name': 'Daily SWE accumulation rate',
            'units': 'mm day-1',
        },
    )
    return out


# ---------------------------------------------------------------------------
# Degree-day melt factor — per-station scalar
# ---------------------------------------------------------------------------

def calculate_degree_day_factor(
    swe_ds: xr.Dataset,
    temp_ds: xr.Dataset,
    temp_var: str = 'temp_mean',
    min_melt_rate: float = 0.5,
) -> xr.Dataset:
    """
    Per-station degree-day melt factor (DDM) calibrated against SWE loss.

        DDM = snowmelt_rate / temp_mean    [mm °C-1 day-1]

    Only days where snowmelt_rate >= min_melt_rate AND temp_mean > 0 qualify.
    Returns per-station median DDM; NaN if fewer than 3 qualifying days.

    Args:
        swe_ds:         Dataset with 'swe' [mm]; dims (station_id, time).
        temp_ds:        Dataset with temp_var [°C]; same dims.
        temp_var:       Temperature variable name (default 'temp_mean').
        min_melt_rate:  Minimum melt rate [mm/day] to include in calibration.

    Returns:
        Dataset indexed by station_id with:
            degree_day_factor  float [mm °C-1 day-1]
            ddm_n_days         int   — qualifying melt days used
    """
    swe_dyn   = calculate_snowmelt_dynamics(swe_ds)
    melt_rate = swe_dyn['snowmelt_rate'].values.astype(float)
    temp      = temp_ds[temp_var].values.astype(float)

    n_stations = swe_ds.sizes['station_id']
    ddm    = np.full(n_stations, np.nan)
    n_days = np.zeros(n_stations, dtype=int)

    for s in range(n_stations):
        valid = (
            ~np.isnan(melt_rate[s])
            & (melt_rate[s] >= min_melt_rate)
            & (temp[s] > 0)
        )
        if valid.sum() >= 3:
            ddm[s]    = float(np.nanmedian(melt_rate[s][valid] / temp[s][valid]))
            n_days[s] = int(valid.sum())

    out = xr.Dataset(
        {
            'degree_day_factor': ('station_id', ddm),
            'ddm_n_days':        ('station_id', n_days),
        },
        coords={'station_id': swe_ds['station_id'].values},
    )
    out['degree_day_factor'].attrs = {
        'long_name': 'Degree-day melt factor (median over qualifying melt days)',
        'units': 'mm degree_C-1 day-1',
        'min_melt_rate_mm_day': min_melt_rate,
    }
    out['ddm_n_days'].attrs = {
        'long_name': 'Number of qualifying melt days used for DDM calibration',
        'units': '1',
    }
    return out


# ---------------------------------------------------------------------------
# Rain-on-snow detection — station × time flag
# ---------------------------------------------------------------------------

def detect_rain_on_snow(
    snow_depth_ds: xr.Dataset,
    temp_ds: xr.Dataset,
    precip_ds: xr.Dataset,
    depth_threshold: float = 0.01,
    temp_threshold: float = 0.0,
    precip_threshold: float = 0.5,
    temp_var: str = 'temp_mean',
    precip_var: str = 'precip',
) -> xr.Dataset:
    """
    Rain-on-snow (ROS) event flag.

    Flagged when: snow_depth > depth_threshold
               AND temp_mean  > temp_threshold
               AND precip     > precip_threshold

    Args:
        snow_depth_ds:    Dataset with 'snow_depth' [m].
        temp_ds:          Dataset with temp_var [°C]; same dims.
        precip_ds:        Dataset with precip_var [mm]; same dims.
        depth_threshold:  Minimum snow depth (m) to be snow-covered.
        temp_threshold:   Minimum temperature (°C) to classify precip as rain.
        precip_threshold: Minimum precip (mm/day) to count as a rain event.
        temp_var:         Temperature variable name.
        precip_var:       Precipitation variable name.

    Returns:
        Input dataset augmented with 'rain_on_snow' (int8, 0/1).
    """
    snow   = snow_depth_ds['snow_depth'].values > depth_threshold
    temp   = temp_ds[temp_var].values > temp_threshold
    precip = precip_ds[precip_var].values > precip_threshold

    ros = (snow & temp & precip).astype(np.int8)

    out = snow_depth_ds.copy()
    out['rain_on_snow'] = xr.DataArray(
        ros, dims=snow_depth_ds['snow_depth'].dims,
        attrs={
            'long_name': 'Rain-on-snow event flag',
            'flag_values': '0, 1',
            'flag_meanings': 'no_event rain_on_snow_event',
            'units': '1',
            'depth_threshold_m': depth_threshold,
            'temp_threshold_degC': temp_threshold,
            'precip_threshold_mm': precip_threshold,
        },
    )
    return out


# ---------------------------------------------------------------------------
# Freeze-thaw cycles — per-station scalar
# ---------------------------------------------------------------------------

def calculate_freeze_thaw_cycles(
    temp_ds: xr.Dataset,
    temp_var: str = 'temp_mean',
) -> xr.Dataset:
    """
    Per-station count of freeze-thaw (0°C crossing) events.

    A crossing is counted each time the sign of daily temp_mean changes
    between consecutive non-NaN days. Days exactly at 0°C inherit the
    previous day's sign to avoid spurious double-counting.

    Args:
        temp_ds:  Dataset with temp_var [°C]; dims (station_id, time).
        temp_var: Temperature variable name (default 'temp_mean').

    Returns:
        Dataset indexed by station_id with:
            freeze_thaw_count  int — 0°C crossings over the full period
    """
    temp = temp_ds[temp_var].values.astype(float)
    n_stations = temp_ds.sizes['station_id']
    counts = np.zeros(n_stations, dtype=int)

    for s in range(n_stations):
        t = temp[s]
        valid_mask = ~np.isnan(t)
        t_clean = t[valid_mask]
        if len(t_clean) < 2:
            continue
        signs = np.sign(t_clean)
        for i in range(1, len(signs)):
            if signs[i] == 0:
                signs[i] = signs[i - 1] if signs[i - 1] != 0 else 1
        counts[s] = int(np.sum(np.diff(signs) != 0))

    out = xr.Dataset(
        {'freeze_thaw_count': ('station_id', counts)},
        coords={'station_id': temp_ds['station_id'].values},
    )
    out['freeze_thaw_count'].attrs = {
        'long_name': 'Number of freeze-thaw (0 degC crossing) events in season',
        'units': '1',
    }
    return out


# ---------------------------------------------------------------------------
# Cold content — station × time series
# ---------------------------------------------------------------------------

def calculate_cold_content(
    snow_depth_ds: xr.Dataset,
    temp_ds: xr.Dataset,
    temp_var: str = 'temp_mean',
) -> xr.Dataset:
    """
    Snowpack cold content proxy.

    Energy required to bring the snowpack to 0°C:
        CC = -ρ_ice × c_ice × h_snow × min(T_air, 0)   [MJ m-2]

    T_air is used as a proxy for bulk snow temperature — valid for
    cold continental (taiga) snowpacks where pack temperature tracks air.
    ρ_ice = 917 kg m-3, c_ice = 2090 J kg-1 K-1.

    Returns zero where snow_depth = 0.

    Args:
        snow_depth_ds: Dataset with 'snow_depth' [m]; dims (station_id, time).
        temp_ds:       Dataset with temp_var [°C]; same dims.
        temp_var:      Temperature variable name (default 'temp_mean').

    Returns:
        Input dataset augmented with 'cold_content' [MJ m-2].
    """
    RHO_ICE = 917.0   # kg m-3
    C_ICE   = 2090.0  # J kg-1 K-1

    depth  = snow_depth_ds['snow_depth'].values.astype(float)
    temp   = temp_ds[temp_var].values.astype(float)
    t_snow = np.minimum(temp, 0.0)

    cc = (-RHO_ICE * C_ICE * depth * t_snow) * 1e-6   # J m-2 → MJ m-2
    cc = np.where(depth > 0, cc, 0.0)

    out = snow_depth_ds.copy()
    out['cold_content'] = xr.DataArray(
        cc, dims=snow_depth_ds['snow_depth'].dims,
        attrs={
            'long_name': 'Snowpack cold content (energy deficit to 0 degC)',
            'units': 'MJ m-2',
            'positive': 'energy required for melt initiation',
            'source': 'rho_ice=917 kg m-3, c_ice=2090 J kg-1 K-1, T_snow=min(temp_mean, 0)',
        },
    )
    return out
