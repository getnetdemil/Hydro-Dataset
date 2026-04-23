#!/usr/bin/env python3
"""
Download Finnish Meteorological Institute (FMI) station metadata via WFS API.

Retrieves station name, latitude, longitude, and WMO identifier for all
FMI weather observation stations in Finland. Elevation is not provided by
the WFS station endpoint and defaults to 0.

FMI WFS endpoint:
    https://opendata.fmi.fi/wfs
Stored query used:
    fmi::ef::stations  (Environmental Facility stations)

Usage:
    python scripts/download_fmi_stations.py
    python scripts/download_fmi_stations.py --output data/raw/fmi_station_metadata.csv
    python scripts/download_fmi_stations.py --bbox 18,59,32,71 --active-only
"""

import argparse
import requests
import pandas as pd
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

FMI_WFS_URL = "https://opendata.fmi.fi/wfs"

# XML namespaces used in FMI WFS responses
NS = {
    'wfs':    'http://www.opengis.net/wfs/2.0',
    'ef':     'http://inspire.ec.europa.eu/schemas/ef/4.0',
    'omop':   'http://inspire.ec.europa.eu/schemas/omop/3.0',
    'gml':    'http://www.opengis.net/gml/3.2',
    'xlink':  'http://www.w3.org/1999/xlink',
    'swe':    'http://www.opengis.net/swe/2.0',
}


def fetch_stations(
    bbox: str = "18,59,32,71",
    timeout: int = 60
) -> List[Dict]:
    """
    Fetch FMI station metadata from the WFS ef::stations stored query.

    Args:
        bbox: Bounding box "min_lon,min_lat,max_lon,max_lat"
        timeout: Request timeout in seconds

    Returns:
        List of station dictionaries with keys:
            station_id, name, latitude, longitude, elevation, wmo_id, country
    """
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "storedquery_id": "fmi::ef::stations",
        "bbox": bbox,
    }

    logger.info(f"Fetching FMI stations with bbox={bbox} ...")
    resp = requests.get(FMI_WFS_URL, params=params, timeout=timeout)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    logger.info(f"WFS numberMatched = {root.get('numberMatched', 'unknown')}")

    stations = []
    for member in root.findall('.//wfs:member', NS):
        for env_facility in member.findall('.//ef:EnvironmentalMonitoringFacility', NS):
            station = _parse_facility(env_facility)
            if station is not None:
                stations.append(station)

    logger.info(f"Parsed {len(stations)} station records from WFS response")
    return stations


def _parse_facility(node: ET.Element) -> Optional[Dict]:
    """
    Parse a single ef:EnvironmentalMonitoringFacility element.

    Returns a dict or None if required fields are missing.
    """
    # Station ID (gml:identifier)
    id_elem = node.find('gml:identifier', NS)
    if id_elem is None or not id_elem.text:
        return None
    raw_id = id_elem.text.strip()
    # Extract numeric part from URI like "http://xml.fmi.fi/stations/100683"
    station_id = raw_id.split('/')[-1]

    # Name
    name_elem = node.find('gml:name', NS)
    name = name_elem.text.strip() if name_elem is not None and name_elem.text else ""

    # Position (lat lon) from gml:pos
    pos_elem = node.find('.//gml:pos', NS)
    if pos_elem is None or not pos_elem.text:
        return None
    coords = pos_elem.text.strip().split()
    if len(coords) < 2:
        return None
    try:
        latitude = float(coords[0])
        longitude = float(coords[1])
    except ValueError:
        return None

    # WMO identifier (if available)
    wmo_id = None
    for identifier in node.findall('.//gml:identifier', NS):
        href = identifier.get('{http://www.w3.org/1999/xlink}href', '')
        if 'wmo' in href.lower():
            wmo_id = identifier.text.strip() if identifier.text else None
            break

    return {
        'station_id': station_id,
        'name': name,
        'latitude': latitude,
        'longitude': longitude,
        'elevation': 0.0,     # Not provided by fmi::ef::stations
        'wmo_id': wmo_id,
        'country': 'FI',
    }


def download_fmi_stations(
    output_path: str = "data/raw/fmi_station_metadata.csv",
    bbox: str = "18,59,32,71",
    min_lat: float = 59.0,
    max_lat: float = 71.0,
    min_lon: float = 18.0,
    max_lon: float = 32.0,
) -> pd.DataFrame:
    """
    Download, filter, and save FMI station metadata.

    Args:
        output_path: Path for the output CSV file
        bbox: WFS bounding box string
        min_lat/max_lat/min_lon/max_lon: Secondary geographic filter

    Returns:
        DataFrame with station metadata
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stations = fetch_stations(bbox=bbox)
    if not stations:
        logger.error("No stations retrieved — check WFS connectivity or bbox.")
        return pd.DataFrame()

    df = pd.DataFrame(stations)

    # Secondary geographic filter (handles any bbox overshooting)
    mask = (
        (df['latitude'] >= min_lat) & (df['latitude'] <= max_lat) &
        (df['longitude'] >= min_lon) & (df['longitude'] <= max_lon)
    )
    df = df[mask].copy()
    logger.info(f"After geographic filter (Finland): {len(df)} stations")

    # Deduplicate by station_id (keep first occurrence)
    before = len(df)
    df = df.drop_duplicates(subset='station_id', keep='first')
    if len(df) < before:
        logger.info(f"Dropped {before - len(df)} duplicate station_id entries")

    df = df.sort_values('station_id').reset_index(drop=True)

    df.to_csv(output_path, index=False)
    logger.info(f"Saved {len(df)} FMI stations to {output_path}")

    logger.info("\nStation Summary:")
    logger.info(f"  Total stations:  {len(df)}")
    logger.info(f"  Latitude range:  {df['latitude'].min():.2f} – {df['latitude'].max():.2f}")
    logger.info(f"  Longitude range: {df['longitude'].min():.2f} – {df['longitude'].max():.2f}")
    logger.info(f"  With WMO ID:     {df['wmo_id'].notna().sum()}")

    return df


def main():
    parser = argparse.ArgumentParser(
        description='Download FMI station metadata via WFS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all Finnish weather stations (default)
  python scripts/download_fmi_stations.py

  # Custom output path
  python scripts/download_fmi_stations.py --output data/raw/fmi_station_metadata.csv

  # Expand bbox to include Åland Islands
  python scripts/download_fmi_stations.py --bbox 17,59,32,71
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/fmi_station_metadata.csv')
    parser.add_argument('--bbox', type=str, default='18,59,32,71',
                        help='WFS bounding box: min_lon,min_lat,max_lon,max_lat')
    parser.add_argument('--min-lat', type=float, default=59.0)
    parser.add_argument('--max-lat', type=float, default=71.0)
    parser.add_argument('--min-lon', type=float, default=18.0)
    parser.add_argument('--max-lon', type=float, default=32.0)

    args = parser.parse_args()

    df = download_fmi_stations(
        output_path=args.output,
        bbox=args.bbox,
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
    )

    if not df.empty:
        print(f"\nDone! Saved {len(df)} FMI stations to {args.output}")
    else:
        print("ERROR: No stations saved. Check log output above.", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
