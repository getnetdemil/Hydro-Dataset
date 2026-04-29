import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr
from pykrige.ok import OrdinaryKriging

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.geo_utils import get_laea_transformer

logger = logging.getLogger(__name__)


def resample_temporal(df: pd.DataFrame, time_col: str, freq: str = 'D', agg_func: str = 'mean') -> pd.DataFrame:
    """Standardizes the temporal resolution of a DataFrame. freq: 'H', 'D', or 'M'."""
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col)
    return df.resample(freq).agg(agg_func).reset_index()


def harmonize_point_to_grid(
    station_ds: xr.Dataset,
    variable: str = 'snow_depth',
    grid_resolution_m: float = 2500.0,
    variogram_model: str = 'spherical',
    min_stations: int = 3,
) -> xr.Dataset:
    """
    Ordinary kriging of a station-point variable onto a regular LAEA EPSG:3035 grid.

    Grid extent is derived from the station lat/lon bounding box plus 10 km padding.
    Time steps with fewer than min_stations valid observations are filled with NaN.

    Args:
        station_ds:        xr.Dataset with dims (station_id, time) and coords lat/lon.
        variable:          Variable name in station_ds to interpolate.
        grid_resolution_m: Output grid spacing in metres (default 2500 m = MESAN resolution).
        variogram_model:   pykrige variogram model ('spherical', 'gaussian', 'exponential').
        min_stations:      Minimum valid stations required to run kriging for a time step.

    Returns:
        xr.Dataset with dims (y, x, time) in LAEA coordinates.
    """
    if variable not in station_ds:
        raise ValueError(f"Variable '{variable}' not found in station_ds. Available: {list(station_ds.data_vars)}")

    # --- Project station lat/lon to LAEA once ---
    transformer = get_laea_transformer()   # always_xy=True: input (lon, lat) → output (x, y)
    lons = station_ds['lon'].values.astype(float)
    lats = station_ds['lat'].values.astype(float)
    x_stations, y_stations = transformer.transform(lons, lats)

    # --- Build target grid from station extent + 10 km padding ---
    pad = 10_000.0
    x_grid = np.arange(x_stations.min() - pad, x_stations.max() + pad, grid_resolution_m)
    y_grid = np.arange(y_stations.min() - pad, y_stations.max() + pad, grid_resolution_m)
    nx, ny = len(x_grid), len(y_grid)

    n_times = station_ds.sizes['time']
    data_3d = np.full((ny, nx, n_times), np.nan, dtype=np.float64)

    logger.info(
        f"Kriging '{variable}' onto {ny}×{nx} grid "
        f"(res={grid_resolution_m:.0f} m) over {n_times} time steps"
    )

    for t in range(n_times):
        if t > 0 and t % 30 == 0:
            logger.info(f"  [{t}/{n_times}] time steps processed")

        values = station_ds[variable].isel(time=t).values
        valid = ~np.isnan(values)

        if valid.sum() < min_stations:
            continue   # leave slice as NaN

        # Kriging requires non-zero variance; constant fields bypass the variogram fit
        if np.std(values[valid]) < 1e-10:
            data_3d[:, :, t] = values[valid][0]
            continue

        ok = OrdinaryKriging(
            x_stations[valid],
            y_stations[valid],
            values[valid],
            variogram_model=variogram_model,
            nlags=6,
            weight=True,
            enable_statistics=False,
            verbose=False,
        )
        z, _ = ok.execute('grid', x_grid, y_grid)   # returns masked array, shape (ny, nx)
        data_3d[:, :, t] = np.asarray(z)

    logger.info(f"Kriging complete for '{variable}'")

    # --- Assemble output dataset ---
    var_attrs = dict(station_ds[variable].attrs)
    var_attrs['interpolation'] = f'OrdinaryKriging (pykrige), variogram={variogram_model}'

    out_ds = xr.Dataset(
        {variable: (['y', 'x', 'time'], data_3d, var_attrs)},
        coords={
            'x': ('x', x_grid),
            'y': ('y', y_grid),
            'time': station_ds['time'],
            'crs': 'EPSG:3035',
        },
    )
    out_ds['x'].attrs = {'standard_name': 'projection_x_coordinate', 'units': 'm', 'axis': 'X'}
    out_ds['y'].attrs = {'standard_name': 'projection_y_coordinate', 'units': 'm', 'axis': 'Y'}
    out_ds.attrs = {
        'grid_mapping': 'EPSG:3035',
        'grid_resolution_m': grid_resolution_m,
    }
    return out_ds


def align_spatially_to_laea(ds: xr.Dataset) -> xr.Dataset:
    """
    Stub: Reprojects a raster xr.Dataset to ETRS89-LAEA (EPSG:3035) using rioxarray.
    Applicable to gridded inputs (MESAN, ERA5-Land) once they are available.
    """
    # return ds.rio.write_crs("EPSG:4326").rio.reproject("EPSG:3035")
    return ds
