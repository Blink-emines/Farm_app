# Decisions

Every decision, its reason, and who approved it.

| Date | Decision | Reason | Approved by |
|------|----------|--------|-------------|
| 2026-11-14 | Installed third-party skills unslop, frontend-design and webapp-testing in .claude/skills/, including their helper scripts | Needed by fullstack-dev (UI) and qa-docs (end-to-end tests) | user |
| 2026-11-14 | Replaced the root CLAUDE.md (weather-app rules) with the multi-agent project rules | The project is now the crop-rotation decision-support tool; old version kept in git history | user |
| 2026-11-14 | Kept the earlier agents backend-developer, frontend-developer and qa-security in .claude/agents/ next to the four Phase 2 agents | User choice; Phase 2 spawns data-engineer, agronomy-engine, fullstack-dev and qa-docs | user |
| 2026-11-14 | Approved docs/plan.md and the contracts (features.schema.json, strategy.schema.json, contracts/README.md) | Step 0 of the kickoff | user |
| 2026-11-14 | Dependencies: pandas, PyYAML, jsonschema, pytest, playwright (Python); react, react-dom, vite, @vitejs/plugin-react, leaflet, react-leaflet (JS); Playwright Chromium download | Plan section 5.1; Python ones installed once by the lead to avoid parallel installs clashing | user |
| 2026-11-14 | OpenStreetMap tiles for the map picker, with attribution | Plan section 5.2 | user |
| 2026-11-14 | /api/features and /api/strategies open without login; nothing stored per user | Plan section 5.3 | user |
| 2026-11-14 | Saïss box lat 33.70-34.20, lon -5.70 to -4.70; default point 33.96, -5.27 (approximate) | Plan section 5.4 | user |
| 2026-11-14 | "fallow" allowed next to the 10 crops | Plan section 5.5 | user |
| 2026-11-14 | extra_income and forage scored from qualitative crop flags, low confidence, "local prices" always an information gap | Plan section 5.6 | user |
| 2026-11-14 | Rule points approved as proposed by agronomy-engine (legume after cereal +10; family change +5 / repeat -10; deep roots +5; bare month -2; cover fills bare month +3; enough-water month +5 / water-stress month -5; income/forage flag high +10 / medium +5 / low 0), per rotation year | Initial weights required human approval (CLAUDE.md) | user |
| 2026-11-14 | by_priority scores are min-max scaled across ALL scored candidates (templates + current rotation), not only the returned 3-5 | Avoids small differences showing as 0 vs 100 | user |
| 2026-11-14 | Frost and heat: shown as stress months and risks for local review with an information gap, zero score points | FAO-56 gives no crop frost/heat tolerances; no approved source | user |
| 2026-11-14 | Sow/harvest months: engine proposes defaults (FAO-56 Table 11 Mediterranean examples where they exist), labelled "default, to confirm locally"; user reviews the list; farmer can override in the app | No Saïss-specific calendar source found | user |
| 2026-11-14 | Default months approved: wheat 11-6, barley 11-5, chickpea 3-7, lentil 11-5, faba bean 11-5 (changed from FAO-56 example 3-6), sunflower 4-8, potato 1-5, vetch-oat 11-4, alfalfa/olive/fallow all year; all labelled "to confirm locally" | No Saïss calendar source; faba bean is usually autumn-sown in Morocco | user |
| 2026-11-14 | Income/forage flags approved as proposed except faba bean income and alfalfa income raised to medium | Qualitative only, no price data | user |
| 2026-11-14 | vetch_oat_cover treated as legume family (Fabaceae) for the family rule | Oats are generally a break crop for wheat diseases; avoids a contradictory bonus + penalty | user |
| 2026-11-14 | Calendar bug sent back to agronomy-engine: seasons crossing New Year were dropped or overlapped | Found by lead running score() on the real sample (wheat → fallow) | lead |
| 2026-11-14 | unslop direction approved (plain, patient, trustworthy; neutral surfaces, earth colours only in the calendar; furrow-strip calendar; clay tick for stress; one card level; foldable sections) with two changes: "why", risks and expert note always open; rainfall line only from API precipitation and et0, labelled "rain vs reference evaporation" | Kickoff requires "why" visible; frontend must not invent crop-water figures | user |
| 2026-11-14 | Design direction changed: the user wants a high-end, impressive look; the "plain, patient" direction is replaced. The designer shows 2 premium directions of the results screen, the user picks one | User feedback that the design was weak | user |
| 2026-11-14 | Scope expansion: climate dashboard, compare two strategies, soil profile visual, printable report for the advisor (frontend only, existing API data, hand-drawn SVG, no chart library) | Requested by the user | user |
| 2026-11-14 | New dependency: self-hosted font package(s) in frontend/ (Latin + Arabic pair) | Premium typography in FR and AR | user |
| 2026-11-14 | New external service: Esri World Imagery satellite tiles as default map layer (attribution shown; terms to check before any public launch), OpenStreetMap kept as alternative | Farmers see their own field | user |
| 2026-11-14 | Design picked: direction B's year dial and amber score on direction A's light page, IBM Plex Sans + IBM Plex Sans Arabic; chart legends, whole-number scores in the UI, hero shows strengths first then the main risk | Impressive visual, still readable outdoors in bright sun | user |
| 2026-11-14 | Installed ui-ux-pro-max skill (reviewed: local CSV search scripts, no network) and asked for a full redesign with it; "Données manquantes" renamed to data limits | User: design ugly, no life | user |
| 2026-11-14 | Hackathon features: landing story page, 20-year time machine, field from space (MODIS NDVI via ORNL DAAC, new NASA dataset), live what-if builder; contract features.schema.json extended with optional "yearly" and "vegetation" blocks | User wants a NASA-hackathon-winning app | user |
| 2026-11-14 | Contract: added 500 internal_error to docs/contracts/README.md | Defined reply for unexpected failures, same error body | user |
| 2026-11-14 | Run the four roles as background subagents with the lead relaying messages, not as an agent team | This session (VS Code) has no named-teammate or shared task-list tools | lead (informed user) |
| 2026-11-14 | Build the Phase 2 Django REST API on the existing Django project in backend/ (layers 1-3 of the weather app: user accounts, JWT login, Field/Measurement models, data-isolation tests) instead of starting from scratch | Reuse working, tested code; docs/plan.md must state what is reused, changed or removed | user |
