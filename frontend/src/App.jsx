import { useEffect, useRef, useState } from 'react';
import { LANGS, useI18n } from './i18n/index.jsx';
import SettingsPanel, { GearButton } from './components/SettingsPanel.jsx';
import { ApiError, USE_MOCK, getFarms, getFeatures, getStrategies, isLoggedIn, logout, savePlan, updateFarm } from './api.js';
import { DEFAULT_POINT, buildRequest } from './constants.js';
import Results from './components/Results.jsx';
import OptimiserFlow from './components/OptimiserFlow.jsx';
import Landing from './components/Landing.jsx';
import Auth from './components/Auth.jsx';
import FarmSetup from './components/FarmSetup.jsx';
import Dashboard from './components/Dashboard.jsx';
import OptimiseTab from './components/OptimiseTab.jsx';
import PrintReport from './components/PrintReport.jsx';
import { BrandMark } from './components/icons.jsx';

const initial = {
  lat: DEFAULT_POINT.lat,
  lon: DEFAULT_POINT.lon,
  seasons: [
    { crop_id: 'wheat', sow_month: '', harvest_month: '' },
    { crop_id: 'fallow', sow_month: '', harvest_month: '' },
  ],
  priorities: { save_water: 3, improve_soil: 3, extra_income: 3, reduce_erosion: 3, forage: 3 },
  allowedCrops: [],
};

const VIEWS = ['farm', 'optimise'];

export default function App() {
  const { t, lang, setLang } = useI18n();
  const [form, setForm] = useState(initial);
  const [features, setFeatures] = useState(null);
  const [started, setStarted] = useState(false);
  const [authed, setAuthed] = useState(isLoggedIn);
  const [saved, setSaved] = useState('');
  // undefined: not loaded yet, null: no farm yet (show the setup wizard), 'error': could not load.
  const [farm, setFarm] = useState(undefined);
  const [farmTry, setFarmTry] = useState(0);
  const [view, setView] = useState('farm');
  const [fieldId, setFieldId] = useState(null);
  const [allFields, setAllFields] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [status, setStatus] = useState({ state: 'idle' });
  const topRef = useRef(null);
  const patch = (p) => setForm((f) => ({ ...f, ...p }));
  const toTop = () => topRef.current?.scrollIntoView({ block: 'start' });

  // Put a loaded or new farm in place: its point, its first field, its crops.
  const applyFarm = (f) => {
    setFarm(f);
    if (!f) return;
    setForm((cur) => ({ ...cur, lat: f.latitude, lon: f.longitude, allowedCrops: f.crops ?? [] }));
    setFieldId(f.parcels?.[0]?.id ?? null);
  };

  // After login, look for the user's farm. Without one, the farm setup wizard comes first.
  useEffect(() => {
    if (!started || !authed) return undefined;
    let stale = false;
    setFarm(undefined);
    getFarms().then(
      (farms) => { if (!stale) applyFarm(farms[0] ?? null); },
      (err) => { if (stale) return; if (err.code === 'auth') setAuthed(false); else setFarm('error'); },
    );
    return () => { stale = true; };
  }, [started, authed, farmTry]); // eslint-disable-line react-hooks/exhaustive-deps

  // Climate and soil for the farm's point (dashboard indicators and result pictures).
  useEffect(() => {
    if (!farm || farm === 'error') return undefined;
    let stale = false;
    setFeatures(null);
    getFeatures(farm.latitude, farm.longitude).then((f) => { if (!stale) setFeatures(f); }, () => {});
    return () => { stale = true; };
  }, [farm]);

  async function compare() {
    setStatus({ state: 'loading' });
    setSaved('');
    try {
      const request = buildRequest(form);
      const data = await getStrategies(request);
      setStatus({ state: 'done', data, features });
      setTimeout(toTop, 0);
      // Remember the crops the farmer can get, and keep the plan in their account.
      // A failed save never hides the results.
      if (JSON.stringify(form.allowedCrops) !== JSON.stringify(farm.crops ?? [])) {
        updateFarm(farm.id, { crops: form.allowedCrops }).then(() => setFarm((f) => ({ ...f, crops: form.allowedCrops })), () => {});
      }
      savePlan(form.lat, form.lon, { request, strategies: data }, fieldId)
        .then((r) => setSaved(r ? 'ok' : ''), () => setSaved('fail'));
    } catch (err) {
      setStatus({ state: 'error', code: err instanceof ApiError ? err.code : 'internal_error' });
    }
  }

  const head = (
    <header className="app-head" ref={topRef}>
      <span className="brand"><BrandMark />{t('ui.brand')}</span>
      <div className="head-actions">
        <div className="lang" role="group" aria-label={t('ui.language')}>
          {LANGS.map((l) => (
            <button key={l.id} type="button" lang={l.id} aria-label={l.label} aria-pressed={lang === l.id} onClick={() => setLang(l.id)}>
              {l.short}
            </button>
          ))}
        </div>
        <GearButton onClick={() => setSettingsOpen(true)} />
        {started && authed && !USE_MOCK && (
          <button type="button" className="btn-text head-logout" onClick={() => { logout(); setAuthed(false); setStatus({ state: 'idle' }); setView('farm'); }}>
            {t('ui.auth_logout')}
          </button>
        )}
      </div>
    </header>
  );
  const showResults = status.state === 'done';

  return (
    <>
      <div className="screen-only">
        {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
        {(USE_MOCK || features?._mockExtras) && <div className="mock-banner" role="alert">{t('ui.mock_banner')}</div>}
        {!started ? (
          <Landing head={head} onStart={() => setStarted(true)} />
        ) : !authed ? (
          <Auth head={head} onDone={() => setAuthed(true)} onBack={() => setStarted(false)} />
        ) : farm === undefined || farm === 'error' ? (
          <>
            {head}
            <main className="wizard">
              {farm === 'error' ? (
                <>
                  <p className="notice notice-error" role="alert">{t('ui.farm_load_error')}</p>
                  <button type="button" className="btn btn-primary" onClick={() => setFarmTry((n) => n + 1)}>{t('ui.retry')}</button>
                </>
              ) : <p className="help" role="status">{t('ui.farm_loading')}</p>}
            </main>
          </>
        ) : farm === null ? (
          <FarmSetup head={head} onDone={applyFarm} />
        ) : (
        <>
        {head}
        <nav className="modes" role="tablist" aria-label={t('ui.views_label')}>
          {VIEWS.map((v) => (
            <button key={v} type="button" role="tab" aria-selected={view === v} aria-pressed={view === v} onClick={() => { setView(v); setAllFields(false); }}>{t(`ui.view_${v}`)}</button>
          ))}
        </nav>
        <main>
          {view === 'farm' && <Dashboard farm={farm} features={features} onOptimise={() => { setView('optimise'); toTop(); }} />}
          {view === 'optimise' && allFields && (
            <>
              <button type="button" className="btn-text" onClick={() => setAllFields(false)}>{t('ui.back')}</button>
              <OptimiserFlow lat={form.lat} lon={form.lon} onLocation={(lat, lon) => patch({ lat, lon })} />
            </>
          )}
          {view === 'optimise' && !allFields && !showResults && (
            <OptimiseTab
              farm={farm} form={form} patch={patch} fieldId={fieldId} onField={setFieldId}
              loading={status.state === 'loading'} error={status.state === 'error' ? status.code : null}
              onRun={compare} onAllFields={() => setAllFields(true)}
            />
          )}
          {view === 'optimise' && !allFields && showResults && (
            <section className="results-wrap" aria-labelledby="results-h">
              <div className="results-head">
                <h2 id="results-h">{t('ui.results_title')}</h2>
                <button type="button" className="btn btn-quiet" onClick={() => { setStatus({ state: 'idle' }); toTop(); }}>
                  {t('ui.change_answers')}
                </button>
              </div>
              {saved && <p className={`notice${saved === 'fail' ? ' notice-error' : ''}`} role="status">{t(saved === 'ok' ? 'ui.auth_saved' : 'ui.auth_save_failed')}</p>}
              <Results data={status.data} features={status.features} form={form} onPrint={() => window.print()} />
            </section>
          )}
        </main>
        <footer className="app-foot"><p>{t('ui.talk_expert')}</p></footer>
        </>
        )}
      </div>
      {showResults && (
        <div className="print-only"><PrintReport form={form} data={status.data} features={status.features} /></div>
      )}
    </>
  );
}
