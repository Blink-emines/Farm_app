"""MILP of the rotation plan (Pyomo + HiGHS). Cyclic horizon of 24 months.

x[p,c,s] = 1 if crop c is sown on parcel p in month s (only inside the sowing window).
Occupancy z[p,c,t] = sum of x[p,c,s] over sowings still in the field at month t (cyclic), and the
fields hold at most one crop per month. A state P[p,c,t] = "crop c was the last one harvested
before month t" lets the succession rules (legume after cereal, same family) be linear.
Every objective is a utility to maximise; the rule points use weights.yaml only."""
import time

import pyomo.environ as pyo

from ..loaders import families, rooting_class, val
from .objectives import OBJ, objective_income_per_sowing

EPS_TIE = 1e-3


class FarmModel:
    def __init__(self, tables, windows, crops, weights, features, areas, water_m3=None, budget=None, irrigated=None):
        self.tables, self.windows, self.crops, self.weights = tables, windows, crops, weights
        self.areas, self.L = list(areas), tables.horizon
        self.irrigated = [True] * len(self.areas) if irrigated is None else list(irrigated)
        self.years = self.L // 12
        self.list = [c for c in crops if c not in tables.excluded]
        self.last_status = None
        self.ideal = self.nadir = None
        self.time_used = 0.0
        self.n_solves = 0
        self._build(water_m3, budget)
        self.opt = pyo.SolverFactory("appsi_highs")
        self.opt.config.time_limit = float(weights["optimiser"]["solver_time_limit_s"])

    # ---- model -------------------------------------------------------------------------
    def _allowed(self, c, irrigated):
        if not irrigated and val(self.crops, c, "irrigation_required"):
            return []  # rainfed parcel: crops that need irrigation are excluded
        if val(self.crops, c, "perennial"):
            return [0]
        if c == "fallow":
            return list(range(self.L))
        return [s for s in range(self.L) if (s % 12) + 1 in self.windows[c]]

    def _build(self, water_m3, budget):
        L, T, C = self.L, range(self.L), self.list
        w = self.weights["rules"]
        m = self.m = pyo.ConcreteModel()
        self.allowed_p = [{c: self._allowed(c, irr) for c in C} for irr in self.irrigated]
        P = range(len(self.areas))
        m.x = pyo.Var([(p, c, s) for p in P for c in C for s in self.allowed_p[p][c]], domain=pyo.Binary)
        m.P = pyo.Var([(p, c, t) for p in P for c in C for t in T], bounds=(0, 1))
        m.cons = pyo.ConstraintList()
        x, St = m.x, pyo.quicksum
        d = self.tables.duration

        def occ(p, c, t):
            return St(x[p, c, s] for s in self.allowed_p[p][c] if (t - s) % L < d[c])

        def done(p, c, t):  # crop c is harvested at the end of month t
            s = (t - d[c] + 1) % L
            return x[p, c, s] if s in self.allowed_p[p][c] else 0

        fam = {c: families(self.crops, c) for c in C}
        famset = sorted({f for fs in fam.values() for f in fs})
        cereals = [c for c in C if val(self.crops, c, "cereal")]
        legumes = [c for c in C if val(self.crops, c, "legume")]
        perennials = [c for c in C if val(self.crops, c, "perennial")]
        self.u_p, self.expr = [], {}
        for p in P:
            for t in T:
                m.cons.add(St(occ(p, c, t) for c in C) <= 1)
                prev = (t - 1) % L
                tot_done = St(done(p, c, prev) for c in C)
                m.cons.add(St(m.P[p, c, t] for c in C) == 1)
                for c in C:
                    e = done(p, c, prev)
                    m.cons.add(m.P[p, c, t] >= e)
                    m.cons.add(m.P[p, c, t] >= m.P[p, c, prev] - tot_done)
                    m.cons.add(m.P[p, c, t] <= e + m.P[p, c, prev])
                    m.cons.add(m.P[p, c, t] <= 1 - (tot_done - e))
            m.cons.add(St(x[p, c, s] for c in C for s in self.allowed_p[p][c]) >= 1)

            def X(cs, t, p=p):
                return St(x[p, c, t] for c in cs if t in self.allowed_p[p][c])

            def Pst(cs, t, p=p):
                return St(m.P[p, c, t] for c in cs)

            def both(name, a, b, t, p=p):  # continuous AND of two 0/1 expressions
                v = pyo.Var(bounds=(0, 1))
                setattr(m, f"{name}_{p}_{t}", v)
                m.cons.add(v <= a)
                m.cons.add(v <= b)
                m.cons.add(v >= a + b - 1)
                return v

            gaps = self.weights["optimiser"].get("family_gap_months", {})
            for f, q in gaps.items():
                cs = [c for c in C if f in fam[c] and c not in perennials]
                if not cs:
                    continue
                for t in (T if q < L else [0]):
                    win = [(t + k) % L for k in range(min(q, L))]
                    terms = [x[p, c, s] for s in win for c in cs if s in self.allowed_p[p][c]]
                    if len(terms) > 1:
                        m.cons.add(St(terms) <= 1)
            ycl = [both("ycl", Pst(cereals, t), X(legumes, t), t) for t in T] if cereals and legumes else []
            yf = [both(f"yf{f}", Pst([c for c in C if f in fam[c]], t), X([c for c in C if f in fam[c]], t), t)
                  for f in famset for t in T]
            ys = [both(f"ys{c}", m.P[p, c, t], X([c], t), t) for c in perennials for t in T]
            famcrops = [c for c in C if fam[c]]
            yfb = [both("yfb", m.P[p, "fallow", t], X(famcrops, t), t) for t in T] if "fallow" in C else []
            sfam = St(X(famcrops, t) for t in T) - St(yfb)
            changes, repeats = sfam - St(yf), St(yf) - St(ys)
            seas = {c: (self.years if c in perennials else 1) for c in C}  # a perennial counts one season per year
            deep = St(seas[c] * x[p, c, s] for c in C if rooting_class(self.crops, c, self.weights) == "deep"
                      for s in self.allowed_p[p][c])
            yrs = self.years
            soil = (w["n_credit_legume_after_cereal"]["points_per_transition"] * St(ycl)
                    + w["family_break"]["points_per_family_change"] * changes
                    + w["family_break"]["points_per_same_family_repeat"] * repeats
                    + w["deep_root_structure"]["points_per_deep_crop_year"] * deep) / yrs
            real = [c for c in C if c != "fallow"]
            bare = St(1 - St(occ(p, c, t) for c in real) for t in T)
            cover = St(occ(p, c, t) for c in C if val(self.crops, c, "cover") for t in T)
            ero = (w["bare_months_penalty"]["points_per_bare_month"] * bare
                   + w["cover_fills_bare"]["points_per_cover_month"] * cover) / yrs
            lv = w["forage_flag"]["points_by_level"]
            forage = St(seas[c] * lv.get(val(self.crops, c, "forage_flag"), 0) * x[p, c, s] for c in C for s in self.allowed_p[p][c]) / yrs
            income = St(objective_income_per_sowing(self.tables, c) * (d[c] / 12 if c in perennials else 1)
                        * x[p, c, s] for c in C for s in self.allowed_p[p][c]) / yrs
            water = -St(self.tables.deficit[c][t % 12] * occ(p, c, t) for c in C for t in T) / yrs
            self.u_p.append({"save_water": water, "improve_soil": soil, "extra_income": income,
                             "reduce_erosion": ero, "forage": forage})
            self._water_terms = getattr(self, "_water_terms", [])
            self._water_terms.append({t: St(self.tables.deficit[c][t % 12] * occ(p, c, t) for c in C) for t in T})
            self._cost_terms = getattr(self, "_cost_terms", [])
            self._cost_terms.append(St((self.tables.cost[c] or 0.0) * (d[c] / 12 if c in perennials else 1)
                                       * x[p, c, s] for c in C for s in self.allowed_p[p][c]) / yrs)
        tot = sum(self.areas)
        self.u = {k: St(self.areas[p] / tot * self.u_p[p][k] for p in P) for k in OBJ}
        if water_m3 is not None and any(self.irrigated):
            for t in T:
                m.cons.add(St(self.areas[p] * 10 * self._water_terms[p][t] for p in P if self.irrigated[p]) <= water_m3[t % 12])
        if budget is not None and any(v is not None for v in self.tables.cost.values()):
            m.cons.add(St(self.areas[p] * self._cost_terms[p] for p in P) <= budget)

    # ---- solving -----------------------------------------------------------------------
    def _solve(self, expr, eps_constraint=None):
        m = self.m
        for name in ("obj", "eps"):
            if hasattr(m, name):
                m.del_component(name)
        m.obj = pyo.Objective(expr=expr, sense=pyo.maximize)
        if eps_constraint is not None:
            m.eps = pyo.Constraint(expr=eps_constraint)
        t0 = time.time()
        res = self.opt.solve(m)
        self.time_used += time.time() - t0
        self.n_solves += 1
        tc = str(res.solver.termination_condition).lower()
        if "optimal" in tc:
            self.last_status = "optimal"
        elif "time" in tc and self._has_solution():
            self.last_status = "feasible"
        else:
            self.last_status = "infeasible" if "infeasible" in tc else "error"
            raise RuntimeError(f"solver status {tc}")
        plans = self._plans()
        return plans, {k: pyo.value(self.u[k]) for k in OBJ}

    def _has_solution(self):
        try:
            return any(pyo.value(v) is not None for v in self.m.x.values())
        except ValueError:
            return False

    def _plans(self):
        plans = []
        for p in range(len(self.areas)):
            spans = []
            for c in self.list:
                for s in self.allowed_p[p][c]:
                    if pyo.value(self.m.x[p, c, s]) > 0.5:
                        if val(self.crops, c, "perennial"):  # one 12-month season per year of the cycle
                            spans += [(s + 12 * k, s + 12 * k + 11, c) for k in range(self.years)]
                        else:
                            spans.append((s, s + self.tables.duration[c] - 1, c))
            plans.append({"length": self.L, "spans": sorted(spans)})
        return plans

    def maximise_utility(self, k):
        return self._solve(self.u[k])

    def payoff(self):
        """Single-objective solves give the ideal point; nadir = worst value met in the table."""
        vals = {k: self.maximise_utility(k)[1] for k in OBJ}
        self.ideal = {k: vals[k][k] for k in OBJ}
        self.nadir = {k: min(vals[j][k] for j in OBJ) for k in OBJ}
        return self.ideal, self.nadir

    def extend_nadir(self, values):
        """Make sure the farmer's current plans lie inside the normalisation range."""
        for k in OBJ:
            self.nadir[k] = min(self.nadir[k], values[k])

    def norm(self, k, v):
        """0..1 score; 0.5 when the objective cannot discriminate between plans."""
        rng = self.ideal[k] - self.nadir[k]
        return 0.5 if rng <= 1e-9 else min(1.0, max(0.0, (v - self.nadir[k]) / rng))

    def _n_expr(self, k):
        rng = self.ideal[k] - self.nadir[k]
        return 0 if rng <= 1e-9 else (self.u[k] - self.nadir[k]) / rng

    def solve_weighted(self, priorities):
        if self.ideal is None:
            self.payoff()
        tot = sum(priorities.values())
        wts = {k: (priorities[k] / tot if tot else 1 / len(OBJ)) for k in OBJ}
        expr = pyo.quicksum(wts[k] * self._n_expr(k) for k in OBJ) + EPS_TIE * pyo.quicksum(self._n_expr(k) for k in OBJ)
        return self._solve(expr)

    def pareto(self, n):
        """Epsilon-constraint, income against water: maximise income with water at least eps."""
        if self.ideal is None:
            self.payoff()
        pts, seen = [], set()
        steps = [1 - i / (n - 1) for i in range(n)] if n > 1 else [1.0]
        others = [k for k in OBJ if k not in ("extra_income", "save_water")]
        for eps in steps:
            expr = self._n_expr("extra_income") + EPS_TIE * pyo.quicksum(self._n_expr(k) for k in others)
            try:
                plans, u = self._solve(expr, eps_constraint=self._n_expr("save_water") >= eps - 1e-9)
            except RuntimeError:
                continue
            key = (round(u["extra_income"], 3), round(u["save_water"], 3))
            if key not in seen:
                seen.add(key)
                pts.append({"eps": eps, "plans": plans, "u": u})
        return pts
