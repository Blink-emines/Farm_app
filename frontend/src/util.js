// Display helpers. The engine's numbers are never changed, only shown rounded.
export const whole = (n) => Math.sign(n) * Math.round(Math.abs(n));
export const signed = (n) => {
  const w = whole(n);
  return w > 0 ? `+${w}` : String(w);
};

// [3,4,5,6,9] -> [[3,6],[9,9]]. A run can wrap over December to January.
export function monthRuns(months) {
  const has = new Set(months);
  if (has.size === 0) return [];
  if (has.size === 12) return [[1, 12]];
  const runs = [];
  for (let m = 1; m <= 12; m += 1) {
    if (!has.has(m)) continue;
    if (runs.length && runs[runs.length - 1][1] === m - 1) runs[runs.length - 1][1] = m;
    else runs.push([m, m]);
  }
  if (runs.length > 1 && runs[0][0] === 1 && runs[runs.length - 1][1] === 12) {
    const last = runs.pop();
    runs[0] = [last[0], runs[0][1]];
  }
  return runs;
}

export const sum = (xs) => xs.reduce((a, b) => a + (b ?? 0), 0);

// Months per year of one calendar status, averaged over the rotation's year rows.
export function monthsPerYear(strategy, status) {
  const rows = strategy.calendar;
  return sum(rows.map((r) => r.months.filter((m) => m.status === status).length)) / rows.length;
}

import { useEffect, useRef, useState } from 'react';

// Number that eases from its previous value to the new one. Instant when the user prefers less motion.
export function useTween(target, ms = 700) {
  const [value, setValue] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    if (target == null || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      setValue(target);
      from.current = target;
      return undefined;
    }
    const start = performance.now();
    const a = from.current ?? 0;
    let id;
    const tick = (now) => {
      const k = Math.min((now - start) / ms, 1);
      const v = a + (target - a) * (1 - (1 - k) ** 3);
      from.current = v;
      setValue(v);
      if (k < 1) id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [target, ms]);
  return value;
}

export const mean = (xs) => {
  const v = xs.filter((x) => x != null);
  return v.length ? sum(v) / v.length : null;
};
