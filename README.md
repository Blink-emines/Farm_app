# Safe Cycle · Cycle Sûr · دورة آمنة

**Crop-rotation decision support for Moroccan farmers, built on NASA data.**

NASA Space Apps Challenge 2026: *"Field Shift: Adapting Farms with NASA Data"*
Team SENIME, EMINES – UM6P

> This tool supports farmers. It never replaces their judgment or local experts.

---

## What it does

A farmer picks a field on a satellite map, chooses the crops they can grow, and sets
their goals (save water, improve soil, extra income, reduce erosion, forage). The app
then suggests a crop rotation and explains it: **why** it was picked, the **evidence**
behind it, and the **risks**. It works in French, Arabic (RTL) and English.

- **Simple view for farmers:** one recommendation, crop icons, month-by-month
  traffic lights, plain-language reasons, and the main risk.
- **Advanced view:** scores, climate, a 20-year history, the field seen from space
  (NDVI), the soil profile, side-by-side comparison, what-if tests, and a print view.
- **Multi-parcel optimiser:** plans several parcels together over a 24-month cycle,
  with economic, balanced or ecological profiles and an income-vs-water Pareto curve.

## Data sources

| Source | What we use |
|---|---|
| **NASA POWER** | 20 years (2005–2024) of daily weather for all of Morocco (821 grid cells) |
| **FAO-56 Penman-Monteith** | Reference evapotranspiration (ET0), water balance |
| **ISRIC SoilGrids** | Soil properties (15 rasters, 250 m) |
| **MODIS NDVI** | Vegetation greenness |
| **FAOSTAT** | Morocco producer prices and 10-year mean yields |

Every value carries its unit, source and method. Missing values stay `null` and are
listed as data gaps. Nothing is invented.

## Architecture

```
data/       NASA POWER + SoilGrids + NDVI pipeline → features.json
engine/     Transparent rule-based scorer + MILP optimiser (Pyomo + HiGHS)
backend/    Django REST API (rotation/ app; farms/ app)
frontend/   React + Vite web app (FR / AR / EN, dark mode)
docs/       Contracts (single source of truth), plan, decisions, progress
tests/      API, contract, integration and end-to-end tests
```

### API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET`  | `/api/features`   | Climate, soil and NDVI features for a point |
| `POST` | `/api/strategies` | Scored rotation strategies with reasons |
| `POST` | `/api/optimize`   | Multi-parcel MILP optimisation |

JSON schemas are in [`docs/contracts/`](docs/contracts/).

### How scoring works

The rule-based engine rewards agronomic practices you can check: a legume after a
cereal, family breaks, deep roots, fewer bare months, cover crops, and crop water
demand matched to rainfall. Weights live in [`engine/weights.yaml`](engine/weights.yaml)
and crop data in [`engine/crops.yaml`](engine/crops.yaml). Frost and heat show up as
warnings and do not change the score. Scores compare options with each other; they
are not yield predictions.

## Getting started

### Requirements
- Python 3.12
- Node.js 18+

### Backend

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example .env        # then set DJANGO_SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver      # API on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                               # app on http://localhost:3000
```

### Tests

See [`tests/report.md`](tests/report.md): 261 Python tests and 49 Django tests pass.

## Deploy (Docker)

On any server with Docker and Docker Compose:

```bash
git clone https://github.com/Blink-emines/Farm_app.git && cd Farm_app
cp .env.example backend/.env
# edit backend/.env:
#   DJANGO_SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(50))">
#   DJANGO_DEBUG=False
#   DJANGO_ALLOWED_HOSTS=your-domain.com,your-server-ip
#   DATABASE_URL=<Supabase session-pooler URI>   (see docs/supabase-setup.md)
docker compose up -d --build
```

The database is Supabase Postgres when `DATABASE_URL` is set in `backend/.env`;
the container runs `migrate` on start, so tables and row-level security are
created automatically. Without `DATABASE_URL` it uses SQLite inside the container,
which is lost when the container is rebuilt, so always set it on a server.

The app is served on port 80: nginx serves the React build and forwards `/api` to
Django (gunicorn).

### Data files (required for points other than the default)

The NASA weather cache (~130 MB) and the SoilGrids rasters (~330 MB) are too big for
git. Either copy them from a teammate into `data/cache/` and `data/soil_rasters/`,
or rebuild them (takes a long time):

```bash
python data/bulk_download.py
python data/download_soil.py
```

Both folders are mounted into the container, so there's no need to rebuild after
adding data.

> Note: user accounts are stored in SQLite inside the container and are reset when
> the backend image is rebuilt. Fine for a demo; use a real database for production.

## Limitations

- NASA's grid is about 50 km wide, so it smooths out cold valleys and frost is underestimated.
- ET0 is at the high end of typical values, so treat water stress as a rough guide.
- Soil values are 250 m model estimates, not soil tests.
- NDVI is only available at the default point.
- Prices and yields are national FAOSTAT averages that mix irrigated and rainfed farms.
- The FR, AR and EN texts were written with AI help and still need a native-speaker review.
- Past climate is not a forecast. Always check with a local agronomist.

## Documentation

- [AGENTS.md](AGENTS.md): architecture and how to make changes (for AI models and new developers)
- [Build summary](docs/build-summary.md)
- [Decision log](docs/decisions.md)
- [Progress](docs/progress.md)
- [Plan](docs/plan.md)

---

Built for NASA Space Apps Challenge 2026 by Team SENIME (EMINES – UM6P).
