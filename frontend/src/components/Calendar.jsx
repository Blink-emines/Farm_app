import { useI18n } from '../i18n/index.jsx';
import { NO_MONTHS } from '../constants.js';
import { MonthBars, StatusKey } from './charts.jsx';

// Colour AND a mark show each month's state, so colour is never the only clue.
const MARK = { growing: '', stress: '!', bare: '' };

export function Ribbon({ months }) {
  const { t, month } = useI18n();
  return (
    <ol className="ribbon">
      {months.map((m) => (
        <li
          key={m.month}
          className={`cell cell-${m.status}`}
          title={`${month(m.month)}: ${t(`ui.month_status_${m.status}`)}`}
          aria-label={`${month(m.month)}: ${t(`ui.month_status_${m.status}`)}`}
        >
          <span aria-hidden="true">{m.month}</span>
          <span aria-hidden="true" className="mark">{MARK[m.status]}</span>
        </li>
      ))}
    </ol>
  );
}

// Real precipitation and reference evaporation (ET0) from GET /api/features. Nothing is computed.
export function RainChart({ climate }) {
  const { t } = useI18n();
  const rain = climate?.precipitation?.values;
  const et0 = climate?.et0?.values;
  if (!rain || !et0 || rain.length !== 12 || et0.length !== 12) return null;
  return (
    <figure className="chart">
      <figcaption>
        {t('ui.rain_title')} <span className="muted">({t('ui.rain_unit')})</span>
      </figcaption>
      <MonthBars values={rain} line={et0} label={t('ui.rain_title')} />
      <ul className="chart-key">
        <li><i className="sw bar-water-sw" />{t('ui.rain_bar')}</li>
        <li><i className="sw-line" />{t('ui.rain_tick')}</li>
      </ul>
    </figure>
  );
}

// One line per kind of stress, with its months listed once.
function StressSummary({ months }) {
  const { t, tm, month } = useI18n();
  const groups = new Map();
  for (const m of months) {
    for (const r of m.stress_reasons) {
      if (!groups.has(r.code)) groups.set(r.code, { first: r, months: [] });
      groups.get(r.code).months.push(m.month);
    }
  }
  return (
    <ul className="stress-list">
      {[...groups.entries()].map(([code, g]) => (
        <li key={code}>
          <strong>{g.months.map(month).join(t('ui.list_sep'))} :</strong>{' '}
          {t(`ui.${code}`, g.first.params) !== `ui.${code}` ? t(`ui.${code}`, g.first.params) : tm(g.first)}
        </li>
      ))}
    </ul>
  );
}

export default function Calendar({ calendar, seasons, climate }) {
  const { t, month } = useI18n();
  return (
    <div className="calendar">
      {calendar.map((row) => {
        const stressed = row.months.filter((m) => m.status === 'stress');
        return (
          <div className="cal-year" key={row.year}>
            <h5>{t('ui.year_n', { n: row.year })}</h5>
            <Ribbon months={row.months} />
            {stressed.length > 0 && <StressSummary months={stressed} />}
          </div>
        );
      })}
      <StatusKey />
      <RainChart climate={climate} />
      <ul className="season-months">
        {seasons.filter((s) => !NO_MONTHS.includes(s.crop_id)).map((s, i) => (
          <li key={i}>
            {t('ui.season_months', { crop: s.crop_id, sow: month(s.sow_month), harvest: month(s.harvest_month) })}
          </li>
        ))}
      </ul>
      <p className="muted">{t('ui.months_hint')}</p>
    </div>
  );
}
