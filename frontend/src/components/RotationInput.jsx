import { useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { CROPS, MAX_SEASONS, NO_MONTHS } from '../constants.js';
import { CropIcon } from './icons.jsx';

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

// One year at a time: pick a crop card; months stay at "typical" unless you open them.
export default function RotationInput({ seasons, onChange }) {
  const { t, crop, month } = useI18n();
  const [active, setActive] = useState(0);
  const idx = Math.min(active, seasons.length - 1);
  const s = seasons[idx];
  const set = (patch) => onChange(seasons.map((x, j) => (j === idx ? { ...x, ...patch } : x)));
  const add = () => {
    onChange([...seasons, { crop_id: 'wheat', sow_month: '', harvest_month: '' }]);
    setActive(seasons.length);
  };
  const remove = () => {
    onChange(seasons.filter((_, j) => j !== idx));
    setActive(Math.max(0, idx - 1));
  };

  return (
    <div className="stack">
      <p className="help">{t('ui.rotation_help')}</p>

      <div className="years" role="tablist" aria-label={t('ui.step_rotation')}>
        {seasons.map((x, i) => (
          <button
            key={i}
            type="button"
            role="tab"
            aria-selected={i === idx}
            className="year-chip"
            onClick={() => setActive(i)}
          >
            <CropIcon id={x.crop_id} size={28} />
            <span><small>{t('ui.season_n', { n: i + 1 })}</small>{crop(x.crop_id)}</span>
          </button>
        ))}
        {seasons.length < MAX_SEASONS && (
          <button type="button" className="year-chip year-add" onClick={add}>
            <span aria-hidden="true" className="plus">+</span>
            <span>{t('ui.add_season')}</span>
          </button>
        )}
      </div>

      <fieldset className="crop-picker">
        <legend>{t('ui.crop_pick', { n: idx + 1 })}</legend>
        <div className="crop-grid" role="radiogroup">
          {CROPS.map((c) => (
            <button
              key={c}
              type="button"
              role="radio"
              aria-checked={s.crop_id === c}
              className="crop-card"
              onClick={() => set({ crop_id: c })}
            >
              <CropIcon id={c} size={44} />
              <span>{crop(c)}</span>
            </button>
          ))}
        </div>
      </fieldset>

      {!NO_MONTHS.includes(s.crop_id) && (
        <details className="months">
          <summary>{t('ui.edit_months')}</summary>
          <div className="row">
            {['sow_month', 'harvest_month'].map((key) => (
              <label className="field" key={key}>
                <span>{t(`ui.${key}`)}</span>
                <select value={s[key]} onChange={(e) => set({ [key]: e.target.value })}>
                  <option value="">{t('ui.typical_months')}</option>
                  {MONTHS.map((m) => <option key={m} value={m}>{month(m)}</option>)}
                </select>
              </label>
            ))}
          </div>
          <p className="help">{t('ui.months_hint')}</p>
        </details>
      )}

      {seasons.length > 1 && (
        <button type="button" className="btn btn-text" onClick={remove}>
          {t('ui.remove_season', { n: idx + 1 })}
        </button>
      )}
    </div>
  );
}
