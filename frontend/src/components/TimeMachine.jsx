import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { mean, whole } from '../util.js';
import { MonthBars } from './charts.jsx';

const DROUGHT_COUNT = 3; // the driest years are the 3 lowest rain totals

function YearBars({ years, rain, avg, current, drought, onPick }) {
  const { t } = useI18n();
  const W = 360;
  const base = 120;
  const col = W / years.length;
  const top = Math.max(...rain.filter((r) => r != null), 1) * 1.1;
  const y = (v) => base - (v / top) * 104;
  return (
    <svg className="ybars" viewBox="0 0 360 150" role="img" aria-label={t('ui.tm_bar_rain')}>
      <line className="grid-line" x1="0" x2={W} y1={y(avg)} y2={y(avg)} strokeDasharray="4 3" />
      {rain.map((r, i) => r != null && (
        <g key={years[i]} onClick={() => onPick(i)} className="ybar-hit">
          <rect x={col * i} y="0" width={col} height="150" fill="transparent" />
          <rect
            className={`ybar${drought.has(i) ? ' is-dry' : ''}${i === current ? ' is-now' : ''}`}
            x={col * i + 2} width={col - 4} y={y(r)} height={base - y(r)} rx="2"
          >
            <title>{`${years[i]}: ${whole(r)} mm`}</title>
          </rect>
        </g>
      ))}
      {years.map((yr, i) => (i % 5 === 0 || (i === current && Math.abs(i % 5 - 2.5) < 2)) && (
        <text key={yr} className="axis" x={col * i + col / 2} y="142" textAnchor={i === 0 ? 'start' : i === years.length - 1 ? 'end' : 'middle'}>{yr}</text>
      ))}
    </svg>
  );
}

function Stat({ label, value }) {
  return <li><span className="muted">{label}</span><strong>{value}</strong></li>;
}

export default function TimeMachine({ features }) {
  const { t, lang } = useI18n();
  const yr = features?.yearly;
  const [i, setI] = useState(yr ? yr.years.length - 1 : 0);
  const [playing, setPlaying] = useState(false);
  const n = yr?.years.length ?? 0;

  useEffect(() => {
    if (!playing) return undefined;
    const id = setInterval(() => setI((k) => {
      if (k >= n - 1) { setPlaying(false); return k; }
      return k + 1;
    }), 700);
    return () => clearInterval(id);
  }, [playing, n]);

  if (!yr) return <section className="panel"><p>{t('ui.tm_none')}</p></section>;

  const { years, precipitation: rain } = yr;
  const avg = mean(rain);
  const driest = new Set(
    rain.map((r, k) => [r, k]).filter(([r]) => r != null).sort((a, b) => a[0] - b[0]).slice(0, DROUGHT_COUNT).map(([, k]) => k),
  );
  const half = Math.floor(n / 2);
  const part = (arr, from, to) => mean(arr.slice(from, to));
  const rows = [
    ['rain', yr.precipitation], ['balance', yr.water_balance], ['heat', yr.heat_days_35], ['frost', yr.frost_days],
  ].map(([key, arr]) => ({ key, early: part(arr, 0, half), late: part(arr, n - half, n) }));
  const d = Object.fromEntries(rows.map((r) => [r.key, r.late - r.early]));
  const monthly = yr.precipitation_monthly[i];
  const climatology = features.climate?.monthly?.precipitation?.values;
  const fmt = (k, v) => `${whole(v)}`;

  return (
    <section className="panel" aria-labelledby="tm-h">
      <h3 id="tm-h">{t('ui.tm_title', { start: years[0], end: years[n - 1] })}</h3>
      <p className="muted">{t('ui.tm_intro')}</p>

      <div className="tm-controls">
        <button type="button" className="btn btn-quiet" onClick={() => { if (!playing && i >= n - 1) setI(0); setPlaying((p) => !p); }}>
          {playing ? t('ui.tm_pause') : t('ui.tm_play')}
        </button>
        <label className="tm-scrub">
          <span>{t('ui.tm_year')} <strong>{years[i]}</strong></span>
          <input
            type="range" min="0" max={n - 1} step="1" value={i}
            style={{ '--pct': `${(i / Math.max(n - 1, 1)) * 100}%` }}
            onChange={(e) => { setPlaying(false); setI(Number(e.target.value)); }}
          />
        </label>
      </div>

      <figure className="chart">
        <figcaption>{t('ui.tm_bar_rain')} <span className="muted">({t('ui.rain_unit').replace(/ .*$/, '')}/{lang === 'ar' ? 'سنة' : 'an'})</span></figcaption>
        <YearBars years={years} rain={rain} avg={avg} current={i} drought={driest} onPick={(k) => { setPlaying(false); setI(k); }} />
        <ul className="chart-key">
          <li><i className="sw ybar-sw" />{t('ui.tm_key_normal')}</li>
          <li><i className="sw ybar-dry-sw" />{t('ui.tm_key_dry', { n: DROUGHT_COUNT })}</li>
          <li><i className="sw ybar-now-sw" />{t('ui.tm_key_now')}</li>
          <li><i className="sw-dash" />{t('ui.tm_key_avg', { n: whole(avg) })}</li>
        </ul>
        <p>{t('ui.tm_drought_list', { years: [...driest].sort((a, b) => a - b).map((k) => years[k]).join(t('ui.list_sep')) })}</p>
      </figure>

      <div className="notice">
        <h4>{years[i]}</h4>
        <ul className="tm-stats">
          <Stat label={t('ui.tm_stat_rain')} value={`${whole(rain[i])} mm`} />
          <Stat label={t('ui.tm_stat_et0')} value={`${whole(yr.et0[i])} mm`} />
          <Stat label={t('ui.tm_stat_balance')} value={`${whole(yr.water_balance[i])} mm`} />
          <Stat label={t('ui.tm_stat_frost')} value={whole(yr.frost_days[i])} />
          <Stat label={t('ui.tm_stat_heat')} value={whole(yr.heat_days_35[i])} />
        </ul>
      </div>

      <figure className="chart">
        <figcaption>{t('ui.tm_month_title', { year: years[i] })} <span className="muted">({t('ui.rain_unit')})</span></figcaption>
        <MonthBars key={years[i]} values={monthly.map((v) => v ?? 0)} line={climatology} label={t('ui.tm_month_title', { year: years[i] })} />
        <ul className="chart-key">
          <li><i className="sw bar-water-sw" />{t('ui.tm_key_year', { year: years[i] })}</li>
          <li><i className="sw-line" />{t('ui.tm_key_avgyear')}</li>
        </ul>
      </figure>

      <div className="notice">
        <h4>{t('ui.tm_cmp_title', { a: years[n - half], b: years[n - 1], c: years[0], d: years[half - 1] })}</h4>
        <table className="cmp-table">
          <thead>
            <tr><th scope="col" /><th scope="col">{years[0]}–{years[half - 1]}</th><th scope="col">{years[n - half]}–{years[n - 1]}</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <th scope="row">{t(`ui.tm_row_${r.key}`)}</th>
                <td>{fmt(r.key, r.early)}</td>
                <td>{fmt(r.key, r.late)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul className="summary">
          {whole(d.rain) !== 0 && <li>{t(d.rain < 0 ? 'ui.tm_rain_less' : 'ui.tm_rain_more', { n: Math.abs(whole(d.rain)) })}</li>}
          {whole(d.heat) !== 0 && <li>{t(d.heat > 0 ? 'ui.tm_heat_more' : 'ui.tm_heat_less', { n: Math.abs(whole(d.heat)) })}</li>}
          {whole(d.frost) !== 0 && <li>{t(d.frost > 0 ? 'ui.tm_frost_more' : 'ui.tm_frost_less', { n: Math.abs(whole(d.frost)) })}</li>}
        </ul>
      </div>
    </section>
  );
}
