import { useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { GOALS } from '../constants.js';
import { monthsPerYear, whole } from '../util.js';
import { Ribbon } from './Calendar.jsx';
import { StatusKey } from './charts.jsx';

const oneDecimal = (n) => String(Math.round(Math.abs(n) * 10) / 10);

// Differences are computed here from the response only: scores, and calendar months per year.
function differences(a, b, t) {
  const out = [];
  const dTotal = whole(a.score.total - b.score.total);
  if (dTotal) out.push(t(dTotal > 0 ? 'ui.diff_total_more' : 'ui.diff_total_less', { n: Math.abs(dTotal) }));
  for (const [status, key] of [['bare', 'bare'], ['stress', 'stress']]) {
    const d = monthsPerYear(a, status) - monthsPerYear(b, status);
    if (Math.round(Math.abs(d) * 10) >= 1) out.push(t(d < 0 ? `ui.diff_${key}_less` : `ui.diff_${key}_more`, { n: oneDecimal(d) }));
  }
  GOALS
    .map((g) => [g, a.score.by_priority[g] - b.score.by_priority[g]])
    .filter(([, d]) => whole(d) !== 0)
    .sort((x, y) => Math.abs(y[1]) - Math.abs(x[1]))
    .forEach(([g, d]) => out.push(t(d > 0 ? 'ui.diff_goal_more' : 'ui.diff_goal_less', { goal: t(`ui.goal_${g}`), n: Math.abs(whole(d)) })));
  if (a.confidence !== b.confidence) {
    out.push(t('ui.diff_conf', { a: t(`ui.confidence_${a.confidence}`), b: t(`ui.confidence_${b.confidence}`) }));
  }
  return out;
}

export default function Compare({ strategies }) {
  const { t, tm } = useI18n();
  const [ids, setIds] = useState([strategies[0].id, (strategies.find((s) => s.is_current) ?? strategies[1]).id]);
  const [a, b] = ids.map((id) => strategies.find((s) => s.id === id));
  const same = a.id === b.id;
  const diffs = same ? [] : differences(a, b, t);
  const pick = (i, id) => setIds(ids.map((x, j) => (j === i ? id : x)));

  return (
    <section className="panel" aria-labelledby="compare-h">
      <h3 id="compare-h">{t('ui.compare_title')}</h3>
      <div className="row">
        {[a, b].map((s, i) => (
          <label className="field" key={i}>
            <span><i className={`sw cmp-sw-${i}`} />{t(i ? 'ui.compare_b' : 'ui.compare_a')}</span>
            <select value={s.id} onChange={(e) => pick(i, e.target.value)}>
              {strategies.map((o) => <option key={o.id} value={o.id}>{tm(o.name)}</option>)}
            </select>
          </label>
        ))}
      </div>
      {same ? <p className="notice">{t('ui.compare_same')}</p> : (
        <>
          <figure className="chart">
            <figcaption>{t('ui.compare_goals')}</figcaption>
            <ul className="goal-bars">
              {GOALS.map((g) => (
                <li key={g}>
                  <span className="goal-name">{t(`ui.goal_${g}`)}</span>
                  {[a, b].map((s, i) => (
                    <span className="goal-row" key={i}>
                      <span className="goal-track"><span className={`goal-fill cmp-fill-${i}`} style={{ inlineSize: `${s.score.by_priority[g]}%` }} /></span>
                      <span className="goal-num">{whole(s.score.by_priority[g])}</span>
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          </figure>

          <div className="stack">
            <h4>{t('ui.compare_calendars')}</h4>
            {[a, b].map((s, i) => (
              <div className="cal-year" key={s.id}>
                <h5><i className={`sw cmp-sw-${i}`} />{tm(s.name)}</h5>
                {s.calendar.map((row) => <Ribbon key={row.year} months={row.months} />)}
              </div>
            ))}
            <StatusKey />
          </div>

          <div className="notice">
            <h4>{t('ui.compare_diff')}</h4>
            {diffs.length ? <ul>{diffs.map((d, i) => <li key={i}>{d}</li>)}</ul> : <p>{t('ui.diff_none')}</p>}
          </div>
        </>
      )}
    </section>
  );
}
