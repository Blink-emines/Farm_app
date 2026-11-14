import { useEffect, useRef } from 'react';
import { useI18n } from '../i18n/index.jsx';
import Calendar from './Calendar.jsx';
import { signed } from '../util.js';

function Fold({ title, children }) {
  return (
    <details className="block">
      <summary>{title}</summary>
      {children}
    </details>
  );
}

function Items({ list }) {
  const { t, tm } = useI18n();
  return list.length ? <ul>{list.map((m, i) => <li key={i}>{tm(m)}</li>)}</ul> : <p className="muted">{t('ui.none')}</p>;
}

// The expanded view: opens over the results, closes with the button or Escape.
export default function StrategyDetail({ strategy: s, climate, onClose }) {
  const { t, tm, feature, value, unit } = useI18n();
  const closeRef = useRef(null);
  const fmt = (v) => (Array.isArray(v) ? v.map((x) => (x == null ? '–' : x)).join(', ') : String(value(v) ?? '–'));

  useEffect(() => {
    const previous = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
      previous?.focus?.();
    };
  }, [onClose]);

  return (
    <div className="sheet-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={tm(s.name)}>
        <header className="sheet-head">
          <div>
            <p className="tag">{s.is_current ? t('ui.yours') : s.rank === 1 ? t('ui.best') : t('ui.rank', { n: s.rank })}</p>
            <h3>{tm(s.name)}</h3>
            <p className="score-line">
              {t('ui.score', { n: Math.round(s.score.total) })} &nbsp;{t('ui.confidence')} {t(`ui.confidence_${s.confidence}`)}
            </p>
          </div>
          <button ref={closeRef} type="button" className="btn btn-quiet close" onClick={onClose}>{t('ui.close')}</button>
        </header>

        <div className="sheet-body">
          <p className="notice expert">{t('ui.talk_expert')}</p>

          <section className="block">
            <h4>{t('ui.why')}</h4>
            <ul className="why">
              {s.why.map((w, i) => (
                <li key={i}>
                  <span className={`pts pts-${w.effect}`}>
                    {t('ui.points_for', { n: signed(w.points), goal: t(`ui.goal_${w.priority}`) })}
                  </span>
                  <span>{tm(w.message)}</span>
                </li>
              ))}
            </ul>
          </section>

          <section className="block">
            <h4>{t('ui.risks')}</h4>
            <Items list={s.risks_for_local_review} />
          </section>

          <section className="block">
            <h4>{t('ui.calendar')}</h4>
            <Calendar calendar={s.calendar} seasons={s.seasons} climate={climate} />
          </section>

          <Fold title={t('ui.benefits')}><Items list={s.benefits} /></Fold>
          <Fold title={t('ui.gaps')}><Items list={s.information_gaps} /></Fold>
          <Fold title={t('ui.evidence')}>
            <ul>
              {s.evidence.map((e, i) => (
                <li key={i}>
                  {feature(e.feature)} : <bdi dir="ltr">{fmt(e.value)} {unit(e.unit)}</bdi>
                  <span className="muted"> ({e.source})</span>
                </li>
              ))}
            </ul>
          </Fold>
        </div>
      </div>
    </div>
  );
}
