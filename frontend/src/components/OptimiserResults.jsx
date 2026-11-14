import { useI18n } from '../i18n/index.jsx';
import { signed, whole } from '../util.js';
import Calendar from './Calendar.jsx';
import ParetoChart from './ParetoChart.jsx';

const fmt = (n) => new Intl.NumberFormat('fr-FR').format(whole(n)).replace(/\s/g, ' ');

function Money({ n }) {
  const { t } = useI18n();
  return <bdi dir="ltr">{fmt(n)} {t('ui.opt_mad')}</bdi>;
}

function ParcelResult({ r, name }) {
  const { t, tm, num: fmt } = useI18n();
  const v = r.values;
  const plan = r.plan;
  return (
    <article className="parcel-res panel">
      <header>
        <h3>{name}</h3>
        <p className="muted">
          {t('ui.opt_area', { n: r.area_ha })} · {r.irrigated ? t('ui.opt_irrigated') : t('ui.opt_rainfed')}
        </p>
        <p><strong>{tm(plan.name)}</strong></p>
        <p className="muted">{t('ui.opt_before')} : {tm(r.baseline.name)}</p>
      </header>

      <ul className="opt-facts">
        <li>
          <span>{t('ui.opt_revenue_ha')}</span>
          <b><Money n={v.revenue_mad_per_ha_year} /></b>
          <small>{t('ui.opt_before')} <Money n={v.baseline_revenue_mad_per_ha_year} /> · {t('ui.opt_range', { bad: fmt(v.revenue_range_mad_per_ha_year.bad_year), good: fmt(v.revenue_range_mad_per_ha_year.good_year) })}</small>
        </li>
        <li>
          <span>{r.irrigated ? t('ui.opt_water_irrig_ha') : t('ui.opt_water_risk_ha')}</span>
          <b><bdi dir="ltr">{whole(v.water_deficit_mm_per_year)} mm</bdi></b>
          <small>{t('ui.opt_before')} <bdi dir="ltr">{whole(v.baseline_water_deficit_mm_per_year)} mm</bdi></small>
        </li>
      </ul>

      <section className="block">
        <h4>{t('ui.opt_plan24')}</h4>
        <Calendar calendar={plan.calendar} seasons={plan.seasons} />
      </section>
      <section className="block">
        <h4>{t('ui.why')}</h4>
        <ul className="why">
          {plan.why.map((w, i) => (
            <li key={i}>
              <span className={`pts pts-${w.effect}`}>{t('ui.points_for', { n: signed(w.points), goal: t(`ui.goal_${w.priority}`) })}</span>
              <span>{tm(w.message)}</span>
            </li>
          ))}
        </ul>
      </section>
      <section className="block">
        <h4>{t('ui.risks')}</h4>
        <ul>{plan.risks_for_local_review.map((m, i) => <li key={i}>{tm(m)}</li>)}</ul>
      </section>
      <details className="block">
        <summary>{t('ui.data_gaps')}</summary>
        <ul>{plan.information_gaps.map((m, i) => <li key={i}>{tm(m)}</li>)}</ul>
      </details>
    </article>
  );
}

export default function OptimiserResults({ data, names, onBack }) {
  const { t, tm, num: fmt } = useI18n();
  const tot = data.totals;
  const plan = {
    water: -data.objectives.save_water.plan_value,
    revenue: data.objectives.extra_income.plan_value,
  };
  const main = data.notes.filter((n) => ['note_relative_scores', 'note_local_expert'].includes(n.code));
  const rest = data.notes.filter((n) => !main.includes(n));
  const gain = tot.baseline_gross_revenue_mad_per_year ? tot.gross_revenue_mad_per_year - tot.baseline_gross_revenue_mad_per_year : 0;

  return (
    <section className="results-wrap" aria-labelledby="opt-res-h">
      <div className="results-head">
        <h2 id="opt-res-h">{t('ui.opt_results_title')}</h2>
        <button type="button" className="btn btn-quiet" onClick={onBack}>{t('ui.change_answers')}</button>
      </div>
      <ul className="notes">{main.map((n, i) => <li key={i}>{tm(n)}</li>)}</ul>

      <section className="panel totals" aria-labelledby="tot-h">
        <h3 id="tot-h">{t('ui.opt_totals')}</h3>
        <ul className="opt-facts big">
          <li>
            <span>{t('ui.opt_gross')}</span>
            <b><Money n={tot.gross_revenue_mad_per_year} /></b>
            <small>{t('ui.opt_range', { bad: fmt(tot.revenue_range_mad_per_year.bad_year), good: fmt(tot.revenue_range_mad_per_year.good_year) })}</small>
            <small>{t('ui.opt_before')} <Money n={tot.baseline_gross_revenue_mad_per_year} />{gain ? ` (${signed(gain / 1000)}k)` : ''}</small>
          </li>
          <li>
            <span>{t('ui.opt_irrigation')}</span>
            <b><bdi dir="ltr">{fmt(tot.irrigation_need_m3_per_year)} m³</bdi></b>
            <small>{t('ui.opt_per_year')}</small>
          </li>
          <li>
            <span>{t('ui.opt_farm_area')}</span>
            <b><bdi dir="ltr">{tot.area_ha} ha</bdi></b>
          </li>
        </ul>
        <p className="muted">{t('ui.opt_estimate')}</p>
        {tot.profit_mad_per_year == null && <p className="muted">{t('ui.opt_no_profit')}</p>}
        {data.information_gaps.length > 0 && (
          <details className="block"><summary>{t('ui.data_gaps')}</summary><ul>{data.information_gaps.map((m, i) => <li key={i}>{tm(m)}</li>)}</ul></details>
        )}
      </section>

      <ParetoChart points={data.pareto} plan={plan} parcelNames={names} />

      {data.parcels.map((r, i) => <ParcelResult key={r.id} r={r} name={names[i]} />)}

      {rest.length > 0 && (
        <details className="block"><summary>{t('ui.other_notes')}</summary><ul>{rest.map((n, i) => <li key={i}>{tm(n)}</li>)}</ul></details>
      )}
    </section>
  );
}
