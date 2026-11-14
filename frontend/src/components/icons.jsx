// Hand-drawn SVG icons for crops and goals. 48x48, no external set.
const L = 'var(--leaf)';
const G = 'var(--gold)';
const S = { fill: 'none', stroke: 'var(--ink)', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' };

const ears = (y) => [
  <ellipse key={`l${y}`} cx="19" cy={y} rx="3.4" ry="5.6" transform={`rotate(-32 19 ${y})`} fill={G} stroke="var(--ink)" strokeWidth="1.6" />,
  <ellipse key={`r${y}`} cx="29" cy={y} rx="3.4" ry="5.6" transform={`rotate(32 29 ${y})`} fill={G} stroke="var(--ink)" strokeWidth="1.6" />,
];

const CROPS = {
  wheat: (
    <>
      <path d="M24 44V16" {...S} />
      {[14, 22, 30].flatMap(ears)}
      <ellipse cx="24" cy="8" rx="3.4" ry="5.6" fill={G} stroke="var(--ink)" strokeWidth="1.6" />
    </>
  ),
  barley: (
    <>
      <path d="M24 44V16" {...S} />
      {[14, 22, 30].flatMap(ears)}
      <ellipse cx="24" cy="9" rx="3.4" ry="5" fill={G} stroke="var(--ink)" strokeWidth="1.6" />
      <path d="M24 4V0M20 8L14 2M28 8L34 2M15 14L8 8M33 14L40 8M15 22L8 16M33 22L40 16" {...S} strokeWidth="1.5" />
    </>
  ),
  chickpea: (
    <>
      <path d="M8 29C8 17 24 11 35 19C41 24 39 34 31 37C20 41 8 38 8 29Z" fill="#E7C57A" stroke="var(--ink)" strokeWidth="2" />
      <circle cx="19" cy="28" r="5" fill="#F6E3B0" stroke="var(--ink)" strokeWidth="1.6" />
      <circle cx="30" cy="28" r="5" fill="#F6E3B0" stroke="var(--ink)" strokeWidth="1.6" />
      <path d="M30 14C32 8 38 6 42 7C42 12 38 16 32 16Z" fill={L} stroke="var(--ink)" strokeWidth="1.6" />
    </>
  ),
  lentil: (
    <>
      {[[15, 19, -20], [31, 17, 20], [23, 29, 0], [36, 31, -25], [12, 35, 25]].map(([x, y, r], i) => (
        <ellipse key={i} cx={x} cy={y} rx="8" ry="5.4" transform={`rotate(${r} ${x} ${y})`} fill="#D9743C" stroke="var(--ink)" strokeWidth="1.8" />
      ))}
    </>
  ),
  faba_bean: (
    <>
      <path d="M7 37C5 28 13 14 30 8C41 5 43 12 39 21C33 33 18 43 7 37Z" fill={L} stroke="var(--ink)" strokeWidth="2" />
      {[[17, 29], [25, 22], [32, 15]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r="4.4" fill="#B5D984" stroke="var(--ink)" strokeWidth="1.5" />)}
    </>
  ),
  alfalfa: (
    <>
      <path d="M24 45V28" {...S} />
      {[[24, 15], [14, 26], [34, 26]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r="8" fill={L} stroke="var(--ink)" strokeWidth="1.8" />)}
      <path d="M24 28V19M24 28L17 24M24 28L31 24" {...S} strokeWidth="1.3" />
    </>
  ),
  vetch_oat_cover: (
    <>
      <path d="M10 44C10 32 12 24 8 14M18 44C18 30 22 22 20 8M26 44C26 32 30 24 34 12M34 44C34 34 38 28 42 20M42 44C42 38 42 34 44 30" fill="none" stroke={L} strokeWidth="3" strokeLinecap="round" />
      <circle cx="20" cy="8" r="3.6" fill="#9C7BD0" stroke="var(--ink)" strokeWidth="1.4" />
      <circle cx="34" cy="12" r="3.6" fill="#9C7BD0" stroke="var(--ink)" strokeWidth="1.4" />
    </>
  ),
  sunflower: (
    <>
      <path d="M24 30V46" {...S} strokeWidth="2.4" />
      <path d="M24 40C30 40 34 36 34 32C28 32 24 35 24 40Z" fill={L} stroke="var(--ink)" strokeWidth="1.5" />
      {Array.from({ length: 12 }, (_, i) => (
        <ellipse key={i} cx="24" cy="9" rx="3.2" ry="6" transform={`rotate(${i * 30} 24 20)`} fill={G} stroke="var(--ink)" strokeWidth="1.2" />
      ))}
      <circle cx="24" cy="20" r="7.5" fill="#6B4423" stroke="var(--ink)" strokeWidth="1.6" />
    </>
  ),
  potato: (
    <>
      <path d="M9 26C9 14 22 8 33 12C42 15 42 28 36 35C30 42 14 40 10 33C9 31 9 28 9 26Z" fill="#CFA56B" stroke="var(--ink)" strokeWidth="2" />
      {[[18, 22], [29, 19], [27, 31]].map(([x, y], i) => <ellipse key={i} cx={x} cy={y} rx="1.8" ry="1.2" fill="var(--ink)" />)}
    </>
  ),
  olive_intercrop: (
    <>
      <path d="M5 40C16 34 28 26 42 12" {...S} strokeWidth="2.4" />
      {[[13, 33, -50], [21, 28, 40], [29, 21, -50], [37, 15, 40], [17, 38, 40]].map(([x, y, r], i) => (
        <ellipse key={i} cx={x} cy={y - 4} rx="3" ry="7" transform={`rotate(${r} ${x} ${y})`} fill="#8CA866" stroke="var(--ink)" strokeWidth="1.3" />
      ))}
      {[[24, 33], [33, 27], [38, 22]].map(([x, y], i) => <ellipse key={i} cx={x} cy={y} rx="3.4" ry="4.4" fill="#4A5D2A" stroke="var(--ink)" strokeWidth="1.3" />)}
    </>
  ),
  fallow: (
    <>
      <circle cx="35" cy="12" r="6" fill={G} stroke="var(--ink)" strokeWidth="1.8" />
      <path d="M4 30C12 26 18 34 26 30S38 26 44 30M4 37C12 33 18 41 26 37S38 33 44 37M4 44C12 40 18 48 26 44S38 40 44 44" fill="none" stroke="#9A6B3F" strokeWidth="3" strokeLinecap="round" />
    </>
  ),
};

export function CropIcon({ id, size = 48 }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      {CROPS[id] ?? null}
    </svg>
  );
}

const GOALS = {
  save_water: (
    <>
      <path d="M24 5C24 5 11 20 11 30a13 13 0 0 0 26 0C37 20 24 5 24 5Z" fill="var(--water)" stroke="var(--ink)" strokeWidth="2" />
      <path d="M17 31a7 7 0 0 0 6 7" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
    </>
  ),
  improve_soil: (
    <>
      <rect x="6" y="28" width="36" height="6" rx="3" fill="#B98B5A" stroke="var(--ink)" strokeWidth="1.8" />
      <rect x="6" y="35" width="36" height="6" rx="3" fill="#8A6540" stroke="var(--ink)" strokeWidth="1.8" />
      <path d="M24 28V16" {...S} />
      <path d="M24 20C24 13 18 10 12 11C12 17 17 21 24 20ZM24 16C24 10 29 7 35 8C35 14 30 18 24 16Z" fill={L} stroke="var(--ink)" strokeWidth="1.6" />
    </>
  ),
  extra_income: (
    <>
      <ellipse cx="24" cy="34" rx="15" ry="6" fill="#E3A82B" stroke="var(--ink)" strokeWidth="1.8" />
      <path d="M9 34v-6M39 34v-6" {...S} strokeWidth="1.8" />
      <ellipse cx="24" cy="28" rx="15" ry="6" fill={G} stroke="var(--ink)" strokeWidth="1.8" />
      <circle cx="24" cy="15" r="10" fill={G} stroke="var(--ink)" strokeWidth="2" />
      <path d="M24 9v12M20.5 12.5c0-2 7-2 7 0s-7 3-7 5.5 7 2 7 0" {...S} strokeWidth="1.6" />
    </>
  ),
  reduce_erosion: (
    <>
      <path d="M3 40C14 16 34 16 45 40Z" fill="#9C7A4F" stroke="var(--ink)" strokeWidth="2" />
      <path d="M12 38C20 26 30 26 38 38" fill="none" stroke={L} strokeWidth="3" strokeLinecap="round" />
      <path d="M12 6l-3 8M24 4l-3 8M36 6l-3 8" stroke="var(--water)" strokeWidth="3" strokeLinecap="round" />
    </>
  ),
  forage: (
    <>
      <rect x="6" y="15" width="36" height="24" rx="6" fill="#E3BB5C" stroke="var(--ink)" strokeWidth="2" />
      <path d="M17 15v24M31 15v24" stroke="#9A6B3F" strokeWidth="2.4" />
      <path d="M10 22h4M10 29h4M20 22h8M20 29h8M34 22h4M34 29h4" stroke="var(--ink)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M12 15l-3-6M24 15v-8M36 15l3-6" stroke="#C99A2E" strokeWidth="2.2" strokeLinecap="round" />
    </>
  ),
};

export function GoalIcon({ id, size = 40 }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
      {GOALS[id] ?? null}
    </svg>
  );
}

// The brand mark: a tiny year dial.
export function BrandMark({ size = 28 }) {
  const cols = ['var(--leaf)', 'var(--leaf)', 'var(--clay)', 'var(--clay)', 'var(--sand)', 'var(--sand)', 'var(--sand)', 'var(--sand)', 'var(--sand)', 'var(--sand)', 'var(--leaf)', 'var(--leaf)'];
  return (
    <svg width={size} height={size} viewBox="-24 -24 48 48" aria-hidden="true" focusable="false">
      {cols.map((c, i) => (
        <path key={i} d="M-3,-22 A22,22 0 0 1 3,-22 L2.2,-13 A13,13 0 0 0 -2.2,-13Z" transform={`rotate(${i * 30})`} fill={c} />
      ))}
    </svg>
  );
}

export function PinIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12Z" />
      <circle cx="12" cy="10" r="2.6" />
    </svg>
  );
}
