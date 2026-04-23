#!/usr/bin/env python3
"""
Download FMI hourly weather observations and aggregate to daily values.

Uses the FMI Open Data WFS hourly multipointcoverage stored query to retrieve
temperature, humidity, wind speed, precipitation, and weather phenomena code
for Finnish stations. Observations are aggregated to daily resolution matching
the MESAN feature table used for Swedish stations.

FMI WFS endpoint:
    https://opendata.fmi.fi/wfs
Stored query:
    fmi::observations::weather::hourly::multipointcoverage

Hourly parameters retrieved:
    TA_PT1H_AVG   — hourly mean air temperature (°C)
    RH_PT1H_AVG   — hourly mean relative humidity (%)
    WS_PT1H_AVG   — hourly mean wind speed (m/s)
    PRA_PT1H_ACC  — hourly precipitation accumulation (mm)
    WAWA_PT1H_RANK — hourly weather phenomena rank (see below)

Daily aggregation:
    temperature   = mean(TA_PT1H_AVG)
    humidity      = mean(RH_PT1H_AVG)
    wind_speed    = mean(WS_PT1H_AVG)
    precipitation = sum(PRA_PT1H_ACC)
    visibility    = derived from WAWA rank:
                    WAWA 40-49 (fog/mist)      → 200 m
                    WAWA 10-19 (haze/dust)     → 5000 m
                    WAWA 70-79 (snow)          → 2000 m
                    all other (clear/unknown)  → 10000 m (default)

Usage:
    # Download full archive and aggregate to daily
    python scripts/download_fmi_hourly.py

    # Single month test
    python scripts/download_fmi_hourly.py --start-date 2024-01-01 --end-date 2024-01-31

    # Custom output
    python scripts/download_fmi_hourly.py --output data/raw/fmi_hourly_daily.csv
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

FMI_WFS_URL     = "https://opendata.fmi.fi/wfs"
CHUNK_DAYS      = 30          # hourly requests: smaller chunks than daily
RETRY_LIMIT     = 3
RETRY_BACKOFF   = 5

# WAWA weather phenomenon rank → estimated visibility (metres)
# Based on WMO WAWA code table (code table 4677 / BUFR table 020003)
def wawa_to_visibility(wawa_series: pd.Series) -> pd.Series:
    """
    Convert WAWA code values to estimated visibility in metres.

    Fog/thick mist codes (40-49) → 200 m
    Precipitation near station (codes 50-69, 80-99) → 2000 m
    Snow/blowing snow (70-79) → 2000 m
    Haze/dust (10-19) → 5000 m
    Drizzle/rain (20-29, 30-39) → 4000 m
    Default (clear, unknown, NaN) → 10000 m
    """
    vis = pd.Series(10000.0, index=wawa_series.index)  # default: 10 km
    vis = vis.where(~wawa_series.between(10, 19, inclusive='both'), 5000.0)
    vis = vis.where(~wawa_series.between(20, 39, inclusive='both'), 4000.0)
    vis = vis.where(~wawa_series.between(40, 49, inclusive='both'), 200.0)
    vis = vis.where(~wawa_series.between(50, 79, inclusive='both'), 2000.0)
    vis = vis.where(~wawa_series.between(80, 99, inclusive='both'), 2000.0)
    # Convert to km (matching MESAN convention)
    return vis / 1000.0

HOURLY_PARAMS = "TA_PT1H_AVG,RH_PT1H_AVG,WS_PT1H_AVG,PRA_PT1H_ACC,WAWA_PT1H_RANK"

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


def fetch_hourly_chunk(
    start: date,
    end: date,
    bbox: str = "18,59,32,71",
    timeout: int = 180,
) -> Optional[pd.DataFrame]:
    """Fetch one chunk of hourly observations from the FMI WFS."""
    params = {
        "service":          "WFS",
        "version":          "2.0.0",
        "request":          "GetFeature",
        "storedquery_id":   "fmi::observations::weather::hourly::multipointcoverage",
        "bbox":             bbox,
        "starttime":        _iso(start),
        "endtime":          _iso(end),
        "parameters":       HOURLY_PARAMS,
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
                logger.error(f"All retries exhausted for {start}–{end}")
                return None
    return _parse_multipointcoverage_hourly(resp.content)


def _parse_multipointcoverage_hourly(xml_bytes: bytes) -> Optional[pd.DataFrame]:
    """
    Parse a FMI hourly gmlcov:MultiPointCoverage XML response.

    Domain: gmlcov:positions with (lat lon unixtime) triplets.
    Range:  gml:doubleOrNilReasonTupleList, one tuple per position.
    Station IDs extracted from gml:Point/@gml:id = 'point-{fmisid}'.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return None

    # --- Field names ---
    fields = [f.get('name', '') for f in root.iter(f'{{{NS_SWE}}}field')]
    if not fields:
        logger.warning("No swe:field elements found in hourly response")
        return None

    # --- Build (lat, lon) → (station_id, name) mapping ---
    coord_to_id = {}
    for point in root.iter(f'{{{NS_GML}}}Point'):
        pid = point.get(f'{{{NS_GML}}}id', '')
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
        name = name_elem.text.strip() if name_elem is not None and name_elem.text else ''
        coord_to_id[(lat, lon)] = (station_id, name)

    if not coord_to_id:
        logger.warning("No station positions found in hourly response")
        return None

    # --- Parse gmlcov:positions (lat lon unixtime) ---
    positions_elem = root.find(f'.//{{{NS_GMLCOV}}}positions')
    if positions_elem is None or not positions_elem.text:
        logger.warning("No gmlcov:positions found in hourly response")
        return None

    pos_tokens = positions_elem.text.split()
    if len(pos_tokens) % 3 != 0:
        logger.warning(f"Positions token count ({len(pos_tokens)}) not divisible by 3")
        return None

    positions = []
    for i in range(0, len(pos_tokens), 3):
        lat = round(float(pos_tokens[i]),     5)
        lon = round(float(pos_tokens[i + 1]), 5)
        ts  = int(pos_tokens[i + 2])
        obs_dt = datetime.utcfromtimestamp(ts)
        positions.append((lat, lon, obs_dt))

    n_positions = len(positions)

    # --- Parse data values ---
    data_elem = root.find(f'.//{{{NS_GML}}}doubleOrNilReasonTupleList')
    if data_elem is None or not data_elem.text:
        logger.warning("No gml:doubleOrNilReasonTupleList found in hourly response")
        return None

    raw_tokens = data_elem.text.split()
    n_fields   = len(fields)
    expected   = n_positions * n_fields

    if len(raw_tokens) != expected:
        if len(raw_tokens) % n_fields != 0:
            logger.warning(f"Token count mismatch: got {len(raw_tokens)}, expected {expected}")
            return None
        n_positions = len(raw_tokens) // n_fields
        positions = positions[:n_positions]

    values = []
    for tok in raw_tokens:
        values.append(np.nan if tok == 'NaN' else float(tok))

    arr = np.array(values, dtype=float).reshape(n_positions, n_fields)
    field_map = {f: i for i, f in enumerate(fields)}

    def _get(row_idx, fname):
        fi = field_map.get(fname)
        return arr[row_idx, fi] if fi is not None else np.nan

    # --- Build hourly records ---
    records = []
    for row_idx, (lat, lon, obs_dt) in enumerate(positions):
        info = coord_to_id.get((lat, lon))
        if info is None:
            best = min(coord_to_id.keys(),
                       key=lambda k: (k[0] - lat) ** 2 + (k[1] - lon) ** 2)
            if abs(best[0] - lat) < 0.01 and abs(best[1] - lon) < 0.01:
                info = coord_to_id[best]
            else:
                continue
        station_id, name = info

        records.append({
            'datetime_utc': obs_dt,
            'date':         obs_dt.date(),
            'station_id':   station_id,
            'name':         name,
            'latitude':     lat,
            'longitude':    lon,
            'temp_c':       _get(row_idx, 'TA_PT1H_AVG'),
            'humidity_pct': _get(row_idx, 'RH_PT1H_AVG'),
            'wind_ms':      _get(row_idx, 'WS_PT1H_AVG'),
            'precip_mm':    _get(row_idx, 'PRA_PT1H_ACC'),
            'wawa_rank':    _get(row_idx, 'WAWA_PT1H_RANK'),
        })

    if not records:
        return None

    df = pd.DataFrame(records)
    # FMI uses NaN for missing; replace any remaining sentinel values
    for col in df.select_dtypes(include='number').columns:
        df.loc[df[col] < -900, col] = np.nan

    return df


def aggregate_to_daily(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate hourly observations to daily values per station.

    Rules:
        temperature   = daily mean of hourly means (°C)
        humidity      = daily mean of hourly means (%)
        wind_speed    = daily mean of hourly means (m/s)
        precipitation = daily sum of hourly accumulations (mm)
        visibility    = daily mean of visibility derived from WAWA rank (km)

    Requires at least 6 valid hourly observations per day for temp/humidity/wind.
    Days with fewer than 6 obs are NaN-filled.

    Returns:
        DataFrame with columns [date, station_id, name, latitude, longitude,
        temperature, humidity, wind_speed, precipitation, visibility]
    """
    if df_hourly.empty:
        return pd.DataFrame()

    # Derive visibility from WAWA before grouping
    df_hourly = df_hourly.copy()
    wawa_valid = df_hourly['wawa_rank'].dropna()
    vis_all = wawa_to_visibility(df_hourly['wawa_rank'].fillna(-1))
    # Where WAWA was NaN, set visibility to default (10 km)
    vis_all = vis_all.where(df_hourly['wawa_rank'].notna(), 10.0)
    df_hourly['visibility_km'] = vis_all

    group_cols = ['date', 'station_id', 'name', 'latitude', 'longitude']

    def safe_mean(s, min_obs=6):
        valid = s.dropna()
        return valid.mean() if len(valid) >= min_obs else np.nan

    def daily_precip(s):
        valid = s.dropna()
        return valid.sum() if len(valid) > 0 else np.nan

    daily = df_hourly.groupby(group_cols).agg(
        temperature=('temp_c',       lambda s: safe_mean(s, min_obs=6)),
        humidity=   ('humidity_pct', lambda s: safe_mean(s, min_obs=6)),
        wind_speed= ('wind_ms',      lambda s: safe_mean(s, min_obs=6)),
        precipitation=('precip_mm',  daily_precip),
        visibility= ('visibility_km',lambda s: s.mean()),
    ).reset_index()

    return daily


def build_date_windows(start_year: int, end_year: int) -> List[Tuple[date, date]]:
    windows = []
    for y in range(start_year, end_year):
        windows.append((date(y, 10, 1), date(y + 1, 4, 30)))
    return windows


def download_fmi_hourly(
    output_path: str = "data/raw/fmi_hourly_daily.csv",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    start_year: int = 2015,
    end_year: int = 2024,
    bbox: str = "18,59,32,71",
    chunk_days: int = CHUNK_DAYS,
    resume: bool = True,
) -> pd.DataFrame:
    """
    Download FMI hourly observations, aggregate to daily, and save.

    Args:
        output_path:  Output CSV (daily aggregates)
        start_date:   Override start date
        end_date:     Override end date
        start_year:   First winter year
        end_year:     Last year
        bbox:         Geographic bounding box
        chunk_days:   Days per WFS request
        resume:       Skip already-downloaded dates

    Returns:
        DataFrame of daily aggregates
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if start_date is not None and end_date is not None:
        all_windows = [(start_date, end_date)]
    else:
        all_windows = build_date_windows(start_year, end_year)

    # Resume
    existing_df = pd.DataFrame()
    covered_dates = set()
    if resume and output_path.exists():
        try:
            existing_df = pd.read_csv(output_path, parse_dates=['date'])
            existing_df['date'] = existing_df['date'].dt.date
            covered_dates = set(existing_df['date'].unique())
            logger.info(f"Resuming: {len(covered_dates)} dates already downloaded")
        except Exception as e:
            logger.warning(f"Could not load existing file: {e}")

    all_chunks = []
    for ws, we in all_windows:
        for cs, ce in _date_chunks(ws, we, chunk_days):
            chunk_dates = {cs + timedelta(days=i) for i in range((ce - cs).days + 1)}
            if chunk_dates.issubset(covered_dates):
                continue
            all_chunks.append((cs, ce))

    logger.info(f"Chunks to download: {len(all_chunks)}")

    new_daily_frames = []
    for i, (cs, ce) in enumerate(all_chunks, 1):
        logger.info(f"[{i}/{len(all_chunks)}] Downloading hourly {cs} – {ce} ...")
        df_hourly = fetch_hourly_chunk(cs, ce, bbox=bbox)
        if df_hourly is not None and not df_hourly.empty:
            df_day = aggregate_to_daily(df_hourly)
            if not df_day.empty:
                new_daily_frames.append(df_day)
                logger.info(f"  → {len(df_day)} daily rows from {df_hourly['station_id'].nunique()} stations")
        else:
            logger.warning(f"  No data for {cs}–{ce}")
        if i < len(all_chunks):
            time.sleep(1.0)

    parts = []
    if not existing_df.empty:
        parts.append(existing_df)
    parts.extend(new_daily_frames)

    if not parts:
        logger.error("No data downloaded.")
        return pd.DataFrame()

    combined = pd.concat(parts, ignore_index=True)
    combined['date'] = pd.to_datetime(combined['date']).dt.date
    combined = combined.drop_duplicates(subset=['date', 'station_id'], keep='last')
    combined = combined.sort_values(['station_id', 'date']).reset_index(drop=True)

    combined.to_csv(output_path, index=False)
    logger.info(f"\nSaved {len(combined):,} daily rows → {output_path}")
    logger.info(f"  Stations: {combined['station_id'].nunique()}")
    logger.info(f"  Dates:    {combined['date'].nunique()}")

    for col in ['temperature', 'humidity', 'wind_speed', 'precipitation', 'visibility']:
        if col in combined.columns:
            n_valid = combined[col].notna().sum()
            logger.info(f"  {col}: {n_valid:,} non-NaN ({100*n_valid/len(combined):.1f}%)")

    return combined


def main():
    parser = argparse.ArgumentParser(
        description='Download FMI hourly observations and aggregate to daily',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download full archive (Oct 2015 – Apr 2024)
  python scripts/download_fmi_hourly.py

  # Quick test: January 2024
  python scripts/download_fmi_hourly.py --start-date 2024-01-01 --end-date 2024-01-31

  # One winter season
  python scripts/download_fmi_hourly.py --start-date 2023-10-01 --end-date 2024-04-30
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/fmi_hourly_daily.csv')
    parser.add_argument('--start-date', type=str, default=None)
    parser.add_argument('--end-date', type=str, default=None)
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2024)
    parser.add_argument('--bbox', type=str, default='18,59,32,71')
    parser.add_argument('--chunk-days', type=int, default=CHUNK_DAYS)
    parser.add_argument('--no-resume', action='store_true')

    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date   = date.fromisoformat(args.end_date)   if args.end_date   else None

    df = download_fmi_hourly(
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
    print(f"\nDone! {len(df):,} daily rows → {args.output}")


if __name__ == '__main__':
    main()
