---
name: nasa-power-data
description: How to fetch, cache and harmonize NASA POWER and SoilGrids data for a lat/lon point. Use whenever working in data/.
---
# NASA POWER + SoilGrids

## NASA POWER (no API key)
- Base: https://power.larc.nasa.gov/api/temporal/{daily|monthly|climatology}/point
- Always pass: parameters, community=AG, latitude, longitude, start, end, format=JSON
- Core parameters: T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, WS2M,
  ALLSKY_SFC_SW_DWN, GWETROOT (root-zone soil wetness)
- FIRST TASK: verify every parameter name and unit against the official POWER
  parameter docs and record them in docs/data-dictionary.md. Never guess a name.
- Evapotranspiration: compute reference ET0 with FAO-56 Penman-Monteith from
  T, RH, wind, radiation. Document the formula.
- Derived: frost days (T2M_MIN < 0 °C), heat-stress days (T2M_MAX above crop
  threshold defined in engine/), monthly water balance = rain − ET0.

## SoilGrids
- https://rest.isric.org/soilgrids/v2.0/properties/query?lon=&lat=&property=&depth=&value=mean
- Properties: clay, sand, silt, soc, phh2o; depths 0-5cm, 5-15cm, 15-30cm
- The service can be slow or unavailable: cache everything; keep
  data/fallback/saiss_soil.json as a fallback.

## Rules
- Cache every raw response in data/cache/ (key = endpoint + params). Never
  repeat an identical request.
- Output must validate against docs/contracts/features.schema.json.
- Record units and the source dataset for every feature.
