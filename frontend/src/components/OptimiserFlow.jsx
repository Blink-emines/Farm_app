import { useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { ApiError, optimize } from '../api.js';
import { PROFILES, buildOptimizeRequest } from '../constants.js';
import LocationPicker from './LocationPicker.jsx';
import RotationInput from './RotationInput.jsx';
import Priorities from './Priorities.jsx';
import OptimiserResults from './OptimiserResults.jsx';

const newParcel = () => ({
  name: '', area_ha: '2', irrigated: false,
  seasons: [{ crop_id: 'wheat', sow_month: '', harvest_month: '' }, { crop_id: 'fallow', sow_month: '', harvest_month: '' }],
});
const MAX_PARCELS = 20;

export default function OptimiserFlow({ lat, lon, onLocation }) {
  const { t } = useI18n();
  const [parcels, setParcels] = useState([newParcel()]);
  const [priorities, setPriorities] = useState(PROFILES.balanced);
  const [water, setWater] = useState('');
  const [budget, setBudget] = useState('');
  const [state, setState] = useState({ phase: 'form' });

  const names = parcels.map((p, i) => p.name.trim() || t('ui.opt_parcel_n', { n: i + 1 }));
  const setParcel = (i, patch) => setParcels(parcels.map((p, j) => (j === i ? { ...p, ...patch } : p)));
  const areaOk = (p) => Number(String(p.area_ha).replace(',', '.')) > 0;
  const valid = parcels.every(areaOk);
  const profileOf = Object.entries(PROFILES).find(([, v]) => Object.keys(v).every((k) => v[k] === priorities[k]))?.[0];

  async function run() {
    setState({ phase: 'loading' });
    try {
      const data = await optimize(buildOptimizeRequest({ lat, lon, parcels, priorities, waterM3: water, budget }));
      setState({ phase: 'done', data, names });
      window.scrollTo({ top: 0 });
    } catch (e) {
      setState({ phase: 'error', code: e instanceof ApiError ? e.code : 'internal_error' });
    }
  }

  if (state.phase === 'done') {
    return <OptimiserResults data={state.data} names={state.names} onBack={() => setState({ phase: 'form' })} />;
  }

  return (
    <div className="wizard opt-form">
      <h1>{t('ui.opt_title')}</h1>
      <p className="lead">{t('ui.opt_intro')}</p>

      <section className="step-body">
        <h2>{t('ui.step_place')}</h2>
        <LocationPicker lat={lat} lon={lon} onChange={onLocation} onFeatures={() => {}} />
      </section>

      <section className="step-body">
        <h2>{t('ui.opt_parcels')}</h2>
        {parcels.map((p, i) => (
          <details key={i} className="parcel" open={i === 0}>
            <summary>{names[i]} <span className="muted">· {t('ui.opt_area', { n: p.area_ha || '?' })} · {p.irrigated ? t('ui.opt_irrigated') : t('ui.opt_rainfed')}</span></summary>
            <div className="stack">
              <div className="row">
                <label className="field">
                  <span>{t('ui.opt_name')}</span>
                  <input type="text" value={p.name} maxLength={30} placeholder={t('ui.opt_parcel_n', { n: i + 1 })} onChange={(e) => setParcel(i, { name: e.target.value })} />
                </label>
                <label className="field">
                  <span>{t('ui.opt_area_label')}</span>
                  <input inputMode="decimal" dir="ltr" value={p.area_ha} aria-invalid={!areaOk(p)} onChange={(e) => setParcel(i, { area_ha: e.target.value })} />
                </label>
              </div>
              {!areaOk(p) && <p className="notice notice-error" role="alert">{t('ui.opt_area_error')}</p>}
              <div className="seg" role="group" aria-label={t('ui.opt_water_source')}>
                {[false, true].map((irr) => (
                  <button key={String(irr)} type="button" aria-pressed={p.irrigated === irr} onClick={() => setParcel(i, { irrigated: irr })}>
                    {irr ? t('ui.opt_irrigated') : t('ui.opt_rainfed')}
                  </button>
                ))}
              </div>
              <h4>{t('ui.step_rotation')}</h4>
              <RotationInput seasons={p.seasons} onChange={(seasons) => setParcel(i, { seasons })} />
              {parcels.length > 1 && (
                <button type="button" className="btn btn-text" onClick={() => setParcels(parcels.filter((_, j) => j !== i))}>{t('ui.opt_remove_parcel', { name: names[i] })}</button>
              )}
            </div>
          </details>
        ))}
        {parcels.length < MAX_PARCELS && (
          <button type="button" className="btn btn-quiet" onClick={() => setParcels([...parcels, newParcel()])}>{t('ui.opt_add_parcel')}</button>
        )}
      </section>

      <section className="step-body">
        <h2>{t('ui.step_goals')}</h2>
        <div className="seg profiles" role="group" aria-label={t('ui.opt_profile')}>
          {Object.keys(PROFILES).map((k) => (
            <button key={k} type="button" aria-pressed={profileOf === k} onClick={() => setPriorities(PROFILES[k])}>{t(`ui.opt_profile_${k}`)}</button>
          ))}
        </div>
        <Priorities values={priorities} onChange={setPriorities} />
      </section>

      <details className="coords">
        <summary>{t('ui.opt_limits')}</summary>
        <div className="stack">
          <label className="field">
            <span>{t('ui.opt_water_cap')}</span>
            <input inputMode="decimal" dir="ltr" value={water} onChange={(e) => setWater(e.target.value)} />
            <small className="muted">{t('ui.opt_water_cap_help')}</small>
          </label>
          <label className="field">
            <span>{t('ui.opt_budget')}</span>
            <input inputMode="decimal" dir="ltr" value={budget} onChange={(e) => setBudget(e.target.value)} />
            <small className="muted">{t('ui.opt_budget_help')}</small>
          </label>
        </div>
      </details>

      {state.phase === 'error' && <p className="notice notice-error" role="alert">{t(`err.${state.code}`)}</p>}
      <div className="wizard-nav">
        <button type="button" className="btn btn-primary" disabled={!valid || state.phase === 'loading'} onClick={run}>
          {state.phase === 'loading' ? t('ui.opt_running') : t('ui.opt_run')}
        </button>
      </div>
    </div>
  );
}
