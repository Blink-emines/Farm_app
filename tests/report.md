# QA report

## Update 2026-11-15 (lead): fixes round (items 1, 2, 4, 8)

| Suite | Command | Result |
|-------|---------|--------|
| Engine + cross-layer (contracts, integration, API) | `backend/.venv/bin/python -m pytest engine/tests tests --ignore=tests/e2e` | 178 passed |
| Django backend | `cd backend && DATABASE_URL= .venv/bin/python manage.py test` | 71 passed (OK) |
| e2e (Playwright) | `E2E_APP=http://localhost:3001 backend/.venv/bin/python -m pytest tests/e2e` | 12 passed |

e2e ran against a second dev server (Vite on 3001, Django on 8001 with the local SQLite file),
because Supabase did not yet have migration `farms/0005` (adding it needs the owner's approval
to run `migrate`). `E2E_APP` defaults to `http://localhost:3000`.

New tests for this round:

| Item | Test | Where |
|---|---|---|
| 1. "I don't know" soil shown from the map | `test_unknown_soil_is_shown_from_the_map_not_as_i_dont_know` | `tests/e2e/test_app_flow.py` |
| 2. Each field keeps its own answers | `test_each_field_keeps_its_own_answers` (switch 1→2→1→2); `test_each_field_keeps_its_own_answers`, `test_field_answers_are_validated` | `tests/e2e/test_app_flow.py`; `backend/farms/tests.py` |
| 4. One chosen crop is in every option; one year only | `test_one_chosen_crop_is_in_every_option_and_the_plan_has_steps`; `test_required_crop_is_in_every_alternative` | e2e; `engine/tests/test_scorer.py` |
| 8. Action plan from the timeline and named rules | `test_action_steps_follow_the_timeline`, `test_every_action_step_names_its_source`, `test_same_family_twice_gives_an_avoid_step`, `test_watch_water_steps_match_dry_months`, `test_perennial_gets_a_set_up_once_step`; e2e checks `data-rule` on every step and no Play button | `engine/tests/test_scorer.py`; e2e |
| 13. Return: FAOSTAT range or "no reliable figure" | `test_facts_use_faostat_ranges_and_say_when_there_is_none` | `engine/tests/test_scorer.py` |

Bugs found and fixed while testing: a CSS class collision (`.step-body`) that made the
all-fields optimiser's "Add a parcel" button unclickable (renamed the action-plan classes
to `act-*`); a plan step that read "Do not sow lentil" inside a plan that sows lentil
(now worded as a warning).

Not verified: Listen with recorded clips (no clips recorded yet; the speech fallback was
exercised only for "no voice" handling in headless Chromium); Darija wording (needs the
native-speaker review in `docs/darija-review.md`).

---

Date: 2026-11-14. Results re-run by the lead after the qa-docs final pass.

## Results

| Suite | Command | Result |
|-------|---------|--------|
| Data pipeline | `backend/.venv/bin/python -m pytest data/tests` | 89 passed |
| Engine + optimiser | `backend/.venv/bin/python -m pytest engine/tests` | 88 passed |
| Contracts, real outputs, API, integration, e2e | `backend/.venv/bin/python -m pytest tests` | 84 passed (contract 52, integration 24, e2e 8) |
| **All Python suites together** | `backend/.venv/bin/python -m pytest data/tests engine/tests tests` | **261 passed, 0 failed, 0 skipped** |
| Django backend | `cd backend && .venv/bin/python manage.py test` | 49 passed (OK) |
| Frontend build | `cd frontend && npm run build` | builds; one warning: a JS chunk over 500 kB |

API and e2e tests need both servers running (Django on 8000, Vite on 3000);
otherwise they skip, and a skip means "not verified".

## Failures found during the pass (fixed in test code, not app code)

1. The sentinel check flagged any value ≤ −999 and rejected a real yearly water
   balance of −1338 mm (dry year). It now checks exact sentinels (−999, −9999, −99)
   plus per-unit ranges.
2. First e2e run: 4 of 8 failed because of stale labels and a closed parcel
   `<details>`. Second run: 1 failed because the test opened the wrong parcel.
   Both are now fixed and all 8 pass.

## What the tests cover

- Both data contracts and the optimiser contract (valid and invalid examples).
- Real outputs: features sample, `score()` and `optimize()` validate; no sentinels;
  data-gap codes are consistent.
- API: `/api/features`, `/api/strategies`, `/api/optimize`: status codes, error
  body, validation.
- Optimiser: no potato on rainfed parcels; no family repeated within its gap;
  Pareto points present.
- e2e (Playwright): landing stats show numbers, guided tour advances, wizard to
  simple results in FR/AR/EN, Arabic `dir=rtl`, settings (dark mode, advanced
  data), optimiser flow returns plans and a Pareto chart.

## Not verified

- Visual layout, phone-width rendering, dark-mode colours and RTL mirroring
  (checked only in screenshots, not by tests).
- Optimality of the optimiser beyond the constraint checks.
- End-to-end views: climate, compare, soil, time machine, NDVI, what-if, print.
- Points other than the default point in the browser; live NASA/SoilGrids re-fetch.
- Native-speaker review of the FR, AR and EN text.
- Profit: no cost data, so profit is null unless the farmer enters costs.
