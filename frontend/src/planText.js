// Plain-words description of one option, shared by the Compare cards and the printed report.
import { flatMonths } from './components/FieldLife.jsx';
import { verdicts } from './components/MyPlan.jsx';

const isDry = (m) => m.stress_reasons.some((r) => r.code === 'stress_water_deficit');

export function describeOption(s, cur, { t, crop, month, lang }) {
  const name = (c) => (c === 'fallow' ? t('ui.s_fallow') : crop(c));
  const inSentence = (c) => (lang === 'ar' ? name(c) : name(c).toLowerCase());
  const f = s.facts;
  const crops = s.seasons.map((x) => x.crop_id);
  const dry = [...new Set(flatMonths(s).filter(isDry).map((m) => m.month))];

  let diff;
  if (s.is_current) diff = t('ui.cmp_this_is_now');
  else {
    const c = cur.facts;
    const good = [];
    const bad = [];
    if (f.return.relative_to_current === 'more') good.push(t('ui.cmp_d_more_return'));
    if (f.return.relative_to_current === 'less') bad.push(t('ui.cmp_d_less_return'));
    if (f.water_need_mm_per_year != null && c.water_need_mm_per_year > 0) {
      const r = f.water_need_mm_per_year / c.water_need_mm_per_year;
      if (r > 1.1) bad.push(t('ui.cmp_d_more_water'));
      if (r < 0.9) good.push(t('ui.cmp_d_less_water'));
    }
    if (f.soil_points - c.soil_points > 0.5) good.push(t('ui.cmp_d_better_soil'));
    if (f.soil_points - c.soil_points < -0.5) bad.push(t('ui.cmp_d_worse_soil'));
    if (f.dry_months_per_year - c.dry_months_per_year > 0.5) bad.push(t('ui.cmp_d_more_dry'));
    if (f.dry_months_per_year - c.dry_months_per_year < -0.5) good.push(t('ui.cmp_d_fewer_dry'));
    const sep = t('ui.list_sep');
    const g = good.join(sep);
    const b = bad.join(sep);
    diff = !g && !b ? t('ui.cmp_d_same') : `${t('ui.cmp_d_prefix')} ${g}${g && b ? ` ${t('ui.cmp_d_but')} ` : ''}${b}`;
  }

  return {
    title: t('ui.cmp_if').replace('{crops}', crops.map(inSentence).join(` ${t('ui.s_then')} `)),
    ret: f.return.crops.map((r) => (r.yield_t_per_ha
      ? t('ui.cmp_yield', { crop: name(r.crop_id), min: r.yield_t_per_ha.min, max: r.yield_t_per_ha.max })
      : t('ui.cmp_yield_none', { crop: name(r.crop_id) }))),
    rel: f.return.relative_to_current === 'current' ? '' : t(`ui.cmp_rel_${f.return.relative_to_current}`),
    water: f.water_need_mm_per_year == null ? t('ui.dash_unknown') : t('ui.cmp_water_mm', { mm: f.water_need_mm_per_year }),
    soil: t(`ui.${verdicts(s)[1].key}`),
    risk: dry.length ? t('ui.cmp_risk_months', { n: f.dry_months_per_year, months: dry.map(month).join(t('ui.list_sep')) }) : t('ui.cmp_risk_none'),
    diff,
  };
}
