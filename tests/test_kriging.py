"""Unit tests for the ordinary kriging harmonize_point_to_grid function."""
import numpy as np
import pandas as pd
import pytest
import xarray as xr

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from processing.alignment import harmonize_point_to_grid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_station_ds(n: int = 6, n_times: int = 3, value: float = 0.3,
                     lat_range=(60.0, 61.5), lon_range=(13.0, 16.0)):
    """
    Synthetic station dataset spread across the Dalarna bounding box.
    All stations have a uniform snow_depth value unless overridden per-station.
    """
    lats = np.linspace(lat_range[0], lat_range[1], n)
    lons = np.linspace(lon_range[0], lon_range[1], n)
    times = pd.date_range('2024-01-01', periods=n_times, freq='D')
    depths = np.full((n, n_times), value)

    ds = xr.Dataset(
        {
            'snow_depth': (['station_id', 'time'], depths,
                           {'standard_name': 'surface_snow_thickness', 'units': 'm',
                            '_FillValue': float('nan')})
        },
        coords={
            'station_id': np.arange(n),
            'time': times,
            'lat': ('station_id', lats),
            'lon': ('station_id', lons),
        },
    )
    return ds


# ---------------------------------------------------------------------------
# Grid shape and resolution
# ---------------------------------------------------------------------------

def test_output_has_correct_dims():
    ds = _make_station_ds(n=6, n_times=2)
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0)
    assert 'x' in out.dims and 'y' in out.dims and 'time' in out.dims
    assert out.sizes['time'] == 2


def test_grid_spacing_matches_resolution():
    ds = _make_station_ds(n=6, n_times=1)
    res = 5000.0
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=res)
    x_diffs = np.diff(out['x'].values)
    y_diffs = np.diff(out['y'].values)
    assert np.allclose(x_diffs, res, atol=1.0)
    assert np.allclose(y_diffs, res, atol=1.0)


# ---------------------------------------------------------------------------
# Value range and kriging correctness
# ---------------------------------------------------------------------------

def test_values_within_extended_input_range():
    """Kriged values should not extrapolate wildly outside [0, station_max * 1.5]."""
    ds = _make_station_ds(n=6, n_times=1, value=0.5)
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0)
    valid = out['snow_depth'].values
    valid = valid[~np.isnan(valid)]
    assert valid.min() >= -0.05   # allow tiny numerical undershoot
    assert valid.max() <= 0.5 * 1.5


def test_uniform_field_reproduces_input_value():
    """If all stations have identical values, every kriged cell should match (within tolerance)."""
    const = 0.4
    ds = _make_station_ds(n=7, n_times=1, value=const)
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0)
    valid = out['snow_depth'].isel(time=0).values
    valid = valid[~np.isnan(valid)]
    assert np.allclose(valid, const, atol=0.01)


# ---------------------------------------------------------------------------
# NaN / missing-data handling
# ---------------------------------------------------------------------------

def test_nan_when_too_few_stations():
    """Time step with fewer than min_stations valid obs → all NaN in output slice."""
    ds = _make_station_ds(n=5, n_times=1, value=0.3)
    # Make all but 2 stations NaN for time 0
    ds['snow_depth'].values[2:, :] = np.nan
    ds['snow_depth'].values[0, :] = np.nan
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0,
                                  min_stations=3)
    assert np.all(np.isnan(out['snow_depth'].isel(time=0).values))


def test_nan_stations_are_ignored():
    """Mix of valid + NaN stations: kriging runs for the valid subset."""
    ds = _make_station_ds(n=6, n_times=1, value=0.3)
    ds['snow_depth'].values[0, :] = np.nan   # 1 NaN station, 5 valid
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0,
                                  min_stations=3)
    valid_cells = out['snow_depth'].isel(time=0).values
    assert not np.all(np.isnan(valid_cells))


def test_all_nan_input_returns_nan_grid():
    """If every station is NaN, all grid cells must be NaN."""
    ds = _make_station_ds(n=6, n_times=2, value=0.3)
    ds['snow_depth'].values[:] = np.nan
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0)
    assert np.all(np.isnan(out['snow_depth'].values))


# ---------------------------------------------------------------------------
# CF metadata
# ---------------------------------------------------------------------------

def test_cf_x_y_coord_attrs():
    ds = _make_station_ds(n=5, n_times=1)
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0)
    assert out['x'].attrs['standard_name'] == 'projection_x_coordinate'
    assert out['x'].attrs['units'] == 'm'
    assert out['y'].attrs['standard_name'] == 'projection_y_coordinate'
    assert out['y'].attrs['units'] == 'm'


def test_output_variable_attrs_preserved():
    """CF attributes from the input station variable should carry over to the grid."""
    ds = _make_station_ds(n=5, n_times=1)
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0)
    assert out['snow_depth'].attrs.get('standard_name') == 'surface_snow_thickness'
    assert out['snow_depth'].attrs.get('units') == 'm'
    assert 'OrdinaryKriging' in out['snow_depth'].attrs.get('interpolation', '')


def test_crs_coordinate_set():
    ds = _make_station_ds(n=5, n_times=1)
    out = harmonize_point_to_grid(ds, variable='snow_depth', grid_resolution_m=5000.0)
    assert 'crs' in out.coords
    assert '3035' in str(out.coords['crs'].values)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_unknown_variable_raises():
    ds = _make_station_ds(n=5, n_times=1)
    with pytest.raises(ValueError, match="not found"):
        harmonize_point_to_grid(ds, variable='nonexistent')
