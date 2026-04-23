# SMHI SNOW DEPTH DATA DOWNLOAD - COMPREHENSIVE GUIDE

## TABLE OF CONTENTS
1. [Installation & Setup](#installation--setup)
2. [API Parameters & Configuration](#api-parameters--configuration)
3. [Station Coordinates & Codes](#station-coordinates--codes)
4. [Geographic Regions](#geographic-regions)
5. [Usage Examples](#usage-examples)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)
8. [Data Interpretation Guide](#data-interpretation-guide)
9. [Reference & Support](#reference--support)

---

## Installation & Setup

### System Requirements
```
Python: 3.8+
RAM: 2GB minimum (4GB recommended for full dataset)
Storage: 500MB free space
Internet: Stable connection
OS: Windows, macOS, or Linux
```

### Install Dependencies
```bash
pip install requests pandas openpyxl lxml --upgrade
```

### Quick Start
```bash
# 1. Save the script as: smhi_downloader.py
# 2. Run it:
python smhi_downloader.py

# 3. Check output in: ./smhi_data/ directory
```

---

## API Parameters & Configuration

### Coordinate Parameters (ESSENTIAL)

| Parameter | Type | Range | Description | Example |
|-----------|------|-------|-------------|---------|
| `min_lat` | Float | 55.0 - 70.0 | Minimum latitude (south) | 59.33 |
| `max_lat` | Float | 55.0 - 70.0 | Maximum latitude (north) | 59.34 |
| `min_lon` | Float | 10.0 - 28.0 | Minimum longitude (west) | 18.07 |
| `max_lon` | Float | 10.0 - 28.0 | Maximum longitude (east) | 18.08 |

**Important**: min_lat < max_lat AND min_lon < max_lon

### Date Parameters

| Parameter | Format | Default | Description |
|-----------|--------|---------|-------------|
| `start_date` | YYYY-MM-DD | 1 year ago | Earliest data to fetch |
| `end_date` | YYYY-MM-DD | Today | Latest data to fetch |

**Valid Range**: 1945-01-01 to 2026-01-16 (for some stations)

### Quality Control Parameters

| Code | Meaning | Data Type | Use When |
|------|---------|-----------|----------|
| `G` | Approved | **Green** ✓ | Need validated data only |
| `Y` | Suspect | **Yellow** ⚠️ | Need all available data |
| `None` | All | Mixed | Research/exploratory |

### Performance Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `timeout` | 30 sec | 10-60 | Request timeout |
| `max_retries` | 3 | 1-5 | Retry failed requests |
| `retry_delay` | 2 sec | 1-10 | Wait between retries |
| `request_delay` | 0.5 sec | 0.1-2 | Wait between API calls |

### Output Parameters

| Parameter | Options | Description |
|-----------|---------|-------------|
| `save_format` | csv, xlsx, json | Output file format |
| `output_dir` | Any path | Where to save data |

---

## Station Coordinates & Codes

### Top 30 Major Swedish Snow Measurement Stations

| ID | Station Name | Region | Latitude | Longitude | Elevation (m) | Active | Since |
|----|---|---|---|---|---|---|---|
| 97380 | Enköping | Uppsala | 59.6406 | 17.0655 | 14.31 | ✓ | 1945 |
| 86340 | Norrköping-SMHI | Östergötland | 58.5828 | 16.1470 | 40.33 | ✓ | 1993 |
| 97520 | Uppsala | Uppsala | 59.8471 | 17.6320 | 23.45 | ✓ | 1904 |
| 85250 | Linköping | Östergötland | 58.3479 | 15.6455 | 92.44 | ✓ | 1885 |
| 93250 | Karlstad-Skåre | Värmland | 59.4376 | 13.4329 | 49.30 | ✓ | 1885 |
| 72420 | Göteborg-Landvetter | Västergötland | 57.6678 | 12.2963 | 154 | ✓ | 1974 |
| 96230 | Eskilstuna | Södermanland | 59.3850 | 16.4598 | 9 | ✓ | 1945 |
| 83100 | Skövde | Västergötland | 58.3943 | 13.8406 | 146.59 | ✓ | 1945 |
| 86660 | Nyköping | Södermanland | 58.7545 | 17.0543 | 12 | ✓ | 1890 |
| 74470 | Jönköping | Småland | 57.7994 | 14.1313 | 180.84 | ✓ | 1904 |
| 64030 | Kristianstad | Skåne | 56.0221 | 14.1700 | -1.07 | ✓ | 1905 |
| 53230 | Trelleborg | Skåne | 55.3811 | 13.1195 | 2.57 | ✓ | 1945 |
| 62400 | Halmstad | Halland | 56.6768 | 12.9239 | 30.11 | ✓ | 1904 |
| 65090 | Karlskrona | Blekinge | 56.1670 | 15.5870 | 7 | ✓ | 1952 |
| 160140 | Stockholm-Observatorikullen A | Stockholm | 59.3417 | 18.0549 | 43.13 | ✓ | 2025 |
| 105370 | Falun-Lugnet | Dalarna | 60.6185 | 15.6574 | 161.40 | ✓ | 1881 |
| 114160 | Älvdalen 2 | Dalarna | 61.2549 | 14.0348 | 250 | ✗ | 1968 |
| 134110 | Östersund-Frösön Flygplats | Jämtland | 63.1981 | 14.4869 | 375.81 | ✓ | 1944 |
| 162860 | Luleå-Kallax Flygplats | Norrbotten | 65.5430 | 22.1240 | 19.91 | ✓ | 1946 |
| 180960 | Kiruna | Norrbotten | 67.8513 | 20.2497 | 518.80 | ✓ | 1898 |
| 117440 | Hudiksvall | Gävleborg | 61.7152 | 17.0829 | 12.1 | ✓ | 1945 |
| 127380 | Härnösand | Västernorrland | 62.6364 | 17.9214 | 17.65 | ✓ | 1881 |
| 138180 | Örnsköldsviks | Västernorrland | 63.3029 | 18.7252 | 47.23 | ✓ | 1945 |
| 140490 | Umeå-Röbäcksdalen | Västerbotten | 63.8109 | 20.2407 | 10.04 | ✓ | 1956 |
| 156820 | Abisko Aut | Norrbotten | 68.3538 | 18.8164 | 392.24 | ✓ | 1986 |
| 160630 | Haraliden | Norrbotten | 65.4500 | 20.1000 | 450 | ✗ | 1920 |
| 167790 | Svartberget | Västernorrland | 66.3227 | 17.3173 | 440.32 | ✓ | 2011 |
| 169930 | Randljaur | Norrbotten | 66.7610 | 19.3166 | 285 | ✗ | 1967 |
| 192830 | Kangos | Norrbotten | 67.5031 | 22.6622 | 231.73 | ✓ | 1988 |
| 192920 | Karesuando | Norrbotten | 68.4425 | 22.4453 | 330.92 | ✓ | 1895 |

### How to Find Station Codes

**Method 1: Automatic (Using Script)**
```python
downloader = SMHISnowDownloader(min_lat=59.0, max_lat=60.0, 
                                min_lon=17.0, max_lon=19.0)
stations = downloader.fetch_stations()
for station in stations:
    print(f"ID: {station['id']}, Name: {station['name']}, "
          f"Lat: {station['latitude']}, Lon: {station['longitude']}")
```

**Method 2: Manual Web Search**
Visit: https://www.smhi.se/data/nederbord-och-fuktighet/sno/snowDepth
- Click on station marker on map
- Note the station ID and coordinates

**Method 3: From Station Table**
- Southern table has latest ~500 stations
- Column headers: ID, Name, Owner, Latitude, Longitude, Height, From, To, Active

---

## Geographic Regions

### Swedish Regional Coordinates
```python
# ===== SOUTHERN SWEDEN (Skåne & Halland) =====
SKANE = {
    'name': 'Skåne',
    'min_lat': 55.3,
    'max_lat': 56.3,
    'min_lon': 12.0,
    'max_lon': 15.0,
    'stations_count': 15,
    'major_cities': ['Malmö', 'Lund', 'Kristianstad']
}

# ===== WEST COAST (Bohuslän & Västergötland) =====
WEST_COAST = {
    'name': 'West Coast',
    'min_lat': 57.0,
    'max_lat': 59.0,
    'min_lon': 11.0,
    'max_lon': 13.0,
    'stations_count': 22,
    'major_cities': ['Göteborg', 'Borås', 'Trollhättan']
}

# ===== STOCKHOLM REGION =====
STOCKHOLM = {
    'name': 'Stockholm & Surrounding',
    'min_lat': 59.1,
    'max_lat': 59.5,
    'min_lon': 17.5,
    'max_lon': 18.5,
    'stations_count': 8,
    'major_cities': ['Stockholm', 'Uppsala']
}

# ===== CENTRAL SWEDEN (Dalarna) =====
CENTRAL = {
    'name': 'Central Sweden (Dalarna)',
    'min_lat': 60.3,
    'max_lat': 61.5,
    'min_lon': 14.0,
    'max_lon': 16.5,
    'stations_count': 18,
    'major_cities': ['Falun', 'Borlänge', 'Ludvika']
}

# ===== NORTHERN SWEDEN (Västernorrland & Norrbotten) =====
NORTHERN = {
    'name': 'Northern Sweden',
    'min_lat': 64.5,
    'max_lat': 69.0,
    'min_lon': 17.0,
    'max_lon': 24.0,
    'stations_count': 45,
    'major_cities': ['Kiruna', 'Abisko', 'Luleå', 'Umeå']
}

# ===== ENTIRE SWEDEN =====
ALL_SWEDEN = {
    'name': 'All of Sweden',
    'min_lat': 55.0,
    'max_lat': 70.0,
    'min_lon': 10.0,
    'max_lon': 28.0,
    'stations_count': 500,
    'major_cities': ['All major cities']
}
```

### Mountain Regions (High Elevation)

| Region | Station | Coordinates | Elevation | Data Available |
|--------|---------|-------------|-----------|---|
| Sarek | Abisko | 68.36°N, 18.82°E | 392m | Since 1986 |
| Kebnekaise | Karesuando | 68.44°N, 22.45°E | 331m | Since 1895 |
| Vindelfjällen | Vindel-Björkheden | 65.82°N, 16.71°E | 350m | Since 1977 |

---

## Usage Examples

### Example 1: Download Data for Stockholm Region (Approved Data Only)
```python
from smhi_downloader import SMHISnowDownloader

downloader = SMHISnowDownloader(
    # Stockholm coordinates
    min_lat=59.1,
    max_lat=59.5,
    min_lon=17.5,
    max_lon=18.5,
    # Date range
    start_date="2023-01-01",
    end_date="2026-01-16",
    # Quality & Performance
    quality_code="G",  # Only approved data
    request_delay=0.5,
    # Output
    output_dir="./stockholm_snow_data"
)

# Fetch and download
df = downloader.download_all_data(save_format="csv")

# Print summary
stats = downloader.get_summary_statistics(df)
print(f"Total Records: {stats['total_records']}")
print(f"Stations: {stats['stations_count']}")
```

### Example 2: Download Northern Sweden Winter Data (2024-2025)
```python
downloader = SMHISnowDownloader(
    min_lat=64.5,
    max_lat=69.0,
    min_lon=17.0,
    max_lon=24.0,
    start_date="2024-10-01",  # Start of winter
    end_date="2025-04-30",    # End of winter
    quality_code=None,  # Get all data
    max_retries=5,
    output_dir="./northern_winter_2024"
)

df = downloader.download_all_data(save_format="xlsx")
```

### Example 3: Batch Download Multiple Regions
```python
regions = {
    'skane': {'min_lat': 55.3, 'max_lat': 56.3, 'min_lon': 12.0, 'max_lon': 15.0},
    'west_coast': {'min_lat': 57.0, 'max_lat': 59.0, 'min_lon': 11.0, 'max_lon': 13.0},
    'stockholm': {'min_lat': 59.1, 'max_lat': 59.5, 'min_lon': 17.5, 'max_lon': 18.5},
    'dalarna': {'min_lat': 60.3, 'max_lat': 61.5, 'min_lon': 14.0, 'max_lon': 16.5},
}

for region_name, coords in regions.items():
    downloader = SMHISnowDownloader(
        min_lat=coords['min_lat'],
        max_lat=coords['max_lat'],
        min_lon=coords['min_lon'],
        max_lon=coords['max_lon'],
        start_date="2024-01-01",
        end_date="2024-12-31",
        output_dir=f"./snow_data/{region_name}"
    )
    
    df = downloader.download_all_data(save_format="csv")
    print(f"\\n{region_name.upper()}: Downloaded {len(df)} records")
```

### Example 4: Download Single Specific Station
```python
# Find station: Falun-Lugnet (ID: 105370, Dalarna)
downloader = SMHISnowDownloader(
    # Very small region around Falun
    min_lat=60.61,
    max_lat=60.62,
    min_lon=15.65,
    max_lon=15.66,
    start_date="2020-01-01",
    end_date="2026-01-16"
)

df = downloader.download_all_data(save_format="json")
print(df.head())  # Show first 5 records
```

---

## Troubleshooting

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `404 Not Found` | Wrong API URL | Use: `opendata-download-metobs.smhi.se` |
| `Timeout Error` | Slow internet | Increase `timeout` to 60 |
| `No stations found` | Coordinates outside Sweden | Check: Lat 55-70, Lon 10-28 |
| `Empty DataFrame` | No data in date range | Check station dates (From/To) |
| `Rate Limit (429)` | Too many requests | Increase `request_delay` to 2.0 |
| `Connection refused` | Network issue | Wait 60 seconds, try again |
| `ValueError: No JSON object` | Corrupted response | Retry with `max_retries=5` |

### Checking Station Availability
```python
# Before downloading, verify the station has data
downloader = SMHISnowDownloader(
    min_lat=59.34,
    max_lat=59.34,
    min_lon=18.08,
    max_lon=18.08
)

stations = downloader.fetch_stations()
for s in stations:
    print(f"Station: {s['name']}")
    print(f"  - Active: {s.get('active', 'Unknown')}")
    print(f"  - From: {s.get('from', 'Unknown')}")
    print(f"  - To: {s.get('to', 'Unknown')}")
```

### Debug Mode
```python
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

downloader = SMHISnowDownloader(...)
df = downloader.download_all_data()  # Will print detailed logs
```

---

## Best Practices

### Performance Optimization
```python
# ✓ DO: Use reasonable geographic bounds
downloader = SMHISnowDownloader(
    min_lat=60.0, max_lat=61.0,  # ~100 km x 100 km
    min_lon=15.0, max_lon=16.0
)

# ✗ DON'T: Download entire Sweden at once
# downloader = SMHISnowDownloader(
#     min_lat=55.0, max_lat=70.0,  # 500+ stations
#     min_lon=10.0, max_lon=28.0
# )
```

### Data Quality Management
```python
# Always use quality filtering for research
downloader = SMHISnowDownloader(
    quality_code="G",  # Approved data only
    ...
)

# For exploratory analysis, use all data
downloader = SMHISnowDownloader(
    quality_code=None,  # All quality levels
    ...
)
```

### Rate Limiting Etiquette
```python
# SMHI recommends:
# - Max 2-5 requests/second
# - Don't spam the API

downloader = SMHISnowDownloader(
    request_delay=1.0,   # 1 second between requests
    timeout=30,
    max_retries=3,
    retry_delay=5  # Wait longer before retry
)
```

### Storage Management
```python
# Use compression for large downloads
import gzip

df = downloader.download_all_data(save_format="csv")

# Compress after download
import os
with open('snow_data.csv', 'rb') as f_in:
    with gzip.open('snow_data.csv.gz', 'wb') as f_out:
        f_out.writelines(f_in)
os.remove('snow_data.csv')  # Delete original
```

### Scheduling Regular Downloads
```python
# Using schedule library for daily updates
import schedule
import time

def daily_download():
    downloader = SMHISnowDownloader(...)
    downloader.download_all_data()

schedule.every().day.at("02:00").do(daily_download)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Data Interpretation Guide

### Understanding Snow Depth Values

| Value | Meaning | Interpretation |
|-------|---------|---|
| `0.0` | Bare ground | No snow cover |
| `0.1 - 0.5` | Sparse snow | Less than 5 cm |
| `0.5 - 1.0` | Light snow | 5-10 cm |
| `1.0 - 2.0` | Moderate snow | 10-20 cm |
| `> 2.0` | Heavy snow | >20 cm |
| `-0.01` | <0.5 cm | Spotted with snow |
| `-0.02` | Spotted | Small amounts |
| `NaN` | Missing | Data unavailable |

### Quality Code Explanation

- **G (Green)**: Data reviewed and approved by SMHI experts
- **Y (Yellow)**: Suspected errors, use with caution
- **Unknown**: Data not yet verified

---

## Reference & Support

### SMHI API Documentation

**Base URL**: `https://opendata-download-metobs.smhi.se`

**Key Endpoints**:
```
/api/version/latest/stations
/api/version/latest/parameter/{id}/station/{id}/period/{period}/data.json
```

**Parameter ID for Snow Depth**: `1`

**Time Periods**:
- `latest-months`: Last 1-2 months
- `latest-years`: Last 5-10 years
- Specific range: `from-{date}/to-{date}`

### Support Channels

- **SMHI Customer Service**: https://www.smhi.se/kundbetjaning/
- **Email**: kundtjanst@smhi.se
- **API Issues**: Check API status at https://opendata.smhi.se/
- **Documentation**: https://opendata.smhi.se/apidocs/

---

## Data Restrictions & Download Limits

### Free Access

✅ **No authentication required**
✅ **No download limits documented**
✅ **Unrestricted for reasonable use**
✅ **CC0 / CC-BY license (free to use)**

### Commercial Use

🔒 **Requires authorization key from SMHI**
💰 **Usage is bound to a charge**
📧 **Contact**: https://www.smhi.se/kundbetjaning/

### API Rate Limits

- **Recommended**: 2-5 requests/second
- **Respectful**: Use `request_delay` parameter
- **Timeout**: Default 30 seconds

---

**Last Updated**: January 2026  
**Document Version**: 1.0  
**Author**: SMHI Data Download Guide  
**License**: CC0 (Public Domain)