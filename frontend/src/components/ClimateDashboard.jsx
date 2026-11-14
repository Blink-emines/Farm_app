import { useI18n } from '../i18n/index.jsx';
import { monthRuns, sum, whole } from '../util.js';
import { MonthBars } from './charts.jsx';

const FROST_MIN = 0.5; // days per month, on average
const HEAT_MIN = 5; // days per month, on average
const HEAT_AT = '35'; // the threshold series (°C) used for the heat chart

function useRuns() {
  const { t, month } = useI18n();
  return (months) => {
    const runs = monthRuns(months);
    if (runs.length === 1 && runs[0][0] === 1 && runs[0][1] === 12) return t('ui.all_year');
    return runs
      .map(([a, b]) => (a === b ? month(a) : t('ui.run_from_to', { from: month(a), to: month(b) })))
      .join(t('ui.list_sep'));
  };
}

// Plain-words summary. Every sentence comes straight from the numbers shown in the charts.
function Summary({ rain, et0, frost, heat }) {
  const { t, month } = useI18n();
  const runs = useRuns();
  const idx = (arr, pred) => arr.map((v, i) => (pred(v, i) ? i + 1 : null)).filter(Boolean);
  const dry = idx(rain, (r, i) => r < et0[i]);
  const frosty = idx(frost, (f) => f >= FROST_MIN);
  const hot = idx(heat, (h) => h >= HEAT_MIN);
  const wettest = rain.indexOf(Math.max(...rain)) + 1;
  return (
    <ul className="summary">
      <li>{dry.length ? t('ui.sum_dry', { runs: runs(dry) }) : t('ui.sum_no_dry')}</li>
      <li>{t('ui.sum_rain_total', { mm: whole(sum(rain)), month: month(wettest), mmax: whole(rain[wettest - 1]) })}</li>
      <li>{frosty.length ? t('ui.sum_frost', { d: FROST_MIN, runs: runs(frosty) }) : t('ui.sum_no_frost', { d: FROST_MIN })}</li>
      <li>{hot.length ? t('ui.sum_heat', { d: HEAT_MIN, c: HEAT_AT, runs: runs(hot) }) : t('ui.sum_no_heat', { d: HEAT_MIN, c: HEAT_AT })}</li>
    </ul>
  );
}

export default function ClimateDashboard({ features }) {
  const { t } = useI18n();
  const m = features?.climate?.monthly;
  const period = features?.climate?.period;
  const rain = m?.precipitation?.values;
  const et0 = m?.et0?.values;
  const frost = m?.frost_days?.values;
  const heat = m?.heat_days?.[HEAT_AT]?.values;
  if (![rain, et0, frost, heat].every((a) => a && a.length === 12)) return null;
  return (
    <section className="panel" aria-labelledby="climate-h">
      <h3 id="climate-h">{t('ui.climate_title')}</h3>
      {period && <p className="muted">{t('ui.climate_intro', { start: period.start_year, end: period.end_year })}</p>}
      <div className="notice">
        <h4>{t('ui.sum_title')}</h4>
        <Summary rain={rain} et0={et0} frost={frost} heat={heat} />
      </div>
      <div className="charts">
        <figure className="chart">
          <figcaption>{t('ui.rain_title')} <span className="muted">({t('ui.rain_unit')})</span></figcaption>
          <MonthBars values={rain} line={et0} label={t('ui.rain_title')} />
          <ul className="chart-key">
            <li><i className="sw bar-water-sw" />{t('ui.rain_bar')}</li>
            <li><i className="sw-line" />{t('ui.rain_tick')}</li>
          </ul>
        </figure>
        <figure className="chart">
          <figcaption>{t('ui.chart_frost')}</figcaption>
          <MonthBars values={frost} barClass="bar-frost" label={t('ui.chart_frost')} />
          <ul className="chart-key"><li><i className="sw bar-frost-sw" />{t('ui.chart_frost')}</li></ul>
        </figure>
        <figure className="chart">
          <figcaption>{t('ui.chart_heat', { t: HEAT_AT })}</figcaption>
          <MonthBars values={heat} barClass="bar-heat" label={t('ui.chart_heat', { t: HEAT_AT })} />
          <ul className="chart-key"><li><i className="sw bar-heat-sw" />{t('ui.chart_heat', { t: HEAT_AT })}</li></ul>
        </figure>
      </div>
    </section>
  );
}
