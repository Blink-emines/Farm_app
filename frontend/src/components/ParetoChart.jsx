import { useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { whole } from '../util.js';

// Income against water for the plans the optimiser found. Tap a point to read that plan.
export default function ParetoChart({ points, plan, parcelNames }) {
  const { t, seq } = useI18n();
  const [sel, setSel] = useState(null);
  if (!points.length) return null;
  const W = 360;
  const H = 220;
  const pad = { l: 44, r: 18, t: 30, b: 40 };
  const xs = [...points.map((p) => p.water_deficit_mm_per_year), plan.water];
  const ys = [...points.map((p) => p.revenue_mad_per_ha_year), plan.revenue];
  const xMax = Math.max(...xs, 1) * 1.08;
  const yMax = Math.max(...ys, 1) * 1.08;
  const x = (v) => pad.l + (v / xMax) * (W - pad.l - pad.r);
  const y = (v) => H - pad.b - (v / yMax) * (H - pad.t - pad.b);
  const p = sel != null ? points[sel] : null;
  const path = points.map((q, i) => `${i ? 'L' : 'M'}${x(q.water_deficit_mm_per_year)},${y(q.revenue_mad_per_ha_year)}`).join(' ');
  return (
    <figure className="chart pareto">
      <figcaption>{t('ui.opt_pareto_title')}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('ui.opt_pareto_title')}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line className="grid-line" x1={pad.l} x2={W - pad.r} y1={y(yMax * f)} y2={y(yMax * f)} />
            <text className="axis" x={pad.l - 6} y={y(yMax * f) + 4} textAnchor="end">{whole((yMax * f) / 1000)}k</text>
            <text className="axis" x={x(xMax * f)} y={H - pad.b + 16} textAnchor="middle">{whole(xMax * f)}</text>
          </g>
        ))}
        <text className="axis" x={(W + pad.l) / 2} y={H - 6} textAnchor="middle">{t('ui.opt_axis_water')}</text>
        <text className="axis" x="4" y="10">{t('ui.opt_axis_income')}</text>
        <path className="pareto-line" d={path} />
        {points.map((q, i) => (
          <g key={i} className="pareto-pt" onClick={() => setSel(i)}>
            <circle cx={x(q.water_deficit_mm_per_year)} cy={y(q.revenue_mad_per_ha_year)} r="18" fill="transparent" />
            <circle className={`pareto-dot${sel === i ? ' is-sel' : ''}`} cx={x(q.water_deficit_mm_per_year)} cy={y(q.revenue_mad_per_ha_year)} r={sel === i ? 7 : 5} />
          </g>
        ))}
        <rect className="pareto-plan" x={x(plan.water) - 6} y={y(plan.revenue) - 6} width="12" height="12" transform={`rotate(45 ${x(plan.water)} ${y(plan.revenue)})`} />
      </svg>
      <ul className="chart-key">
        <li><i className="sw-dot" />{t('ui.opt_key_point')}</li>
        <li><i className="sw plan-sw" />{t('ui.opt_key_plan')}</li>
      </ul>
      {/* The buttons below give a keyboard and screen reader route to the same points. */}
      <div className="pareto-pick" role="group" aria-label={t('ui.opt_pareto_pick')}>
        {points.map((q, i) => (
          <button key={i} type="button" aria-pressed={sel === i} onClick={() => setSel(i)}>{i + 1}</button>
        ))}
      </div>
      {p ? (
        <div className="notice" aria-live="polite">
          <h4>{t('ui.opt_pareto_plan', { n: sel + 1 })}</h4>
          <ul>
            {p.crops.map((c, i) => <li key={i}><strong>{parcelNames[i]}</strong> : {seq(c)}</li>)}
          </ul>
          <p className="muted">
            {t('ui.opt_pareto_vals', { income: whole(p.revenue_mad_per_ha_year), water: whole(p.water_deficit_mm_per_year) })}
          </p>
        </div>
      ) : <p className="muted">{t('ui.opt_pareto_hint')}</p>}
    </figure>
  );
}
