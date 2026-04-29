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
