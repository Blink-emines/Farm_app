import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { CROPS } from '../constants.js';
import Priorities from './Priorities.jsx';
import { CropIcon } from './icons.jsx';
import { SOILS, SoilArt, SoilWords } from './FarmSetup.jsx';

const MARKET_CROPS = CROPS.filter((c) => c !== 'fallow');
const NOW_CHOICES = [...MARKET_CROPS, 'fallow']; // 'fallow' = bare field
const PAGES = ['now', 'soil', 'plant', 'goals'];

// "Optimisation" tab, per field: (a) what is on the field now, (b) the soil, (c) what the farmer
// can or wants to plant, then the goal sliders. Each field keeps its own answers (state lives in App).
export default function OptimiseTab({ farm, features, fieldId, onField, st, set, loading, error, onRun, onAllFields }) {
  const { t, crop } = useI18n();
  const chosen = st.crops;
  const all = chosen.length === MARKET_CROPS.length;
  const toggle = (c) => set({ crops: chosen.includes(c) ? chosen.filter((x) => x !== c) : [...chosen, c] });
  const nowName = (c) => (c === 'fallow' ? t('ui.optab_bare') : crop(c));
  const [page, setPage] = useState(0);
  const [missing, setMissing] = useState(false);
  useEffect(() => { setMissing(false); }, [fieldId]); // switching field keeps the page you are on
  const id = PAGES[page];
  const next = () => {
    if (id === 'now' && !st.current) { setMissing(true); return; }
    setMissing(false);
    setPage(page + 1);
    window.scrollTo({ top: 0 });
  };
  const planHint = chosen.length === 0 ? 'ui.optab_plant_none' : chosen.length === 1 ? 'ui.optab_plant_one' : all ? 'ui.optab_plant_all' : 'ui.optab_plant_some';

  return (
    <div className="wizard opt stack">
      <h1>{t('ui.optab_title')}</h1>

      {farm.parcels.length > 1 && (
        <section className="stack" aria-labelledby="opt-field">
          <h2 id="opt-field">{t('ui.opt_field')}</h2>
          <div className="chip-row" role="radiogroup" aria-labelledby="opt-field">
            {farm.parcels.map((p) => (
              <button key={p.id} type="button" role="radio" aria-checked={fieldId === p.id} className="chip" onClick={() => onField(p.id)}>
                {p.name} · {p.area_ha} {t('ui.unit_ha')}
              </button>
            ))}
          </div>
        </section>
      )}

      <nav className="progress" aria-label={t('ui.step_of', { n: page + 1, total: PAGES.length })}>
        <p className="progress-text">{t('ui.step_of', { n: page + 1, total: PAGES.length })}</p>
        <ol style={{ gridTemplateColumns: `repeat(${PAGES.length}, 1fr)` }}>
          {PAGES.map((p, i) => (
            <li key={p} className={i < page ? 'done' : i === page ? 'now' : ''} aria-current={i === page ? 'step' : undefined}>
              <span className="progress-bar" />
              <span className="progress-name">{t(`ui.optab_step_${p}`)}</span>
            </li>
          ))}
        </ol>
      </nav>

      <div className="opt-card">
      {id === 'now' && (
      <section className="stack opt-step" aria-labelledby="opt-now">
        <h2 id="opt-now"><span className="step-n">1</span>{t('ui.optab_now')}</h2>
        <div className="crop-grid" role="radiogroup" aria-labelledby="opt-now">
          {NOW_CHOICES.map((c) => (
            <button key={c} type="button" role="radio" aria-checked={st.current === c} className="crop-card" onClick={() => set({ current: c })}>
              {c === 'fallow' ? <SoilArt id="loam" /> : <CropIcon id={c} size={44} />}
              <span>{nowName(c)}</span>
            </button>
          ))}
        </div>
      </section>
      )}

      {id === 'soil' && (
      <section className="stack opt-step" aria-labelledby="opt-soil">
        <h2 id="opt-soil"><span className="step-n">2</span>{t('ui.optab_soil')}</h2>
        <div className="soil-grid" role="radiogroup" aria-labelledby="opt-soil">
          {SOILS.map((s) => (
            <button key={s} type="button" role="radio" aria-checked={st.soil === s} className="soil-card" onClick={() => set({ soil: s })}>
              <SoilArt id={s} />
              <strong>{t(`ui.soil_${s}`)}</strong>
            </button>
          ))}
        </div>
        {st.soil === 'unknown' && (
          <p className="notice soil-auto" role="status">{t('ui.optab_soil_auto')} <SoilWords soil="unknown" features={features} /></p>
        )}
      </section>
      )}

      {id === 'plant' && (
      <section className="stack opt-step" aria-labelledby="opt-plant">
        <div className="opt-step-head">
          <h2 id="opt-plant"><span className="step-n">3</span>{t('ui.optab_plant')}</h2>
          <button type="button" className="btn btn-quiet" onClick={() => set({ crops: all ? [] : [...MARKET_CROPS] })}>
            {all ? t('ui.optab_clear') : t('ui.optab_select_all')}
          </button>
        </div>
        <div className="crop-grid">
          {MARKET_CROPS.map((c) => (
            <button key={c} type="button" aria-pressed={chosen.includes(c)} className="crop-card" onClick={() => toggle(c)}>
              <CropIcon id={c} size={44} />
              <span>{crop(c)}</span>
            </button>
          ))}
        </div>
        <p className="help" aria-live="polite">{t(planHint, { crop: chosen[0] ?? '' })}</p>
      </section>
      )}

      {id === 'goals' && (
      <section className="stack opt-step" aria-labelledby="opt-goals">
        <h2 id="opt-goals"><span className="step-n">4</span>{t('ui.step_goals')}</h2>
        <Priorities values={st.priorities} onChange={(priorities) => set({ priorities })} />
      </section>
      )}
      </div>

      {missing && <p className="notice notice-error" role="alert">{t('ui.optab_err_now')}</p>}
      {error && <p className="notice notice-error" role="alert">{t(error.startsWith('ui.') ? error : `err.${error}`)}</p>}

      <div className="wizard-nav">
        {page > 0 && <button type="button" className="btn btn-quiet" onClick={() => setPage(page - 1)}>{t('ui.back')}</button>}
        {page < PAGES.length - 1 ? (
          <button type="button" className="btn btn-primary" onClick={next}>{t('ui.next')}</button>
        ) : (
          <button type="button" className="btn btn-primary" disabled={loading} onClick={onRun}>
            {loading ? t('ui.loading') : t('ui.optab_run')}
          </button>
        )}
      </div>
      <button type="button" className="btn-text" onClick={onAllFields}>{t('ui.opt_all_fields')}</button>
    </div>
  );
}
