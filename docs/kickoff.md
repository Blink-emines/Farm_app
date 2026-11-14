Goal: Build a working MVP of a crop-rotation decision-support tool for farmers
(pilot: Saïss plain, Morocco; UI in French + Arabic). It combines NASA Earth
observation data, soil data, crop characteristics and farmer priorities to
compare at least 3 rotation strategies, including the farmer's current one.
End result: React app at http://localhost:3000, Django REST API at
http://localhost:8000, and a QA report.

Every strategy must show: why it was suggested, evidence (which data),
benefits, information gaps, and risks needing local review.
Follow CLAUDE.md at all times.

MVP SCOPE (do not expand without my approval):
- Point-based (lat/lon), one region: Saïss.
- Data: NASA POWER (temperature, rainfall, ET0, frost days, heat days,
  root-zone wetness, 20-year monthly climatology) + SoilGrids.
  SMAP is a stretch goal only.
- ~10 crops relevant to Morocco (wheat, barley, chickpea, lentil, faba bean,
  alfalfa, vetch-oat cover, sunflower, potato, olive intercrop).
- Farmer priorities as weights: save water, improve soil, extra income,
  reduce erosion, forage.

STEP 0 (lead, on Opus): Before spawning anyone, write docs/plan.md,
docs/contracts/features.schema.json and docs/contracts/strategy.schema.json.
Show them to me and WAIT for my approval.

TEAM: after I approve, spawn 4 teammates using the agent definitions in
.claude/agents/ (their model is set in each file):

1. data-engineer (sonnet), uses the nasa-power-data skill.
   Pipeline: lat/lon → cached NASA POWER + SoilGrids → features.json.
   Write docs/data-dictionary.md explaining each term simply (ET, frost
   risk, water balance, soil moisture, satellite vs ground data).
   When output validates, message agronomy-engine and fullstack-dev.

2. agronomy-engine (sonnet), uses the rotation-agronomy skill.
   Write engine/crops.yaml and the rule-based scorer: features + current
   rotation + priority weights → ranked strategies per strategy.schema.json.
   Detect bare-field months and the current crop's stress months.
   Start with mock features; integrate once data-engineer confirms.

3. fullstack-dev (sonnet), uses the frontend-design skill, then unslop.
   Django + DRF: GET /api/features?lat=&lon=, POST /api/strategies.
   React mobile-first, FR/AR with RTL: map location picker, 12-month season
   calendar (bare and stress months), priority sliders, side-by-side strategy
   cards ("why / evidence / risks"), visible "talk to a local expert" note.
   Start from mock JSON; switch to real endpoints when ready.
   Run /unslop on the main screens before reporting done.

4. qa-docs (haiku), uses the webapp-testing skill.
   Scaffold tests from the contracts first; add integration and end-to-end
   tests when the others report done. Write tests/report.md and
   docs/build-summary.md.

ORCHESTRATION:
- Require plan approval: each teammate sends you a short plan before coding.
  Approve routine plans yourself; escalate anything CRITICAL to me.
- Coordinate through contracts and the shared task list, not long chats.
- After each teammate finishes, give me a 3–5 line summary and update
  docs/progress.md.

FINAL DELIVERABLES:
- Running app at http://localhost:3000 with real NASA POWER data for Saïss
- tests/report.md (pass/fail)
- docs/build-summary.md (what was built, key decisions, how to run it,
  limitations, data gaps)
- docs/data-dictionary.md
