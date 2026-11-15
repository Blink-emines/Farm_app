import { useEffect, useRef, useState } from 'react';
import { MapContainer, useMap } from 'react-leaflet';
import { LANGS, useI18n } from '../i18n/index.jsx';
import { DEFAULT_POINT, buildRequest } from '../constants.js';
import { getFeatures, getStrategies, optimize } from '../api.js';
import { monthsPerYear, sum, useTween, whole } from '../util.js';
import { SatelliteTiles } from './tiles.jsx';
import { MonthBars } from './charts.jsx';
import { Ribbon } from './Calendar.jsx';
import { BrandMark } from './icons.jsx';

const START = [34.1, -5.0];
const TARGET = [DEFAULT_POINT.lat, DEFAULT_POINT.lon];
const SECTIONS = ['hero', 'problem', 'how', 'impact', 'features', 'cta'];
const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// The camera starts wide and glides down onto the default point.
function Glide() {
  const map = useMap();
  useEffect(() => {
    if (reduced()) { map.setView(TARGET, 12, { animate: false }); return undefined; }
    const id = setTimeout(() => map.flyTo(TARGET, 12, { duration: 7 }), 500);
    return () => clearTimeout(id);
  }, [map]);
  return null;
}

// True once the element has been on screen (stays true).
function useSeen(ref, threshold = 0.25) {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || seen) return undefined;
    if (reduced() || !('IntersectionObserver' in window)) { setSeen(true); return undefined; }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect(); } }, { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [ref, seen, threshold]);
  return seen;
}

function Reveal({ children, delay = 0, className = '', as: Tag = 'div' }) {
  const ref = useRef(null);
  const seen = useSeen(ref, 0.15);
  return <Tag ref={ref} className={`reveal${seen ? ' in' : ''} ${className}`} style={{ transitionDelay: `${delay}ms` }}>{children}</Tag>;
}

function Counter({ value, go, decimals = 0 }) {
  const v = useTween(go ? value : 0, 1400);
  return <>{decimals ? (Math.round((v ?? 0) * 10) / 10).toFixed(1) : Math.round(v ?? 0)}</>;
}

const avgMonths = (s, pred) => s.calendar.reduce((n, r) => n + r.months.filter(pred).length, 0) / s.calendar.length;
const dec = (n) => (Number.isInteger(n) ? 0 : 1);

// Asks the real endpoint; on failure tries once more, then reports the error so the card can say so.
function useRemote(load) {
  const [state, setState] = useState({ status: 'loading' });
  const [round, setRound] = useState(0);
  useEffect(() => {
    let stale = false;
    setState({ status: 'loading' });
    const attempt = (left) => load().then(
      (data) => { if (!stale) setState({ status: 'ok', data }); },
      () => { if (stale) return; if (left > 0) setTimeout(() => attempt(left - 1), 800); else setState({ status: 'error' }); },
    );
    attempt(1);
    return () => { stale = true; };
  }, [round]); // eslint-disable-line react-hooks/exhaustive-deps
  return [state, () => setRound((r) => r + 1)];
}

const DEFAULT_REQUEST = buildRequest({
  lat: DEFAULT_POINT.lat,
  lon: DEFAULT_POINT.lon,
  seasons: [{ crop_id: 'wheat' }, { crop_id: 'fallow' }],
  priorities: { save_water: 3, improve_soil: 3, extra_income: 3, reduce_erosion: 3, forage: 3 },
});
// Two sample parcels, balanced profile: the same run a farmer would do on the Optimiser screen.
const SAMPLE_FARM = {
  latitude: DEFAULT_POINT.lat,
  longitude: DEFAULT_POINT.lon,
  parcels: [
    { id: 'A', area_ha: 2, irrigated: false, current_rotation: { seasons: [{ crop_id: 'wheat' }, { crop_id: 'fallow' }] } },
    { id: 'B', area_ha: 3, irrigated: true, current_rotation: { seasons: [{ crop_id: 'barley' }] } },
  ],
  profile: 'balanced',
  pareto_points: 0,
};

// Every number on this page comes from the real endpoints for the default point.
function useFacts() {
  const [features, reloadF] = useRemote(() => getFeatures(DEFAULT_POINT.lat, DEFAULT_POINT.lon));
  const [strategies, reloadS] = useRemote(() => getStrategies(DEFAULT_REQUEST));
  const [farm, reloadO] = useRemote(() => optimize(SAMPLE_FARM));
  return { features, strategies, farm, reloadF, reloadS, reloadO };
}

function impactMetrics(r) {
  const area = sum(r.parcels.map((p) => p.area_ha));
  const bare = (key) => sum(r.parcels.map((p) => p.area_ha * monthsPerYear(p[key], 'bare'))) / area;
  const repeats = (key) => sum(r.parcels.map((p) => p[key].why.filter((w) => w.message.code === 'family_repeat').length));
  const range = r.totals.revenue_range_mad_per_year;
  return [
    { key: 'bare', before: bare('baseline'), after: bare('plan'), lowerIsBetter: true },
    { key: 'revenue', before: r.totals.baseline_gross_revenue_mad_per_year / 1000, after: r.totals.gross_revenue_mad_per_year / 1000, lowerIsBetter: false, range: [range.bad_year, range.good_year] },
    { key: 'rules', before: repeats('baseline'), after: repeats('plan'), lowerIsBetter: true },
  ];
}

// One stat card: a skeleton while loading, the number when ready, a message and retry on error. Never empty.
function Stat({ state, reload, children, className = 'fact', delay = 0 }) {
  const { t } = useI18n();
  if (state.status === 'loading') return <div className={`${className} skeleton`} role="status" aria-label={t('ui.loading')}><i /><i /><i /></div>;
  if (state.status === 'error') {
    return (
      <div className={className}>
        <p>{t('ui.l_stat_error')}</p>
        <button type="button" className="btn btn-quiet" onClick={reload}>{t('ui.retry')}</button>
      </div>
    );
  }
  return <Reveal className={className} delay={delay}>{children}</Reveal>;
}

function Section({ id, className = '', children, label }) {
  return <section id={`s-${id}`} data-section={id} className={`s ${className}`} aria-label={label}>{children}</section>;
}

function Problem({ facts }) {
  const { t } = useI18n();
  const ref = useRef(null);
  const seen = useSeen(ref, 0.3);
  const { features, strategies } = facts;
  const m = features.status === 'ok' ? features.data.climate.monthly : null;
  const heat = m?.heat_days['35'].values;
  const hottest = heat ? heat.indexOf(Math.max(...heat)) : 0;
  const current = strategies.status === 'ok' ? strategies.data.strategies.find((x) => x.is_current) : null;
  const bare = current ? monthsPerYear(current, 'bare') : 0;
  return (
    <div ref={ref} className="wrap">
      <Reveal as="h2">{t('ui.problem_title')}</Reveal>
      <Reveal as="p" className="lead" delay={80}>{t('ui.l_problem_lead')}</Reveal>
      <div className="problem-grid">
        <Stat state={strategies} reload={facts.reloadS} delay={120}>
          <strong className="num"><Counter value={bare} go={seen} decimals={dec(bare)} /></strong>
          <span>{t('ui.fact_bare')}</span>
          {current && <Ribbon months={current.calendar[0].months} />}
        </Stat>
        <Stat state={features} reload={facts.reloadF} delay={240}>
          <strong className="num"><Counter value={m ? m.precipitation.values.filter((r, i) => r < m.et0.values[i]).length : 0} go={seen} /></strong>
          <span>{t('ui.fact_dry')}</span>
          {m && <MonthBars values={m.precipitation.values} line={m.et0.values} label={t('ui.rain_title')} />}
        </Stat>
        <Stat state={features} reload={facts.reloadF} delay={360}>
          <strong className="num"><Counter value={heat ? Math.round(heat[hottest]) : 0} go={seen} /></strong>
          <span>{t('ui.fact_heat', { month: hottest + 1 })}</span>
          {heat && <MonthBars values={heat} barClass="bar-heat" label={t('ui.chart_heat', { t: 35 })} />}
        </Stat>
      </div>
      <Reveal as="p" className="source" delay={400}>{t('ui.problem_source', { lat: DEFAULT_POINT.lat, lon: DEFAULT_POINT.lon })}</Reveal>
    </div>
  );
}

function SatelliteIcon() {
  return (
    <svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <rect x="24" y="24" width="16" height="16" rx="3" transform="rotate(45 32 32)" fill="var(--primary-soft)" />
      <path d="M14 30L6 22l8-8 8 8M50 34l8 8-8 8-8-8M26 38l-10 10M38 26l10-10" />
      <path d="M44 8a14 14 0 0 1 12 12M44 16a6 6 0 0 1 4 4" />
    </svg>
  );
}
function AnalysisIcon() {
  return (
    <svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <rect x="8" y="10" width="48" height="44" rx="8" fill="var(--primary-soft)" />
      <path d="M16 44l10-12 8 6 14-18" />
      <circle cx="26" cy="32" r="2.5" fill="currentColor" /><circle cx="34" cy="38" r="2.5" fill="currentColor" /><circle cx="48" cy="20" r="2.5" fill="currentColor" />
    </svg>
  );
}

function How() {
  const { t } = useI18n();
  const ref = useRef(null);
  const seen = useSeen(ref, 0.3);
  const steps = [
    { icon: <SatelliteIcon />, k: 1 },
    { icon: <AnalysisIcon />, k: 2 },
    { icon: <BrandMark size={64} />, k: 3 },
  ];
  return (
    <div ref={ref} className={`wrap flow${seen ? ' go' : ''}`}>
      <Reveal as="h2">{t('ui.l_how_title')}</Reveal>
      <ol className="flow-steps">
        {steps.map((s, i) => (
          <li key={s.k} style={{ '--i': i }}>
            <span className="flow-icon">{s.icon}</span>
            <h3>{t(`ui.l_how_${s.k}`)}</h3>
            <p>{t(`ui.l_how_${s.k}_text`)}</p>
            {i < steps.length - 1 && <span className="flow-link" aria-hidden="true"><i /><i /><i /></span>}
          </li>
        ))}
      </ol>
    </div>
  );
}

function Impact({ facts }) {
  const { t, num } = useI18n();
  const ref = useRef(null);
  const seen = useSeen(ref, 0.3);
  const { farm, features } = facts;
  const metrics = farm.status === 'ok' ? impactMetrics(farm.data) : [null, null, null];
  const period = features.status === 'ok' ? features.data.climate.period : null;
  const better = (m) => (m.lowerIsBetter ? m.after < m.before : m.after > m.before);
  return (
    <div ref={ref} className="wrap">
      <Reveal as="h2">{t('ui.l_impact_title')}</Reveal>
      <Reveal as="p" className="lead" delay={80}>{t('ui.l_impact_lead')}</Reveal>
      <div className="impact-grid">
        {['bare', 'revenue', 'rules'].map((key, i) => {
          const m = metrics[i];
          return (
            <Stat key={key} state={farm} reload={facts.reloadO} className="impact-card" delay={140 + i * 120}>
              {m && (
                <>
                  <h3>{t(`ui.l_m_${m.key}`)}</h3>
                  <p className="ba" dir="ltr">
                    <span className="was"><small>{t('ui.l_before')}</small><b><Counter value={m.before} go={seen} decimals={m.key === 'bare' ? dec(m.before) : 0} /></b></span>
                    <span className="arrow" aria-hidden="true">→</span>
                    <span className={`now${better(m) ? ' good' : ''}`}><small>{t('ui.l_after')}</small><b><Counter value={m.after} go={seen} decimals={m.key === 'bare' ? dec(m.after) : 0} /></b></span>
                  </p>
                  {m.range && <p className="range">{t('ui.opt_range', { bad: num(m.range[0]), good: num(m.range[1]) })} {t('ui.opt_mad')}</p>}
                  <p className="source">{period ? t('ui.l_impact_source', { start: period.start_year, end: period.end_year }) : t('ui.l_impact_source_plain')}</p>
                </>
              )}
            </Stat>
          );
        })}
      </div>
      <Reveal as="p" className="source" delay={500}>{t('ui.l_impact_caveat')}</Reveal>
    </div>
  );
}

const FEATURES = [
  { k: 'dial', art: (
    <svg viewBox="0 0 64 64" aria-hidden="true">{Array.from({ length: 12 }, (_, i) => (
      <path key={i} d="M-4,-28 A28,28 0 0 1 4,-28 L3,-18 A18,18 0 0 0 -3,-18Z" transform={`translate(32 32) rotate(${i * 30})`} fill={[2, 3, 4].includes(i) ? 'var(--clay)' : i > 4 && i < 10 ? 'var(--sand)' : 'var(--leaf)'} />
    ))}</svg>
  ) },
  { k: 'time', art: (
    <svg viewBox="0 0 64 64" aria-hidden="true">{[34, 28, 14, 30, 38, 22, 12, 32].map((h, i) => (
      <rect key={i} x={5 + i * 7} y={52 - h} width="5" height={h} rx="1.5" fill={h < 20 ? 'var(--clay)' : 'var(--water)'} />
    ))}</svg>
  ) },
  { k: 'space', art: (
    <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="4" y="10" width="56" height="44" rx="8" fill="var(--sand)" opacity=".7" /><path d="M6 46C16 20 24 20 32 32S48 44 58 18" fill="none" stroke="var(--primary-dark)" strokeWidth="4" strokeLinecap="round" /></svg>
  ) },
  { k: 'whatif', art: (
    <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="6" y="14" width="34" height="10" rx="5" fill="var(--leaf)" /><rect x="22" y="30" width="36" height="10" rx="5" fill="var(--sand)" /><rect x="10" y="46" width="28" height="10" rx="5" fill="var(--gold)" /></svg>
  ) },
  { k: 'opt', art: (
    <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="6" y="8" width="24" height="22" rx="5" fill="var(--leaf)" /><rect x="34" y="8" width="24" height="22" rx="5" fill="var(--gold)" /><rect x="6" y="34" width="24" height="22" rx="5" fill="var(--water)" /><rect x="34" y="34" width="24" height="22" rx="5" fill="var(--clay)" /></svg>
  ) },
];

function Features() {
  const { t } = useI18n();
  return (
    <div className="wrap">
      <Reveal as="h2">{t('ui.l_feat_title')}</Reveal>
      <ul className="feat-grid">
        {FEATURES.map((f, i) => (
          <Reveal as="li" key={f.k} className="feat" delay={80 + i * 90}>
            <span className="feat-art">{f.art}</span>
            <h3>{t(`ui.l_feat_${f.k}`)}</h3>
            <p>{t(`ui.l_feat_${f.k}_text`)}</p>
          </Reveal>
        ))}
      </ul>
    </div>
  );
}


const WORD = 'SENIME'.split('');

// SENIME is EMINES spelled backwards: each letter glides to its mirrored slot.
// Only transforms move (FLIP). Plays when scrolled into view, and again on hover or tap.
function TeamBand() {
  const { t } = useI18n();
  const band = useRef(null);
  const letters = useRef([]);
  const seen = useSeen(band, 0.5);
  const [done, setDone] = useState(false);

  const play = () => {
    const els = letters.current.filter(Boolean);
    if (!els.length) return;
    const cell = els[0].getBoundingClientRect().width;
    els.forEach((el) => el.getAnimations().forEach((a) => a.cancel()));
    const finalX = (i) => (WORD.length - 1 - 2 * i) * cell;
    if (reduced()) {
      els.forEach((el, i) => { el.style.transform = `translateX(${finalX(i)}px)`; });
      setDone(true);
      return;
    }
    setDone(false);
    let finished = 0;
    els.forEach((el, i) => {
      const dx = finalX(i);
      const lift = (i < WORD.length / 2 ? -1 : 1) * 36;
      const anim = el.animate(
        [
          { transform: 'translate(0, 0)' },
          { transform: `translate(${dx / 2}px, ${lift}px)`, offset: 0.5 },
          { transform: `translate(${dx}px, 0)` },
        ],
        { duration: 1000, delay: i * 110, easing: 'cubic-bezier(.45,.05,.25,1)', fill: 'forwards' },
      );
      anim.onfinish = () => { finished += 1; if (finished === els.length) setDone(true); };
    });
  };

  useEffect(() => { if (seen) play(); }, [seen]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div ref={band} className="team-inner" aria-label={t('ui.l_team_label')} role="group">
      <div className="team-stack">
        <p className="team-label">{t('ui.l_team_label')}</p>
        <button type="button" className="team-word" onPointerEnter={play} onClick={play} aria-label="SENIME, EMINES">
          <bdi dir="ltr">
            {WORD.map((ch, i) => (
              <span key={i} ref={(el) => { letters.current[i] = el; }} className={`tl${i % 2 ? ' alt' : ''}`} aria-hidden="true">{ch}</span>
            ))}
          </bdi>
        </button>
        <p className={`team-school${done ? ' in' : ''}`}><bdi dir="ltr">EMINES – UM6P</bdi></p>
      </div>
    </div>
  );
}

function Footer() {
  const { t, lang, setLang } = useI18n();
  return (
    <footer className="land-foot">
      <div className="wrap foot-grid">
        <div className="foot-brand">
          <span className="brand"><BrandMark size={32} />{t('ui.brand')}</span>
          <p>{t('ui.l_foot_line')}</p>
          <p className="foot-challenge">{t('ui.l_foot_challenge')}</p>
          <div className="lang" role="group" aria-label={t('ui.language')}>
            {LANGS.map((l) => (
              <button key={l.id} type="button" lang={l.id} aria-pressed={lang === l.id} onClick={() => setLang(l.id)}>{l.label}</button>
            ))}
          </div>
        </div>
        <div>
          <h4>{t('ui.l_foot_sources')}</h4>
          <ul>
            {['nasa', 'modis', 'soil', 'fao', 'maps'].map((k) => <li key={k}>{t(`ui.l_src_${k}`)}</li>)}
          </ul>
        </div>
        <div>
          <h4>{t('ui.l_foot_team_title')}</h4>
          <p>{t('ui.l_foot_team')}</p>
          <p className="foot-note">{t('ui.talk_expert')}</p>
          <p className="foot-note">{t('ui.relative_scores')}</p>
        </div>
      </div>
    </footer>
  );
}

const Play = () => <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3l12 7-12 7z" fill="currentColor" /></svg>;
const Pause = () => <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3h4v14H5zM11 3h4v14h-4z" fill="currentColor" /></svg>;

export default function Landing({ head, onStart }) {
  const { t } = useI18n();
  const facts = useFacts();
  const [active, setActive] = useState('hero');
  const [touring, setTouring] = useState(false);
  const canTour = typeof window !== 'undefined' && !reduced();

  // Which section is on screen, from the scroll position (sections taller than the screen still count).
  const currentIndex = () => {
    const y = window.innerHeight * 0.4;
    let cur = 0;
    SECTIONS.forEach((id, i) => {
      const el = document.getElementById(`s-${id}`);
      if (el && el.getBoundingClientRect().top <= y) cur = i;
    });
    return cur;
  };
  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setActive(SECTIONS[currentIndex()]));
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('scroll', onScroll); window.removeEventListener('resize', onScroll); };
  }, []);

  const go = (id) => document.getElementById(`s-${id}`)?.scrollIntoView({ behavior: reduced() ? 'auto' : 'smooth', block: 'start' });

  // Guided tour: moves to the next section at once, then every few seconds. Any wheel, touch, key
  // or click outside the tour button stops it. It also stops at the last section.
  useEffect(() => {
    if (!touring) return undefined;
    const stop = (e) => {
      if (e.target.closest?.('.tour-btn')) return;
      if (e.type === 'wheel' && e.deltaY === 0) return;
      setTouring(false);
    };
    const events = ['wheel', 'touchstart', 'keydown', 'pointerdown'];
    events.forEach((ev) => window.addEventListener(ev, stop, { passive: true }));
    const step = () => {
      const next = currentIndex() + 1;
      if (next >= SECTIONS.length) { setTouring(false); return; }
      go(SECTIONS[next]);
    };
    step();
    const id = setInterval(step, 2500);
    return () => { clearInterval(id); events.forEach((ev) => window.removeEventListener(ev, stop)); };
  }, [touring]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="story">
      <Section id="hero" className="hero-s" label={t('ui.l_nav_hero')}>
        <div className="landing-map" aria-hidden="true">
          <MapContainer center={START} zoom={9} zoomControl={false} dragging={false} scrollWheelZoom={false} doubleClickZoom={false} touchZoom={false} keyboard={false} style={{ height: '100%', width: '100%' }}>
            <SatelliteTiles />
            <Glide />
          </MapContainer>
        </div>
        <div className="hero-wash" />
        {head}
        <div className="hero-copy">
          <p className="kicker">{t('ui.l_hero_kicker')}</p>
          <h1>{t('ui.title')}</h1>
          <p className="lead">{t('ui.l_hero_sub')}</p>
          <div className="hero-actions">
            <button type="button" className="btn btn-primary" onClick={onStart}>{t('ui.analyse')}</button>
            <button type="button" className="btn btn-quiet" onClick={() => go('problem')}>{t('ui.l_scroll')}</button>
          </div>
        </div>
      </Section>

      <Section id="problem" className="s-soft" label={t('ui.l_nav_problem')}><Problem facts={facts} /></Section>
      <Section id="how" label={t('ui.l_nav_how')}><How /></Section>
      <Section id="impact" className="s-soft" label={t('ui.l_nav_impact')}><Impact facts={facts} /></Section>
      <Section id="features" label={t('ui.l_nav_features')}><Features /></Section>
      <Section id="cta" className="s-cta" label={t('ui.l_nav_cta')}>
        <div className="wrap cta-grid">
          <div className="cta-copy">
            <Reveal as="h2">{t('ui.l_cta_title')}</Reveal>
            <Reveal as="p" className="lead" delay={80}>{t('ui.l_cta_sub')}</Reveal>
            <Reveal delay={160}><button type="button" className="btn btn-primary btn-big" onClick={onStart}>{t('ui.analyse')}</button></Reveal>
          </div>
          <TeamBand />
        </div>
      </Section>
      <Footer />

      <nav className="dots" aria-label={t('ui.l_nav_label')}>
        {SECTIONS.map((id) => (
          <button key={id} type="button" aria-label={t(`ui.l_nav_${id}`)} aria-current={active === id ? 'true' : undefined} onClick={() => { setTouring(false); go(id); }}>
            <i />
          </button>
        ))}
      </nav>
      {canTour && (
        <button type="button" className="tour-btn" aria-pressed={touring} onClick={() => setTouring((v) => !v)}>
          {touring ? <Pause /> : <Play />}
          {touring ? t('ui.tour_pause') : t('ui.tour')}
        </button>
      )}
    </div>
  );
}
