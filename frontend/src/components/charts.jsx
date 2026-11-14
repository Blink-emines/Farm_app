import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';

// Hand-drawn SVG from the real numbers. No chart library.

export function smooth(points) {
  // Catmull-Rom to cubic Bezier: a smooth line through every point.
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    d += ` C${p1[0] + (p2[0] - p0[0]) / 6},${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6},${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]},${p2[1]}`;
  }
  return d;
}

const niceMax = (v) => {
  if (v <= 1) return 1;
  const steps = [1, 2, 5, 10];
  const pow = 10 ** Math.floor(Math.log10(v));
  return pow * (steps.find((s) => s * pow >= v) ?? 10);
};

// Bars for one 12-month series, with an optional line over them.
// Bars grow once when the chart appears (skipped when the user prefers less motion, in CSS).
export function MonthBars({ values, line, barClass = 'bar-water', label }) {
  const { month, lang } = useI18n();
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(true));
    return () => cancelAnimationFrame(id);
  }, []);
  const W = 360;
  const base = 124;
  const col = W / 12;
  const top = niceMax(Math.max(...values, ...(line ?? []), 0));
  const x = (i) => col * (lang === 'ar' ? 11 - i : i) + col / 2;
  const y = (v) => base - (v / top) * 104;
  const linePts = line ? line.map((v, i) => [x(i), y(v)]).sort((a, b) => a[0] - b[0]) : null;
  return (
    <svg className={`mbars${shown ? ' is-in' : ''}`} viewBox="0 0 360 148" role="img" aria-label={label}>
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line className="grid-line" x1="0" x2={W} y1={y(top * f)} y2={y(top * f)} />
          <text className="axis" x={lang === 'ar' ? W : 0} y={y(top * f) - 3} textAnchor={lang === 'ar' ? 'end' : 'start'}>{Math.round(top * f * 10) / 10}</text>
        </g>
      ))}
      {values.map((v, i) => (
        <rect
          key={i}
          className={`mbar ${barClass}`}
          x={x(i) - col / 2 + 6}
          width={col - 12}
          y={y(v)}
          height={Math.max(base - y(v), 0)}
          rx="3"
          style={{ transitionDelay: `${i * 40}ms` }}
        >
          <title>{`${month(i + 1)}: ${Math.round(v * 10) / 10}`}</title>
        </rect>
      ))}
      {linePts && (
        <>
          <path className="mline" d={smooth(linePts)} pathLength="1" />
          {linePts.map(([cx, cy], i) => <circle key={i} className="mdot" cx={cx} cy={cy} r="3" />)}
        </>
      )}
      {values.map((_, i) => (
        <text key={i} className="axis" x={x(i)} y="142" textAnchor="middle">{i + 1}</text>
      ))}
    </svg>
  );
}

const STATUS_CLASS = { growing: 'is-growing', stress: 'is-stress', bare: 'is-bare' };

function arc(cx, cy, r0, r1, a0, a1) {
  const p = (r, a) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  const [x0, y0] = p(r1, a0); const [x1, y1] = p(r1, a1);
  const [x2, y2] = p(r0, a1); const [x3, y3] = p(r0, a0);
  return `M${x0},${y0} A${r1},${r1} 0 0 1 ${x1},${y1} L${x2},${y2} A${r0},${r0} 0 0 0 ${x3},${y3} Z`;
}

// The year dial. January at the top, clockwise. The ring is the calendar
// (growing / stress / bare), blue spokes are rain, dots are reference evaporation.
export function YearDial({ months, climate, children }) {
  const { t, month } = useI18n();
  const rain = climate?.precipitation?.values;
  const et0 = climate?.et0?.values;
  const has = rain && et0 && rain.length === 12 && et0.length === 12;
  const top = has ? Math.max(...rain, ...et0, 1) : 1;
  const step = (Math.PI * 2) / 12;
  const gap = 0.03;
  const alt = months.map((m) => `${month(m.month)}: ${t(`ui.month_status_${m.status}`)}`).join(', ');
  return (
    <div className="dial">
      <svg className="art" viewBox="0 0 240 240" role="img" aria-label={alt}>
        {months.map((m, i) => (
          <path key={m.month} className={`cell-fill ${STATUS_CLASS[m.status]}`} d={arc(120, 120, 56, 80, step * i + gap, step * (i + 1) - gap)} />
        ))}
        {has && rain.map((r, i) => {
          const a = step * i + step / 2;
          const len = (v) => 4 + (v / top) * 24;
          const at = (rad) => [120 + rad * Math.sin(a), 120 - rad * Math.cos(a)];
          const [x0, y0] = at(86); const [x1, y1] = at(86 + len(r)); const [x2, y2] = at(86 + len(et0[i]));
          return (
            <g key={i}>
              <line className="spoke-rain" x1={x0} y1={y0} x2={x1} y2={y1} />
              <circle className="spoke-et0" cx={x2} cy={y2} r="2.4" />
            </g>
          );
        })}
      </svg>
      <div className="dial-center">{children}</div>
    </div>
  );
}

// What every colour and mark on the dial means.
export function DialKey() {
  const { t } = useI18n();
  return (
    <div className="chart-key">
      <p className="muted">{t('ui.key_ring')}</p>
      <ul>
        {['growing', 'stress', 'bare'].map((s) => (
          <li key={s}><i className={`sw cell-fill is-${s}`} />{t(`ui.legend_${s}`)}</li>
        ))}
        <li><i className="sw-spoke" />{t('ui.key_spoke')}</li>
        <li><i className="sw-dot" />{t('ui.key_dot')}</li>
      </ul>
    </div>
  );
}

export function StatusKey() {
  const { t } = useI18n();
  return (
    <ul className="chart-key legend">
      {['growing', 'stress', 'bare'].map((s) => (
        <li key={s}><i className={`sw cell-fill is-${s}`} />{t(`ui.legend_${s}`)}</li>
      ))}
    </ul>
  );
}
