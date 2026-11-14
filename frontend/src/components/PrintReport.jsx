import { useI18n } from '../i18n/index.jsx';
import { signed } from '../util.js';
import { Ribbon } from './Calendar.jsx';
import { StatusKey } from './charts.jsx';

// Shown only when printing (see the print rules in styles.css). Browser print gives a PDF.
export default function PrintReport({ form, data, features }) {
  const { t, tm, crop, month, date: fmtDate } = useI18n();
  const date = fmtDate(new Date());
  const top = data.strategies.slice(0, 3);
  const gaps = [
    ...(features?.data_gaps ?? []).map((g) => ({ key: g.code, text: t(`gap.${g.code}`) !== `gap.${g.code}` ? t(`gap.${g.code}`) : g.message })),
    ...top.flatMap((s) => s.information_gaps).map((m) => ({ key: m.code + JSON.stringify(m.params), text: tm(m) })),
  ].filter((g, i, all) => all.findIndex((x) => x.key === g.key) === i);

  return (
    <article className="report">
      <p>{t('ui.brand')}</p>
      <h1>{t('ui.report_title')}</h1>
      <p>{t('ui.report_date')} : {date}</p>
      <p>{t('ui.report_point')} : <bdi dir="ltr">{data.location.latitude}, {data.location.longitude}</bdi></p>
      <h2>{t('ui.report_rotation')}</h2>
      <ol>
        {form.seasons.map((s, i) => (
          <li key={i}>
            {t('ui.season_n', { n: i + 1 })} : {crop(s.crop_id)}
            {s.sow_month && s.harvest_month ? ` (${month(s.sow_month)} → ${month(s.harvest_month)})` : ''}
          </li>
        ))}
      </ol>

      <h2>{t('ui.report_top')}</h2>
      {top.map((s) => (
        <section className="report-strategy" key={s.id}>
          <h3>{tm(s.name)}</h3>
          <p>{t('ui.score', { n: Math.round(s.score.total) })}. {t('ui.confidence')} {t(`ui.confidence_${s.confidence}`)}.</p>
          {s.calendar.map((row) => <Ribbon key={row.year} months={row.months} />)}
          <h4>{t('ui.why')}</h4>
          <ul>
            {s.why.map((w, i) => (
              <li key={i}><strong>{t('ui.points_for', { n: signed(w.points), goal: t(`ui.goal_${w.priority}`) })}</strong> {tm(w.message)}</li>
            ))}
          </ul>
          <h4>{t('ui.risks')}</h4>
          <ul>{s.risks_for_local_review.map((m, i) => <li key={i}>{tm(m)}</li>)}</ul>
        </section>
      ))}
      <StatusKey />

      <h2>{t('ui.report_gaps')}</h2>
      <ul>{gaps.map((g) => <li key={g.key}>{g.text}</li>)}</ul>

      <h2>{t('ui.report_notes')}</h2>
      <ul>
        <li>{t('ui.talk_expert')}</li>
        <li>{t('ui.relative_scores')}</li>
      </ul>
    </article>
  );
}
