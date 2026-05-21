"""Unit tests for the Sturm et al. (2010) SWE derivation."""
import math
import numpy as np
import pandas as pd
import pytest
import xarray as xr

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from derivation.hydrological_parameters import (
    calculate_swe_sturm,
    STURM_CLASSES,
    _day_of_season,
)


def _make_ds(depths_m, start='2023-11-01'):
    """Minimal single-station dataset with a snow_depth variable."""
    times = pd.date_range(start, periods=len(depths_m), freq='D')
    ds = xr.Dataset(
        {'snow_depth': (['station_id', 'time'], np.array([depths_m]))},
        coords={'station_id': [99], 'time': times},
    )
    return ds


# --- _day_of_season ---

def test_dos_start_of_season():
    t = pd.DatetimeIndex(['2023-10-01'])
    assert _day_of_season(t)[0] == 0.0


def test_dos_mid_season():
    t = pd.DatetimeIndex(['2023-11-01'])
    assert _day_of_season(t)[0] == 31.0


def test_dos_wraps_year():
    # Feb 1 2024 is 123 days since Oct 1 2023
    t = pd.DatetimeIndex(['2024-02-01'])
    expected = (pd.Timestamp('2024-02-01') - pd.Timestamp('2023-10-01')).days
    assert _day_of_season(t)[0] == expected


def test_dos_summer_references_prior_season():
    # July 2023 is in the 2022-23 season, 287 days since Oct 1 2022
    t = pd.DatetimeIndex(['2023-07-15'])
    expected = (pd.Timestamp('2023-07-15') - pd.Timestamp('2022-10-01')).days
    assert _day_of_season(t)[0] == expected


# --- calculate_swe_sturm ---

def test_zero_depth_gives_zero_swe():
    ds = _make_ds([0.0, 0.0])
    out = calculate_swe_sturm(ds, ds)
    assert float(out['swe'].sum()) == pytest.approx(0.0)


def test_nan_depth_propagates():
    ds = _make_ds([np.nan, 0.5])
    out = calculate_swe_sturm(ds, ds)
    assert np.isnan(float(out['swe'].isel(station_id=0, time=0)))
    assert not np.isnan(float(out['swe'].isel(station_id=0, time=1)))


def test_swe_positive_for_positive_depth():
    ds = _make_ds([0.3, 0.5, 0.8])
    out = calculate_swe_sturm(ds, ds, snow_class='taiga')
    assert (out['swe'].values > 0).all()


def test_swe_increases_with_depth_same_dos():
    """On the same day, deeper snow → higher SWE."""
    times = pd.date_range('2024-01-01', periods=1)
    depths = np.array([[0.1], [0.3], [0.6]])
    ds = xr.Dataset(
        {'snow_depth': (['station_id', 'time'], depths)},
        coords={'station_id': [1, 2, 3], 'time': times},
    )
    out = calculate_swe_sturm(ds, ds, snow_class='alpine')
    swe_vals = out['swe'].values[:, 0]
    assert swe_vals[0] < swe_vals[1] < swe_vals[2]


def test_taiga_density_nearly_constant():
    """Taiga class has rho_max ≈ rho_0 — density should stay close to rho_0 throughout season."""
    depths = [0.5] * 180
    ds = _make_ds(depths, start='2023-10-15')
    out = calculate_swe_sturm(ds, ds, snow_class='taiga')
    rho = out['snow_density'].values[0]
    c = STURM_CLASSES['taiga']
    assert np.all(rho >= c['rho_0'] - 1e-6)
    assert np.all(rho <= c['rho_max'] + 1e-6)


def test_alpine_density_increases_over_season():
    """Alpine class: density should increase as DOS grows (k2 > 0)."""
    depths = [0.5] * 120
    ds = _make_ds(depths, start='2023-10-01')
    out = calculate_swe_sturm(ds, ds, snow_class='alpine')
    rho = out['snow_density'].values[0]
    assert rho[-1] > rho[0]


def test_hand_calculation_alpine():
    """Cross-check a single point against the analytical formula."""
    # h=0.5m on day 100 of season (Jan 9), alpine
    start = pd.Timestamp('2023-10-01')
    t = start + pd.Timedelta(days=100)
    ds = xr.Dataset(
        {'snow_depth': (['station_id', 'time'], [[0.5]])},
        coords={'station_id': [1], 'time': [t]},
    )
    out = calculate_swe_sturm(ds, ds, snow_class='alpine')
    c = STURM_CLASSES['alpine']
    h_cm = 50.0; dos = 100
    expected_rho = (c['rho_max'] - c['rho_0']) * (1 - math.exp(-c['k1']*h_cm - c['k2']*dos)) + c['rho_0']
    expected_swe = expected_rho * 0.5 * 1000.0
    assert float(out['swe'].values[0, 0]) == pytest.approx(expected_swe, rel=1e-6)


def test_invalid_snow_class_raises():
    ds = _make_ds([0.3])
    with pytest.raises(ValueError, match="Unknown snow class"):
        calculate_swe_sturm(ds, ds, snow_class='bogus')


def test_cf_attrs_present():
    ds = _make_ds([0.4])
    out = calculate_swe_sturm(ds, ds)
    assert 'standard_name' in out['swe'].attrs
    assert out['swe'].attrs['units'] == 'mm'
    assert 'units' in out['snow_density'].attrs


def test_all_snow_classes_run():
    ds = _make_ds([0.3, 0.5])
    for cls in STURM_CLASSES:
        out = calculate_swe_sturm(ds, ds, snow_class=cls)
        assert 'swe' in out
        assert 'snow_density' in out
