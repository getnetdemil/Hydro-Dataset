#!/usr/bin/env python3
"""
Download daily snow depth and basic meteorological observations from FMI WFS.

Uses the FMI Open Data WFS stored query for daily weather observations.
Downloads are chunked into 90-day windows because the FMI WFS service has a
practical limit on the length of a single time-series request.

FMI WFS endpoint:
    https://opendata.fmi.fi/wfs
Stored query:
    fmi::observations::weather::daily::multipointcoverage

Available daily fields:
    snow   — snow depth (cm)
    rrday  — daily precipitation (mm); -1.0 = trace/below threshold (→ 0.0)
    tday   — daily mean temperature (°C)
    tmin   — daily minimum temperature (°C)
    tmax   — daily maximum temperature (°C)
    TG_PT12H_min — 12-hour minimum ground temperature (°C)

Response format (gmlcov:MultiPointCoverage):
    - Domain: gmlcov:SimpleMultiPoint → gmlcov:positions
              Each position is a (lat, lon, unix_timestamp) triplet.
              Positions are ordered: all days for station 1, then all days for station 2, ...
    - Range:  gml:doubleOrNilReasonTupleList
              One tuple per position row, with one value per swe:field.
    - Station metadata: gml:Point elements with gml:id matching station fmisid.

Usage:
    # Download full archive (Oct 2015 – Apr 2024)
    python scripts/download_fmi_snow.py

    # Download a single winter season
    python scripts/download_fmi_snow.py --start-date 2023-10-01 --end-date 2024-04-30

    # Test with a small window
    python scripts/download_fmi_snow.py --start-date 2024-01-01 --end-date 2024-01-31
"""

import argparse
import requests
import pandas as pd
import numpy as np
import sys
import xml.etree.ElementTree as ET
import time
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import List, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

FMI_WFS_URL = "https://opendata.fmi.fi/wfs"
CHUNK_DAYS  = 90
RETRY_LIMIT = 3
RETRY_BACKOFF = 5

# FMI daily observation field names → output column names
DAILY_FIELDS = {
    'snow':          'snow_depth_cm',
    'rrday':         'precip_daily_mm',
    'tday':          'temp_mean_c',
    'tmin':          'temp_min_c',
    'tmax':          'temp_max_c',
    'TG_PT12H_min':  'ground_temp_min_c',
}

# FMI XML namespaces
NS_GML    = 'http://www.opengis.net/gml/3.2'
NS_SWE    = 'http://www.opengis.net/swe/2.0'
NS_GMLCOV = 'http://www.opengis.net/gmlcov/1.0'


def _iso(dt: date) -> str:
    return datetime(dt.year, dt.month, dt.day, 0, 0, 0).strftime('%Y-%m-%dT%H:%M:%SZ')


def _date_chunks(start: date, end: date, chunk_days: int) -> List[Tuple[date, date]]:
    chunks = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


def fetch_daily_chunk(
    start: date,
    end: date,
    bbox: str = "18,59,32,71",
    timeout: int = 120,
) -> Optional[pd.DataFrame]:
    """Fetch one chunk of daily observations."""
    params = {
        "service":          "WFS",
        "version":          "2.0.0",
        "request":          "GetFeature",
        "storedquery_id":   "fmi::observations::weather::daily::multipointcoverage",
        "bbox":             bbox,
        "starttime":        _iso(start),
        "endtime":          _iso(end),
        "parameters":       ",".join(DAILY_FIELDS.keys()),
    }
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            resp = requests.get(FMI_WFS_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt}/{RETRY_LIMIT} for {start}–{end}: {e}")
            if attempt < RETRY_LIMIT:
                time.sleep(RETRY_BACKOFF * attempt)
            else:
                logger.error(f"All retries exhausted for chunk {start}–{end}")
                return None
    return _parse_multipointcoverage(resp.content)


def _parse_multipointcoverage(xml_bytes: bytes) -> Optional[pd.DataFrame]:
    """
    Parse a FMI gmlcov:MultiPointCoverage XML response.

    Domain (gmlcov:positions): flat list of (lat lon unixtime) triplets.
    Range (gml:doubleOrNilReasonTupleList): one value-tuple per position row.
    Field names from gmlcov:rangeType → swe:DataRecord → swe:field.

    Station ID is derived from gml:Point/@gml:id (format: "point-{fmisid}").
    A (lat, lon) → station_id lookup is built from these Point elements.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return None

    # --- Field names from rangeType ---
    fields = []
    for elem in root.iter(f'{{{NS_SWE}}}field'):
        fields.append(elem.get('name', ''))
    if not fields:
        logger.warning("No swe:field elements found")
        return None

    # --- Build (lat, lon) → station_id mapping from gml:Point elements ---
    coord_to_id = {}
    for point in root.iter(f'{{{NS_GML}}}Point'):
        pid = point.get(f'{{{NS_GML}}}id', '')
        # pid format: "point-101695"
        if pid.startswith('point-'):
            station_id = pid[len('point-'):]
        else:
            continue
        name_elem = point.find(f'{{{NS_GML}}}name')
        pos_elem  = point.find(f'{{{NS_GML}}}pos')
        if pos_elem is None or not pos_elem.text:
            continue
        coords = pos_elem.text.strip().split()
        if len(coords) < 2:
            continue
        lat = round(float(coords[0]), 5)
        lon = round(float(coords[1]), 5)
        station_name = name_elem.text.strip() if name_elem is not None and name_elem.text else ''
        coord_to_id[(lat, lon)] = (station_id, station_name)

    if not coord_to_id:
        logger.warning("No station positions found in response")
        return None

    # --- Parse gmlcov:positions (lat lon unixtime per row) ---
    positions_elem = root.find(f'.//{{{NS_GMLCOV}}}positions')
    if positions_elem is None or not positions_elem.text:
        logger.warning("No gmlcov:positions element found")
        return None

    pos_tokens = positions_elem.text.split()
    if len(pos_tokens) % 3 != 0:
        logger.warning(f"Positions token count ({len(pos_tokens)}) not divisible by 3")
        return None

    positions = []  # list of (lat, lon, date)
    for i in range(0, len(pos_tokens), 3):
        lat = round(float(pos_tokens[i]),     5)
        lon = round(float(pos_tokens[i + 1]), 5)
        ts  = int(pos_tokens[i + 2])
        obs_date = datetime.utcfromtimestamp(ts).date()
        positions.append((lat, lon, obs_date))

    n_positions = len(positions)

    # --- Parse gml:doubleOrNilReasonTupleList ---
    data_elem = root.find(f'.//{{{NS_GML}}}doubleOrNilReasonTupleList')
    if data_elem is None or not data_elem.text:
        logger.warning("No gml:doubleOrNilReasonTupleList found")
        return None

    raw_tokens = data_elem.text.split()
    n_fields = len(fields)
    expected = n_positions * n_fields

    if len(raw_tokens) != expected:
        logger.warning(
            f"Token count mismatch: got {len(raw_tokens)}, "
            f"expected {n_positions}×{n_fields}={expected}"
        )
        if len(raw_tokens) % n_fields != 0:
            return None
        n_positions = len(raw_tokens) // n_fields
        positions = positions[:n_positions]

    values = []
    for tok in raw_tokens:
        if tok == 'NaN':
            values.append(np.nan)
        else:
            try:
                values.append(float(tok))
            except ValueError:
                values.append(np.nan)

    arr = np.array(values, dtype=float).reshape(n_positions, n_fields)

    # --- Build tidy DataFrame ---
    records = []
    for row_idx, (lat, lon, obs_date) in enumerate(positions):
        info = coord_to_id.get((lat, lon))
        if info is None:
            # Try nearest match (floating point rounding)
            best = min(coord_to_id.keys(),
                       key=lambda k: (k[0] - lat) ** 2 + (k[1] - lon) ** 2)
            if abs(best[0] - lat) < 0.01 and abs(best[1] - lon) < 0.01:
                info = coord_to_id[best]
            else:
                continue

        station_id, station_name = info
        row = {
            'date':       obs_date,
            'station_id': station_id,
            'name':       station_name,
            'latitude':   lat,
            'longitude':  lon,
        }
        for fi, fname in enumerate(fields):
            val = arr[row_idx, fi]
            out_col = DAILY_FIELDS.get(fname, fname)
            row[out_col] = float(val) if not np.isnan(val) else np.nan
        records.append(row)

    if not records:
        return None

    df = pd.DataFrame(records)

    # FMI uses -1.0 for trace precipitation (below threshold) → treat as 0.0
    if 'precip_daily_mm' in df.columns:
        df['precip_daily_mm'] = df['precip_daily_mm'].replace(-1.0, 0.0)
        df.loc[df['precip_daily_mm'] < 0, 'precip_daily_mm'] = np.nan

    return df


def build_date_windows(start_year: int, end_year: int) -> List[Tuple[date, date]]:
    windows = []
    for y in range(start_year, end_year):
        windows.append((date(y, 10, 1), date(y + 1, 4, 30)))
    return windows


def download_fmi_snow(
    output_path: str = "data/raw/fmi_snow_daily.csv",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    start_year: int = 2015,
    end_year: int = 2024,
    bbox: str = "18,59,32,71",
    chunk_days: int = CHUNK_DAYS,
    resume: bool = True,
) -> pd.DataFrame:
    """Download FMI daily observations and save to CSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if start_date is not None and end_date is not None:
        all_windows = [(start_date, end_date)]
    else:
        all_windows = build_date_windows(start_year, end_year)

    existing_df = pd.DataFrame()
    covered_dates = set()
    if resume and output_path.exists():
        try:
            existing_df = pd.read_csv(output_path, parse_dates=['date'])
            existing_df['date'] = existing_df['date'].dt.date
            covered_dates = set(existing_df['date'].unique())
            logger.info(f"Resuming: {len(covered_dates)} dates already in {output_path}")
        except Exception as e:
            logger.warning(f"Could not load existing file: {e}")
            existing_df = pd.DataFrame()

    all_chunks = []
    for ws, we in all_windows:
        for cs, ce in _date_chunks(ws, we, chunk_days):
            chunk_dates = {cs + timedelta(days=i) for i in range((ce - cs).days + 1)}
            if chunk_dates.issubset(covered_dates):
                continue
            all_chunks.append((cs, ce))

    logger.info(f"Total chunks to download: {len(all_chunks)}")

    new_frames = []
    for i, (cs, ce) in enumerate(all_chunks, 1):
        logger.info(f"[{i}/{len(all_chunks)}] Downloading {cs} – {ce} ...")
        df_chunk = fetch_daily_chunk(cs, ce, bbox=bbox)
        if df_chunk is not None and not df_chunk.empty:
            new_frames.append(df_chunk)
            logger.info(f"  Got {len(df_chunk)} records for {df_chunk['date'].nunique()} dates, "
                        f"{df_chunk['station_id'].nunique()} stations")
        else:
            logger.warning(f"  No data returned for {cs}–{ce}")
        if i < len(all_chunks):
            time.sleep(1.0)

    parts = []
    if not existing_df.empty:
        parts.append(existing_df)
    parts.extend(new_frames)

    if not parts:
        logger.error("No data downloaded.")
        return pd.DataFrame()

    combined = pd.concat(parts, ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date']).dt.date
    combined = combined.drop_duplicates(subset=['date', 'station_id'], keep='last')
    combined = combined.sort_values(['station_id', 'date']).reset_index(drop=True)

    combined.to_csv(output_path, index=False)
    logger.info(f"\nSaved {len(combined):,} rows, {combined['station_id'].nunique()} stations, "
                f"{combined['date'].nunique()} dates → {output_path}")

    if 'snow_depth_cm' in combined.columns:
        valid = combined['snow_depth_cm'].dropna()
        logger.info(f"  Snow depth: {len(valid):,} non-NaN "
                    f"(range {valid.min():.0f}–{valid.max():.0f} cm)")

    return combined


def main():
    parser = argparse.ArgumentParser(
        description='Download FMI daily snow depth observations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/download_fmi_snow.py
  python scripts/download_fmi_snow.py --start-date 2023-10-01 --end-date 2024-04-30
  python scripts/download_fmi_snow.py --start-date 2024-01-01 --end-date 2024-01-31
        """
    )
    parser.add_argument('--output',      type=str, default='data/raw/fmi_snow_daily.csv')
    parser.add_argument('--start-date',  type=str, default=None)
    parser.add_argument('--end-date',    type=str, default=None)
    parser.add_argument('--start-year',  type=int, default=2015)
    parser.add_argument('--end-year',    type=int, default=2024)
    parser.add_argument('--bbox',        type=str, default='18,59,32,71')
    parser.add_argument('--chunk-days',  type=int, default=CHUNK_DAYS)
    parser.add_argument('--no-resume',   action='store_true')

    args = parser.parse_args()
    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date   = date.fromisoformat(args.end_date)   if args.end_date   else None

    df = download_fmi_snow(
        output_path=args.output,
        start_date=start_date,
        end_date=end_date,
        start_year=args.start_year,
        end_year=args.end_year,
        bbox=args.bbox,
        chunk_days=args.chunk_days,
        resume=not args.no_resume,
    )
    if df.empty:
        print("ERROR: No data downloaded.", file=sys.stderr)
        sys.exit(1)
    print(f"\nDone! {len(df):,} rows → {args.output}")


if __name__ == '__main__':
    main()
