import pyproj
from pyproj import Transformer
import geopandas as gpd
from shapely.geometry import Point

# Standard projection for Hydro-Dataset (ETRS89 / LAEA Europe)
EPSG_LAEA = 3035
WGS84 = 4326

def get_laea_transformer() -> Transformer:
    """
    Returns a pyproj transformer from WGS84 to ETRS89-LAEA.
    """
    return Transformer.from_crs(WGS84, EPSG_LAEA, always_xy=True)

def project_points_to_laea(df, lon_col='longitude', lat_col='latitude'):
    """
    Transforms a pandas DataFrame with lon/lat into a GeoDataFrame projected in LAEA.
    """
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, crs=f"EPSG:{WGS84}", geometry=geometry)
    return gdf.to_crs(epsg=EPSG_LAEA)

def get_nordic_extent_laea():
    """
    Returns the bounding box for the Nordic region study area in LAEA coordinates.
    """
    # Placeholder: Example coordinates for Sweden and Finland combined in LAEA
    return {
        "min_x": 3000000,
        "max_x": 5500000,
        "min_y": 3000000,
        "max_y": 6000000
    }
