# Build summary: Cycle Sûr / Safe Cycle / دورة آمنة

NASA Space Apps Challenge 2026, "Field Shift: Adapting Farms with NASA Data".
Team SENIME, EMINES – UM6P.

## What was built

A crop-rotation decision-support web app for Moroccan farmers, in French,
Arabic and English.

- **Data (`data/`):** 20 years (2005–2024) of daily NASA POWER weather for all
  of Morocco (821 grid cells, stored on the server), FAO-56 Penman-Monteith
  reference evapotranspiration, water balance, frost and heat days, a year-by-year
  history, ISRIC SoilGrids soil (15 rasters, read locally), and MODIS NDVI greenness
  (default point). Every value carries its unit, source and method; missing values
  are null, and data limits are listed as "data gaps".
- **Engine (`engine/`):** a transparent rule-based scorer (legume after cereal,
  family break, deep roots, bare months, cover crops, water demand vs rain) with a
  cyclic month calendar, plus a **MILP optimiser** (Pyomo + HiGHS) based on Adam
  Lachkar's formulation: multi-parcel, 24-month cyclic horizon, five goals
  (save water, improve soil, extra income, reduce erosion, forage), profiles
  (economic / balanced / ecological), a Pareto curve (income vs water), and
  why / evidence / risks for every plan.
- **API (`backend/rotation/`, Django REST):** `GET /api/features`,
  `POST /api/strategies`, `POST /api/optimize`. Contracts in `docs/contracts/`.
- **Web app (`frontend/`, React + Vite):** landing presentation with a guided
  tour and impact figures from real runs; a 3-step wizard (satellite map, crop
  cards, goal sliders); a simple results view for farmers (one recommendation,
  crop icons, traffic-light months, plain reasons, main risk); advanced data
  (scores, climate, 20-year history, field from space, soil profile, compare,
  what-if, print); a multi-parcel optimiser; settings (language, dark mode,
  advanced data).

## How to run

```
cd backend && .venv/bin/python manage.py runserver      # API on :8000
cd frontend && npm run dev                              # app on http://localhost:3000
```

Tests: see `tests/report.md` (261 Python tests and 49 Django tests pass).

## Key decisions (full log in `docs/decisions.md`)

- Scope: all of Morocco (rectangle box), data pre-downloaded to the server.
- No invented numbers: unknown crop values are "unknown, needs local data".
- Income = FAOSTAT Morocco producer price × 10-year mean yield; bad/average/good
  year range; profit only when the farmer enters costs.
- Rainfed by default; irrigation-only crops (potato) allowed only on irrigated
  parcels; hard rotation gaps (potato, legumes, sunflower ≥ 24 months).
- Sowing windows from each point's climate (FAO growing-period rule: rain ≥ 0.5·ET0),
  with approved Saïss months as fallback.
- Frost and heat are warnings, not score points.
- Scores are relative comparisons, not yield predictions; every screen tells the
  farmer to talk to a local expert before deciding.

## Limitations and data gaps

- Frost is underestimated: NASA's grid is about 50 km wide and smooths cold valleys.
- ET0 (about 1590 mm/yr in the Saïss) is at the high end of typical values, so
  water stress is indicative.
- Soil values are 250 m model estimates, not soil tests.
- NDVI is available only at the default point (the MODIS service is too slow for
  bulk use); other points show "not available".
- Default crop months are approved defaults to confirm locally.
- Prices and yields are national FAOSTAT values that mix irrigated and rainfed
  farms; no cost-of-production data; no prices for alfalfa and vetch-oat.
- The region is a rectangle, so it also accepts land outside Morocco near the borders.
- FR, AR and EN texts were written by AI and need a native-speaker review.
- Historical climate is not a forecast.

## Open items

Team names and contact for the footer, design review, native text review,
deployment plan (to be explained before any deployment).
