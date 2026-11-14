import { useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { signed } from '../util.js';
import { DialKey, StatusKey, YearDial } from './charts.jsx';
import StrategyDetail from './StrategyDetail.jsx';
import ClimateDashboard from './ClimateDashboard.jsx';
import Compare from './Compare.jsx';
import SoilProfile from './SoilProfile.jsx';
import SimpleResult from './SimpleResult.jsx';
import { useSettings } from '../settings.jsx';
import TimeMachine from './TimeMachine.jsx';
import SpaceView from './SpaceView.jsx';
import WhatIf from './WhatIf.jsx';

// Strengths first: the rules that added the most points. Penalties stay in the details.
function strengths(why) {
  const good = why.filter((w) => w.points > 0).sort((a, b) => b.points - a.points);
  return (good.length ? good : [...why].sort((a, b) => Math.abs(b.points) - Math.abs(a.points))).slice(0, 3);
}

// The first risk that says something specific; the generic "ask an advisor" one is the fallback.
function keyRisk(risks) {
  return risks.find((r) => r.code !== 'risk_local_review') ?? risks[0];
}

function tagOf(t, s) {
  return s.is_current ? t('ui.yours') : s.rank === 1 ? t('ui.best') : t('ui.rank', { n: s.rank });
}

function Hero({ s, climate, onOpen }) {
  const { t, tm } = useI18n();
  const risk = keyRisk(s.risks_for_local_review);
  return (
    <section className="hero" aria-labelledby="hero-name">
      <div className="hero-text">
        <p className="tag">{tagOf(t, s)}</p>
        <h3 id="hero-name">{tm(s.name)}</h3>
        <p className="muted">{t('ui.confidence')} {t(`ui.confidence_${s.confidence}`)}</p>
        <h4>{t('ui.strengths')}</h4>
        <ul className="reasons">
          {strengths(s.why).map((w, i) => (
            <li key={i}>
              <span className={`pts pts-${w.effect}`}>{t('ui.points_for', { n: signed(w.points), goal: t(`ui.goal_${w.priority}`) })}</span>
              <span className="clamp">{tm(w.message)}</span>
            </li>
          ))}
        </ul>
        {risk && <p className="key-risk"><strong>{t('ui.main_risk')}</strong> <span className="clamp">{tm(risk)}</span></p>}
        <button type="button" className="btn btn-primary" onClick={onOpen}>{t('ui.see_details')}</button>
      </div>
      <div className="hero-art">
        <YearDial months={s.calendar[0].months} climate={climate}>
          <span className="big-score">{Math.round(s.score.total)}</span>
          <span className="of">{t('ui.out_of_100')}</span>
        </YearDial>
        <DialKey />
      </div>
    </section>
  );
}

function CompactCard({ s, onOpen }) {
  const { t, tm, month } = useI18n();
  return (
    <button type="button" className={`mini${s.is_current ? ' is-current' : ''}`} onClick={onOpen}>
      <span className="tag">{tagOf(t, s)}</span>
      <span className="mini-name">{tm(s.name)}</span>
      <span className="mini-score">{Math.round(s.score.total)}<small>{t('ui.out_of_100')}</small></span>
      <span className="mini-ribbon" aria-hidden="true">
        {s.calendar[0].months.map((m) => <i key={m.month} className={`cell-fill is-${m.status}`} title={month(m.month)} />)}
      </span>
      <span className="mini-more">{t('ui.see_details')}</span>
    </button>
  );
}

const TABS = ['simple', 'options', 'climate', 'history', 'space', 'soil', 'compare', 'whatif'];

export default function Results({ data, features, form, onPrint }) {
  const { t, tm } = useI18n();
  const [openId, setOpenId] = useState(null);
  const { advanced } = useSettings();
  const [tab, setTab] = useState('simple');
  const climate = features?.climate?.monthly;
  const fs = data.features_summary;
  const [best, ...others] = data.strategies;
  const open = data.strategies.find((s) => s.id === openId);
  const main = data.notes.filter((n) => ['note_relative_scores', 'note_local_expert'].includes(n.code));
  const rest = data.notes.filter((n) => !main.includes(n));

  if (!advanced) return <SimpleResult data={data} onPrint={onPrint} />;

  return (
    <div className="stack results">
      <ul className="notes">
        {main.map((n, i) => <li key={i}>{tm(n)}</li>)}
      </ul>

      <div className="tabs" role="tablist" aria-label={t('ui.tabs_label')}>
        {TABS.filter((id) => !(id === 'history' && !features?.yearly) && !(id === 'space' && !features?.vegetation)).map((id) => (
          <button key={id} type="button" role="tab" id={`tab-${id}`} aria-selected={tab === id} aria-controls="tab-panel" onClick={() => setTab(id)}>
            {t(`ui.tab_${id}`)}
          </button>
        ))}
        <button type="button" className="tab-print" onClick={onPrint}>{t('ui.print')}</button>
      </div>

      <div id="tab-panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="stack">
        {tab === 'simple' && <SimpleResult data={data} onPrint={onPrint} />}
        {tab === 'options' && (
          <>
            {fs.soil_status === 'fallback' && <p className="notice">{t('ui.soil_fallback')}</p>}
            <Hero s={best} climate={climate} onOpen={() => setOpenId(best.id)} />
            <div className="minis">
              {others.map((s) => <CompactCard key={s.id} s={s} onOpen={() => setOpenId(s.id)} />)}
            </div>
            <StatusKey />
            <p className="muted">
              {t('ui.climate_period', { start: fs.climate_period.start_year, end: fs.climate_period.end_year })}
            </p>
            {rest.length > 0 && (
              <details className="block">
                <summary>{t('ui.other_notes')}</summary>
                <ul>{rest.map((n, i) => <li key={i}>{tm(n)}</li>)}</ul>
              </details>
            )}
          </>
        )}
        {tab === 'climate' && <ClimateDashboard features={features} />}
        {tab === 'history' && <TimeMachine features={features} />}
        {tab === 'space' && <SpaceView features={features} strategies={data.strategies} />}
        {tab === 'soil' && <SoilProfile features={features} />}
        {tab === 'compare' && <Compare strategies={data.strategies} />}
        {tab === 'whatif' && <WhatIf base={form.seasons} lat={form.lat} lon={form.lon} priorities={form.priorities} features={features} />}
      </div>

      {open && <StrategyDetail strategy={open} climate={climate} onClose={() => setOpenId(null)} />}
    </div>
  );
}
