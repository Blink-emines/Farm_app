# Contracts

The single source of truth for how the parts talk to each other. Change only
with human approval (see CLAUDE.md).

| File | What it defines |
|------|-----------------|
| `features.schema.json` | Climate + soil features for one point (output of data/) |
| `strategy.schema.json` | `StrategyRequest` (input) and `StrategyResponse` (output of engine/) |

## Who owns what

| Folder / file | Owner | Writes |
|---------------|-------|--------|
| `data/`, `docs/data-dictionary.md` | data-engineer | pipeline, cache, fallback, data tests |
| `engine/` | agronomy-engine | `crops.yaml`, rotation templates, rules, scorer, engine tests |
| `backend/`, `frontend/` | fullstack-dev | Django app `rotation`, React app |
| `tests/`, `docs/build-summary.md` | qa-docs | contract, integration, end-to-end tests, `tests/report.md` |
| `docs/contracts/`, `docs/plan.md`, `docs/progress.md`, `docs/decisions.md` | lead | |

Each owner keeps its own unit tests inside its own folder (`data/tests/`,
`engine/tests/`, `backend/rotation/tests.py`). Cross-part tests live in `tests/`.

## Python interfaces

`data/` and `engine/` are Python packages (each has `__init__.py`). The backend
imports them; the repository root is put on `sys.path` by Django settings.

```python
# data/pipeline.py
def get_features(latitude: float, longitude: float) -> dict:
    """Return a dict valid against features.schema.json.
    Raises OutsidePilotRegion or UpstreamUnavailable (defined in data/errors.py)."""

# engine/scorer.py
def score(features: dict, request: dict) -> dict:
    """features: valid features.json; request: valid StrategyRequest.
    Return a dict valid against StrategyResponse."""
```

Both functions validate their own output against the schema before returning.

## HTTP endpoints (Django, http://localhost:8000)

No login needed; nothing is stored per user.

| Method + path | Body / query | Success | Errors |
|---------------|--------------|---------|--------|
| `GET /api/features?lat=&lon=` | query floats | 200 features.json | 400 `invalid_coordinates`, 422 `outside_pilot_region`, 502 `upstream_unavailable` |
| `POST /api/strategies` | `StrategyRequest` JSON | 200 `StrategyResponse` | 400 `invalid_request`, 422 `outside_pilot_region`, 502 `upstream_unavailable` |

Both endpoints can also return 500 `internal_error` for an unexpected failure
(no technical details in the message). Added 2026-11-14, approved by the user.

Error body, always: `{"error": {"code": "<code>", "message": "<plain English>"}}`

The React dev server runs on http://localhost:3000 and proxies `/api` to port
8000, so no CORS setup is needed.

## Shared rules

- **Pilot region (Saïss), approximate box:** latitude 33.70 to 34.20, longitude
  −5.70 to −4.70. Points outside → `outside_pilot_region`.
  Default point for demos and tests: 33.96, −5.27 (between Meknès and Fès).
- **Coordinates** are rounded to 2 decimals before fetching and caching.
- **Cache key** = endpoint + sorted query parameters (after rounding).
  Files in `data/cache/`. An identical request is never sent twice.
- **Fallback soil file** `data/fallback/saiss_soil.json` is a saved real
  SoilGrids response for the default point, with its fetch date. Never hand-typed.
- **Missing values** are `null`, never `-999` or `0`.
- **Heat days:** features give thresholds 30, 32, 35, 38 °C. The engine uses the
  highest threshold that is not above the crop's own threshold, and names it in
  the evidence.
- **Text:** the engine returns message objects (`code` + `params` +
  English `default_text`). The UI owns the French and Arabic text for every code.
  Every message code the engine can emit is listed in `engine/messages.md`.
- **Mocks** live in the consumer's own folder, have `mock` in the file name,
  and are never used by the running app once the real part is ready.
