#!/usr/bin/env python3
"""
SMHI Snow Depth Data Downloader
Downloads snow depth measurements from SMHI stations within specified geographic bounds
Author: Your Name
License: CC0
"""

import requests
import pandas as pd
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('smhi_downloader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SMHISnowDownloader:
    """
    Download snow depth data from SMHI stations within geographic bounds.
    
    Example usage:
```
    downloader = SMHISnowDownloader(
        min_lat=55.0,
        max_lat=68.0,
        min_lon=12.0,
        max_lon=24.0,
        start_date="2024-01-01",
        end_date="2026-01-16"
    )
    downloader.download_all_data()
```
    """
    
    # API Endpoints
    BASE_URL = "https://opendata-download-metobs.smhi.se"
    STATION_LIST_URL = "https://opendata-download-metobs.smhi.se/api/version/latest/stations"
    
    # Parameters for snow depth measurements
    PARAMETER_ID_SNOW_DEPTH = "1"  # Snow depth daily value
    QUALITY_LEVELS = ["G", "Y", "unknown"]  # G=approved, Y=suspect, unknown
    
    def __init__(
        self,
        min_lat: float = 55.0,
        max_lat: float = 70.0,
        min_lon: float = 10.0,
        max_lon: float = 24.0,
        start_date: str = None,
        end_date: str = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        request_delay: float = 0.5,
        quality_code: str = "G",
        output_dir: str = "./smhi_data"
    ):
        """
        Initialize the downloader with geographic and temporal bounds.
        
        Args:
            min_lat: Minimum latitude (decimal degrees)
            max_lat: Maximum latitude (decimal degrees)
            min_lon: Minimum longitude (decimal degrees)
            max_lon: Maximum longitude (decimal degrees)
            start_date: Start date (YYYY-MM-DD). Default: 1 year ago
            end_date: End date (YYYY-MM-DD). Default: today
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Delay between retries in seconds
            request_delay: Delay between requests (for rate limiting)
            quality_code: Quality filter ("G"=approved, "Y"=suspect, None=all)
            output_dir: Output directory for saved data
        """
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_delay = request_delay
        self.quality_code = quality_code
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Set date range
        if end_date is None:
            self.end_date = datetime.now().strftime("%Y-%m-%d")
        else:
            self.end_date = end_date
            
        if start_date is None:
            # Default to 1 year ago
            start = datetime.strptime(self.end_date, "%Y-%m-%d") - timedelta(days=365)
            self.start_date = start.strftime("%Y-%m-%d")
        else:
            self.start_date = start_date
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SMHI-DataDownloader/1.0 (Python requests)'
        })
        
        self.stations = []
        self.data_cache = {}
        
        logger.info(f"Initialized downloader for region: "
                   f"Lat[{min_lat},{max_lat}] Lon[{min_lon},{max_lon}]")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
        logger.info(f"Quality filter: {quality_code if quality_code else 'all'}")
    
    def _make_request(self, url: str, params: Dict = None) -> Dict:
        """
        Make HTTP request with retry logic and rate limiting.
        
        Args:
            url: URL to request
            params: Query parameters
            
        Returns:
            Response JSON
            
        Raises:
            Exception: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.request_delay)  # Rate limiting
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt+1}/{self.max_retries} for {url}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error on attempt {attempt+1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from {url}: {e}")
                raise
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error: {e.response.status_code} for {url}")
                if e.response.status_code == 429:  # Rate limited
                    logger.warning("Rate limited by SMHI. Waiting longer...")
                    time.sleep(self.retry_delay * 5)
                elif attempt == self.max_retries - 1:
                    raise
        
        raise Exception(f"Failed to fetch {url} after {self.max_retries} retries")
    
    def fetch_stations(self) -> List[Dict]:
        """
        Fetch all available snow measurement stations.
        
        Returns:
            List of station dictionaries with metadata
        """
        logger.info("Fetching station list...")
        
        try:
            data = self._make_request(self.STATION_LIST_URL)
            
            # Filter stations by geographic bounds
            all_stations = data.get('station', [])
            filtered = []
            
            for station in all_stations:
                try:
                    lat = float(station.get('latitude', 0))
                    lon = float(station.get('longitude', 0))
                    
                    if (self.min_lat <= lat <= self.max_lat and 
                        self.min_lon <= lon <= self.max_lon):
                        filtered.append(station)
                except (ValueError, TypeError):
                    continue
            
            self.stations = filtered
            logger.info(f"Found {len(filtered)} stations in geographic range")
            return filtered
            
        except Exception as e:
            logger.error(f"Failed to fetch stations: {e}")
            raise
    
    def get_station_data(self, station_id: int) -> Optional[pd.DataFrame]:
        """
        Download snow depth data for a specific station.
        
        Args:
            station_id: SMHI station ID
            
        Returns:
            DataFrame with snow depth measurements or None if failed
        """
        try:
            # SMHI API endpoint for station data
            url = f"{self.BASE_URL}/api/version/latest/parameter/{self.PARAMETER_ID_SNOW_DEPTH}/station/{station_id}/period/latest-months/data.json"
            
            logger.info(f"Downloading data for station {station_id}...")
            data = self._make_request(url)
            
            # Parse the response
            measurements = data.get('value', [])
            
            if not measurements:
                logger.warning(f"No data found for station {station_id}")
                return None
            
            # Convert to DataFrame
            records = []
            for measurement in measurements:
                timestamp = measurement.get('timestamp')
                value = measurement.get('value')
                quality = measurement.get('quality', 'unknown')
                
                # Filter by quality if specified
                if self.quality_code and quality != self.quality_code:
                    continue
                
                records.append({
                    'timestamp': timestamp,
                    'value': value,
                    'quality': quality,
                    'station_id': station_id
                })
            
            if records:
                df = pd.DataFrame(records)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                logger.info(f"Downloaded {len(df)} records for station {station_id}")
                return df
            else:
                logger.info(f"No records matching quality filter for station {station_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to download data for station {station_id}: {e}")
            return None
    
    def download_all_data(self, save_format: str = "csv") -> pd.DataFrame:
        """
        Download snow depth data from all stations in the geographic range.
        
        Args:
            save_format: Output format ("csv", "xlsx", or "json")
            
        Returns:
            Combined DataFrame with all station data
        """
        if not self.stations:
            logger.info("Fetching stations first...")
            self.fetch_stations()
        
        if not self.stations:
            logger.error("No stations found in specified range")
            return pd.DataFrame()
        
        all_data = []
        failed_stations = []
        
        logger.info(f"Starting download from {len(self.stations)} stations...")
        
        for i, station in enumerate(self.stations, 1):
            station_id = station.get('id')
            station_name = station.get('name', 'Unknown')
            
            logger.info(f"[{i}/{len(self.stations)}] Processing station {station_id} ({station_name})")
            
            df = self.get_station_data(station_id)
            
            if df is not None:
                # Add station metadata
                df['station_name'] = station_name
                df['latitude'] = station.get('latitude')
                df['longitude'] = station.get('longitude')
                df['height'] = station.get('height', 0)
                all_data.append(df)
            else:
                failed_stations.append((station_id, station_name))
        
        # Combine all data
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Downloaded data from {len(all_data)} stations")
            logger.info(f"Failed stations: {len(failed_stations)}")
            
            # Save data
            self._save_data(combined_df, save_format)
            
            return combined_df
        else:
            logger.error("No data downloaded from any station")
            return pd.DataFrame()
    
    def _save_data(self, df: pd.DataFrame, format: str):
        """
        Save downloaded data to file.
        
        Args:
            df: DataFrame to save
            format: File format (csv, xlsx, json)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            if format == "csv":
                filepath = self.output_dir / f"snow_depth_{timestamp}.csv"
                df.to_csv(filepath, index=False)
                logger.info(f"Saved CSV to {filepath}")
                
            elif format == "xlsx":
                filepath = self.output_dir / f"snow_depth_{timestamp}.xlsx"
                df.to_excel(filepath, index=False)
                logger.info(f"Saved XLSX to {filepath}")
                
            elif format == "json":
                filepath = self.output_dir / f"snow_depth_{timestamp}.json"
                df.to_json(filepath, orient='records', date_format='iso')
                logger.info(f"Saved JSON to {filepath}")
            
            # Also save metadata
            metadata = {
                'download_date': datetime.now().isoformat(),
                'geographic_bounds': {
                    'min_lat': self.min_lat,
                    'max_lat': self.max_lat,
                    'min_lon': self.min_lon,
                    'max_lon': self.max_lon
                },
                'date_range': {
                    'start': self.start_date,
                    'end': self.end_date
                },
                'total_records': len(df),
                'stations_count': df['station_id'].nunique(),
                'quality_filter': self.quality_code
            }
            
            metadata_file = self.output_dir / f"metadata_{timestamp}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to {metadata_file}")
            
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def get_summary_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Generate summary statistics for downloaded data.
        
        Args:
            df: DataFrame with snow measurements
            
        Returns:
            Dictionary with statistics
        """
        if df.empty:
            return {}
        
        stats = {
            'total_records': len(df),
            'stations_count': df['station_id'].nunique(),
            'date_range': {
                'min': df['timestamp'].min().isoformat(),
                'max': df['timestamp'].max().isoformat()
            },
            'snow_depth_stats': {
                'mean': float(df['value'].mean()),
                'min': float(df['value'].min()),
                'max': float(df['value'].max()),
                'std': float(df['value'].std())
            },
            'quality_distribution': df['quality'].value_counts().to_dict(),
            'records_per_station': int(len(df) / df['station_id'].nunique())
        }
        
        return stats


def main():
    """Example usage of the downloader."""
    
    # Customize these parameters
    downloader = SMHISnowDownloader(
        min_lat=55.0,      # Southern Sweden
        max_lat=68.0,      # Northern Sweden
        min_lon=12.0,      # Western limit
        max_lon=24.0,      # Eastern limit
        start_date="2024-01-01",
        end_date="2026-01-16",
        quality_code="G",  # Only approved data (remove for all)
        output_dir="./snow_data",
        request_delay=0.5  # 500ms between requests
    )
    
    # Download all data
    df = downloader.download_all_data(save_format="csv")
    
    # Print summary
    if not df.empty:
        stats = downloader.get_summary_statistics(df)
        print("\\n=== Download Summary ===")
        print(json.dumps(stats, indent=2, default=str))
        print(f"\\nData saved to: {downloader.output_dir}")


if __name__ == "__main__":
    main()