# Decisions

Every decision, its reason, and who approved it.

| Date | Decision | Reason | Approved by |
|------|----------|--------|-------------|
| 2026-11-14 | Installed third-party skills unslop, frontend-design and webapp-testing in .claude/skills/, including their helper scripts | Needed by fullstack-dev (UI) and qa-docs (end-to-end tests) | user |
| 2026-11-14 | Replaced the root CLAUDE.md (weather-app rules) with the multi-agent project rules | The project is now the crop-rotation decision-support tool; old version kept in git history | user |
| 2026-11-14 | Kept the earlier agents backend-developer, frontend-developer and qa-security in .claude/agents/ next to the four Phase 2 agents | User choice; Phase 2 spawns data-engineer, agronomy-engine, fullstack-dev and qa-docs | user |
| 2026-11-14 | Build the Phase 2 Django REST API on the existing Django project in backend/ (layers 1-3 of the weather app: user accounts, JWT login, Field/Measurement models, data-isolation tests) instead of starting from scratch | Reuse working, tested code; docs/plan.md must state what is reused, changed or removed | user |
