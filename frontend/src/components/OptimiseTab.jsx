import { useI18n } from '../i18n/index.jsx';
import { CROPS } from '../constants.js';
import RotationInput from './RotationInput.jsx';
import Priorities from './Priorities.jsx';
import { CropIcon } from './icons.jsx';

const MARKET_CROPS = CROPS.filter((c) => c !== 'fallow');

// "Optimisation" tab: which field, what grows there now, which crops the farmer can get,
// what matters to them. Then "Show my plan".
export default function OptimiseTab({ farm, form, patch, fieldId, onField, loading, error, onRun, onAllFields }) {
  const { t, crop } = useI18n();
  const chosen = form.allowedCrops ?? [];
  const toggle = (c) => patch({ allowedCrops: chosen.includes(c) ? chosen.filter((x) => x !== c) : [...chosen, c] });

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

      <section className="stack" aria-labelledby="opt-now">
        <h2 id="opt-now">{t('ui.step_rotation')}</h2>
        <RotationInput seasons={form.seasons} onChange={(seasons) => patch({ seasons })} />
      </section>

      <section className="stack" aria-labelledby="opt-crops">
        <h2 id="opt-crops">{t('ui.farm_q_crops')}</h2>
        <p className="help">{t('ui.opt_crops_help')}</p>
        <div className="crop-grid">
          {MARKET_CROPS.map((c) => (
            <button key={c} type="button" aria-pressed={chosen.includes(c)} className="crop-card" onClick={() => toggle(c)}>
              <CropIcon id={c} size={44} />
              <span>{crop(c)}</span>
            </button>
          ))}
        </div>
        <p className="help" aria-live="polite">{chosen.length ? t('ui.farm_crops_count', { n: chosen.length }) : t('ui.opt_crops_all')}</p>
      </section>

      <section className="stack" aria-labelledby="opt-goals">
        <h2 id="opt-goals">{t('ui.step_goals')}</h2>
        <Priorities values={form.priorities} onChange={(priorities) => patch({ priorities })} />
      </section>

      {error && <p className="notice notice-error" role="alert">{t(`err.${error}`)}</p>}

      <div className="wizard-nav">
        <button type="button" className="btn btn-primary" disabled={loading} onClick={onRun}>
          {loading ? t('ui.loading') : t('ui.optab_run')}
        </button>
      </div>
      <button type="button" className="btn-text" onClick={onAllFields}>{t('ui.opt_all_fields')}</button>
    </div>
  );
}
