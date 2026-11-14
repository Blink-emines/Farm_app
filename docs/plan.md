# Plan: crop-rotation decision-support MVP (Saïss)

Status: **approved by the user on 2026-11-14** (all six decisions in section 5 as written). Written by the lead.

## 1. What we build

A farmer (or advisor) picks a point on a map in the Saïss plain, enters the
current rotation (for example wheat → fallow) and moves five sliders for what
matters to them. The app compares the current rotation with at least two
alternatives, scored by transparent rules from NASA climate data, SoilGrids soil
data and crop characteristics. Each option shows why, evidence, benefits,
information gaps and risks for local review, in French or Arabic.

```
Browser :3000 (React, FR/AR)
   │  /api/... (Vite dev proxy)
   ▼
Django :8000  ── app "rotation" (new) ──┬─► data.pipeline.get_features() ─► NASA POWER, SoilGrids
   │                                    │        (data/cache, data/fallback)
   └─ app "farms" (existing, untouched) └─► engine.scorer.score() ─► crops.yaml + named rules
```

## 2. What we reuse from the existing backend

`backend/` already has a tested Django + DRF project (user sign-up, JWT login,
Field / Measurement / Result models, 30 tests).

- **Reused as is:** the Django project, settings, `.env` handling, the virtual
  environment, the admin.
- **Added:** a new app `backend/rotation/` with the two endpoints. Both are open
  without login (`AllowAny`), because they only take a map point and store
  nothing about a person.
- **Untouched:** the `farms` app and its endpoints. The 30 existing tests must
  keep passing. Linking strategies to a logged-in user's saved fields would be a
  scope expansion and is not part of the MVP.

## 3. Contracts (approve these with the plan)

- `docs/contracts/features.schema.json`: 12-month climatology over 20 complete
  years (temperature mean/max/min, rainfall, ET0, water balance, humidity, wind,
  radiation, root-zone wetness, frost days, heat days at 30/32/35/38 °C) and soil
  (clay, sand, silt, organic carbon, pH at 0-5, 5-15, 15-30 cm). Every series has
  its unit, source and method; missing values are `null`; `data_gaps` lists what
  is missing in plain words.
- `docs/contracts/strategy.schema.json`: request (point, current rotation of 1-6
  seasons, priorities 0-5) and response (3-5 strategies, exactly one is the
  current rotation; each has rank, relative scores 0-100, seasons, a 12-month
  calendar per year with bare and stress months, `why` rules with points,
  evidence, benefits, gaps, risks, confidence; plus disclaimer notes).
- `docs/contracts/README.md`: owners, Python function names, endpoints, error
  format and shared rules (region box, rounding, cache key, fallback, mocks).

I checked both schemas with a validator: correct samples pass, and 13 kinds of
mistake are rejected (wrong unit, 11 months, two current rotations, a score
with no rule, no risks listed, an unknown crop, ...).

## 4. Team and tasks

Teammates are spawned from `.claude/agents/` with the models set there. All
four start at the same time; engine and UI start from mocks built from the
contracts.

| # | Teammate (model) | Tasks, in order | Done when |
|---|------------------|-----------------|-----------|
| 1 | data-engineer (sonnet) | Verify every NASA POWER parameter name and unit against the official docs → `docs/data-dictionary.md` (plain-language terms) → cached fetch of NASA POWER daily data, 2005-2024 → FAO-56 ET0, frost/heat days, water balance → SoilGrids with cache and fallback → `get_features()` | Output for the default point validates; tests pass without network; messages agronomy-engine and fullstack-dev |
| 2 | agronomy-engine (sonnet) | `engine/crops.yaml` for the 10 crops + fallow (family, legume, rooting depth, FAO-56 Kc with citation, typical Saïss sow/harvest months, frost/heat tolerance, or "unknown, needs local data") → candidate rotation templates → one tested function per rule → scorer → `engine/messages.md` | Strategies for mock and real features validate; every point traces to a rule |
| 3 | fullstack-dev (sonnet) | `rotation` app + endpoints + tests (on mocks first) → React app on port 3000: map picker, rotation input, priority sliders, 12-month calendar, strategy cards, "talk to a local expert" note, FR/AR with right-to-left layout → switch to real endpoints → frontend-design, then unslop on the main screens | Works end to end with real data for the default point |
| 4 | qa-docs (haiku) | Contract tests from the schemas now → integration and Playwright end-to-end tests when the others report done → `tests/report.md` → `docs/build-summary.md` | Honest pass/fail report |

Order of dependence: data → engine integration → backend real endpoints →
frontend real data → QA end to end. Each teammate sends me a short plan before
coding; I approve routine plans and bring anything on the CRITICAL list to you.

## 5. Decisions I need from you now

1. **New dependencies** (CLAUDE.md requires your approval):
   - Python, in `backend/requirements.txt`: `pandas` (daily → monthly
     aggregation), `PyYAML` (crops.yaml), `jsonschema` (contract validation),
     `pytest` (data/engine/QA tests), `playwright` (end-to-end tests). HTTP calls
     use Python's built-in `urllib`, so no extra HTTP library.
   - JavaScript, in `frontend/package.json`: `react`, `react-dom`, `vite`,
     `@vitejs/plugin-react`, `leaflet`, `react-leaflet`. No translation, chart or
     CSS library; translations are our own small dictionary files.
   - A one-time Playwright browser download (Chromium, about 150 MB).
2. **New external service:** OpenStreetMap map tiles for the map picker (free,
   needs the attribution shown on the map; fine for local use). Alternative: no
   map, only typed coordinates and a few preset points.
3. **Open endpoints:** `/api/features` and `/api/strategies` work without login
   (see section 2).
4. **Saïss box:** latitude 33.70-34.20, longitude −5.70 to −4.70, default point
   33.96, −5.27. These are my approximations; please correct them if you know
   better.
5. **"Fallow"** as an extra option next to the 10 crops, so the common
   wheat → fallow practice can be entered.
6. **Income and forage without price data:** there is no market data in scope,
   so `extra_income` and `forage` are scored from qualitative crop flags in
   crops.yaml (for example "sold as grain", "used as forage"), always with low
   confidence and "local prices" listed as an information gap.

Coming later, not now: the engine's first rule weights will be shown to you for
approval before they count as final.

## 6. Risks and how we handle them

| Risk | Handling |
|------|----------|
| NASA POWER is slow (20 years of daily data) | Cache on disk; the first fetch for the default point is made once during development |
| SoilGrids is down | Cached response, then the saved fallback file; the UI shows "soil data from fallback" |
| Wrong agronomy numbers | Cited sources only; unknown values are marked "unknown, needs local data" and shown as gaps |
| French/Arabic text written by AI | Listed in the build summary as needing review by a native speaker |
| Teammates editing the same files | Strict folder ownership (contracts/README.md) |
| QA on Haiku misses something | The lead reviews the QA report and spot-checks the running app |
| Token cost of 4 parallel sessions | Short messages, coordination through contracts and the task list |

## 7. Not in this MVP

SMAP (stretch goal only), other regions, machine learning, user accounts for
the new tool, deployment, and the old `web/` and `mobile/` folders.

## 8. Definition of done

- http://localhost:3000 shows at least 3 strategies for a Saïss point using real
  NASA POWER data, in French and Arabic.
- `tests/report.md` with an honest pass/fail list; the 30 existing backend tests
  still pass.
- `docs/build-summary.md` (what was built, decisions, how to run, limitations,
  data gaps) and `docs/data-dictionary.md`.
- `docs/progress.md` and `docs/decisions.md` up to date.
