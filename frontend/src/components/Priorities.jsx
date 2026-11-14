import { useI18n } from '../i18n/index.jsx';
import { GOALS } from '../constants.js';
import { GoalIcon } from './icons.jsx';

export default function Priorities({ values, onChange }) {
  const { t } = useI18n();
  return (
    <div className="stack">
      <p className="help">{t('ui.goals_help')}</p>
      <ul className="goals">
        {GOALS.map((g) => (
          <li className="goal" key={g}>
            <GoalIcon id={g} size={44} />
            <div className="goal-main">
              <label htmlFor={`goal-${g}`}>{t(`ui.goal_${g}`)}</label>
              <output htmlFor={`goal-${g}`} className="level">{t(`ui.lvl_${values[g]}`)}</output>
              <input
                id={`goal-${g}`}
                type="range"
                min="0"
                max="5"
                step="1"
                value={values[g]}
                style={{ '--pct': `${values[g] * 20}%` }}
                aria-valuetext={t(`ui.lvl_${values[g]}`)}
                onChange={(e) => onChange({ ...values, [g]: Number(e.target.value) })}
              />
              <span className="ticks" aria-hidden="true">{[0, 1, 2, 3, 4, 5].map((n) => <i key={n} className={n <= values[g] ? 'on' : ''} />)}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
