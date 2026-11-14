import { useRef, useState } from 'react';
import { LANGS, useI18n } from './i18n/index.jsx';
import SettingsPanel, { GearButton } from './components/SettingsPanel.jsx';
import { ApiError, USE_MOCK, getStrategies } from './api.js';
import { DEFAULT_POINT, buildRequest } from './constants.js';
import LocationPicker from './components/LocationPicker.jsx';
import RotationInput from './components/RotationInput.jsx';
import Priorities from './components/Priorities.jsx';
import Results from './components/Results.jsx';
import OptimiserFlow from './components/OptimiserFlow.jsx';
import Landing from './components/Landing.jsx';
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
};

const STEPS = [1, 2, 3];

function Progress({ step }) {
  const { t } = useI18n();
  return (
    <nav className="progress" aria-label={t('ui.step_of', { n: step, total: 3 })}>
      <p className="progress-text">{t('ui.step_of', { n: step, total: 3 })}</p>
      <ol>
        {STEPS.map((n) => (
          <li key={n} className={n < step ? 'done' : n === step ? 'now' : ''} aria-current={n === step ? 'step' : undefined}>
            <span className="progress-bar" />
            <span className="progress-name">{t(`ui.step_name_${n}`)}</span>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export default function App() {
  const { t, gap, lang, setLang } = useI18n();
  const [form, setForm] = useState(initial);
  const [features, setFeatures] = useState(null);
  const [step, setStep] = useState(1);
  const [started, setStarted] = useState(false);
  const [mode, setMode] = useState('single');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [status, setStatus] = useState({ state: 'idle' });
  const topRef = useRef(null);
  const patch = (p) => setForm((f) => ({ ...f, ...p }));
  const go = (n) => {
    setStep(n);
    topRef.current?.scrollIntoView({ block: 'start' });
  };

  async function compare() {
    setStatus({ state: 'loading' });
    try {
      const data = await getStrategies(buildRequest(form));
      setStatus({ state: 'done', data, features });
      setTimeout(() => topRef.current?.scrollIntoView({ block: 'start' }), 0);
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
      </div>
    </header>
  );
  const gaps = features?.data_gaps ?? [];
  const showResults = status.state === 'done';

  return (
    <>
      <div className="screen-only">
        {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
        {(USE_MOCK || features?._mockExtras) && <div className="mock-banner" role="alert">{t('ui.mock_banner')}</div>}
        {!started ? (
          <Landing head={head} onStart={() => setStarted(true)} />
        ) : (
        <>
        {head}
        <nav className="modes" aria-label={t('ui.mode_label')}>
          {['single', 'optimiser'].map((m) => (
            <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)}>{t(`ui.mode_${m}`)}</button>
          ))}
        </nav>
        <main>
          {mode === 'optimiser' && (
            <OptimiserFlow lat={form.lat} lon={form.lon} onLocation={(lat, lon) => patch({ lat, lon })} />
          )}
          {mode === 'single' && !showResults && (
            <div className="wizard">
              <h1>{t('ui.title')}</h1>
              <Progress step={step} />

              {step === 1 && (
                <section className="step-body" aria-labelledby="step-h">
                  <h2 id="step-h">{t('ui.step_place')}</h2>
                  <LocationPicker lat={form.lat} lon={form.lon} onChange={(lat, lon) => patch({ lat, lon })} onFeatures={setFeatures}>
                    {gaps.length > 0 && (
                      <details className="limits" open={gaps.some((g) => g.code.startsWith('soil_'))}>
                        <summary>{t('ui.data_gaps')} ({gaps.length})</summary>
                        <ul>{gaps.map((g) => <li key={g.code}>{gap(g)}</li>)}</ul>
                      </details>
                    )}
                  </LocationPicker>
                </section>
              )}
              {step === 2 && (
                <section className="step-body" aria-labelledby="step-h">
                  <h2 id="step-h">{t('ui.step_rotation')}</h2>
                  <RotationInput seasons={form.seasons} onChange={(seasons) => patch({ seasons })} />
                </section>
              )}
              {step === 3 && (
                <section className="step-body" aria-labelledby="step-h">
                  <h2 id="step-h">{t('ui.step_goals')}</h2>
                  <Priorities values={form.priorities} onChange={(priorities) => patch({ priorities })} />
                </section>
              )}

              {status.state === 'error' && <p className="notice notice-error" role="alert">{t(`err.${status.code}`)}</p>}

              <div className="wizard-nav">
                {step > 1 && <button type="button" className="btn btn-quiet" onClick={() => go(step - 1)}>{t('ui.back')}</button>}
                {step < 3 ? (
                  <button type="button" className="btn btn-primary" onClick={() => go(step + 1)}>{t('ui.next')}</button>
                ) : (
                  <button type="button" className="btn btn-primary" disabled={status.state === 'loading'} onClick={compare}>
                    {status.state === 'loading' ? t('ui.loading') : t('ui.compare')}
                  </button>
                )}
              </div>
            </div>
          )}

          {mode === 'single' && showResults && (
            <section className="results-wrap" aria-labelledby="results-h">
              <div className="results-head">
                <h2 id="results-h">{t('ui.results_title')}</h2>
                <button type="button" className="btn btn-quiet" onClick={() => { setStatus({ state: 'idle' }); go(1); }}>
                  {t('ui.change_answers')}
                </button>
              </div>
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
