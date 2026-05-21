#!/usr/bin/env python3
"""
Bulk download MESAN GRIB files from SMHI Grid Archive.

Downloads one MESAN analysis file per day (06:00 UTC) for winter months
(October-April) across multiple years. Includes retry logic, resume
capability, and progress tracking.

SMHI Grid Archive structure:
    Feed:     https://opendata-download-grid-archive.smhi.se/feed/6
    Download: https://opendata-download-grid-archive.smhi.se/data/6/{YYYYMM}/MESAN_{YYYYMMDDHHMM}+000H00M

Usage:
    # Download all winters 2015-2024 (default)
    python scripts/download_mesan_bulk.py

    # Download a specific winter season
    python scripts/download_mesan_bulk.py --start-year 2020 --end-year 2021

    # Download specific months
    python scripts/download_mesan_bulk.py --start-date 2024-01-01 --end-date 2024-01-31

    # Test with a few files
    python scripts/download_mesan_bulk.py --max-files 5

    # Use different hour (default 06:00 UTC)
    python scripts/download_mesan_bulk.py --hour 12
"""

import argparse
import json
import requests
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SMHI Grid Archive configuration
BASE_URL = "https://opendata-download-grid-archive.smhi.se"
FEED_URL = f"{BASE_URL}/feed/6"
DATA_URL = f"{BASE_URL}/data/6"
MESAN_PRODUCT_ID = 6

# Winter months (October through April)
WINTER_MONTHS = [10, 11, 12, 1, 2, 3, 4]


def get_download_url(year: int, month: int, day: int, hour: int) -> str:
    """
    Construct direct MESAN file download URL.

    URL Pattern: /data/6/{YYYYMM}/MESAN_{YYYYMMDDHHMM}+000H00M
    """
    yyyymm = f"{year:04d}{month:02d}"
    timestamp = f"{year:04d}{month:02d}{day:02d}{hour:02d}00"
    filename = f"MESAN_{timestamp}+000H00M"
    return f"{DATA_URL}/{yyyymm}/{filename}"


def get_filename(year: int, month: int, day: int, hour: int) -> str:
    """Get the MESAN filename for a given date/time."""
    timestamp = f"{year:04d}{month:02d}{day:02d}{hour:02d}00"
    return f"MESAN_{timestamp}+000H00M"


def download_file(
    url: str,
    output_path: Path,
    max_retries: int = 3,
    retry_delay: float = 5.0,
    timeout: int = 300
) -> bool:
    """
    Download a single file with retry logic.

    Args:
        url: Download URL
        output_path: Where to save the file
        max_retries: Maximum number of retry attempts
        retry_delay: Seconds to wait between retries
        timeout: Request timeout in seconds

    Returns:
        True if download succeeded, False otherwise
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, stream=True)

            if resp.status_code == 200:
                # Write to temporary file first, then rename (atomic)
                tmp_path = output_path.with_suffix('.tmp')
                with open(tmp_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        f.write(chunk)

                # Verify file is not empty or suspiciously small
                file_size = tmp_path.stat().st_size
                if file_size < 1000:
                    logger.warning(f"File too small ({file_size} bytes), likely error response")
                    tmp_path.unlink()
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    return False

                # Rename to final path
                tmp_path.rename(output_path)
                return True

            elif resp.status_code == 404:
                # File doesn't exist on server (e.g., date before MESAN started)
                logger.debug(f"Not found (404): {output_path.name}")
                return False

            else:
                logger.warning(
                    f"HTTP {resp.status_code} for {output_path.name} "
                    f"(attempt {attempt}/{max_retries})"
                )

        except requests.exceptions.Timeout:
            logger.warning(
                f"Timeout downloading {output_path.name} "
                f"(attempt {attempt}/{max_retries})"
            )
        except requests.exceptions.ConnectionError:
            logger.warning(
                f"Connection error for {output_path.name} "
                f"(attempt {attempt}/{max_retries})"
            )
        except Exception as e:
            logger.warning(
                f"Error downloading {output_path.name}: {e} "
                f"(attempt {attempt}/{max_retries})"
            )

        if attempt < max_retries:
            time.sleep(retry_delay * attempt)  # Exponential backoff

    return False


def generate_winter_dates(
    start_year: int,
    end_year: int,
    winter_months: List[int] = None
) -> List[datetime]:
    """
    Generate list of dates for winter months across years.

    A "winter season" spans Oct of year N to Apr of year N+1.
    For start_year=2015, end_year=2024, generates:
        Oct 2015 - Apr 2016, Oct 2016 - Apr 2017, ..., Oct 2023 - Apr 2024

    Args:
        start_year: First year (October of this year starts first winter)
        end_year: Last year (April of this year ends last winter)
        winter_months: Months to include (default: Oct-Apr)

    Returns:
        Sorted list of dates
    """
    if winter_months is None:
        winter_months = WINTER_MONTHS

    dates = []

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if month not in winter_months:
                continue

            # Determine number of days in this month
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            days_in_month = (next_month - datetime(year, month, 1)).days

            for day in range(1, days_in_month + 1):
                dates.append(datetime(year, month, day))

    dates.sort()
    return dates


def generate_date_range(start_date: str, end_date: str) -> List[datetime]:
    """Generate list of dates from start to end (inclusive)."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)

    return dates


def load_progress(progress_file: Path) -> Dict:
    """Load download progress from file."""
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {'downloaded': [], 'failed': [], 'skipped': []}


def save_progress(progress_file: Path, progress: Dict) -> None:
    """Save download progress to file."""
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)


def download_mesan_bulk(
    output_dir: str = "data/raw/mesan",
    start_year: int = 2015,
    end_year: int = 2024,
    start_date: str = None,
    end_date: str = None,
    hour: int = 6,
    max_files: int = None,
    max_retries: int = 3,
    delay: float = 0.5,
    overwrite: bool = False,
    organize_by_year: bool = True
) -> Dict:
    """
    Download MESAN GRIB files in bulk.

    Args:
        output_dir: Base output directory
        start_year: First year for winter downloads
        end_year: Last year for winter downloads
        start_date: Specific start date (overrides start_year/end_year)
        end_date: Specific end date (overrides start_year/end_year)
        hour: UTC hour to download (default 6 = 06:00 UTC)
        max_files: Maximum number of files to download (for testing)
        max_retries: Retry attempts per file
        delay: Seconds between downloads (rate limiting)
        overwrite: Overwrite existing files
        organize_by_year: Create year subdirectories

    Returns:
        Dictionary with download statistics
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Progress tracking
    progress_file = output_dir / '_download_progress.json'
    progress = load_progress(progress_file)
    already_downloaded = set(progress['downloaded'])

    # Generate date list
    if start_date and end_date:
        dates = generate_date_range(start_date, end_date)
        logger.info(f"Date range mode: {start_date} to {end_date}")
    else:
        dates = generate_winter_dates(start_year, end_year)
        logger.info(f"Winter mode: Oct {start_year} to Apr {end_year}")

    total_dates = len(dates)
    if max_files:
        dates = dates[:max_files]

    logger.info(f"Total dates to process: {len(dates)} (of {total_dates} total)")
    logger.info(f"Download hour: {hour:02d}:00 UTC")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Already downloaded: {len(already_downloaded)} files")

    # Statistics
    stats = {
        'total': len(dates),
        'downloaded': 0,
        'skipped_exists': 0,
        'skipped_already': 0,
        'failed': 0,
        'total_size_mb': 0.0
    }

    start_time = time.time()

    for i, date in enumerate(dates):
        filename = get_filename(date.year, date.month, date.day, hour)

        # Check if already downloaded in previous run
        if filename in already_downloaded and not overwrite:
            stats['skipped_already'] += 1
            continue

        # Determine output path
        if organize_by_year:
            year_dir = output_dir / str(date.year)
            year_dir.mkdir(exist_ok=True)
            file_path = year_dir / filename
        else:
            file_path = output_dir / filename

        # Check if file already exists on disk
        if file_path.exists() and not overwrite:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > 0.01:  # Not empty
                stats['skipped_exists'] += 1
                stats['total_size_mb'] += size_mb
                progress['downloaded'].append(filename)
                already_downloaded.add(filename)
                continue

        # Download
        url = get_download_url(date.year, date.month, date.day, hour)
        success = download_file(url, file_path, max_retries=max_retries)

        if success:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            stats['downloaded'] += 1
            stats['total_size_mb'] += size_mb
            progress['downloaded'].append(filename)
            already_downloaded.add(filename)

            # Progress reporting
            processed = stats['downloaded'] + stats['skipped_exists'] + stats['skipped_already'] + stats['failed']
            elapsed = time.time() - start_time
            rate = stats['downloaded'] / elapsed if elapsed > 0 else 0
            remaining = (len(dates) - processed) / rate if rate > 0 else 0

            if stats['downloaded'] % 10 == 0 or stats['downloaded'] <= 3:
                logger.info(
                    f"[{processed}/{len(dates)}] "
                    f"Downloaded: {filename} ({size_mb:.1f} MB) | "
                    f"Total: {stats['total_size_mb']:.0f} MB | "
                    f"Rate: {rate:.1f} files/s | "
                    f"ETA: {remaining/60:.0f} min"
                )
        else:
            stats['failed'] += 1
            progress['failed'].append(filename)
            logger.warning(f"Failed: {filename}")

        # Save progress periodically
        if (stats['downloaded'] + stats['failed']) % 50 == 0:
            save_progress(progress_file, progress)

        # Rate limiting
        if success:
            time.sleep(delay)

    # Final progress save
    save_progress(progress_file, progress)

    # Summary
    elapsed = time.time() - start_time
    logger.info("")
    logger.info("=" * 60)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Total dates:      {stats['total']}")
    logger.info(f"  Downloaded:       {stats['downloaded']}")
    logger.info(f"  Skipped (exists): {stats['skipped_exists']}")
    logger.info(f"  Skipped (prev):   {stats['skipped_already']}")
    logger.info(f"  Failed:           {stats['failed']}")
    logger.info(f"  Total size:       {stats['total_size_mb']:.1f} MB ({stats['total_size_mb']/1024:.2f} GB)")
    logger.info(f"  Elapsed time:     {elapsed/60:.1f} minutes")
    logger.info(f"  Output:           {output_dir}")

    if stats['failed'] > 0:
        logger.warning(f"\n  {stats['failed']} files failed. Re-run the script to retry them.")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Bulk download MESAN GRIB files from SMHI Grid Archive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all winter months 2015-2024
  python scripts/download_mesan_bulk.py

  # Download a single winter season
  python scripts/download_mesan_bulk.py --start-year 2023 --end-year 2024

  # Download specific date range
  python scripts/download_mesan_bulk.py --start-date 2024-01-01 --end-date 2024-03-31

  # Test with 5 files
  python scripts/download_mesan_bulk.py --max-files 5

  # Re-download failed files (already-downloaded are skipped)
  python scripts/download_mesan_bulk.py
        """
    )

    parser.add_argument('--output', type=str, default='data/raw/mesan',
                        help='Output directory (default: data/raw/mesan)')
    parser.add_argument('--start-year', type=int, default=2015,
                        help='Start year for winter downloads (default: 2015)')
    parser.add_argument('--end-year', type=int, default=2024,
                        help='End year for winter downloads (default: 2024)')
    parser.add_argument('--start-date', type=str, default=None,
                        help='Specific start date YYYY-MM-DD (overrides year range)')
    parser.add_argument('--end-date', type=str, default=None,
                        help='Specific end date YYYY-MM-DD (overrides year range)')
    parser.add_argument('--hour', type=int, default=6,
                        help='UTC hour to download (default: 6 = 06:00 UTC)')
    parser.add_argument('--max-files', type=int, default=None,
                        help='Maximum files to download (for testing)')
    parser.add_argument('--max-retries', type=int, default=3,
                        help='Retry attempts per file (default: 3)')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Seconds between downloads (default: 0.5)')
    parser.add_argument('--overwrite', action='store_true',
                        help='Overwrite existing files')
    parser.add_argument('--flat', action='store_true',
                        help='Do not organize by year subdirectories')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if args.start_date and not args.end_date:
        parser.error("--end-date is required when --start-date is specified")
    if args.end_date and not args.start_date:
        parser.error("--start-date is required when --end-date is specified")

    stats = download_mesan_bulk(
        output_dir=args.output,
        start_year=args.start_year,
        end_year=args.end_year,
        start_date=args.start_date,
        end_date=args.end_date,
        hour=args.hour,
        max_files=args.max_files,
        max_retries=args.max_retries,
        delay=args.delay,
        overwrite=args.overwrite,
        organize_by_year=not args.flat
    )


if __name__ == '__main__':
    main()
