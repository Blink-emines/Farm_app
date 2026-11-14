# Project rules (all agents)
- Contracts in docs/contracts/ are the single source of truth.
- Edit only your own folder. Cross-folder changes go through the lead.
- Read only your folder + docs/contracts/. Do not scan the whole repo.
- Keep messages short (≤5 lines).

## CRITICAL: the lead must get human approval before:
- changing a contract after it is approved
- adding a dependency, external service or API key
- changing scoring rules or weights in engine/
- deleting or rewriting more than ~50 lines of another agent's work
- expanding scope (new region, dataset, ML, auth, deployment)
Present: what, why, alternatives, impact. Then wait.

## Transparency
- docs/progress.md: update after each milestone (who, what, status, blockers)
- docs/decisions.md: log every decision, its reason, and who approved it

## This tool supports farmers; it never replaces their judgment or local experts.
