import { Fragment, useEffect, useRef, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { CropIcon } from './icons.jsx';
import FieldLife, { flatMonths, soilEnd } from './FieldLife.jsx';

// Plain-words view for farmers: one recommendation, the life of the field in one picture,
// three verdicts, and a button that reads it aloud.
const Check = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M7.5 12.5l3 3 6-6.5" /></svg>
);
const Warn = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18.2v.1" /></svg>
);
const Cross = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M8.5 8.5l7 7M15.5 8.5l-7 7" /></svg>
);
const TONE_ICON = { good: Check, caution: Warn, risk: Cross };
const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const isWater = (r) => r.code === 'risk_water_stress_months';

export function keyRisk(risks) {
  return risks.find((r) => r.code !== 'risk_local_review') ?? risks[0];
}

// Three verdicts from the engine's own facts (calendar, soil_steps, family rule), not from scores.
export function verdicts(s) {
  const years = s.calendar.length || 1;
  const dryPerYear = flatMonths(s).filter((m) => m.stress_reasons.some((r) => r.code === 'stress_water_deficit')).length / years;
  const soil = soilEnd(s);
  const fam = s.why.filter((w) => w.rule_id === 'family_break').map((w) => w.message.code);
  return [
    { id: 'water', tone: dryPerYear === 0 ? 'good' : dryPerYear <= 2 ? 'caution' : 'risk', key: dryPerYear === 0 ? 'v_water_good' : dryPerYear <= 2 ? 'v_water_some' : 'v_water_dry' },
    { id: 'soil', tone: soil > 0.5 ? 'good' : soil < -0.5 ? 'risk' : 'caution', key: soil > 0.5 ? 'v_soil_up' : soil < -0.5 ? 'v_soil_down' : 'v_soil_flat' },
    { id: 'pests', tone: fam.includes('family_repeat') ? 'risk' : fam.includes('family_change') ? 'good' : 'caution', key: fam.includes('family_repeat') ? 'v_pests_repeat' : fam.includes('family_change') ? 'v_pests_break' : 'v_pests_unknown' },
  ];
}

const VOICE_LANGS = { ar: ['ar-MA', 'ar'], fr: ['fr-FR', 'fr'], en: ['en-US', 'en-GB', 'en'] };

// Reads the plan aloud with the browser's own voices. Hidden when no voice speaks this language.
function Listen({ text }) {
  const { t, lang } = useI18n();
  const [voice, setVoice] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => {
    const synth = window.speechSynthesis;
    if (!synth) return undefined;
    const pick = () => {
      const voices = synth.getVoices();
      const found = VOICE_LANGS[lang].map((code) => voices.find((v) => v.lang.toLowerCase().startsWith(code.toLowerCase()))).find(Boolean);
      setVoice(found ?? null);
    };
    pick();
    synth.addEventListener?.('voiceschanged', pick);
    return () => { synth.removeEventListener?.('voiceschanged', pick); synth.cancel(); };
  }, [lang]);
  if (!voice) return null;
  const toggle = () => {
    const synth = window.speechSynthesis;
    if (speaking) { synth.cancel(); setSpeaking(false); return; }
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voice;
    u.lang = voice.lang;
    u.rate = 0.9;
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    synth.cancel();
    synth.speak(u);
    setSpeaking(true);
  };
  return (
    <button type="button" className="btn btn-quiet listen-btn" aria-pressed={speaking} onClick={toggle}>
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 9v6h4l5 4V5L8 9z" /><path d="M16.5 8.5a5 5 0 010 7M19 6a8.5 8.5 0 010 12" /></svg>
      {speaking ? t('ui.listen_stop') : t('ui.listen')}
    </button>
  );
}

export default function MyPlan({ strategy: s, features, onCompare, onPrint }) {
  const { t, tm, crop, month } = useI18n();
  const climate = features?.climate?.monthly;
  const months = flatMonths(s);
  const [cursor, setCursor] = useState(null);
  const [marked, setMarked] = useState(null);
  const timer = useRef(null);
  const crops = s.seasons.map((x) => x.crop_id);
  const name = (c) => (c === 'fallow' ? t('ui.s_fallow') : crop(c));
  const conf = { high: 'good', medium: 'caution', low: 'caution' }[s.confidence];
  const risk = keyRisk(s.risks_for_local_review);
  const vs = verdicts(s);

  useEffect(() => () => clearInterval(timer.current), []);
  useEffect(() => { clearInterval(timer.current); setCursor(null); setMarked(null); }, [s.id]);

  const play = () => {
    clearInterval(timer.current);
    setMarked(null);
    let i = 0;
    setCursor(0);
    timer.current = setInterval(() => {
      i += 1;
      if (i >= months.length) { clearInterval(timer.current); setCursor(null); return; }
      setCursor(i);
    }, 450);
  };

  const m = cursor != null ? months[cursor] : marked != null ? months[marked] : null;
  const dry = m?.stress_reasons.find((r) => r.code === 'stress_water_deficit');
  const where = m ? (m.crop_id === null ? t('ui.life_bare') : name(m.crop_id)) : '';

  const advice = `${t('ui.s_plant')} ${crops.map(name).join(` ${t('ui.s_then')} `)}.`;
  const spoken = [
    advice,
    ...vs.map((v) => `${t(`ui.v_${v.id}`)}: ${t(`ui.${v.key}`)}.`),
    risk && risk.code !== 'risk_local_review' ? tm(risk) : '',
    t('ui.talk_expert'),
  ].filter(Boolean).join(' ');

  return (
    <div className="simple">
      <section className="advice" aria-labelledby="advice-h">
        <p className="tag">{t('ui.s_title')}</p>
        <h2 id="advice-h">
          {t('ui.s_plant')}{' '}
          {crops.map((c, i) => (
            <span key={i}>{i > 0 && ` ${t('ui.s_then')} `}<b>{name(c)}</b></span>
          ))}
        </h2>
        <ul className="crop-line" aria-hidden="true">
          {crops.map((c, i) => (
            <Fragment key={i}>
              {i > 0 && <li className="then" aria-hidden="true">→</li>}
              <li><CropIcon id={c} size={64} /><span>{crop(c)}</span></li>
            </Fragment>
          ))}
        </ul>
        <ul className="sow-lines">
          {s.seasons.filter((x) => x.crop_id !== 'fallow' && !['alfalfa', 'olive_intercrop'].includes(x.crop_id)).map((x, i) => (
            <li key={i}>
              <CropIcon id={x.crop_id} size={32} />
              {t('ui.season_months', { crop: x.crop_id, sow: month(x.sow_month), harvest: month(x.harvest_month) })}
            </li>
          ))}
        </ul>
        <div className="advice-actions">
          <p className={`badge badge-${conf}`}>
            {conf === 'good' ? <Check /> : <Warn />}
            {t(`ui.s_conf_${s.confidence}`)}
          </p>
          <Listen text={spoken} />
        </div>
      </section>

      <section className="stack life" aria-labelledby="life-h">
        <div className="life-head">
          <h3 id="life-h">{t('ui.life_title')}</h3>
          {!reduced() && (
            <button type="button" className="btn btn-quiet play-btn" onClick={play}>
              <svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true"><path d="M5 3l12 7-12 7z" fill="currentColor" /></svg>
              {t('ui.life_play')}
            </button>
          )}
        </div>
        <FieldLife strategy={s} climate={climate} cursor={cursor} marked={marked} onMark={(i) => { clearInterval(timer.current); setCursor(null); setMarked(i); }} />
        <p className={`life-caption${dry ? ' is-dry' : ''}`} aria-live="polite">
          {m ? (
            <>
              <strong>{month(m.month)} · {t('ui.year_n', { n: m.year })}:</strong> {where}.{' '}
              {dry ? tm(dry) : ''}
            </>
          ) : t('ui.life_hint')}
        </p>
        <ul className="life-key">
          <li><i className="k-crop" />{t('ui.life_key_crop')}</li>
          <li><i className="k-bare" />{t('ui.life_key_bare')}</li>
          <li><i className="k-dot" />{t('ui.life_key_dry')}</li>
          <li><i className="k-soil" />{t('ui.life_key_soil')}</li>
        </ul>
        {risk && risk.code !== 'risk_local_review' && !isWater(risk) && (
          <p className="life-risk"><Warn /> {tm(risk)}</p>
        )}
      </section>

      <ul className="verdicts" aria-label={t('ui.v_label')}>
        {vs.map((v) => {
          const Icon = TONE_ICON[v.tone];
          return (
            <li key={v.id} className={`verdict v-${v.tone}`}>
              <Icon />
              <span className="v-name">{t(`ui.v_${v.id}`)}</span>
              <strong>{t(`ui.${v.key}`)}</strong>
            </li>
          );
        })}
      </ul>

      {s.benefits.length > 0 && (
        <section className="stack" aria-labelledby="why-h">
          <h3 id="why-h">{t('ui.s_reasons')}</h3>
          <ul className="reason-list">
            {s.benefits.slice(0, 3).map((b, i) => <li key={i}><Check />{tm(b)}</li>)}
          </ul>
        </section>
      )}

      <p className="expert-big">{t('ui.talk_expert')}</p>
      <div className="plan-actions">
        <button type="button" className="btn btn-quiet" onClick={onCompare}>{t('ui.plan_compare')}</button>
        <button type="button" className="btn btn-quiet" onClick={onPrint}>{t('ui.print')}</button>
      </div>
    </div>
  );
}
