#!/usr/bin/env python3
"""
Download MODIS MOD10A1 NDSI snow-cover patches (32x32 pixels per station) via GEE.

This is Phase 1 / Month 2 of the multi-modal fusion project. Produces per-station
per-month NPZ shards whose layout mirrors scripts/download_era5_land_patches.py,
so build_multimodal_shards.py can align both modalities by station_id + date.

MODIS dataset:   MODIS/061/MOD10A1  (daily Terra snow cover, 500 m)
Bands used:      NDSI_Snow_Cover           (0-100 %, 0 = no snow)
                 NDSI_Snow_Cover_Basic_QA  (0 best, 1 good, 2 ok, 3 poor,
                                           211 night, 239 cloud, 250/254/255 fill)
Patch:           32 x 32 pixels (~16 km x 16 km) centred on each station via
                 ee.Geometry.Point(lon, lat).buffer(8000).bounds().

Per-pixel validity mask is derived from QA:
    mask = 1 iff QA <= 2  (keep best/good/ok)
    mask = 0 otherwise (poor/cloud/night/fill)

This per-pixel, per-day mask is the cloud-variable missingness signal that the
MaskedGatedFusion module is designed to exploit -- distinct from ERA5-Land
(which is only NaN over sea).

Output layout:
    data/processed/modis_patches/<station_id>/<YYYY-MM>.npz
        patch     (days, 32, 32, 2) float32   # channels: ['ndsi', 'qa_basic']
        mask      (days, 32, 32)     uint8    # per-pixel per-day valid flag
        dates     (days,)            |S10
        channels  (2,)               object
        station_id, latitude, longitude

Prerequisites:
    1. pip install earthengine-api
    2. earthengine authenticate  (one-time, opens browser)
    3. A GCP project linked to GEE; pass via --gee-project

Usage:
    # Pilot: 10 stations, winter 2023-24
    python scripts/download_modis_patches.py \\
        --start-year 2023 --end-year 2024 --pilot 10 \\
        --gee-project my-gee-project-id

    # Full run
    python scripts/download_modis_patches.py \\
        --start-year 2015 --end-year 2024 \\
        --gee-project my-gee-project-id
"""

import argparse
import calendar
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

WINTER_MONTHS = [10, 11, 12, 1, 2, 3, 4]
MODIS_COLLECTION = 'MODIS/061/MOD10A1'
NDSI_BAND = 'NDSI_Snow_Cover'
QA_BAND = 'NDSI_Snow_Cover_Basic_QA'
MODIS_NATIVE_RES_M = 500.0
QA_VALID_MAX = 2


def _check_ee():
    try:
        import ee
        return ee
    except ImportError:
        logger.error(
            "earthengine-api not installed. Run: pip install earthengine-api\n"
            "Also run `earthengine authenticate` (one-time, opens browser).\n"
            "See https://developers.google.com/earth-engine/guides/python_install"
        )
        sys.exit(1)


def load_station_metadata(
    smhi_file: Path,
    fmi_file: Path,
    pilot_n: Optional[int] = None,
) -> pd.DataFrame:
    """Same signature/behaviour as download_era5_land_patches.load_station_metadata."""
    frames = []
    if smhi_file.exists():
        df_se = pd.read_csv(smhi_file, usecols=['station_id', 'latitude', 'longitude'])
        df_se['source'] = 'SMHI'
        frames.append(df_se)
        logger.info(f"Loaded {len(df_se)} SMHI stations from {smhi_file}")
    else:
        logger.warning(f"SMHI station file not found: {smhi_file}")

    if fmi_file.exists():
        df_fi = pd.read_csv(fmi_file, usecols=['station_id', 'latitude', 'longitude'])
        df_fi['source'] = 'FMI'
        frames.append(df_fi)
        logger.info(f"Loaded {len(df_fi)} FMI stations from {fmi_file}")
    else:
        logger.warning(f"FMI station file not found: {fmi_file}")

    if not frames:
        logger.error("No station metadata available. Aborting.")
        sys.exit(1)

    stations = pd.concat(frames, ignore_index=True)
    stations = stations.dropna(subset=['latitude', 'longitude'])
    stations = stations.drop_duplicates(subset=['station_id'])
    stations['station_id'] = stations['station_id'].astype(str)
    stations = stations.sort_values('station_id').reset_index(drop=True)

    if pilot_n is not None:
        stations = stations.head(pilot_n).reset_index(drop=True)
        logger.info(f"PILOT MODE: limited to first {pilot_n} stations")

    logger.info(f"Final station set: {len(stations)} stations "
                f"({(stations['source']=='SMHI').sum()} SE, "
                f"{(stations['source']=='FMI').sum()} FI)")
    return stations


def build_year_month_list(start_year: int, end_year: int) -> List[Tuple[int, int]]:
    """Mirror of download_era5_land_patches.build_year_month_list for consistency."""
    pairs = []
    for y in range(start_year, end_year + 1):
        for m in WINTER_MONTHS:
            if m >= 10:
                if y < end_year:
                    pairs.append((y, m))
            else:
                if y <= end_year:
                    pairs.append((y, m))
    return pairs


def _station_rectangle(ee, lat: float, lon: float, patch_size: int = 32,
                       res_m: float = MODIS_NATIVE_RES_M):
    """Metric-correct rectangle: (patch_size * res_m) / 2 half-width buffer from centre point."""
    half_m = (patch_size * res_m) / 2.0
    return ee.Geometry.Point(lon, lat).buffer(half_m).bounds()


def _sample_image_day(ee, img, rect, patch_size: int, max_retries: int = 3):
    """
    Sample one day's NDSI + QA image over the rectangle, crop/pad to patch_size.
    Returns (ndsi_arr, qa_arr) each shaped (patch_size, patch_size), or None on failure.
    """
    for attempt in range(1, max_retries + 1):
        try:
            info = img.select([NDSI_BAND, QA_BAND]).sampleRectangle(
                region=rect, defaultValue=255,
            ).getInfo()
            props = info.get('properties', {})
            ndsi_raw = props.get(NDSI_BAND)
            qa_raw = props.get(QA_BAND)
            if ndsi_raw is None or qa_raw is None:
                return None
            ndsi_arr = np.asarray(ndsi_raw, dtype=np.float32)
            qa_arr = np.asarray(qa_raw, dtype=np.float32)
            return _crop_pad(ndsi_arr, patch_size), _crop_pad(qa_arr, patch_size, fill=255.0)
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 * attempt)
                continue
            return None


def _crop_pad(arr: np.ndarray, size: int, fill: float = np.nan) -> np.ndarray:
    """Centre-crop a 2D array to size x size, padding with `fill` if smaller."""
    h, w = arr.shape
    out = np.full((size, size), fill, dtype=np.float32)
    H = min(h, size)
    W = min(w, size)
    h_src0 = (h - H) // 2
    w_src0 = (w - W) // 2
    h_dst0 = (size - H) // 2
    w_dst0 = (size - W) // 2
    out[h_dst0:h_dst0 + H, w_dst0:w_dst0 + W] = arr[h_src0:h_src0 + H, w_src0:w_src0 + W]
    return out


def extract_modis_month(
    ee,
    lat: float,
    lon: float,
    year: int,
    month: int,
    patch_size: int = 32,
    qa_valid_max: int = QA_VALID_MAX,
    max_retries: int = 3,
) -> Optional[dict]:
    """
    Pull one station-month of MODIS MOD10A1 patches, one day at a time.

    Returns dict with patch, mask, dates, channels. Days with no image get all-NaN
    NDSI, QA=255, mask=0. Uses per-day sampleRectangle calls to guarantee correct
    native-resolution reprojection (toBands() on the collection was silently
    returning fill values on the collection-level reprojection).
    """
    rect = _station_rectangle(ee, lat, lon, patch_size)
    _, n_days = calendar.monthrange(year, month)
    expected_dates = [f"{year}-{month:02d}-{d:02d}" for d in range(1, n_days + 1)]

    ndsi = np.full((n_days, patch_size, patch_size), np.nan, dtype=np.float32)
    qa   = np.full((n_days, patch_size, patch_size), 255.0, dtype=np.float32)

    for i, date_iso in enumerate(expected_dates):
        day_start = ee.Date(date_iso)
        day_end = day_start.advance(1, 'day')
        coll = (ee.ImageCollection(MODIS_COLLECTION)
                .filterDate(day_start, day_end)
                .filterBounds(rect))
        img = ee.Image(coll.first())
        if img is None:
            continue
        try:
            has_img = coll.size().getInfo() > 0
        except Exception:
            has_img = False
        if not has_img:
            continue

        out = _sample_image_day(ee, img, rect, patch_size, max_retries=max_retries)
        if out is None:
            continue
        ndsi_arr, qa_arr = out
        ndsi[i] = ndsi_arr
        qa[i]   = qa_arr

    # QA<=qa_valid_max AND NDSI in [0,100]: fill values (e.g. 255) can appear
    # with QA=0/2 in MOD10A1 at scan edges — must additionally gate on NDSI range.
    mask = ((qa <= qa_valid_max) & (ndsi >= 0) & (ndsi <= 100)).astype(np.uint8)
    ndsi[mask == 0] = np.nan

    patch = np.stack([ndsi, qa], axis=-1).astype(np.float32)

    return {
        'patch':    patch,
        'mask':     mask,
        'dates':    expected_dates,
        'channels': ['ndsi', 'qa_basic'],
    }


def save_station_shard(
    payload: dict,
    station_id: str,
    latitude: float,
    longitude: float,
    shard_dir: Path,
    year: int,
    month: int,
) -> Path:
    ym = f"{year}-{month:02d}"
    station_dir = shard_dir / str(station_id)
    station_dir.mkdir(parents=True, exist_ok=True)
    out_path = station_dir / f"{ym}.npz"
    np.savez_compressed(
        out_path,
        patch=payload['patch'],
        mask=payload['mask'],
        dates=np.array(payload['dates'], dtype='S10'),
        channels=np.array(payload['channels'], dtype=object),
        station_id=str(station_id),
        latitude=latitude,
        longitude=longitude,
    )
    return out_path


def shard_exists(shard_dir: Path, station_id: str, year: int, month: int) -> bool:
    return (shard_dir / str(station_id) / f"{year}-{month:02d}.npz").exists()


def main():
    parser = argparse.ArgumentParser(
        description='Download MODIS MOD10A1 patches (32x32, 2 vars) for Nordic stations via GEE.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--smhi-station-file', type=str,
                        default='data/raw/station_metadata.csv')
    parser.add_argument('--fmi-station-file', type=str,
                        default='data/raw/fmi_station_metadata.csv')
    parser.add_argument('--shard-dir', type=str,
                        default='data/processed/modis_patches')
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2024)
    parser.add_argument('--patch-size', type=int, default=32)
    parser.add_argument('--qa-max', type=int, default=QA_VALID_MAX,
                        help='Max QA value considered valid (default: 2 = best/good/ok)')
    parser.add_argument('--pilot', type=int, default=None,
                        help='If set, limit to first N stations')
    parser.add_argument('--gee-project', type=str, default=None,
                        help='GCP project ID linked to GEE (required for ee.Initialize)')
    args = parser.parse_args()

    ee = _check_ee()

    try:
        if args.gee_project:
            ee.Initialize(project=args.gee_project)
        else:
            ee.Initialize()
        logger.info(f"GEE initialised "
                    f"(project={args.gee_project or 'default'})")
    except Exception as e:
        logger.error(f"GEE initialisation failed: {e}")
        logger.error("Run `earthengine authenticate` and pass --gee-project <id>.")
        sys.exit(1)

    shard_dir = Path(args.shard_dir)
    shard_dir.mkdir(parents=True, exist_ok=True)

    stations = load_station_metadata(
        Path(args.smhi_station_file),
        Path(args.fmi_station_file),
        pilot_n=args.pilot,
    )

    year_months = build_year_month_list(args.start_year, args.end_year)
    logger.info(f"Year-month pairs to process: {len(year_months)}")

    total_requests = 0
    t0 = time.time()
    for i, (y, m) in enumerate(year_months, 1):
        logger.info(f"\n[{i}/{len(year_months)}] {y}-{m:02d}")
        for _, row in stations.iterrows():
            sid = row['station_id']
            lat = float(row['latitude'])
            lon = float(row['longitude'])

            if shard_exists(shard_dir, sid, y, m):
                continue

            payload = extract_modis_month(
                ee, lat, lon, y, m,
                patch_size=args.patch_size,
                qa_valid_max=args.qa_max,
            )
            total_requests += 1
            if payload is None:
                logger.warning(f"    station {sid}: extraction failed; skipping")
                continue

            save_station_shard(payload, sid, lat, lon, shard_dir, y, m)
            valid_frac = payload['mask'].mean()
            logger.info(f"    station {sid} ({lat:.2f}, {lon:.2f})  "
                        f"valid pixels: {valid_frac:.1%}")

    elapsed = time.time() - t0
    logger.info(f"\nDone. Issued {total_requests} GEE requests in {elapsed/60:.1f} min.")


if __name__ == '__main__':
    main()
