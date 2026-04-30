"""Unit tests for derived snow parameters (phenology, melt dynamics, process)."""
import numpy as np
import pandas as pd
import pytest
import xarray as xr

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from derivation.hydrological_parameters import (
    _first_persistent_snow_idx,
    _last_snow_idx,
    calculate_snow_phenology,
    calculate_snowmelt_dynamics,
    calculate_degree_day_factor,
    detect_rain_on_snow,
    calculate_freeze_thaw_cycles,
    calculate_cold_content,
    calculate_swe_sturm,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_ds(n_stations=2, n_times=30, start='2023-11-01', seed=0):
    """Synthetic dataset with snow_depth, temp_mean, precip, frozen_precip."""
    rng = np.random.default_rng(seed)
    times = pd.date_range(start, periods=n_times, freq='D')
    depth = np.clip(rng.normal(0.3, 0.15, (n_stations, n_times)), 0, None)
    temp  = rng.normal(-5.0, 8.0, (n_stations, n_times))
    precip = np.abs(rng.normal(2.0, 3.0, (n_stations, n_times)))
    return xr.Dataset(
        {
            'snow_depth':    (['station_id', 'time'], depth),
            'temp_mean':     (['station_id', 'time'], temp),
            'precip':        (['station_id', 'time'], precip),
            'frozen_precip': (['station_id', 'time'], precip * 0.5),
        },
        coords={
            'station_id': list(range(n_stations)),
            'time': times,
            'lat': ('station_id', [60.5] * n_stations),
            'lon': ('station_id', [14.0] * n_stations),
        },
    )


def _snow_season_ds():
    """Two-station dataset: station 0 has clear season, station 1 is bare ground."""
    times = pd.date_range('2023-10-01', periods=60, freq='D')
    # Station 0: snow from day 5 to day 50
    d0 = np.zeros(60)
    d0[5:51] = 0.3
    # Station 1: always bare
    d1 = np.zeros(60)
    depth = np.array([d0, d1])
    temp  = np.full((2, 60), -5.0)
    precip = np.zeros((2, 60))
    return xr.Dataset(
        {
            'snow_depth':    (['station_id', 'time'], depth),
            'temp_mean':     (['station_id', 'time'], temp),
            'precip':        (['station_id', 'time'], precip),
            'frozen_precip': (['station_id', 'time'], precip),
        },
        coords={'station_id': [0, 1], 'time': times,
                'lat': ('station_id', [60.5, 60.5]),
                'lon': ('station_id', [14.0, 14.0])},
    )


# ---------------------------------------------------------------------------
# _first_persistent_snow_idx / _last_snow_idx
# ---------------------------------------------------------------------------

def test_first_persistent_start():
    arr = np.array([True, True, True, False])
    assert _first_persistent_snow_idx(arr, min_consecutive=3) == 0


def test_first_persistent_skip_short():
    arr = np.array([True, True, False, True, True, True])
    assert _first_persistent_snow_idx(arr, min_consecutive=3) == 3


def test_first_persistent_none():
    arr = np.array([True, True, False, True, False])
    assert _first_persistent_snow_idx(arr, min_consecutive=3) == -1


def test_last_snow_idx_normal():
    arr = np.array([False, True, True, False])
    assert _last_snow_idx(arr) == 2


def test_last_snow_idx_empty():
    arr = np.array([False, False])
    assert _last_snow_idx(arr) == -1


# ---------------------------------------------------------------------------
# calculate_snow_phenology
# ---------------------------------------------------------------------------

def test_phenology_known_season():
    ds = _snow_season_ds()
    out = calculate_snow_phenology(ds, depth_threshold=0.01, min_consecutive=3)
    # Station 0 onset = day index 5 → DOS = 5; melt-out = index 50 → DOS = 50
    assert float(out['snow_onset_doy'].sel(station_id=0)) == pytest.approx(5.0)
    assert float(out['melt_out_doy'].sel(station_id=0)) == pytest.approx(50.0)
    assert float(out['snow_cover_duration'].sel(station_id=0)) == pytest.approx(46.0)


def test_phenology_bare_station_is_nan():
    ds = _snow_season_ds()
    out = calculate_snow_phenology(ds)
    assert np.isnan(float(out['snow_onset_doy'].sel(station_id=1)))
    assert np.isnan(float(out['melt_out_doy'].sel(station_id=1)))
    assert np.isnan(float(out['snow_cover_duration'].sel(station_id=1)))


def test_phenology_peak_swe_with_swe_variable():
    ds = _snow_season_ds()
    swe_ds = calculate_swe_sturm(ds, ds, snow_class='taiga')
    out = calculate_snow_phenology(swe_ds, depth_threshold=0.01, min_consecutive=3)
    assert not np.isnan(float(out['peak_swe'].sel(station_id=0)))
    assert float(out['peak_swe'].sel(station_id=0)) > 0


def test_phenology_no_swe_gives_nan_peak():
    ds = _snow_season_ds()
    out = calculate_snow_phenology(ds)
    assert np.isnan(float(out['peak_swe'].sel(station_id=0)))


def test_phenology_cf_attrs():
    ds = _snow_season_ds()
    out = calculate_snow_phenology(ds)
    assert 'units' in out['snow_onset_doy'].attrs
    assert 'units' in out['snow_cover_duration'].attrs


# ---------------------------------------------------------------------------
# calculate_snowmelt_dynamics
# ---------------------------------------------------------------------------

def test_melt_rate_positive_on_decrease():
    times = pd.date_range('2024-01-01', periods=4, freq='D')
    swe_vals = np.array([[100.0, 80.0, 60.0, 40.0]])
    ds = xr.Dataset(
        {'swe': (['station_id', 'time'], swe_vals)},
        coords={'station_id': [0], 'time': times},
    )
    out = calculate_snowmelt_dynamics(ds)
    melt = out['snowmelt_rate'].values[0]
    assert np.isnan(melt[0])           # first step is NaN
    assert melt[1] == pytest.approx(20.0)
    assert melt[2] == pytest.approx(20.0)


def test_accum_rate_nan_on_melt_days():
    times = pd.date_range('2024-01-01', periods=3, freq='D')
    swe_vals = np.array([[100.0, 80.0, 60.0]])
    ds = xr.Dataset(
        {'swe': (['station_id', 'time'], swe_vals)},
        coords={'station_id': [0], 'time': times},
    )
    out = calculate_snowmelt_dynamics(ds)
    assert np.isnan(out['swe_accumulation_rate'].values[0, 1])


def test_accum_rate_positive_on_increase():
    times = pd.date_range('2024-01-01', periods=3, freq='D')
    swe_vals = np.array([[50.0, 80.0, 100.0]])
    ds = xr.Dataset(
        {'swe': (['station_id', 'time'], swe_vals)},
        coords={'station_id': [0], 'time': times},
    )
    out = calculate_snowmelt_dynamics(ds)
    assert out['swe_accumulation_rate'].values[0, 1] == pytest.approx(30.0)
    assert np.isnan(out['snowmelt_rate'].values[0, 1])


def test_melt_dynamics_cf_attrs():
    ds = _make_ds(n_stations=1, n_times=10)
    swe_ds = calculate_swe_sturm(ds, ds)
    out = calculate_snowmelt_dynamics(swe_ds)
    assert out['snowmelt_rate'].attrs['units'] == 'mm day-1'
    assert out['swe_accumulation_rate'].attrs['units'] == 'mm day-1'


# ---------------------------------------------------------------------------
# calculate_degree_day_factor
# ---------------------------------------------------------------------------

def test_ddm_positive_on_melt_days():
    times = pd.date_range('2024-03-01', periods=10, freq='D')
    swe_vals  = np.array([[200.0, 190.0, 180.0, 170.0, 160.0,
                           150.0, 140.0, 130.0, 120.0, 110.0]])
    temp_vals = np.array([[3.0, 4.0, 5.0, 4.0, 3.5, 4.5, 5.5, 3.0, 4.0, 5.0]])
    swe_ds  = xr.Dataset({'swe': (['station_id', 'time'], swe_vals)},
                         coords={'station_id': [0], 'time': times})
    temp_ds = xr.Dataset({'temp_mean': (['station_id', 'time'], temp_vals)},
                         coords={'station_id': [0], 'time': times})
    out = calculate_degree_day_factor(swe_ds, temp_ds)
    ddm = float(out['degree_day_factor'].sel(station_id=0))
    assert ddm > 0


def test_ddm_nan_when_no_qualifying_days():
    times = pd.date_range('2024-01-01', periods=5, freq='D')
    swe_vals  = np.array([[100.0, 100.0, 100.0, 100.0, 100.0]])
    temp_vals = np.array([[-5.0, -4.0, -3.0, -2.0, -1.0]])
    swe_ds  = xr.Dataset({'swe': (['station_id', 'time'], swe_vals)},
                         coords={'station_id': [0], 'time': times})
    temp_ds = xr.Dataset({'temp_mean': (['station_id', 'time'], temp_vals)},
                         coords={'station_id': [0], 'time': times})
    out = calculate_degree_day_factor(swe_ds, temp_ds)
    assert np.isnan(float(out['degree_day_factor'].sel(station_id=0)))


# ---------------------------------------------------------------------------
# detect_rain_on_snow
# ---------------------------------------------------------------------------

def test_ros_flag_set_correctly():
    times = pd.date_range('2024-02-01', periods=3, freq='D')
    depth  = np.array([[0.2, 0.2, 0.0]])   # snow only on first two days
    temp   = np.array([[2.0, -1.0, 2.0]])  # warm only on day 0 and 2
    precip = np.array([[5.0, 5.0, 5.0]])   # rain every day

    ds = xr.Dataset(
        {
            'snow_depth':    (['station_id', 'time'], depth),
            'temp_mean':     (['station_id', 'time'], temp),
            'precip':        (['station_id', 'time'], precip),
            'frozen_precip': (['station_id', 'time'], np.zeros((1, 3))),
        },
        coords={'station_id': [0], 'time': times,
                'lat': ('station_id', [60.5]), 'lon': ('station_id', [14.0])},
    )
    out = detect_rain_on_snow(ds, ds, ds)
    ros = out['rain_on_snow'].values[0]
    assert ros[0] == 1   # snow + warm + rain
    assert ros[1] == 0   # snow + cold
    assert ros[2] == 0   # no snow


def test_ros_all_cold_returns_zeros():
    ds = _make_ds(n_stations=1, n_times=20)
    ds['temp_mean'][:] = -10.0
    out = detect_rain_on_snow(ds, ds, ds)
    assert int(out['rain_on_snow'].values.sum()) == 0


def test_ros_cf_attrs():
    ds = _make_ds(n_stations=1, n_times=5)
    out = detect_rain_on_snow(ds, ds, ds)
    assert 'flag_values' in out['rain_on_snow'].attrs


# ---------------------------------------------------------------------------
# calculate_freeze_thaw_cycles
# ---------------------------------------------------------------------------

def test_ftc_known_crossings():
    times = pd.date_range('2024-01-01', periods=6, freq='D')
    temp_vals = np.array([[3.0, -1.0, 2.0, -3.0, 1.0, -2.0]])  # 5 crossings
    ds = xr.Dataset(
        {'temp_mean': (['station_id', 'time'], temp_vals)},
        coords={'station_id': [0], 'time': times},
    )
    out = calculate_freeze_thaw_cycles(ds)
    assert int(out['freeze_thaw_count'].sel(station_id=0)) == 5


def test_ftc_no_crossings_always_cold():
    times = pd.date_range('2024-01-01', periods=5, freq='D')
    temp_vals = np.array([[-5.0, -3.0, -7.0, -2.0, -4.0]])
    ds = xr.Dataset(
        {'temp_mean': (['station_id', 'time'], temp_vals)},
        coords={'station_id': [0], 'time': times},
    )
    out = calculate_freeze_thaw_cycles(ds)
    assert int(out['freeze_thaw_count'].sel(station_id=0)) == 0


def test_ftc_nan_skipped():
    times = pd.date_range('2024-01-01', periods=5, freq='D')
    temp_vals = np.array([[3.0, np.nan, -2.0, np.nan, 1.0]])
    ds = xr.Dataset(
        {'temp_mean': (['station_id', 'time'], temp_vals)},
        coords={'station_id': [0], 'time': times},
    )
    out = calculate_freeze_thaw_cycles(ds)
    assert int(out['freeze_thaw_count'].sel(station_id=0)) == 2


def test_ftc_cf_attrs():
    ds = _make_ds(n_stations=1, n_times=5)
    out = calculate_freeze_thaw_cycles(ds)
    assert out['freeze_thaw_count'].attrs['units'] == '1'


# ---------------------------------------------------------------------------
# calculate_cold_content
# ---------------------------------------------------------------------------

def test_cold_content_zero_when_no_snow():
    times = pd.date_range('2024-01-01', periods=3, freq='D')
    depth = np.zeros((1, 3))
    temp  = np.array([[-10.0, -5.0, -3.0]])
    ds = xr.Dataset(
        {'snow_depth': (['station_id', 'time'], depth),
         'temp_mean':  (['station_id', 'time'], temp)},
        coords={'station_id': [0], 'time': times,
                'lat': ('station_id', [60.5]), 'lon': ('station_id', [14.0])},
    )
    out = calculate_cold_content(ds, ds)
    assert float(out['cold_content'].values.sum()) == pytest.approx(0.0)


def test_cold_content_zero_when_warm():
    times = pd.date_range('2024-03-01', periods=3, freq='D')
    depth = np.array([[0.5, 0.5, 0.5]])
    temp  = np.array([[2.0, 5.0, 3.0]])   # all above 0°C
    ds = xr.Dataset(
        {'snow_depth': (['station_id', 'time'], depth),
         'temp_mean':  (['station_id', 'time'], temp)},
        coords={'station_id': [0], 'time': times,
                'lat': ('station_id', [60.5]), 'lon': ('station_id', [14.0])},
    )
    out = calculate_cold_content(ds, ds)
    assert float(out['cold_content'].values.sum()) == pytest.approx(0.0)


def test_cold_content_positive_with_cold_snow():
    times = pd.date_range('2024-01-01', periods=3, freq='D')
    depth = np.array([[0.5, 0.5, 0.5]])
    temp  = np.array([[-10.0, -10.0, -10.0]])
    ds = xr.Dataset(
        {'snow_depth': (['station_id', 'time'], depth),
         'temp_mean':  (['station_id', 'time'], temp)},
        coords={'station_id': [0], 'time': times,
                'lat': ('station_id', [60.5]), 'lon': ('station_id', [14.0])},
    )
    out = calculate_cold_content(ds, ds)
    cc = out['cold_content'].values
    assert (cc > 0).all()


def test_cold_content_hand_calc():
    # CC = 917 × 2090 × 0.5 × 10 × 1e-6 = 9.59365 MJ/m²
    times = pd.date_range('2024-01-01', periods=1, freq='D')
    depth = np.array([[0.5]])
    temp  = np.array([[-10.0]])
    ds = xr.Dataset(
        {'snow_depth': (['station_id', 'time'], depth),
         'temp_mean':  (['station_id', 'time'], temp)},
        coords={'station_id': [0], 'time': times,
                'lat': ('station_id', [60.5]), 'lon': ('station_id', [14.0])},
    )
    out = calculate_cold_content(ds, ds)
    expected = 917.0 * 2090.0 * 0.5 * 10.0 * 1e-6
    assert float(out['cold_content'].values[0, 0]) == pytest.approx(expected, rel=1e-6)


def test_cold_content_cf_attrs():
    ds = _make_ds(n_stations=1, n_times=5)
    out = calculate_cold_content(ds, ds)
    assert out['cold_content'].attrs['units'] == 'MJ m-2'
