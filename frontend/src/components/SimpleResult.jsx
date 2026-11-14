import { Fragment, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { CropIcon } from './icons.jsx';

// Plain-words view for farmers: one recommendation, big icons, traffic lights, no numbers or jargon.
const Check = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M7.5 12.5l3 3 6-6.5" /></svg>
);
const Warn = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18.2v.1" /></svg>
);
const Cross = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><path d="M8.5 8.5l7 7M15.5 8.5l-7 7" /></svg>
);
const LIGHT = { growing: ['good', Check], bare: ['caution', Warn], stress: ['risk', Cross] };

function keyRisk(risks) {
  return risks.find((r) => r.code !== 'risk_local_review') ?? risks[0];
}

export default function SimpleResult({ data, onPrint }) {
  const { t, tm, crop, month } = useI18n();
  const [id, setId] = useState(data.strategies[0].id);
  const s = data.strategies.find((x) => x.id === id) ?? data.strategies[0];
  const others = data.strategies.filter((x) => x.id !== s.id);
  const risk = keyRisk(s.risks_for_local_review);
  const crops = s.seasons.map((x) => x.crop_id);
  const name = (c) => (c === 'fallow' ? t('ui.s_fallow') : crop(c));
  const conf = { high: 'good', medium: 'caution', low: 'caution' }[s.confidence];

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
        <p className={`badge badge-${conf}`}>
          {conf === 'good' ? <Check /> : <Warn />}
          {t(`ui.s_conf_${s.confidence}`)}
        </p>
      </section>

      <section className="stack" aria-labelledby="months-h">
        <h3 id="months-h">{t('ui.s_months_title')}</h3>
        {s.calendar.map((row) => (
          <div className="stack" key={row.year}>
            {s.calendar.length > 1 && <h4>{t('ui.year_n', { n: row.year })}</h4>}
            <ol className="tl-grid">
              {row.months.map((m) => {
                const [tone, Icon] = LIGHT[m.status];
                return (
                  <li key={m.month} className={`tl-tile tl-${tone}`}>
                    <Icon />
                    <span>{month(m.month)}</span>
                  </li>
                );
              })}
            </ol>
          </div>
        ))}
        <ul className="tl-key">
          <li className="tl-good"><Check />{t('ui.s_good')}</li>
          <li className="tl-caution"><Warn />{t('ui.s_caution')}</li>
          <li className="tl-risk"><Cross />{t('ui.s_risk_tl')}</li>
        </ul>
      </section>

      {s.benefits.length > 0 && (
        <section className="stack" aria-labelledby="why-h">
          <h3 id="why-h">{t('ui.s_reasons')}</h3>
          <ul className="reason-list">
            {s.benefits.slice(0, 3).map((m, i) => <li key={i}><Check />{tm(m)}</li>)}
          </ul>
        </section>
      )}

      {risk && (
        <section className="risk-box" aria-labelledby="risk-h">
          <h3 id="risk-h">{t('ui.s_risk')}</h3>
          <p>{tm(risk)}</p>
        </section>
      )}

      <p className="expert-big">{t('ui.talk_expert')}</p>

      {others.length > 0 && (
        <section className="stack" aria-labelledby="other-h">
          <h3 id="other-h">{t('ui.s_other')}</h3>
          <div className="other-ideas">
            {others.map((o) => (
              <button key={o.id} type="button" aria-pressed="false" onClick={() => { setId(o.id); window.scrollTo({ top: 0 }); }}>{tm(o.name)}</button>
            ))}
          </div>
        </section>
      )}

      <p className="muted">{t('ui.relative_scores')}</p>
      <p className="muted">{t('ui.s_more_hint')}</p>
      <button type="button" className="btn btn-quiet" onClick={onPrint}>{t('ui.print')}</button>
    </div>
  );
}
