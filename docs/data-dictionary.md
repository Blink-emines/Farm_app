# Data dictionary

What every number in `features.json` means, where it comes from, and how far to
trust it. Written for farmers, advisers and beginners. The machine-readable
contract is `docs/contracts/features.schema.json`.

## 1. Sources

| Source | What we use | Link |
|--------|-------------|------|
| NASA POWER, daily point API, `community=AG` | 20 years (2005-2024) of daily weather for the point's grid cell | https://power.larc.nasa.gov/docs/services/api/temporal/daily/ |
| NASA MODIS MOD13Q1 NDVI via the ORNL DAAC MODIS web service | Satellite greenness of the point, 250 m, every 16 days | https://modis.ornl.gov/rst/api/v1/ |
| NASA POWER parameter list | Meaning of each parameter | https://power.larc.nasa.gov/parameters/ |
| ISRIC SoilGrids 2.0, official WCS (rasters) | Clay, sand, silt, organic carbon, pH at 3 depths, 250 m | https://maps.isric.org/ |
| ISRIC SoilGrids 2.0, REST point query | Backup only, used when the local rasters are missing | https://rest.isric.org/soilgrids/v2.0/docs |
| FAO Irrigation and Drainage Paper 56 (Allen et al., 1998) | Reference ET formula | https://www.fao.org/4/x0490e/x0490e00.htm |

**Region: all of Morocco**, box latitude 20.70 to 35.95, longitude -17.20 to
-0.95 (as defined by the user). A point outside the box, or inside it but over the
sea (no SoilGrids land pixel), is rejected as `outside_pilot_region`. No political
boundary file is used, so a point in Algeria or Mauritania that falls inside the
box is accepted: the box is the definition.

Coordinates are rounded to 2 decimals (about 1 km). Every raw response is saved
in `data/cache/`, so an identical request is never sent twice.

**Everything is pre-downloaded on the server** so farmers never trigger an outside
request: NASA POWER cells with `python -m data.bulk_download`, SoilGrids rasters
with `python -m data.download_soil`, NDVI per point with `python -m data.ndvi LAT LON`.

## 2. NASA POWER parameters (verified)

Names, units and long names were read from the `parameters` block of a live
response of the POWER daily API (version 2.10.3) for the default point, 33.96 N,
-5.27 E, with `community=AG`. The code refuses a response whose units differ from
this table.

| Parameter | NASA long name | Unit in the API | Unit in features.json | Used for |
|-----------|----------------|-----------------|-----------------------|----------|
| `T2M` | Temperature at 2 Meters | C | °C | mean temperature, ET0 |
| `T2M_MAX` | Temperature at 2 Meters Maximum | C | °C | max temperature, heat days, ET0 |
| `T2M_MIN` | Temperature at 2 Meters Minimum | C | °C | min temperature, frost days, ET0 |
| `PRECTOTCORR` | Precipitation Corrected | mm/day | mm/month (sum) | rainfall, water balance |
| `RH2M` | Relative Humidity at 2 Meters | % | % | humidity, ET0 |
| `WS2M` | Wind Speed at 2 Meters | m/s | m/s | wind, ET0 (already at 2 m) |
| `ALLSKY_SFC_SW_DWN` | All Sky Surface Shortwave Downward Irradiance | MJ/m^2/day | MJ/m²/day | sunshine energy, ET0 |
| `GWETROOT` | Root Zone Soil Wetness | 1 (no unit) | 0-1 | soil moisture indicator |

Notes:
- **Solar radiation unit.** For `community=AG` POWER reports `ALLSKY_SFC_SW_DWN`
  in MJ/m^2/day (other communities use kW-hr/m^2/day). The contract wants
  MJ/m²/day, so no conversion is applied.
- **Missing values.** POWER marks a missing day with `-999` (the `fill_value`
  in the response header). We turn it into "no data" immediately; `-999` never
  reaches the output. A month with no valid data is `null`, never 0.
- **Elevation** is the third coordinate of the response geometry (metres). It is
  the mean elevation of the NASA grid cell, not of your field (for example 575 m
  for the Saïss cell, 1700 m for a cell in the High Atlas).

### NASA grid cells (verified by probing the live API)

Two points in the same cell return identical numbers, and the numbers jump at the
cell edge. Probing a line of points across the Saïss showed two grids:

| Parameters | Grid (source) | Cell edges |
|------------|---------------|------------|
| `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M`, `GWETROOT` | 0.5 deg latitude x 0.625 deg longitude (MERRA-2), about 55 x 58 km | latitude x.25 and x.75; longitude (k + 0.5) x 0.625 |
| `ALLSKY_SFC_SW_DWN` | 1 x 1 degree (SYN1DEG), about 100 km | whole degrees |

Cell centres are at multiples of 0.5 / 0.625 degrees (MERRA-2) and at x.5 (radiation).
A point exactly on an edge belongs to the cell to the north or east. The cache is
keyed by cell: the request is sent at the cell centre, so every point in the cell
shares one file. Each point therefore needs two cache entries (a MERRA-2 cell and a
radiation cell). The Saïss default point sits in MERRA-2 cell 34.0 N / -5.0 E and
radiation cell 33.5 N / -5.5 E. Two points in the same cell still get slightly
different ET0 because the sun geometry (extraterrestrial radiation) depends on the
exact latitude.

Bulk download: land cells are found from the SoilGrids clay raster (2 km blocks with
any land pixel). Requests are sequential with a 0.5 s pause, resumable (cells already
cached are skipped) and gzip-compressed (about 0.2 MB per MERRA-2 cell instead of 1 MB).

## 3. SoilGrids properties and unit conversion (verified)

SoilGrids returns whole numbers in "mapped units" and tells us a `d_factor`.
Value in conventional units = mapped value / `d_factor`.

**Main path: local rasters.** `python -m data.download_soil` downloads 15 GeoTIFFs
(5 properties x 3 depths, statistic `mean`, 250 m) for the Morocco box from the
official ISRIC WCS (`maps.isric.org`, coverage `<property>_<depth>_mean`, native
Interrupted Goode Homolosine grid, EPSG:152160). A point is looked up locally; the
values were checked against the REST service at the default point (clay 361 =
36.1 %). The WCS marks sea and other no-data pixels with 0 (no nodata flag is set),
so 0 means "no data": in one layer it becomes `null`; if the pixel in the surface
clay layer is empty the nearest valid pixel within about 3 km is used (SoilGrids masks built-up areas: the centres of Casablanca and Marrakech have no pixel of their own)
(`soil_nearest_pixel`); if there is none the point is sea and is rejected.
Rasters are large and not committed. **Backup path:** the REST point query (cached),
then `data/fallback/saiss_soil.json`; the REST response reports its own `d_factor` and
target unit, and the code checks them.

| SoilGrids name | Mapped unit | d_factor | Conventional unit (features.json) | Example (0-5 cm, default point) |
|----------------|-------------|----------|-----------------------------------|---------------------------------|
| `clay` | g/kg | 10 | % (`clay_pct`) | 361 g/kg = 36.1 % |
| `sand` | g/kg | 10 | % (`sand_pct`) | 275 g/kg = 27.5 % |
| `silt` | g/kg | 10 | % (`silt_pct`) | 363 g/kg = 36.3 % |
| `soc` | dg/kg | 10 | g/kg (`soc_g_kg`) | 262 dg/kg = 26.2 g/kg |
| `phh2o` | pH*10 | 10 | pH in water (`ph_h2o`) | 80 = pH 8.0 |

Depths used: 0-5 cm, 5-15 cm, 15-30 cm. Statistic: `mean`. A missing value stays `null`.

## 4. How each climate feature is computed

All features are 12 monthly values (January first), each averaged over the 20
complete years 2005-2024.

| Feature | Unit | How |
|---------|------|-----|
| `t2m_mean`, `t2m_max`, `t2m_min` | °C | monthly mean of the daily value |
| `precipitation` | mm/month | sum of daily `PRECTOTCORR` in the month |
| `et0` | mm/month | sum of daily FAO-56 Penman-Monteith ET0 (section 5) |
| `water_balance` | mm/month | precipitation minus ET0, month by month |
| `rh2m`, `ws2m`, `solar_radiation`, `root_zone_wetness` | see table | monthly mean of the daily value |
| `frost_days` | days/month | days with daily `T2M_MIN` below 0 °C |
| `heat_days` 30/32/35/38 | days/month | days with daily `T2M_MAX` strictly above that temperature |

Sums and day counts are only used for months where every day has data; a year
with a gap in that month is skipped for that month. Heat-day and frost-day
averages over 20 years move in steps of 0.05 days.

### Year-by-year values (`yearly`)

From the same daily data, for each of the 20 years: annual rain (mm/year), annual
ET0, water balance (rain minus ET0), frost days (daily minimum below 0 °C), days
above 35 °C, and 12 monthly rain totals. A year with a missing day in the variable
needed is `null`. Use it to see drought years: for the default point 2010 had about
1340 mm of rain, 2023 about 310 mm.

### Vegetation greenness (`vegetation`, NASA MODIS NDVI)

Product: MOD13Q1, 250 m, 16-day composites, through the ORNL DAAC MODIS web service
(`/MOD13Q1/subset`, no key). Verified from the service's band list: band
`250m_16_days_NDVI`, scale factor 0.0001, valid range -2000 to 10000, fill value
-3000; band `250m_16_days_pixel_reliability` (0 good, 1 marginal, 2 snow/ice, 3
cloudy, -1 fill). We keep a value only if it is not the fill value, is inside the
valid range, and its pixel reliability is 0 or 1; then NDVI = value x 0.0001. One
pixel (the one containing the point) is used. The service allows 10 dates per
request and takes about 1 minute per request, so a point needs 24 requests
(12 date blocks x 2 bands) for 5 years. A composite counts for the month of its
mid-point (start date + 8 days). `ndvi_monthly` is the average over **2020-2024**
(5 years, not 20, because of the request count); `recent` is the monthly series of the
last complete year (2024). Because the service is slow, `get_features` reads NDVI
from the cache only; run `python -m data.ndvi LAT LON` once per point to download it.
Without it, `vegetation.status` is `unavailable` and the gap `ndvi_not_cached` appears.

## 5. FAO-56 Penman-Monteith, as implemented (`data/et0.py`)

Daily reference ET0 (mm/day), FAO-56 equation 6:

```
ET0 = [ 0.408 * D * (Rn - G)  +  g * 900/(T + 273) * u2 * (es - ea) ]
      / [ D + g * (1 + 0.34 * u2) ]
```

| Symbol | Meaning | How we get it |
|--------|---------|---------------|
| T | mean air temperature, °C | `T2M` |
| u2 | wind speed at 2 m, m/s | `WS2M`, **used as given**. It is already at 2 m, so the FAO-56 eq. 47 height correction (the 0.748 factor is for a 10 m anemometer) is NOT applied |
| es | saturation vapour pressure, kPa | **(e0(Tmax) + e0(Tmin)) / 2** (eq. 12), with e0(T) = 0.6108 exp(17.27 T / (T + 237.3)) (eq. 11) |
| ea | actual vapour pressure, kPa | **RHmean / 100 * es** (eq. 19, the FAO option when only mean humidity is known), RHmean = `RH2M` |
| D | slope of the vapour pressure curve | 4098 e0(T) / (T + 237.3)^2 (eq. 13), at the mean temperature |
| g | psychrometric constant, kPa/°C | 0.000665 * P (eq. 8), P = 101.3 ((293 - 0.0065 z)/293)^5.26 (eq. 7), z = elevation from NASA |
| Rs | solar radiation, MJ/m²/day | `ALLSKY_SFC_SW_DWN` |
| Ra | extraterrestrial radiation | from latitude and day of the year (eq. 21-25) |
| Rns | net shortwave | (1 - 0.23) * Rs (eq. 38, grass albedo 0.23) |
| Rnl | net longwave | s * [(Tmax,K^4 + Tmin,K^4)/2] * (0.34 - 0.14 sqrt(ea)) * (1.35 Rs/Rso - 0.35) (eq. 39), Rso = (0.75 + 2e-5 z) Ra (eq. 37), Rs/Rso capped at 1 |
| Rn | net radiation | Rns - Rnl (eq. 40) |
| G | soil heat flux | 0 (daily step) |

A negative result is set to 0. A day with any missing input gives "no data".
The implementation reproduces FAO-56 Example 18 (Uccle, 6 July: 3.9 mm/day);
this is a unit test.

Limits: it is computed from satellite/model inputs, not from a weather station,
and using mean humidity (instead of morning and afternoon humidity) can shift
ET0 slightly. Treat it as a good estimate of the right size, not an exact figure.

## 6. Plain-language explanations

**ET (evapotranspiration).** The water that leaves a field as vapour: it
evaporates from the soil and is breathed out by plants. Think of a bucket with a
small leak that gets bigger on hot, dry, windy, sunny days. ET0 ("reference ET")
is the water a well-watered short green grass field would use. A real crop uses
ET0 times a crop factor, so ET0 is a yardstick, not your crop's exact need.

**Water balance.** Rain minus ET0, in mm per month. Like a bank account: rain
is money in, ET0 is money out. A negative month (summer in the Saïss) means the
crop would need irrigation or stored soil water to be fully supplied; a positive
month means rain was enough and extra can fill the soil. It ignores runoff,
irrigation and what is already stored in the soil.

**Frost risk.** A frost day here is a day when the coldest temperature of the
day drops below 0 °C. Frost can kill seedlings or damage flowers (for example
faba bean or chickpea in flower). The number shown is the average over 20
years: "0.5 in January" means one January in two has a frost day, roughly. The
NASA grid averages an area of about 50 km, so cold valleys and hilltops can have
more frost than shown. Ask local farmers about late frosts.

**Heat days.** Days when the hottest temperature exceeds 30, 32, 35 or 38 °C.
Crops lose yield when hot days hit flowering or grain filling; each crop has its
own limit, so we count several thresholds.

**Soil moisture (root-zone wetness).** A number from 0 (bone dry) to 1 (fully
saturated) for the soil layer where roots live (roughly the top metre). It is a
fraction of what the soil can hold, not millimetres of water, and it is an
estimate from a model fed by satellites. A day of 0.5 does not mean your field
is at 50 %: use it only to compare seasons and months.

**NDVI (how green the field looks from space).** A satellite measures how much red
and near-infrared light the ground reflects. Healthy green plants absorb red light
and reflect near-infrared, so the ratio gives a number: close to 0 or below for bare
soil, rock, water or snow, about 0.2 to 0.4 for sparse or dry vegetation, 0.6 to 0.9
for dense green crops or forest. Through the year, a winter cereal field rises in
winter and spring and falls when it dries and is harvested; a fallow field stays
low. Clouds and haze are filtered out, and the pixel is 250 m wide, so it mixes the
crop with anything else inside it (trees, tracks, bare patches). It shows how green
the area looks, not the yield.

**Satellite/model data versus ground data.** A weather station measures at one
spot. NASA POWER combines satellite observations and weather models to estimate
conditions for every grid cell of the Earth, about 50 km wide here. It is
available everywhere and for decades, but it smooths local differences (a valley,
a hill, a nearby river), so rainfall of a single storm or a cold night in your
field may differ. SoilGrids works the same way for soil: it is a 250 m map made
by a model trained on soil samples, not a laboratory analysis of your field.
For decisions that cost money, confirm with a local soil test and local advice.

## 7. data_gaps codes

`data_gaps` lists what is missing or uncertain. The UI translates each message by
its `code`. Messages below are the English `message` values the pipeline emits.

| Code | When | Affects | English message |
|------|------|---------|-----------------|
| `climate_coarse_grid` | always | `climate` | NASA POWER is satellite/model data on a coarse grid (about 50 km), so all fields in the same cell get the same climate. It is not a weather-station record. |
| `root_zone_wetness_model` | always | `climate.monthly.root_zone_wetness` | Root-zone wetness is a satellite/model estimate, not a measurement in your field. |
| `soil_model_estimate` | whenever soil data is present (raster, REST or fallback) | `soil` | SoilGrids values are 250 m model estimates, not a soil test; check with a local soil analysis. |
| `soil_fallback_used` | SoilGrids unreachable, saved default-point response used | `soil` | SoilGrids could not be reached, so soil values come from a saved response for the default point (33.96, -5.27), not for this exact location. |
| `soil_unavailable` | SoilGrids unreachable and no usable fallback (`soil.status` = `unavailable`, `layers` empty) | `soil` | No soil data could be obtained (SoilGrids unreachable and no saved copy). |
| `soil_missing_values` | some soil property or depth is `null` | `soil.layers` | SoilGrids has no value for some soil properties or depths at this point. |
| `soil_nearest_pixel` | no soil value exactly at the point; nearest valid SoilGrids pixel within about 3 km used | `soil` | There is no soil value exactly at this point (town, water or edge pixel); the nearest SoilGrids pixel within about 3 km was used. |
| `ndvi_unavailable` | the MODIS service failed or no valid NDVI value exists (`vegetation.status` = `unavailable`, values null) | `vegetation` | Satellite greenness (NDVI) could not be obtained from the NASA MODIS service; NDVI values are empty (null). |
| `ndvi_not_cached` | NDVI for this point has not been downloaded yet (`vegetation.status` = `unavailable`) | `vegetation` | Satellite greenness (NDVI) for this point has not been downloaded yet (the NASA MODIS service is slow), so NDVI values are empty (null). |
| `ndvi_coarse_note` | whenever NDVI is present | `vegetation` | NDVI comes from a 250 m satellite pixel that may mix crops, trees and bare soil, with cloudy observations removed; it shows how green the area looks, not your exact field. |
| `ndvi_short_period` | whenever NDVI is present (period shorter than 20 years) | `vegetation` | NDVI is averaged over only 5 years (2020-2024) because the NASA MODIS service is slow, so it is less stable than the 20-year climate values. |
| `climate_missing_values` | some daily NASA values were missing (`-999`) | the affected `climate.monthly.*` paths | Some daily NASA POWER values were missing; affected months were averaged from fewer days or are empty (null). |

Not a gap but worth knowing: if NASA POWER cannot be reached and the point is not
cached, `get_features` raises `UpstreamUnavailable` (HTTP 502), because there is
no climate to show. Soil problems never raise; they become a gap.

## 8. Default point at a glance (33.96 N, -5.27 E, 2005-2024)

Annual rain is about 680 mm and annual ET0 about 1590 mm, so the water balance
is negative from April to October. Frost is rare (about 1 day per winter on
average at this grid cell, mostly January-February). July and August are hot:
about 30 days above 30 °C and 24-26 days above 35 °C per month.
