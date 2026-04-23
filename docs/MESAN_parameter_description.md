# API Parameters

This document provides a comprehensive list and description of all meteorological parameters available through the SMHI Open Data API.

## All Parameters

| Parameter | Short Name | Description | Level (m) | Unit |
| :--- | :--- | :--- | :--- | :--- |
| Air pressure at mean sea level | `msl` | Air pressure at mean sea level. | 0 | hPa |
| Air temperature | `t` | Air temperature at 2 metres height. | 2 | Cel |
| Change over time in surface snow amount 1 hours | `frsn1h` | Change of snow on surface in last hour | 0 | cm |
| Cloud are fraction significant | `c_sigfr` | Fraction of significant clouds | 0 | octas |
| Cloud area fraction | `tcc` | Total cloud cover | 0 | octas |
| Cloud base altitude | `cb_sig` | Cloud base altitude. | 0 | m |
| Cloud top altitude | `ct_sig` | Cloud top altitude. | 0 | m |
| High type cloud area fraction | `hcc` | High cloud cover | 0 | octas |
| Low type cloud area fraction | `lcc` | Low cloud cover | 0 | octas |
| Medium type cloud area fraction | `mcc` | Medium cloud cove | 0 | octas |
| Precipitation amount last 1 hours | `prec1h` | Precipitation amount last hour | 0 | mm |
| Precipitation amount last 3 hours | `prec3h` | Precipitation amount last 3 hours | 0 | mm |
| Precipitation frozen part | `spp` | Frozen part of precipitation. | 0 | fraction |
| Precipitation rate max | `pmax` | Maximum precipitation rate | 0 | kg/m2/s |
| Precipitation rate mean | `pmean` | Median precipitation rate | 0 | kg/m2/s |
| Precipitation rate median | `pmedian` | Median precipitation rate | 0 | kg/m2/s |
| Precipitation rate min | `pmin` | Minimum precipitation rate | 0 | kg/m2/s |
| Precipitation sort | `prsort` | Sort of precipitation | 0 | code |
| Predominant precipitation type at surface | `prtype` | Type of precipitation | 0 | code |
| Relative humidity | `r` | Relative humidity at 2 metres height. | 2 | percent |
| Symbol code | `Wsymb2` | Weather symbol code with 27 different codes. | 0 | category |
| Visibility in air | `vis` | Visibility in air. | 2 | km |
| Wet bulb temperature | `Tiw` | Wet bulb temperature | 2 | Cel |
| Wind from direction | `wd` | Wind from direction at 10 metre. | 10 | degree |
| Wind speed | `ws` | Wind speed at 10 metre. | 10 | m/s |
| Wind speed of gust | `gust` | Wind gusts | 10 | m/s |

---

## Detailed Parameter Descriptions

This section provides more detailed information for parameters that use coded values or require further explanation.

### Cloud Cover Parameters

Cloud cover is split into four different parameters, including total cover and cover at specific altitudes.

| Parameter | Level Description |
| :--- | :--- |
| `tcc` (Total cloud cover) | How big part of the sky is covered by clouds. |
| `lcc` (Low cloud cover) | Clouds between 0 and 2500 meters. |
| `mcc` (Medium cloud cover) | Clouds between 2500 and 6000 meters. |
| `hcc` (High cloud cover) | Clouds above 6000 meters. |

### Precipitation Parameters

#### Precipitation Type (`prtype`)

The `prtype` parameter is an integer with a value range of 0 to 12.

| Value | Meaning |
| :--- | :--- |
| 0 | No precipitation |
| 1 | Rain |
| 2 | Thunderstorm |
| 3 | Freezing rain (i.e. supercooled raindrops which freeze on contact) |
| 4 | Mixed/ice |
| 5 | Snow |
| 6 | Wet snow (i.e. snow particles which are starting to melt) |
| 7 | Mixture of rain and snow |
| 8 | Ice pellets |
| 9 | Graupel |
| 10 | Hail |
| 11 | Drizzle |
| 12 | Freezing drizzle (i.e. supercooled drizzle which freezes on contact) |

#### Percent of Precipitation in Frozen Form (`spp`)

This parameter represents the frozen part of the precipitation.

> **Note:** If there is no precipitation, the value of the `spp` parameter will be `-9`. Make sure to handle this case in your application.

#### Precipitation Sort (`prsort`)

The `prsort` parameter is an integer with a value range of 0 to 6.

| Value | Meaning |
| :--- | :--- |
| 0 | No precipitation |
| 1 | Snow |
| 2 | Snow and rain |
| 3 | Rain |
| 4 | Drizzle |
| 5 | Freezing rain |
| 6 | Freezing drizzle |

### Weather Symbol (`Wsymb2`)

The `Wsymb2` parameter consists of integers from 1 to 27, where every value represents a different kind of weather situation.

| Value | Meaning |
| :--- | :--- |
| 1 | Clear sky |
| 2 | Nearly clear sky |
| 3 | Variable cloudiness |
| 4 | Halfclear sky |
| 5 | Cloudy sky |
| 6 | Overcast |
| 7 | Fog |
| 8 | Light rain showers |
| 9 | Moderate rain showers |
| 10 | Heavy rain showers |
| 11 | Thunderstorm |
| 12 | Light sleet showers |
| 13 | Moderate sleet showers |
| 14 | Heavy sleet showers |
| 15 | Light snow showers |
| 16 | Moderate snow showers |
| 17 | Heavy snow showers |
| 18 | Light rain |
| 19 | Moderate rain |
| 20 | Heavy rain |
| 21 | Thunder |
| 22 | Light sleet |
| 23 | Moderate sleet |
| 24 | Heavy sleet |
| 25 | Light snowfall |
| 26 | Moderate snowfall |
| 27 | Heavy snowfall |