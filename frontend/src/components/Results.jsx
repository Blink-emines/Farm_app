import { useState } from 'react';
import { createPortal } from 'react-dom';
import PrintReport from './PrintReport.jsx';
import { useI18n } from '../i18n/index.jsx';
import { signed } from '../util.js';
import { DialKey, StatusKey, YearDial } from './charts.jsx';
import StrategyDetail from './StrategyDetail.jsx';
import ClimateDashboard from './ClimateDashboard.jsx';
import SoilProfile from './SoilProfile.jsx';
import MyPlan from './MyPlan.jsx';
import Listen from './Listen.jsx';
import { describeOption } from '../planText.js';
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

// Compare: one card per option with the same rows (return, water, soil, risk months), then one plain
// sentence on how it differs from the current rotation. Yields are FAOSTAT national ranges or nothing.
function CompareCards({ strategies, selected, onPick }) {
  const i18n = useI18n();
  const { t } = i18n;
  const cur = strategies.find((s) => s.is_current);

  return (
    <div className="stack">
      <p className="help">{t('ui.cmp_help')}</p>
      <div className="cmp-cards">
        {strategies.map((s) => {
          const { title, ret, rel, water, soil, risk, diff } = describeOption(s, cur, i18n);
          const spoken = [title, t('ui.cmp_row_return'), ...ret, rel, t('ui.cmp_row_water'), water, t('ui.cmp_row_soil'), soil, t('ui.cmp_row_risk'), risk, diff].filter(Boolean).join('. ');
          return (
            <article key={s.id} className={`cmp-card${s.id === selected ? ' is-selected' : ''}`}>
              <header className="cmp-head">
                <span className="tag">{tagOf(t, s)}</span>
                <h3>{title}</h3>
              </header>
              <dl className="cmp-rows">
                <dt>{t('ui.cmp_row_return')}</dt>
                <dd>{ret.map((r, i) => <span key={i} className="cmp-line">{r}</span>)}{rel && <span className="cmp-line cmp-rel">{rel}</span>}</dd>
                <dt>{t('ui.cmp_row_water')}</dt>
                <dd>{water}</dd>
                <dt>{t('ui.cmp_row_soil')}</dt>
                <dd>{soil}</dd>
                <dt>{t('ui.cmp_row_risk')}</dt>
                <dd>{risk}</dd>
              </dl>
              <p className="cmp-diff">{diff}</p>
              <div className="cmp-actions">
                <button type="button" className="btn btn-quiet" onClick={() => onPick(s.id)}>{t('ui.cmp_show')}</button>
                <Listen compact clips={[]} text={spoken} />
              </div>
            </article>
          );
        })}
      </div>
      <p className="muted">{t('ui.cmp_yield_note')}</p>
    </div>
  );
}

const TABS = ['plan', 'compare', 'details'];
const DETAILS = ['options', 'climate', 'history', 'space', 'soil', 'whatif'];

export default function Results({ data, features, form, soil, onPrint }) {
  const { t, tm } = useI18n();
  const [openId, setOpenId] = useState(null);
  const [tab, setTab] = useState('plan');
  const [sub, setSub] = useState('options');
  const [selId, setSelId] = useState(data.strategies[0].id);
  const selected = data.strategies.find((s) => s.id === selId) ?? data.strategies[0];
  const climate = features?.climate?.monthly;
  const fs = data.features_summary;
  const [best, ...others] = data.strategies;
  const open = data.strategies.find((s) => s.id === openId);
  const main = data.notes.filter((n) => ['note_relative_scores', 'note_local_expert'].includes(n.code));
  const rest = data.notes.filter((n) => !main.includes(n));

  return (
    <div className="stack results">
      <ul className="notes">
        {main.map((n, i) => <li key={i}>{tm(n)}</li>)}
      </ul>

      <div className="tabs" role="tablist" aria-label={t('ui.tabs_label')}>
        {TABS.map((id) => (
          <button key={id} type="button" role="tab" id={`tab-${id}`} aria-selected={tab === id} aria-controls="tab-panel" onClick={() => setTab(id)}>
            {t(`ui.tab_${id}`)}
          </button>
        ))}
      </div>

      <div id="tab-panel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="stack">
        {tab === 'plan' && <MyPlan strategy={selected} features={features} soil={soil} onCompare={() => setTab('compare')} onPrint={onPrint} />}
        {tab === 'compare' && (
          <CompareCards strategies={data.strategies} selected={selected.id} onPick={(id) => { setSelId(id); setTab('plan'); window.scrollTo({ top: 0 }); }} />
        )}
        {tab === 'details' && (
          <>
            <p className="help">{t('ui.details_help')}</p>
            <div className="chip-row" role="tablist" aria-label={t('ui.tab_details')}>
              {DETAILS.filter((id) => !(id === 'history' && !features?.yearly) && !(id === 'space' && !features?.vegetation)).map((id) => (
                <button key={id} type="button" role="tab" className="chip" aria-selected={sub === id} onClick={() => setSub(id)}>{t(`ui.tab_${id}`)}</button>
              ))}
            </div>
            {sub === 'options' && (
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
            {sub === 'climate' && <ClimateDashboard features={features} />}
            {sub === 'history' && <TimeMachine features={features} />}
            {sub === 'space' && <SpaceView features={features} strategies={data.strategies} />}
            {sub === 'soil' && <SoilProfile features={features} />}
            {sub === 'whatif' && <WhatIf base={form.seasons} lat={form.lat} lon={form.lon} priorities={form.priorities} features={features} />}
          </>
        )}
      </div>

      {createPortal(<div className="print-only"><PrintReport data={data} strategy={selected} features={features} soil={soil} /></div>, document.body)}
      {open && <StrategyDetail strategy={open} climate={climate} onClose={() => setOpenId(null)} />}
    </div>
  );
}
