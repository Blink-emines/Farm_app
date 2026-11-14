import { useEffect, useRef, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { CROPS, MAX_SEASONS, NO_MONTHS, buildRequest } from '../constants.js';
import { ApiError, getStrategies } from '../api.js';
import { useTween, whole } from '../util.js';
import { YearDial } from './charts.jsx';
import { CropIcon } from './icons.jsx';

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

// Bars on a 12-month axis: sow month to harvest month (may wrap over December).
function Timeline({ seasons, result }) {
  const { t, crop, lang } = useI18n();
  const used = result?.seasons ?? [];
  return (
    <ol className="timeline" aria-label={t('ui.wi_timeline')}>
      {seasons.map((s, i) => {
        const u = used[i] ?? { sow_month: 1, harvest_month: 12 };
        const a = u.sow_month;
        const b = u.harvest_month;
        const segs = a <= b ? [[a, b]] : [[a, 12], [1, b]];
        return (
          <li key={i}>
            <span className="tl-name"><CropIcon id={s.crop_id} size={24} />{crop(s.crop_id)}</span>
            <span className="tl-axis">
              {segs.map(([x, y], k) => {
                const start = lang === 'ar' ? 12 - y : x - 1;
                return <i key={k} className={`tl-bar${s.crop_id === 'fallow' ? ' is-fallow' : ''}`} style={{ insetInlineStart: `${(start / 12) * 100}%`, inlineSize: `${((y - x + 1) / 12) * 100}%` }} />;
              })}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export default function WhatIf({ base, lat, lon, priorities, features }) {
  const { t, crop, month } = useI18n();
  const [seasons, setSeasons] = useState(base);
  const [state, setState] = useState({ phase: 'idle' });
  const [first, setFirst] = useState(null);
  const climate = features?.climate?.monthly;
  const timer = useRef(null);

  // Every change asks the real engine again, after the farmer stops for 400 ms.
  useEffect(() => {
    let stale = false;
    setState((s) => ({ ...s, phase: 'loading' }));
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        const data = await getStrategies(buildRequest({ lat, lon, seasons, priorities }));
        if (stale) return;
        const current = data.strategies.find((x) => x.is_current);
        setFirst((f) => f ?? current.score.total);
        setState({ phase: 'done', current });
      } catch (e) {
        if (!stale) setState({ phase: 'error', code: e instanceof ApiError ? e.code : 'internal_error' });
      }
    }, 400);
    return () => { stale = true; clearTimeout(timer.current); };
  }, [seasons, lat, lon, priorities]);

  const cur = state.current;
  const score = useTween(cur ? cur.score.total : null);
  const countMonths = (pred) => (cur ? cur.calendar.reduce((n, r) => n + r.months.filter(pred).length, 0) / cur.calendar.length : 0);
  const bare = countMonths((m) => m.status === 'bare');
  const dry = countMonths((m) => m.stress_reasons.some((r) => r.code === 'stress_water_deficit'));
  const dryTween = useTween(cur ? dry : null);
  const bareTween = useTween(cur ? bare : null);

  const set = (i, patch) => setSeasons(seasons.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const delta = cur && first != null ? whole(cur.score.total - first) : 0;

  return (
    <section className="panel" aria-labelledby="wi-h">
      <h3 id="wi-h">{t('ui.wi_title')}</h3>
      <p className="muted">{t('ui.wi_intro')}</p>

      <div className="wi-grid">
        <div className="stack">
          <Timeline seasons={seasons} result={cur} />
          {seasons.map((s, i) => (
            <fieldset key={i} className="wi-season">
              <legend>{t('ui.season_n', { n: i + 1 })}</legend>
              <div className="row">
                <label className="field">
                  <span>{t('ui.crop')}</span>
                  <select value={s.crop_id} onChange={(e) => set(i, { crop_id: e.target.value })}>
                    {CROPS.map((c) => <option key={c} value={c}>{crop(c)}</option>)}
                  </select>
                </label>
                {!NO_MONTHS.includes(s.crop_id) && ['sow_month', 'harvest_month'].map((key) => (
                  <label className="field" key={key}>
                    <span>{t(`ui.${key}`)}</span>
                    <select value={s[key]} onChange={(e) => set(i, { [key]: e.target.value })}>
                      <option value="">{t('ui.typical_months')}</option>
                      {MONTHS.map((m) => <option key={m} value={m}>{month(m)}</option>)}
                    </select>
                  </label>
                ))}
              </div>
              {seasons.length > 1 && (
                <button type="button" className="btn btn-text" onClick={() => setSeasons(seasons.filter((_, j) => j !== i))}>
                  {t('ui.remove_season', { n: i + 1 })}
                </button>
              )}
            </fieldset>
          ))}
          <div className="wi-actions">
            {seasons.length < MAX_SEASONS && (
              <button type="button" className="btn btn-quiet" onClick={() => setSeasons([...seasons, { crop_id: 'wheat', sow_month: '', harvest_month: '' }])}>
                {t('ui.add_season')}
              </button>
            )}
            <button type="button" className="btn btn-text" onClick={() => setSeasons(base)}>{t('ui.wi_reset')}</button>
          </div>
        </div>

        <div className="wi-result" aria-live="polite">
          {state.phase === 'error' && <p className="notice notice-error" role="alert">{t(`err.${state.code}`)}</p>}
          {cur && (
            <>
              <YearDial months={cur.calendar[0].months} climate={climate}>
                <span className="big-score">{Math.round(score ?? 0)}</span>
                <span className="of">{t('ui.out_of_100')}</span>
              </YearDial>
              <p className={`wi-status${state.phase === 'loading' ? ' is-busy' : ''}`}>{state.phase === 'loading' ? t('ui.wi_updating') : t('ui.wi_score')}</p>
              {delta !== 0 && <p className="muted">{t(delta > 0 ? 'ui.wi_more' : 'ui.wi_less', { n: Math.abs(delta) })}</p>}
              <ul className="wi-facts">
                <li><strong>{(Math.round(dryTween * 10) / 10)}</strong> {t('ui.wi_water')}</li>
                <li><strong>{(Math.round(bareTween * 10) / 10)}</strong> {t('ui.wi_bare')}</li>
              </ul>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
