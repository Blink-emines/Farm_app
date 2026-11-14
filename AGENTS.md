# AGENTS.md — guide for AI models and new developers

Read this first. It explains how the app is built and how to change it safely.

## 1. What the app is

Safe Cycle is a crop-rotation decision-support web app for Moroccan farmers
(FR / AR / EN). The user picks a point on a map, chooses crops and goals, and gets
rotation strategies with reasons, evidence and risks. It supports farmers and never
replaces their judgment or local experts. Every screen must keep that message.

## 2. Data flow

```
NASA POWER / SoilGrids / MODIS / FAOSTAT
        │
        ▼
data/            pipeline.py → "features" dict (validated by docs/contracts/features.schema.json)
        │
        ▼
engine/          scorer.py (rule-based scores)  →  strategies (strategy.schema.json)
engine/optimize/ model.py (Pyomo + HiGHS MILP)  →  multi-parcel plans (optimize.schema.json)
        │
        ▼
backend/rotation/ Django REST views: GET /api/features, POST /api/strategies, POST /api/optimize
backend/farms/    user accounts (JWT via /api/token/, /api/register/) and saved fields
        │
        ▼
frontend/src/api.js  →  React components  →  the farmer
```

## 3. Folder map

| Folder | Role | Key files |
|---|---|---|
| `docs/contracts/` | **Single source of truth** for all JSON between layers | `features.schema.json`, `strategy.schema.json`, `optimize.schema.json` |
| `data/` | Fetches and harmonises climate, soil, NDVI for a lat/lon | `pipeline.py` (entry), `nasa_power.py`, `et0.py` (FAO-56), `climatology.py`, `soilgrids.py`, `soil_raster.py`, `ndvi.py`, `region.py` (Morocco box), `cache.py` |
| `engine/` | Transparent scoring of rotations | `scorer.py` (entry), `rules.py`, `weights.yaml`, `crops.yaml`, `economics.yaml`, `season_calendar.py`, `messages.py` + `templates.py` (text shown to farmers) |
| `engine/optimize/` | MILP optimiser | `api.py` (entry), `model.py`, `objectives.py`, `windows.py`, `METHOD.md` (the maths) |
| `backend/` | Django project | `config/settings.py`, `config/urls.py`, `rotation/views.py`, `rotation/validation.py`, `farms/models.py` |
| `frontend/` | React + Vite | `src/api.js` (all HTTP calls), `src/App.jsx`, `src/components/`, `src/i18n/{fr,ar,en}.js` |
| `tests/` | Cross-layer tests (API, contracts, integration, e2e) | `report.md` |
| `deploy/` | Docker files and nginx config | used by `docker-compose.yml` |

The backend adds the repo root to `sys.path`, so `data` and `engine` are imported as
plain Python packages from Django.

## 4. How to make common changes

**Add or edit a crop:** edit `engine/crops.yaml` (and `economics.yaml` for price and
yield). Unknown values must be `null` / "unknown, needs local data". Never invent
numbers. Add the crop name to all three files in `frontend/src/i18n/`.

**Change a scoring rule or weight:** rules live in `engine/rules.py`, weights in
`engine/weights.yaml`. Each rule must give a reason the farmer can read. Run the
`engine/tests` afterwards. Scoring changes need the team's approval; log them in
`docs/decisions.md`.

**Add a field to an API response:**
1. Update the schema in `docs/contracts/` first.
2. Produce the field in `data/` or `engine/`.
3. The backend validates outputs against the schema (`rotation/validation.py`).
4. Read it in `frontend/src/api.js` and the component.
5. Run `tests/test_contract_schemas.py`.

**Add a UI text:** add the same key to `fr.js`, `ar.js` and `en.js`. Arabic is RTL;
check the layout in Arabic.

**Add a new screen or component:** put it in `frontend/src/components/`. All network
calls go through `src/api.js`, never call `fetch` directly from a component.

**Add a new data source:** add a module in `data/` that returns values with
`unit`, `source` and `method`, cached through `cache.py`. Missing data is `null` plus
an entry in the data gaps list.

## 5. Rules that must not break

- Contracts in `docs/contracts/` come first; code follows them.
- No invented numbers. Unknown → `null` + data gap.
- Frost and heat are warnings, not score points.
- Scores are relative comparisons, not yield predictions.
- Secrets only in `backend/.env` (see `.env.example`); never commit it.
- Log every decision in `docs/decisions.md` and update `docs/progress.md`.

## 6. Run and test

```bash
# backend
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env && .venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver          # :8000

# frontend
cd frontend && npm install && npm run dev     # :3000, proxies /api to :8000
# VITE_USE_MOCK=1 npm run dev  → runs the UI on mock data without the backend

# tests (from repo root)
backend/.venv/bin/python -m pytest
cd backend && .venv/bin/python manage.py test

# production
docker compose up -d --build                  # see README "Deploy"
```

## 7. More reading

- `docs/data-dictionary.md`: every feature, unit and source
- `engine/optimize/METHOD.md`: optimiser maths
- `docs/decisions.md`: why things are the way they are
- `docs/build-summary.md`: what was built and known limitations
