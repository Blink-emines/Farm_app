# Progress

Updated after each milestone.

| Date | Who | What | Status | Blockers |
|------|-----|------|--------|----------|
| 2026-11-14 | lead | Phase 1 setup completed | done | none |
| 2026-11-14 | lead | Step 0: plan.md, features.schema.json, strategy.schema.json, contracts/README.md drafted and validated | done (approved by user) | none |
| 2026-11-14 | lead | Installed approved Python libraries; spawned data-engineer, agronomy-engine, fullstack-dev, qa-docs (plan-first) | done | none |
| 2026-11-14 | qa-docs | Contract tests in tests/ (52 tests: 30 pass, 6 API fail until data/engine exist, 16 skip) | done (stage 2) | e2e waits for the app |
| 2026-11-14 | data-engineer | data/ pipeline: NASA POWER daily 2005-2024 + FAO-56 ET0 + SoilGrids with cache/fallback; docs/data-dictionary.md; 48 tests pass offline; real sample validates (lead re-ran) | done | limits: frost understated and ET0 high-end (coarse grid), soil SOC model estimate |
| 2026-11-14 | agronomy-engine | rules, calendar (cross-year bug found by lead, fixed), scorer; weights, months, flags approved by user; 47 tests pass (lead re-ran) | done | none |
| 2026-11-14 | fullstack-dev | backend/rotation endpoints (41 Django tests pass) + React app on mocks, FR/AR screenshots reviewed | done (stage 2) | next: real data, engine message translations, unslop |
| 2026-11-14 | qa-docs | stage 3 part 1: integration tests against the real API | in progress | e2e waits for final UI |

## Handoff (2026-11-14, end of session)

Done: data (all Morocco: 821 NASA cells + 15 SoilGrids rasters, local), engine (rules + MILP optimiser, Pyomo/HiGHS), API (/api/features, /api/strategies, /api/optimize), web app (landing presentation, wizard, simple + advanced results, settings/dark mode, FR/AR/EN, optimiser flow). Brand: FR "Cycle Sûr", EN "Safe Cycle", AR "دورة آمنة".

Next steps:
1. DONE: final QA pass (261 Python + 49 Django tests pass); tests/report.md and docs/build-summary.md written (commit b30c12f).
2. Footer: real team names + contact (team SENIME, EMINES – UM6P).
3. Design discussion with the user; native review of FR/AR/EN text.
4. Deployment plan (explain only, never deploy without asking).
Decided, don't revisit: NDVI only for the default point (demo); region = rectangle box.

Run: backend `cd backend && .venv/bin/python manage.py runserver`; frontend `cd frontend && npm run dev` → http://localhost:3000.
