import { Fragment, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { CropIcon } from './icons.jsx';
import FieldLife, { flatMonths, soilEnd } from './FieldLife.jsx';
import Listen from './Listen.jsx';
import { SoilWords } from './FarmSetup.jsx';

// Plain-words view for farmers: a month-by-month action plan built from the engine's action_steps
// (each one comes from the calendar and a named rule), the life of the field, three verdicts.
const Check = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M7.5 12.5l3 3 6-6.5" /></svg>
);
const Warn = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18.2v.1" /></svg>
);
const Cross = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M8.5 8.5l7 7M15.5 8.5l-7 7" /></svg>
);
const Drop = () => (
  <svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 6C18 16 12 23 12 30a12 12 0 0024 0c0-7-6-14-12-24z" fill="var(--water)" stroke="var(--ink)" strokeWidth="2" /></svg>
);
const Bare = () => (
  <svg viewBox="0 0 48 48" aria-hidden="true"><rect x="4" y="26" width="40" height="14" rx="4" fill="var(--amber)" opacity="0.7" stroke="var(--ink)" strokeWidth="2" /><path d="M10 26l4-6M22 26l2-7M34 26l4-6" stroke="var(--ink)" strokeWidth="2" strokeLinecap="round" /></svg>
);
const TONE_ICON = { good: Check, caution: Warn, risk: Cross };
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

// Which year each step falls in: walk the timeline once, in order.
export function withYears(s) {
  const months = flatMonths(s);
  let at = 0;
  return s.action_steps.map((st) => {
    let i = months.findIndex((m, k) => k >= at && m.month === st.months[0]);
    if (i < 0) i = at;
    at = i;
    return { ...st, year: months[i]?.year ?? 1 };
  });
}

export const actionKey = (st) => (st.action === 'cover_bare' && st.crop_id === 'fallow' ? 'act_cover_fallow' : `act_${st.action}`);
const DONT = new Set(['avoid', 'cover_bare']);

export function stepClips(st) {
  const a = st.months[0];
  const b = st.months[st.months.length - 1];
  const when = a === b ? [`month_${a}`] : [`month_${a}`, 'to', `month_${b}`];
  const crop = st.crop_id && st.crop_id !== 'fallow' && st.action !== 'cover_bare' ? [`crop_${st.crop_id}`] : [];
  const end = st.action === 'avoid' ? ['act_avoid_end'] : []; // "careful:" + crop + "follows the same family"
  return [...when, actionKey(st), ...crop, ...end, `why_${st.message.code}`];
}

function StepPic({ st }) {
  if (st.action === 'watch_water') return <Drop />;
  if (st.action === 'cover_bare') return <Bare />;
  return (
    <span className={`act-crop${st.action === 'avoid' ? ' is-avoid' : ''}`}>
      <CropIcon id={st.crop_id} size={40} />
      {st.action === 'avoid' && <Cross />}
    </span>
  );
}

export default function MyPlan({ strategy: s, features, soil, onCompare, onPrint }) {
  const { t, tm, crop, month, lang } = useI18n();
  const climate = features?.climate?.monthly;
  const months = flatMonths(s);
  const [marked, setMarked] = useState(null);
  // Inside a sentence, crop names are lower case in English and French ("Sow lentil").
  const inSentence = (c) => (lang === 'ar' ? crop(c) : crop(c).toLowerCase());
  const crops = s.seasons.map((x) => x.crop_id);
  const name = (c) => (c === 'fallow' ? t('ui.s_fallow') : crop(c));
  const conf = { high: 'good', medium: 'caution', low: 'caution' }[s.confidence];
  const risk = keyRisk(s.risks_for_local_review);
  const vs = verdicts(s);
  const steps = withYears(s);
  const years = s.calendar.length;

  const range = (st) => {
    const a = st.months[0];
    const b = st.months[st.months.length - 1];
    return a === b ? month(a) : `${month(a)} → ${month(b)}`;
  };
  const action = (st) => t(`ui.${actionKey(st)}`).replace('{crop}', st.crop_id ? inSentence(st.crop_id) : '');
  const stepText = (st) => `${range(st)}: ${action(st)}. ${tm(st.message)}`;

  const m = marked != null ? months[marked] : null;
  const dry = m?.stress_reasons.find((r) => r.code === 'stress_water_deficit');
  const where = m ? (m.crop_id === null ? t('ui.life_bare') : name(m.crop_id)) : '';

  const summary = crops.map(name).join(' → ');
  // Read as one text (server voice): each step on its own lines, like a spoken script.
  const planText = [
    `${t('ui.plan_summary')} ${crops.map(name).join(` ${t('ui.s_then')} `)}.`,
    ...steps.map((st) => `${range(st)}\n${action(st)}\n${tm(st.message)}`),
    vs.map((v) => `${t(`ui.v_${v.id}`)}: ${t(`ui.${v.key}`)}.`).join('\n'),
    t('ui.talk_expert'),
  ].join('\n\n');
  const planClips = [
    'plan_intro', ...crops.flatMap((c, i) => (i ? ['then', `crop_${c}`] : [`crop_${c}`])),
    ...steps.flatMap((st) => stepClips(st).slice(0, -1)),
    ...vs.flatMap((v) => [`v_${v.id}`, v.key]),
    'talk_expert',
  ];

  return (
    <div className="simple">
      <section className="advice" aria-labelledby="steps-h">
        <p className="plan-summary">
          <span className="tag">{t('ui.plan_summary')}</span>
          <span className="plan-crops">{crops.map((c, i) => <span key={i}><CropIcon id={c} size={24} />{name(c)}</span>)}</span>
        </p>
        <h2 id="steps-h">{t('ui.steps_title')}</h2>
        <div className="advice-actions">
          <Listen clips={planClips} text={planText} label={t('ui.listen_plan')} />
          <p className={`badge badge-${conf}`}>
            {conf === 'good' ? <Check /> : <Warn />}
            {t(`ui.s_conf_${s.confidence}`)}
          </p>
        </div>
        {soil && <p className="plan-soil">{t('ui.plan_soil')} <SoilWords soil={soil} features={features} /></p>}

        <ol className="act-steps" aria-label={summary}>
          {steps.map((st, i) => (
            <Fragment key={i}>
            {years > 1 && (i === 0 || steps[i - 1].year !== st.year) && <li className="act-year" aria-hidden="true">{t('ui.year_n', { n: st.year })}</li>}
            <li className={`act-step${DONT.has(st.action) ? ' is-dont' : ''}${st.action === 'watch_water' ? ' is-water' : ''}`} data-rule={st.rule_id}>
              <span className="act-when">{range(st)}</span>
              <span className="act-pic"><StepPic st={st} /></span>
              <span className="act-body">
                <strong>{action(st)}</strong>
                <span>{tm(st.message)}</span>
              </span>
              <Listen compact clips={stepClips(st)} text={stepText(st)} label={`${t('ui.listen')}: ${action(st)}`} />
            </li>
            </Fragment>
          ))}
        </ol>
      </section>

      <section className="stack life" aria-labelledby="life-h">
        <h3 id="life-h">{t('ui.life_title')}</h3>
        <FieldLife strategy={s} climate={climate} marked={marked} onMark={setMarked} />
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

      <div className="expert-big">
        <p>{t('ui.talk_expert')}</p>
        <Listen compact clips={['talk_expert']} text={t('ui.talk_expert')} />
      </div>
      <div className="plan-actions">
        <button type="button" className="btn btn-quiet" onClick={onCompare}>{t('ui.plan_compare')}</button>
        <button type="button" className="btn btn-quiet" onClick={onPrint}>{t('ui.print')}</button>
      </div>
    </div>
  );
}
