import { useEffect, useRef, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { CropShape } from './icons.jsx';

// "Life of your field": rain on top, the crops in the middle, a relative soil line at the bottom,
// months underneath. Everything comes from the strategy (calendar, soil_steps) and features.json.

const isDry = (m) => m.stress_reasons.some((r) => r.code === 'stress_water_deficit');

// Calendar rows flattened into one list of months (rows already start at the first sowing).
export function flatMonths(strategy) {
  return strategy.calendar.flatMap((row) => row.months.map((m) => ({ ...m, year: row.year })));
}

// Consecutive months with the same crop (null = bare field).
function spansOf(months) {
  const out = [];
  months.forEach((m, i) => {
    const last = out[out.length - 1];
    if (last && last.crop === m.crop_id) last.end = i;
    else out.push({ start: i, end: i, crop: m.crop_id });
  });
  return out;
}

// Soil trend at each month boundary (N + 1 values): each season's soil points build up over that
// season's months. Relative only, never a measurement.
export function soilLine(strategy, months) {
  const n = months.length;
  const steps = strategy.soil_steps ?? [];
  const seasonSpans = spansOf(months).filter((s) => s.crop !== null);
  const values = new Array(n + 1).fill(0);
  steps.forEach((st) => {
    const span = seasonSpans.length === strategy.seasons.length
      ? seasonSpans[st.season_index]
      : { start: Math.floor((st.season_index * n) / steps.length), end: Math.floor(((st.season_index + 1) * n) / steps.length) - 1 };
    if (!span) return;
    const a = span.start;
    const b = span.end + 1;
    for (let k = 0; k <= n; k += 1) {
      if (k >= b) values[k] += st.points;
      else if (k > a) values[k] += (st.points * (k - a)) / (b - a);
    }
  });
  return values;
}

export const dryMonths = (strategy) => flatMonths(strategy).filter(isDry).length;
export const soilEnd = (strategy) => (strategy.soil_steps ?? []).reduce((a, s) => a + s.points, 0);

function useWidth(ref, fallback = 343) {
  const [w, setW] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    setW(el.clientWidth || fallback);
    if (!('ResizeObserver' in window)) return undefined;
    const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width) || fallback));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref, fallback]);
  return w;
}

export default function FieldLife({ strategy, climate, compact = false, marked = null, onMark, soilRange }) {
  const { t, crop, month, lang } = useI18n();
  const box = useRef(null);
  const width = useWidth(box);
  const rtl = lang === 'ar';
  const months = flatMonths(strategy);
  const n = months.length;
  const cell = width / n;
  const x = (i) => (rtl ? width - (i + 1) * cell : i * cell); // left edge of month i
  const xb = (k) => (rtl ? width - k * cell : k * cell); // month boundary k

  const rainVals = climate?.precipitation?.values;
  const showRain = !compact && Array.isArray(rainVals) && rainVals.length === 12;
  const rainMax = showRain ? Math.max(1, ...rainVals.filter((v) => typeof v === 'number')) : 1;

  // Vertical layout (px).
  const L = compact
    ? { field: [4, 26], soil: [38, 28], axis: 78, height: 84 }
    : { rain: [24, 52], field: [122, 40], soil: [194, 44], axis: 256, height: 286 };
  const [fTop, fH] = L.field;
  const [sTop, sH] = L.soil;

  const soil = soilLine(strategy, months);
  const [lo, hi] = soilRange ?? [Math.min(0, ...soil), Math.max(0, ...soil)];
  const sy = (v) => (hi === lo ? sTop + sH / 2 : sTop + sH - ((v - lo) / (hi - lo)) * sH);
  const soilPath = soil.map((v, k) => `${k ? 'L' : 'M'}${xb(k).toFixed(1)},${sy(v).toFixed(1)}`).join(' ');
  const zeroY = sy(0);

  const initial = (m) => (lang === 'ar' ? String(m) : month(m).charAt(0).toUpperCase());
  const labelStep = lang === 'ar' ? (cell >= 18 ? 1 : cell >= 9 ? 3 : 6) : (cell >= 11 ? 1 : cell >= 6 ? 3 : 6);
  const years = strategy.calendar.length;
  const anchorStart = rtl ? 'end' : 'start';
  const bandLabelX = rtl ? width - 2 : 2;

  return (
    <div ref={box} className={`field-life${compact ? ' is-compact' : ''}`}>
      <svg width={width} height={L.height} viewBox={`0 0 ${width} ${L.height}`} direction="ltr" role="img" aria-label={t('ui.life_aria', { years })}>
        {showRain && (
          <g className="fl-rain">
            <text x={bandLabelX} y={14} textAnchor={anchorStart} className="fl-band">{t('ui.life_rain')}</text>
            {months.map((m, i) => {
              const v = rainVals[m.month - 1];
              if (typeof v !== 'number') return null;
              const h = (v / rainMax) * L.rain[1];
              return (
                <rect key={i} x={x(i) + cell * 0.18} width={cell * 0.64} y={L.rain[0] + L.rain[1] - h} height={Math.max(h, 1)} rx={Math.min(3, cell * 0.2)}>
                  <title>{`${month(m.month)}: ${Math.round(v)} mm`}</title>
                </rect>
              );
            })}
          </g>
        )}

        {!compact && <text x={bandLabelX} y={fTop - 22} textAnchor={anchorStart} className="fl-band">{t('ui.life_field')}</text>}
        <g className="fl-field">
          {spansOf(months).map((sp) => {
            const bare = sp.crop === null || sp.crop === 'fallow';
            const w = (sp.end - sp.start + 1) * cell;
            const left = rtl ? x(sp.end) : x(sp.start);
            const name = sp.crop === null ? t('ui.life_bare') : sp.crop === 'fallow' ? t('ui.s_fallow') : crop(sp.crop);
            const icon = !compact && !bare && w >= 22;
            const iconSize = Math.min(fH - 10, 26);
            const showName = w >= (icon ? iconSize + 8 : 6) + name.length * 6.6;
            const cx = left + w / 2;
            return (
              <g key={sp.start}>
                <rect x={left + 1} y={fTop} width={Math.max(w - 2, 1)} height={fH} rx={6} className={bare ? 'fl-bare' : 'fl-crop'}>
                  <title>{name}</title>
                </rect>
                {icon && !showName && <svg x={cx - iconSize / 2} y={fTop + (fH - iconSize) / 2} width={iconSize} height={iconSize} viewBox="0 0 48 48" aria-hidden="true"><CropShape id={sp.crop} /></svg>}
                {showName && (() => {
                  // Icon then name, centred as one group (mirrored in Arabic).
                  const gap = icon ? iconSize + 4 : 0;
                  const half = (gap + name.length * 6.6) / 2;
                  const iconX = rtl ? cx + half - iconSize : cx - half;
                  const textX = rtl ? cx + half - gap : cx - half + gap;
                  return (
                    <>
                      {icon && <svg x={iconX} y={fTop + (fH - iconSize) / 2} width={iconSize} height={iconSize} viewBox="0 0 48 48" aria-hidden="true"><CropShape id={sp.crop} /></svg>}
                      <text x={textX} y={fTop + fH / 2 + 4} textAnchor={rtl ? 'end' : 'start'} className={`fl-name${bare ? ' on-bare' : ''}`}>{name}</text>
                    </>
                  );
                })()}
              </g>
            );
          })}
        </g>

        {/* Red dots: months where rain is below what the crop needs. Tap for one sentence. */}
        <g className="fl-dots">
          {months.map((m, i) => (isDry(m) ? (
            <g
              key={i}
              role={onMark ? 'button' : undefined}
              tabIndex={onMark ? 0 : undefined}
              aria-label={onMark ? t('ui.life_dot_aria', { month: month(m.month) }) : undefined}
              onClick={onMark ? () => onMark(i) : undefined}
              onKeyDown={onMark ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onMark(i); } } : undefined}
              className={marked === i ? 'is-marked' : ''}
            >
              <circle cx={x(i) + cell / 2} cy={fTop - 7} r={Math.max(12, cell / 2)} className="fl-hit" />
              <circle cx={x(i) + cell / 2} cy={fTop - 7} r={compact ? 3 : 4.5} className="fl-dot" />
            </g>
          ) : null))}
        </g>

        {!compact && <text x={bandLabelX} y={sTop - 8} textAnchor={anchorStart} className="fl-band">{t('ui.life_soil')}</text>}
        <g className="fl-soil">
          <line x1={0} x2={width} y1={zeroY} y2={zeroY} className="fl-zero" />
          <path d={soilPath} className="fl-soil-line" />
        </g>

        {/* Year separators across all bands. */}
        {Array.from({ length: years - 1 }, (_, y) => (
          <line key={y} x1={xb(12 * (y + 1))} x2={xb(12 * (y + 1))} y1={compact ? 0 : 20} y2={L.axis + 6} className="fl-year-line" />
        ))}

        {!compact && months.map((m, i) => (i % labelStep === 0 ? (
          <text key={i} x={x(i) + cell / 2} y={L.axis} textAnchor="middle" className="fl-month">{initial(m.month)}</text>
        ) : null))}
        {Array.from({ length: years }, (_, y) => (
          <text key={y} x={(xb(12 * y) + xb(12 * (y + 1))) / 2} y={compact ? L.axis : L.axis + 22} textAnchor="middle" className="fl-yearlabel">{t('ui.year_n', { n: y + 1 })}</text>
        ))}
      </svg>
    </div>
  );
}
