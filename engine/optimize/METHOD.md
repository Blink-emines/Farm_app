# Optimiser method (engine/optimize)

Mixed-integer linear model solved with Pyomo + HiGHS. No ML: every score is a rule from
`engine/weights.yaml`; the solver only searches for the plan that maximises them.

## Model
- Months 1..24, cyclic (occupancy wraps, so winter crops crossing New Year work). The calendar rows
  are the two calendar years of the cycle.
- `x[p,c,s] = 1` if crop c is sown on parcel p in month s, only inside the sowing window of c.
  A crop occupies `d_c` months from its sowing (d from the approved default sow/harvest months;
  fallow 12; perennials the whole cycle). At most one crop per month.
- A state `P[p,c,t]` ("c was the last crop harvested before month t") makes the succession rules linear:
  legume after cereal, same family / family change, perennial following itself (no penalty), fallow
  (no family). The rule points are exactly those of `engine/rules.py` (tests compare the MILP value
  with the rule-based evaluator on the solved plan).
- Optional water cap: monthly irrigation m3 for the whole farm vs sum(area x 10 x deficit mm).
  Optional budget: only used when costs are known. Either one couples the parcels (one joint solve);
  otherwise all parcels share one optimal plan and the solve is done once.

## Irrigation and family gaps (lead decisions 2026-11-14)
- Each parcel has `irrigated` (default false = rainfed). Crops with `irrigation_required` in crops.yaml
  (potato; reason cited there) are excluded on rainfed parcels. On rainfed parcels the water goal is the
  rainfed deficit (a stress risk), not a volume. The monthly water cap applies to irrigated parcels only;
  when it leaves an irrigated parcel fallow the plan says so (`gap_irrigation_insufficient`).
- Hard minimum months between two sowings of the same family on a parcel, cyclic
  (`optimiser.family_gap_months`: solanaceae 24, fabaceae 24, asteraceae 24, poaceae 12). Assumption,
  common rotation guidance, approved by the lead; perennials are exempt. Poaceae repeats stay allowed
  yearly, and the soil goal still penalises them.
- A perennial counts as one 12-month season per year of the cycle, as in the rules.
- Parcels with the same constraints share one solve (one class rainfed, one irrigated); a water cap makes
  each irrigated parcel its own solve, a budget (with costs) makes every parcel its own.

## Objectives (all maximised, per hectare and year, area-weighted over parcels)
| goal | value |
|---|---|
| save_water | minus sum over growing months of max(0, Kc_mid x ET0 - precipitation), mm. Plain precipitation is used (no effective-rain formula) |
| improve_soil | rule points: n_credit_legume_after_cereal, family_break, deep_root_structure |
| extra_income | gross revenue = FAOSTAT price x 10-year mean yield (MAD), or profit when the farmer gives costs |
| reduce_erosion | rule points: bare_months_penalty, cover_fills_bare |
| forage | rule points: forage_flag (qualitative labels) |

Water details: fallow has no crop transpiration, so its deficit is 0 (bare-soil evaporation is
ignored). vetch_oat_cover uses the FAO-56 Table 12 oats Kc_mid as a labelled proxy (an unknown Kc must
not mean zero water). Any other crop with an unknown Kc is excluded from optimisation (still shown)
and listed as a gap. Crops without price data (alfalfa, vetch_oat_cover) count as zero revenue in the
optimiser and are listed as a gap; the income label rule still appears in the explanation.

## Normalisation and weights
Payoff table: one single-objective solve per goal gives the ideal; the nadir is the worst value met
in that table, widened to include the farmer's current rotations and the chosen plans (ties in the
payoff table can hide a worse value; widening keeps every plan shown inside 0-100). Score =
100 x (value - nadir) / (ideal - nadir) (50 when a goal cannot discriminate). The plan maximises the
weighted sum of normalised goals (slider weights or a profile from `weights.yaml`) plus a tiny tie-break.
Pareto: epsilon-constraint, income against water, `pareto_points` solves.

## Sowing windows (windows.py, levels in weights.yaml)
- Autumn crops: scanning forward from the driest month, the window opens at the first month with
  precipitation >= 0.5 x ET0 (FAO AEZ definition of the start of the growing period, Kassam et al.).
- Spring crops: scanning forward from the coldest month, the window opens at the first month with
  t2m_min >= a generic level and frost_days below a generic level (assumptions, labelled).
- Window length 3 months (assumption, approved by the lead). Perennials and fallow: any month.
- If nothing qualifies: approved default sow month +/- 1, with the gap `gap_window_fallback`.

## Economics (economics.yaml)
FAOSTAT producer prices 2024 (Producer Prices domain) and FAOSTAT yields 2015-2024 (QCL domain), Morocco,
national, each with item, element, unit and year; all "editable default". No Moroccan cost per hectare
source was found: costs stay "unknown, needs local data". Profit is therefore shown only when costs are
entered. Revenue range = price x min / mean / max yield of the 10 years (Moroccan yields swing with drought).
Caveat: national FAOSTAT yields (potato about 31 t/ha) mix irrigated and rainfed fields.
