import { useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { smooth, StatusKey } from './charts.jsx';

const STATUS_FILL = { growing: 'band-growing', stress: 'band-stress', bare: 'band-bare' };

// NDVI (satellite greenness) over the 12 months, with the option's calendar as coloured
// bands behind it, so a bare month can be compared with what the satellite sees.
function NdviChart({ avg, recent, months }) {
  const { t, month, lang } = useI18n();
  const W = 360;
  const col = W / 12;
  const x = (i) => col * (lang === 'ar' ? 11 - i : i) + col / 2;
  const y = (v) => 128 - Math.max(Math.min(v, 1), 0) * 112;
  const line = (arr) => {
    const pts = arr.map((v, i) => (v == null ? null : [x(i), y(v)])).filter(Boolean).sort((a, b) => a[0] - b[0]);
    return pts.length > 1 ? smooth(pts) : null;
  };
  const dAvg = line(avg);
  const dRec = recent ? line(recent.values) : null;
  return (
    <svg className="ndvi" viewBox="0 0 360 160" role="img" aria-label={t('ui.sp_title')}>
      {months.map((m, i) => (
        <rect key={m.month} className={`band ${STATUS_FILL[m.status]}`} x={x(i) - col / 2} y="8" width={col} height="120">
          <title>{`${month(m.month)}: ${t(`ui.month_status_${m.status}`)}`}</title>
        </rect>
      ))}
      {[0, 0.5, 1].map((v) => (
        <g key={v}>
          <line className="grid-line" x1="0" x2={W} y1={y(v)} y2={y(v)} />
          <text className="axis" x={lang === 'ar' ? W : 0} y={y(v) - 3} textAnchor={lang === 'ar' ? 'end' : 'start'}>{v}</text>
        </g>
      ))}
      {dAvg && <path className="ndvi-avg" d={dAvg} />}
      {dRec && <path className="ndvi-recent" d={dRec} />}
      {avg.map((v, i) => v != null && <circle key={i} className="ndvi-dot" cx={x(i)} cy={y(v)} r="3" />)}
      {months.map((m, i) => <text key={m.month} className="axis" x={x(i)} y="150" textAnchor="middle">{m.month}</text>)}
    </svg>
  );
}

export default function SpaceView({ features, strategies }) {
  const { t, tm, month } = useI18n();
  const [id, setId] = useState(strategies[0].id);
  const veg = features?.vegetation;
  const s = strategies.find((x) => x.id === id) ?? strategies[0];

  if (!veg || veg.status === 'unavailable' || !veg.ndvi_monthly?.some((v) => v != null)) {
    return (
      <section className="panel" aria-labelledby="sp-h">
        <h3 id="sp-h">{t('ui.sp_title')}</h3>
        <p className="notice">{t('ui.sp_unavailable')}</p>
      </section>
    );
  }
  const avg = veg.ndvi_monthly;
  const valid = avg.map((v, i) => [v, i]).filter(([v]) => v != null);
  const hi = valid.reduce((a, b) => (b[0] > a[0] ? b : a));
  const lo = valid.reduce((a, b) => (b[0] < a[0] ? b : a));

  return (
    <section className="panel" aria-labelledby="sp-h">
      <h3 id="sp-h">{t('ui.sp_title')}</h3>
      <p className="muted">{t('ui.sp_intro')}</p>

      <label className="field">
        <span>{t('ui.sp_pick')}</span>
        <select value={s.id} onChange={(e) => setId(e.target.value)}>
          {strategies.map((o) => <option key={o.id} value={o.id}>{tm(o.name)}</option>)}
        </select>
      </label>

      <figure className="chart">
        <figcaption>{t('ui.sp_axis')}</figcaption>
        <NdviChart avg={avg} recent={veg.recent} months={s.calendar[0].months} />
        <ul className="chart-key">
          <li><i className="sw-line" />{t('ui.sp_key_avg', { start: veg.period?.start_year, end: veg.period?.end_year })}</li>
          {veg.recent && <li><i className="sw-line sw-recent" />{t('ui.sp_key_recent', { year: veg.recent.year })}</li>}
        </ul>
        <StatusKey />
      </figure>

      <p className="notice">
        {t('ui.sp_peak', { m1: month(hi[1] + 1), v1: hi[0].toFixed(2), m2: month(lo[1] + 1), v2: lo[0].toFixed(2) })}
      </p>
      <p className="muted">{t('ui.sp_note')}</p>
      <p className="muted">{t('ui.sp_product', { product: veg.product })}</p>
    </section>
  );
}
