import { useI18n } from '../i18n/index.jsx';
import { actionKey, verdicts, withYears } from './MyPlan.jsx';
import { SoilWords } from './FarmSetup.jsx';
import { describeOption } from '../planText.js';

// Shown only when printing (see the print rules in styles.css); the browser's print gives a PDF.
// Same content as the screen: the plan being viewed, its steps, verdicts, and all options compared.
export default function PrintReport({ data, strategy: s, features, soil }) {
  const i18n = useI18n();
  const { t, tm, crop, month, lang, date: fmtDate } = i18n;
  const name = (c) => (c === 'fallow' ? t('ui.s_fallow') : crop(c));
  const inSentence = (c) => (lang === 'ar' ? crop(c) : crop(c).toLowerCase());
  const range = (st) => (st.months.length > 1 ? `${month(st.months[0])} → ${month(st.months[st.months.length - 1])}` : month(st.months[0]));
  const action = (st) => t(`ui.${actionKey(st)}`).replace('{crop}', st.crop_id ? inSentence(st.crop_id) : '');
  const cur = data.strategies.find((x) => x.is_current);
  const steps = withYears(s);
  const gaps = (features?.data_gaps ?? []).map((g) => (t(`gap.${g.code}`) !== `gap.${g.code}` ? t(`gap.${g.code}`) : g.message));

  return (
    <article className="report">
      <p>{t('ui.brand')} · {t('ui.report_date')} : {fmtDate(new Date())}</p>
      <h1>{t('ui.report_title')}</h1>
      <p>{t('ui.report_point')} : <bdi dir="ltr">{data.location.latitude}, {data.location.longitude}</bdi></p>
      {soil && <p>{t('ui.plan_soil')} <SoilWords soil={soil} features={features} /></p>}
      <p><strong>{t('ui.plan_summary')}</strong> {s.seasons.map((x) => name(x.crop_id)).join(' → ')}</p>

      <h2>{t('ui.steps_title')}</h2>
      <table className="report-steps">
        <tbody>
          {steps.map((st, i) => (
            <tr key={i}>
              <td>{s.calendar.length > 1 ? `${t('ui.year_n', { n: st.year })} · ` : ''}{range(st)}</td>
              <td><strong>{action(st)}</strong><br />{tm(st.message)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>{t('ui.v_label')}</h2>
      <ul>{verdicts(s).map((v) => <li key={v.id}><strong>{t(`ui.v_${v.id}`)}:</strong> {t(`ui.${v.key}`)}</li>)}</ul>

      <h2>{t('ui.tab_compare')}</h2>
      {data.strategies.map((o) => {
        const d = describeOption(o, cur, i18n);
        return (
          <section className="report-strategy" key={o.id}>
            <h3>{d.title}</h3>
            <p><strong>{t('ui.cmp_row_return')}:</strong> {d.ret.join(' · ')}{d.rel ? ` (${d.rel})` : ''}</p>
            <p><strong>{t('ui.cmp_row_water')}:</strong> {d.water} · <strong>{t('ui.cmp_row_soil')}:</strong> {d.soil} · <strong>{t('ui.cmp_row_risk')}:</strong> {d.risk}</p>
            <p>{d.diff}</p>
          </section>
        );
      })}
      <p>{t('ui.cmp_yield_note')}</p>

      {gaps.length > 0 && (<><h2>{t('ui.report_gaps')}</h2><ul>{gaps.map((g, i) => <li key={i}>{g}</li>)}</ul></>)}

      <h2>{t('ui.report_notes')}</h2>
      <ul>
        <li><strong>{t('ui.talk_expert')}</strong></li>
        <li>{t('ui.relative_scores')}</li>
      </ul>
    </article>
  );
}
