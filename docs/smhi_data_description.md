# SMHI Data Description & Guidelines

## Comprehensive Reference for Nordic Snow Monitoring Project

**Document Version**: 1.0
**Last Updated**: January 2025
**Data Source**: Swedish Meteorological and Hydrological Institute (SMHI)
**Data Period**: 2015-01-01 to 2025-10-01

---

## Table of Contents

1. [Overview](#1-overview)
2. [Data Source](#2-data-source)
3. [Downloaded Parameters](#3-downloaded-parameters)
4. [Parameter Details](#4-parameter-details)
5. [Station Coverage](#5-station-coverage)
6. [Key Parameters for Snow Monitoring](#6-key-parameters-for-snow-monitoring)
7. [Data Quality](#7-data-quality)
8. [File Structure](#8-file-structure)
9. [Recommendations](#9-recommendations)
10. [Usage Examples](#10-usage-examples)

---

## 1. Overview

### Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Parameters Downloaded** | 32 out of 39 defined |
| **Total Unique Stations** | 936 |
| **Date Range** | 2015-01-01 to 2025-10-01 |
| **Total Data Size** | ~1.1 GB |
| **Primary Target** | Snow Depth (param 8) |

### What This Data Contains

This dataset comprises meteorological observations from SMHI's network of weather stations across Sweden. Each parameter is stored in a separate CSV file, enabling flexible analysis and merging based on specific research needs.

### Key Finding

**Critical Insight**: Different stations measure different parameters. Only ~87 stations (9%) have 15+ parameters, while 626 stations (67%) have only 2 parameters. This sparse coverage is the fundamental challenge for multi-parameter analysis.

---

## 2. Data Source

### SMHI Open Data API

- **API Base URL**: `https://opendata-download-metobs.smhi.se/api/version/1.0`
- **Documentation**: https://opendata.smhi.se/apidocs/metobs/
- **License**: Open data (CC0 for most parameters)
- **Update Frequency**: Near real-time for most stations

### Data Collection Method

Data was downloaded using the `corrected-archive` period, which provides quality-controlled historical observations. Each station-parameter combination was queried individually, then aggregated to daily values using appropriate methods (mean, sum, max, min, or last depending on parameter type).

---

## 3. Downloaded Parameters

### Complete Parameter List (32 Parameters)

| ID | Name | Description | Unit | Stations | Records | Aggregation |
|----|------|-------------|------|----------|---------|-------------|
| 1 | temp_1min | Air temperature (1-min samples) | °C | 295 | 1,017,296 | mean |
| 3 | wind_dir | Wind direction | ° | 184 | 682,773 | mean |
| 4 | wind_speed | Wind speed (10-min mean) | m/s | 184 | 685,749 | mean |
| 6 | precip_6h | Precipitation (6-hourly) | mm | 182 | 679,219 | sum |
| 7 | precip_15min | Precipitation (15-min) | mm | 210 | 575,456 | sum |
| **8** | **snow_depth** | **Snow depth (daily)** | **m** | **659** | **1,616,151** | **last** |
| 9 | pressure_sea | Sea-level pressure | hPa | 120 | 448,061 | mean |
| 10 | sunshine | Sunshine duration | s | 19 | 74,608 | sum |
| 11 | global_irrad | Global irradiance | W/m² | 17 | 66,743 | mean |
| 12 | longwave_irrad | Longwave irradiance | W/m² | 170 | 623,709 | mean |
| 13 | visibility | Visibility | m | 168 | 631,848 | mean |
| 14 | precip_hourly | Precipitation (hourly) | mm | 190 | 498,850 | sum |
| 15 | precip_intensity | Precipitation intensity | mm/h | 8 | 4,190 | mean |
| 16 | cloud_cover | Total cloud cover | % | 114 | 410,487 | mean |
| 21 | wind_gust | Wind gust speed | m/s | 158 | 599,517 | max |
| 24 | snow_cover | Snow cover presence | code | 7 | 26,751 | last |
| 25 | wind_speed_max | Wind speed (daily max) | m/s | 138 | 533,131 | max |
| 26 | temp_min_grass | Min temperature at grass | °C | 247 | 890,708 | min |
| 27 | temp_min_bare | Min temperature (bare ground) | °C | 247 | 890,711 | min |
| 28 | cloud_base | Cloud base height (lowest) | m | 129 | 394,950 | mean |
| 29 | humidity | Relative humidity | % | 130 | 399,004 | mean |
| 30 | cloud_base_2 | Cloud base height (2nd layer) | m | 127 | 337,364 | mean |
| 31 | cloud_base_3 | Cloud base height (3rd layer) | m | 127 | 363,439 | mean |
| 32 | cloud_base_4 | Cloud base height (4th layer) | m | 127 | 229,812 | mean |
| 33 | cloud_amount_1 | Cloud amount (1st layer) | code | 127 | 288,756 | mean |
| 34 | cloud_amount_2 | Cloud amount (2nd layer) | code | 109 | 96,380 | mean |
| 35 | cloud_amount_3 | Cloud amount (3rd layer) | code | 109 | 192,739 | mean |
| 36 | cloud_amount_4 | Cloud amount (4th layer) | code | 138 | 429,531 | mean |
| 37 | weather_wawa | Present weather (WaWa code) | code | 90 | 200,133 | last |
| 38 | thunder | Thunder indicator | code | 124 | 470,661 | max |
| 39 | dew_point | Dew point temperature | °C | 183 | 679,182 | mean |
| 40 | ground_state | Ground state code | code | 658 | 1,666,837 | last |

### Parameters NOT Downloaded (7 Parameters)

These parameters were defined but not downloaded (API returned no data or errors):

| ID | Name | Description | Reason |
|----|------|-------------|--------|
| 2 | temp_mean | Air temperature (daily mean) | No corrected-archive data |
| 5 | precip_sum | Precipitation (daily sum) | No corrected-archive data |
| 17 | precip_2x_daily | Precipitation (2x daily) | No corrected-archive data |
| 19 | temp_min | Air temperature (daily min) | No corrected-archive data |
| 20 | temp_max | Air temperature (daily max) | No corrected-archive data |
| 22 | precip_type | Precipitation type code | No corrected-archive data |
| 23 | snow_type | Snow type code | No corrected-archive data |

**Note**: Parameters 2, 5, 19, 20 are critical for snow monitoring. Consider alternative sources or use proxies:
- Use `temp_1min` (param 1) as temperature proxy (295 stations)
- Use `dew_point` (param 39) as temperature-related feature (183 stations)
- Use `precip_6h` or `precip_hourly` instead of `precip_sum`

---

## 4. Parameter Details

### Temperature Parameters

| Parameter | Coverage | Use Case | Notes |
|-----------|----------|----------|-------|
| **temp_1min** (1) | 295 stations | Primary temperature | Best coverage for temperature |
| **temp_min_grass** (26) | 247 stations | Cold events | Measured at grass level |
| **temp_min_bare** (27) | 247 stations | Ground temperature | Measured on bare ground |
| **dew_point** (39) | 183 stations | Humidity/condensation | Good temperature proxy |

### Precipitation Parameters

| Parameter | Coverage | Use Case | Notes |
|-----------|----------|----------|-------|
| **precip_6h** (6) | 182 stations | Daily precipitation | Aggregate to daily sum |
| **precip_15min** (7) | 210 stations | Intense events | High temporal resolution |
| **precip_hourly** (14) | 190 stations | General precipitation | Good coverage |
| **precip_intensity** (15) | 8 stations | Rain intensity | Very limited coverage |

### Snow Parameters

| Parameter | Coverage | Use Case | Notes |
|-----------|----------|----------|-------|
| **snow_depth** (8) | 659 stations | **PRIMARY TARGET** | Best coverage, most important |
| **snow_cover** (24) | 7 stations | Snow presence | Very limited coverage |
| **ground_state** (40) | 658 stations | Ground conditions | Good companion to snow_depth |

### Wind Parameters

| Parameter | Coverage | Use Case | Notes |
|-----------|----------|----------|-------|
| **wind_speed** (4) | 184 stations | Average wind | 10-min mean values |
| **wind_dir** (3) | 184 stations | Wind direction | In degrees |
| **wind_gust** (21) | 158 stations | Peak wind | Maximum gusts |
| **wind_speed_max** (25) | 138 stations | Daily max wind | Useful for extremes |

### Atmospheric Parameters

| Parameter | Coverage | Use Case | Notes |
|-----------|----------|----------|-------|
| **pressure_sea** (9) | 120 stations | Weather systems | Sea-level corrected |
| **humidity** (29) | 130 stations | Moisture content | Relative humidity % |
| **cloud_cover** (16) | 114 stations | Sky conditions | Total cloud percentage |
| **visibility** (13) | 168 stations | Atmospheric clarity | In meters |

---

## 5. Station Coverage

### Distribution by Parameter Count

| Parameters | Stations | Percentage | Cumulative |
|------------|----------|------------|------------|
| 25-29 | 87 | 9.3% | 87 |
| 20-24 | 22 | 2.4% | 109 |
| 15-19 | 41 | 4.4% | 150 |
| 10-14 | 18 | 1.9% | 168 |
| 5-9 | 82 | 8.8% | 250 |
| 3-4 | 34 | 3.6% | 284 |
| 2 | 626 | **66.9%** | 910 |
| 1 | 26 | 2.8% | 936 |

**Key Insight**: Two-thirds of stations (626) have only 2 parameters (typically snow_depth + ground_state). Only 150 stations have 10+ parameters.

### Top 20 Stations by Parameter Count

| Rank | Station | ID | Lat | Lon | Elev (m) | Params |
|------|---------|-----|-----|-----|----------|--------|
| 1 | Norrköping-SMHI | 86340 | 58.58 | 16.15 | 40 | **29** |
| 2 | Abisko Aut | 188790 | 68.35 | 18.82 | 392 | 28 |
| 3 | Arjeplog A | 167710 | 66.05 | 17.84 | 431 | 28 |
| 4 | Rångedala A | 73480 | 57.78 | 13.16 | 297 | 27 |
| 5 | Kolmården-Strömsfors A | 86420 | 58.69 | 16.31 | 154 | 26 |
| 6 | Kettstaka A | 85460 | 58.72 | 15.03 | 225 | 26 |
| 7 | Kerstinbo A | 106160 | 60.27 | 16.97 | 56 | 26 |
| 8 | Kvikkjokk-Årrenjarka A | 167990 | 66.89 | 18.02 | 315 | 26 |
| 9 | Ljungby A | 63510 | 56.85 | 13.88 | 148 | 26 |
| 10 | Gårdsjö A | 84520 | 58.88 | 14.39 | 211 | 26 |
| 11 | Film A | 107140 | 60.24 | 17.90 | 33 | 26 |
| 12 | Falsterbo A | 52240 | 55.38 | 12.82 | 2 | 26 |
| 13 | Eskilstuna A | 96190 | 59.38 | 16.45 | 10 | 26 |
| 14 | Sala A | 96560 | 59.91 | 16.68 | 57 | 26 |
| 15 | Floda A | 96040 | 59.06 | 16.39 | 31 | 26 |
| 16 | Hällum A | 83190 | 58.32 | 13.04 | 70 | 26 |
| 17 | Horn A | 75520 | 57.89 | 15.86 | 90 | 26 |
| 18 | Holmön A | 140460 | 63.81 | 20.86 | 7 | 26 |
| 19 | Edsbyn A | 115220 | 61.36 | 15.71 | 184 | 26 |
| 20 | Delsbo A | 116490 | 61.83 | 16.54 | 71 | 26 |

### Geographic Coverage

- **Latitude Range**: 55.38°N (Falsterbo) to 68.68°N (Naimakka)
- **Longitude Range**: 11.01°E (Nordkoster) to 24.11°E (Haparanda)
- **Elevation Range**: 1m (Falsterbo) to 723m (Tännäs)

The station network covers all of Sweden from Skåne in the south to Lapland in the north, including coastal, inland, and mountainous regions.

---

## 6. Key Parameters for Snow Monitoring

### Defined Key Parameters

For the multi-task snow monitoring model, these parameters were identified as most important:

| ID | Parameter | Status | Stations | Records | Priority |
|----|-----------|--------|----------|---------|----------|
| 8 | snow_depth | ✓ Available | 659 | 1,616,151 | **Critical** |
| 2 | temp_mean | ✗ Not downloaded | - | - | Critical |
| 19 | temp_min | ✗ Not downloaded | - | - | Important |
| 20 | temp_max | ✗ Not downloaded | - | - | Important |
| 5 | precip_sum | ✗ Not downloaded | - | - | Important |
| 4 | wind_speed | ✓ Available | 184 | 685,749 | Useful |
| 9 | pressure_sea | ✓ Available | 120 | 448,061 | Useful |
| 29 | humidity | ✓ Available | 130 | 399,004 | Useful |
| 39 | dew_point | ✓ Available | 183 | 679,182 | Useful |
| 16 | cloud_cover | ✓ Available | 114 | 410,487 | Useful |

### Stations with Snow + Multiple Key Parameters

Only a limited number of stations have snow_depth AND multiple other key parameters:

| Station | ID | Key Params | Total Params | Available Parameters |
|---------|-----|------------|--------------|---------------------|
| Norrköping-SMHI | 86340 | 6 | 29 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Abisko Aut | 188790 | 6 | 28 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Arjeplog A | 167710 | 6 | 28 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Enköping | 97370 | 6 | 22 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Vidsel | 160970 | 6 | 22 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Såtenäs | 82260 | 6 | 22 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Luleå-Kallax | 162860 | 6 | 22 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Ronneby-Bredåkra | 65160 | 6 | 22 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Linköping-Malmslätt | 85240 | 6 | 22 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |
| Falsterbo | 52230 | 6 | 16 | snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover |

**Summary**:
- **10 stations** have snow_depth + 6 key parameters
- **11 stations** have snow_depth + 5 key parameters
- **16 stations** have snow_depth + 3+ key parameters
- **643 stations** have snow_depth only (or + ground_state)

---

## 7. Data Quality

### Overall Quality Metrics

| Metric | Value |
|--------|-------|
| Null values in downloaded data | 0 (all nulls filtered during download) |
| Date range consistency | 2015-01-01 to 2025-10-01 (3,926 days) |
| Duplicate rows | None (aggregated to daily) |

### Known Data Issues

1. **Negative Snow Depth**: Some records show negative values (min: -0.02m)
   - Recommendation: Clip to 0 or investigate as measurement errors

2. **Extreme Precipitation Values**: `precip_15min` and `precip_hourly` contain extreme values up to 1,000,000 mm
   - Recommendation: Apply outlier filtering (e.g., cap at 500mm/day)

3. **Humidity Scale**: Humidity values appear to be in code (0-9) rather than percentage
   - Recommendation: Verify SMHI documentation for correct interpretation

4. **Weather Codes**: Parameters like ground_state, weather_wawa use SMHI/WMO codes
   - Recommendation: Decode using official SMHI code tables

### Value Ranges

| Parameter | Min | Max | Mean | Std |
|-----------|-----|-----|------|-----|
| snow_depth (m) | -0.02 | 2.29 | 0.08 | 0.20 |
| temp_1min (°C) | -43.5 | 29.8 | 5.5 | 9.0 |
| wind_speed (m/s) | 0.0 | 33.8 | 3.4 | 2.5 |
| pressure_sea (hPa) | 947.3 | 1054.1 | 1011.6 | 11.7 |
| dew_point (°C) | -48.1 | 24.0 | 1.7 | 8.3 |
| cloud_cover (%) | 0.0 | 113.0 | 59.0 | 33.3 |

---

## 8. File Structure

### Directory Layout

```
data/raw/parameters/
├── param_01_temp_1min.csv          (65 MB, 1,017,296 records)
├── param_03_wind_dir.csv           (45 MB, 682,773 records)
├── param_04_wind_speed.csv         (45 MB, 685,749 records)
├── param_06_precip_6h.csv          (39 MB, 679,219 records)
├── param_07_precip_15min.csv       (32 MB, 575,456 records)
├── param_08_snow_depth.csv         (85 MB, 1,616,151 records)  ★ Primary target
├── param_09_pressure_sea.csv       (30 MB, 448,061 records)
├── param_10_sunshine.csv           (4 MB, 74,608 records)
├── param_11_global_irrad.csv       (4 MB, 66,743 records)
├── param_12_longwave_irrad.csv     (41 MB, 623,709 records)
├── param_13_visibility.csv         (40 MB, 631,848 records)
├── param_14_precip_hourly.csv      (28 MB, 498,850 records)
├── param_15_precip_intensity.csv   (0.3 MB, 4,190 records)
├── param_16_cloud_cover.csv        (26 MB, 410,487 records)
├── param_21_wind_gust.csv          (33 MB, 599,517 records)
├── param_24_snow_cover.csv         (2 MB, 26,751 records)
├── param_25_wind_speed_max.csv     (29 MB, 533,131 records)
├── param_26_temp_min_grass.csv     (49 MB, 890,708 records)
├── param_27_temp_min_bare.csv      (49 MB, 890,711 records)
├── param_28_cloud_base.csv         (25 MB, 394,950 records)
├── param_29_humidity.csv           (26 MB, 399,004 records)
├── param_30_cloud_base_2.csv       (21 MB, 337,364 records)
├── param_31_cloud_base_3.csv       (22 MB, 363,439 records)
├── param_32_cloud_base_4.csv       (13 MB, 229,812 records)
├── param_33_cloud_amount_1.csv     (17 MB, 288,756 records)
├── param_34_cloud_amount_2.csv     (6 MB, 96,380 records)
├── param_35_cloud_amount_3.csv     (11 MB, 192,739 records)
├── param_36_cloud_amount_4.csv     (27 MB, 429,531 records)
├── param_37_weather_wawa.csv       (11 MB, 200,133 records)
├── param_38_thunder.csv            (26 MB, 470,661 records)
├── param_39_dew_point.csv          (46 MB, 679,182 records)
├── param_40_ground_state.csv       (88 MB, 1,666,837 records)
├── _parameter_summary.csv          (Analysis: parameter statistics)
├── _station_param_counts.csv       (Analysis: station coverage)
└── _snow_station_analysis.csv      (Analysis: snow stations detail)
```

### CSV File Format

All parameter files follow the same structure:

| Column | Type | Description |
|--------|------|-------------|
| date | datetime | Observation date (YYYY-MM-DD) |
| station_id | int | SMHI station identifier |
| station_name | string | Station name |
| latitude | float | Station latitude (°N) |
| longitude | float | Station longitude (°E) |
| elevation | float | Station elevation (m) |
| {param_name} | float | Parameter value |

---

## 9. Recommendations

### For Multi-Task Snow Model

#### Option A: Rich Feature Set (Limited Stations)
- **Use**: 10-16 stations with 5+ key parameters
- **Features**: snow_depth, wind_speed, pressure_sea, humidity, dew_point, cloud_cover, lat, lon, elevation
- **Pros**: Complete multi-variate data, no missing values
- **Cons**: Limited geographic coverage
- **Best for**: Proof of concept, model development

#### Option B: Maximum Geographic Coverage
- **Use**: All 659 stations with snow_depth
- **Features**: snow_depth, ground_state, temp_1min (where available), lat, lon, elevation, day_of_year
- **Pros**: Full Swedish coverage, large dataset
- **Cons**: Many missing features, sparse meteorological data
- **Best for**: Spatial prediction tasks

#### Option C: Hybrid Approach (Recommended)
1. Train encoder on rich-feature stations (Option A)
2. Fine-tune/transfer to all snow stations (Option B)
3. Use position encodings and day_of_year as universal features

### Feature Engineering Suggestions

```python
# Universal features (always available)
'latitude',           # Station location
'longitude',          # Station location
'elevation',          # Station height
'day_sin',            # sin(2π × day_of_year / 365)
'day_cos',            # cos(2π × day_of_year / 365)

# Temperature proxies (when temp_mean unavailable)
'temp_1min',          # 295 stations - best alternative
'dew_point',          # 183 stations - strongly correlated
'temp_min_grass',     # 247 stations - minimum temperature

# Precipitation alternatives (when precip_sum unavailable)
'precip_6h',          # 182 stations - sum to daily
'precip_hourly',      # 190 stations - sum to daily
```

### Data Preprocessing Steps

1. **Convert snow_depth to cm**: `snow_depth_cm = snow_depth * 100`
2. **Clip negative values**: `snow_depth = max(0, snow_depth)`
3. **Filter extreme precipitation**: `precip = min(precip, 500)`
4. **Create day features**: `day_sin = sin(2π × day_of_year / 365)`
5. **Normalize by station**: Consider station-wise normalization for temperature
6. **Handle missing values**: Use forward-fill within station or masking

### Train/Val/Test Split

| Split | Years | Purpose |
|-------|-------|---------|
| Train | 2015-2021 | Model training (7 years) |
| Validation | 2022 | Hyperparameter tuning (1 year) |
| Test | 2023-2025 | Final evaluation (3 years) |

---

## 10. Usage Examples

### Load Single Parameter

```python
import pandas as pd
from pathlib import Path

DATA_DIR = Path('data/raw/parameters')

# Load snow depth data
snow_df = pd.read_csv(DATA_DIR / 'param_08_snow_depth.csv', parse_dates=['date'])
print(f"Snow data: {len(snow_df):,} records from {snow_df['station_id'].nunique()} stations")
```

### Merge Multiple Parameters

```python
def load_and_merge(param_ids, station_ids=None):
    """Load and merge multiple parameters."""
    PARAMS = {
        8: 'snow_depth', 4: 'wind_speed', 9: 'pressure_sea',
        29: 'humidity', 39: 'dew_point', 16: 'cloud_cover'
    }

    dfs = []
    for pid in param_ids:
        name = PARAMS.get(pid, f'param_{pid}')
        path = DATA_DIR / f'param_{pid:02d}_{name}.csv'
        if path.exists():
            df = pd.read_csv(path, parse_dates=['date'])
            if station_ids:
                df = df[df['station_id'].isin(station_ids)]
            dfs.append(df)

    # Merge on date and station_id
    merged = dfs[0]
    for df in dfs[1:]:
        param_col = df.columns[-1]
        merged = merged.merge(
            df[['date', 'station_id', param_col]],
            on=['date', 'station_id'],
            how='outer'
        )
    return merged

# Example: Load data for best 10 stations
best_stations = [86340, 188790, 167710, 97370, 160970, 82260, 162860, 65160, 85240, 52230]
merged = load_and_merge([8, 4, 9, 29, 39, 16], station_ids=best_stations)
```

### Find Stations with Specific Parameters

```python
# Load station analysis
station_df = pd.read_csv(DATA_DIR / '_station_param_counts.csv')

# Find stations with 20+ parameters
rich_stations = station_df[station_df['param_count'] >= 20]
print(f"Stations with 20+ params: {len(rich_stations)}")

# Load snow station analysis
snow_df = pd.read_csv(DATA_DIR / '_snow_station_analysis.csv')

# Find snow stations with 5+ key parameters
best_snow = snow_df[snow_df['key_param_count'] >= 5]
print(f"Snow stations with 5+ key params: {len(best_snow)}")
```

---

## Appendix: SMHI Ground State Codes

| Code | Description |
|------|-------------|
| 0 | Surface dry |
| 1 | Surface moist |
| 2 | Surface wet |
| 3 | Flooded |
| 4 | Frozen surface |
| 5 | Glaze |
| 6 | Loose dry dust/sand |
| 7 | Thin (<50%) snow cover |
| 8 | Moderate/thick (50-100%) snow cover |
| 9 | Complete snow cover |
| 10-19 | Extended snow depth codes |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 2025 | Initial comprehensive documentation |

---

*Generated for the Nordic Snow Monitoring Project*
*RISE Research Institutes of Sweden*
