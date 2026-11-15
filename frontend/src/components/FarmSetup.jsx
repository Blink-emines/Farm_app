import { useEffect, useRef, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { DEFAULT_POINT, inBox } from '../constants.js';
import { createFarm } from '../api.js';
import LocationPicker from './LocationPicker.jsx';
import { PinIcon } from './icons.jsx';

// Crops are chosen later, in the optimisation tab.
const STEPS = ['name', 'fields', 'soil', 'location'];
const SOILS = ['clay', 'loam', 'sandy', 'red', 'stony', 'unknown'];
const MAX_FIELDS = 20;

// Small drawings of each soil, so the farmer picks by look rather than by name.
// Scattered but always the same (no randomness between renders).
const scatter = (i, seed) => { const x = Math.sin(i * 12.9898 + seed * 78.233) * 43758.5453; return x - Math.floor(x); };
const dots = (n, seed, r, fill) => Array.from({ length: n }, (_, i) => (
  <circle key={i} cx={2 + scatter(i, seed) * 116} cy={2 + scatter(i + 500, seed) * 76} r={r} fill={fill} />
));
const SOIL_ART = {
  clay: (
    <>
      <rect width="120" height="80" fill="#3b2a20" />
      <path d="M10 0L24 22L18 44L30 80M24 22L56 30L70 0M56 30L60 56L44 80M60 56L96 50L120 62M96 50L104 20L120 14M104 20L84 0" fill="none" stroke="#1c120c" strokeWidth="3" strokeLinejoin="round" />
    </>
  ),
  loam: (
    <>
      <rect width="120" height="80" fill="#7a5233" />
      {dots(26, 1, 5, '#5e3d24')}
      {dots(18, 4, 3, '#9a6b45')}
    </>
  ),
  sandy: (
    <>
      <rect width="120" height="80" fill="#e3c88f" />
      {dots(60, 2, 1.6, '#b9975a')}
      {dots(30, 5, 1.2, '#fff3d6')}
    </>
  ),
  red: (
    <>
      <rect width="120" height="80" fill="#a5432a" />
      {dots(24, 3, 4.5, '#83311d')}
      {dots(16, 6, 2.5, '#c4623f')}
    </>
  ),
  stony: (
    <>
      <rect width="120" height="80" fill="#cfc4b0" />
      <ellipse cx="22" cy="20" rx="13" ry="9" fill="#8f8574" stroke="#5f5749" strokeWidth="2" />
      <ellipse cx="74" cy="16" rx="9" ry="7" fill="#efe9dc" stroke="#8f8574" strokeWidth="2" />
      <ellipse cx="96" cy="52" rx="15" ry="10" fill="#8f8574" stroke="#5f5749" strokeWidth="2" />
      <ellipse cx="40" cy="58" rx="11" ry="8" fill="#efe9dc" stroke="#8f8574" strokeWidth="2" />
      <ellipse cx="66" cy="44" rx="6" ry="5" fill="#a69c89" stroke="#5f5749" strokeWidth="2" />
    </>
  ),
  unknown: (
    <>
      <rect width="120" height="80" fill="var(--page)" />
      <text x="60" y="56" textAnchor="middle" fontSize="48" fontWeight="600" fill="var(--muted)">?</text>
    </>
  ),
};

export function SoilArt({ id }) {
  return <svg className="soil-art" viewBox="0 0 120 80" aria-hidden="true" focusable="false">{SOIL_ART[id]}</svg>;
}

const toNumber = (text) => Number(String(text).replace(',', '.'));
const validSize = (text) => String(text).trim() !== '' && toNumber(text) > 0 && toNumber(text) <= 10000;

// First wizard after sign-up: describe the farm once (name, fields, soil, place).
export default function FarmSetup({ head, onDone }) {
  const { t } = useI18n();
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [sizes, setSizes] = useState(['']);
  const [soil, setSoil] = useState('');
  // The map shows a starting point; the farmer must tap the map or use GPS before going on.
  const [point, setPoint] = useState({ ...DEFAULT_POINT });
  const [placed, setPlaced] = useState(false);
  const [geo, setGeo] = useState({ state: 'idle' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const alertRef = useRef(null);

  // On a phone the message could sit under the buttons: bring it into view.
  useEffect(() => { if (error) alertRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }); }, [error]);

  const setCount = (n) => {
    const count = Math.min(MAX_FIELDS, Math.max(1, n));
    setSizes((s) => Array.from({ length: count }, (_, i) => s[i] ?? ''));
  };

  function locate() {
    if (!('geolocation' in navigator)) { setGeo({ state: 'unavailable' }); return; }
    setGeo({ state: 'asking' });
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (!inBox(coords.latitude, coords.longitude)) { setGeo({ state: 'outside' }); return; }
        const r = (x) => Math.round(x * 10000) / 10000;
        setPoint({ lat: r(coords.latitude), lon: r(coords.longitude) });
        setPlaced(true);
        setGeo({ state: 'ok', accuracy: Math.round(coords.accuracy) });
        setError('');
      },
      (e) => setGeo({ state: e.code === 1 ? 'denied' : 'unavailable' }),
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 },
    );
  }

  // The message to show if the current step is not filled in yet.
  const problem = () => {
    const id = STEPS[step];
    if (id === 'name' && !name.trim()) return 'ui.farm_err_name';
    if (id === 'fields' && !sizes.every(validSize)) return 'ui.farm_err_size';
    if (id === 'soil' && !soil) return 'ui.farm_err_soil';
    if (id === 'location' && !placed) return 'ui.farm_err_location';
    return '';
  };

  async function next() {
    const p = problem();
    if (p) { setError(p); return; }
    setError('');
    if (step < STEPS.length - 1) { setStep(step + 1); window.scrollTo({ top: 0 }); return; }
    setSaving(true);
    try {
      const farm = await createFarm({
        name: name.trim(),
        latitude: point.lat,
        longitude: point.lon,
        soil_type: soil,
        parcels: sizes.map((s, i) => ({ name: t('ui.farm_field_name', { n: i + 1 }), area_ha: toNumber(s) })),
      });
      onDone(farm);
    } catch {
      setError('ui.farm_err_save');
      setSaving(false);
    }
  }

  const back = () => { setError(''); setStep(step - 1); };
  const id = STEPS[step];
  const geoMsg = { asking: 'ui.farm_gps_asking', denied: 'ui.farm_gps_denied', unavailable: 'ui.farm_gps_unavailable', outside: 'ui.farm_gps_outside' }[geo.state];

  return (
    <>
      {head}
      <main>
        <div className="wizard farm-setup">
          <h1>{t('ui.farm_title')}</h1>
          <nav className="progress" aria-label={t('ui.step_of', { n: step + 1, total: STEPS.length })}>
            <p className="progress-text">{t('ui.step_of', { n: step + 1, total: STEPS.length })}</p>
            <ol style={{ gridTemplateColumns: `repeat(${STEPS.length}, 1fr)` }}>
              {STEPS.map((s, i) => (
                <li key={s} className={i < step ? 'done' : i === step ? 'now' : ''} aria-current={i === step ? 'step' : undefined}>
                  <span className="progress-bar" />
                  <span className="progress-name">{t(`ui.farm_step_${s}`)}</span>
                </li>
              ))}
            </ol>
          </nav>

          <section className="step-body stack" aria-labelledby="farm-q">
            <h2 id="farm-q">{t(`ui.farm_q_${id}`)}</h2>
            <p className="help">{t(`ui.farm_help_${id}`)}</p>

            {id === 'name' && (
              <label className="field">
                <span>{t('ui.farm_name_label')}</span>
                <input type="text" value={name} maxLength={100} autoComplete="off" placeholder={t('ui.farm_name_placeholder')} onChange={(e) => setName(e.target.value)} />
              </label>
            )}

            {id === 'fields' && (
              <>
                <div className="counter" role="group" aria-label={t('ui.farm_fields_count')}>
                  <button type="button" className="counter-btn" aria-label={t('ui.farm_less')} disabled={sizes.length <= 1} onClick={() => setCount(sizes.length - 1)}>−</button>
                  <output className="counter-value" aria-live="polite">{sizes.length}</output>
                  <button type="button" className="counter-btn" aria-label={t('ui.farm_more')} disabled={sizes.length >= MAX_FIELDS} onClick={() => setCount(sizes.length + 1)}>+</button>
                </div>
                <div className="size-list">
                  {sizes.map((s, i) => (
                    <label className="field size-row" key={i}>
                      <span>{t('ui.farm_field_size', { n: i + 1 })}</span>
                      <span className="size-input">
                        <input type="text" inputMode="decimal" value={s} placeholder="1.5" aria-invalid={error && !validSize(s) ? 'true' : undefined}
                          onChange={(e) => setSizes((all) => all.map((x, j) => (j === i ? e.target.value : x)))} />
                        <span className="unit">{t('ui.farm_ha')}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </>
            )}

            {id === 'soil' && (
              <div className="soil-grid" role="radiogroup" aria-labelledby="farm-q">
                {SOILS.map((s) => (
                  <button key={s} type="button" role="radio" aria-checked={soil === s} className="soil-card" onClick={() => { setSoil(s); setError(''); }}>
                    <SoilArt id={s} />
                    <strong>{t(`ui.soil_${s}`)}</strong>
                    <span>{t(`ui.soil_${s}_desc`)}</span>
                  </button>
                ))}
              </div>
            )}

            {id === 'location' && (
              <>
                <LocationPicker lat={point.lat} lon={point.lon} onChange={(lat, lon) => { setPoint({ lat, lon }); setPlaced(true); setError(''); }} onFeatures={() => {}}>
                  <div className="gps-box">
                    <p className="help">{t('ui.farm_gps_or')}</p>
                    <button type="button" className="btn btn-quiet gps-btn" onClick={locate} disabled={geo.state === 'asking'}>
                      <PinIcon size={22} />{t('ui.farm_gps_button')}
                    </button>
                    {geoMsg && <p className={`notice${geo.state === 'asking' ? '' : ' notice-error'}`} role="status">{t(geoMsg)}</p>}
                    {geo.state === 'ok' && <p className="notice" role="status">{t('ui.farm_gps_ok', { m: geo.accuracy })} {t('ui.farm_gps_check')}</p>}
                  </div>
                </LocationPicker>
              </>
            )}

            {error && <p ref={alertRef} className="notice notice-error" role="alert">{t(error)}</p>}
          </section>

          <div className="wizard-nav">
            {step > 0 && <button type="button" className="btn btn-quiet" onClick={back}>{t('ui.back')}</button>}
            <button type="button" className="btn btn-primary" disabled={saving} onClick={next}>
              {saving ? t('ui.loading') : step < STEPS.length - 1 ? t('ui.next') : t('ui.farm_save')}
            </button>
          </div>
        </div>
      </main>
    </>
  );
}
