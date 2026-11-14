import { useI18n } from '../i18n/index.jsx';
import { whole } from '../util.js';

// Colour of a layer from its texture (sand, silt, clay mixed), darkened by organic carbon.
const BASE = { sand: [227, 201, 143], silt: [190, 176, 146], clay: [156, 96, 64] };
function layerColour(l) {
  const w = { sand: l.sand_pct ?? 0, silt: l.silt_pct ?? 0, clay: l.clay_pct ?? 0 };
  const total = w.sand + w.silt + w.clay || 1;
  const dark = 1 - Math.min((l.soc_g_kg ?? 0) / 80, 0.4);
  const c = [0, 1, 2].map((i) => Math.round((Object.keys(BASE).reduce((s, k) => s + BASE[k][i] * w[k], 0) / total) * dark));
  return `rgb(${c.join(',')})`;
}

function depthOf(label) {
  const m = /^(\d+)-(\d+)/.exec(label ?? '');
  return m ? [Number(m[1]), Number(m[2])] : null;
}

const val = (v, digits = 0) => (v == null ? '–' : digits ? v.toFixed(digits) : String(whole(v)));

export default function SoilProfile({ features }) {
  const { t } = useI18n();
  const layers = (features?.soil?.layers ?? []).filter((l) => depthOf(l.depth));
  return (
    <section className="panel" aria-labelledby="soil-h">
      <h3 id="soil-h">{t('ui.soil_title')}</h3>
      <p className="notice notice-error" role="note">{t('ui.soil_warning')}</p>
      {features?.soil?.status === 'fallback' && <p className="notice">{t('ui.soil_fallback')}</p>}
      {layers.length === 0 ? <p>{t('ui.soil_none')}</p> : (
        <>
          <ol className="soil">
            {layers.map((l) => {
              const [a, b] = depthOf(l.depth);
              const parts = [['clay', l.clay_pct], ['sand', l.sand_pct], ['silt', l.silt_pct]];
              return (
                <li key={l.depth} style={{ minBlockSize: `${Math.max((b - a) * 8, 112)}px` }}>
                  <span className="soil-block" style={{ background: layerColour(l) }} aria-hidden="true">
                    <span>{t('ui.depth_range', { a, b })}</span>
                  </span>
                  <div className="soil-data">
                    <h4>{t('ui.depth_range', { a, b })}</h4>
                    <div className="texture" role="img" aria-label={parts.map(([k, v]) => `${t(`ui.${k}`)} ${val(v)}%`).join(', ')}>
                      {parts.map(([k, v]) => <span key={k} className={`tex tex-${k}`} style={{ inlineSize: `${v ?? 0}%` }} />)}
                    </div>
                    <ul className="soil-facts">
                      {parts.map(([k, v]) => <li key={k}><i className={`sw tex-${k}`} />{t(`ui.${k}`)} <strong>{val(v)}%</strong></li>)}
                      <li>{t('ui.soc')} <strong>{val(l.soc_g_kg, 1)}</strong> {t('ui.unit_gkg')}</li>
                      <li>{t('ui.ph')} <strong>{val(l.ph_h2o, 1)}</strong></li>
                    </ul>
                  </div>
                </li>
              );
            })}
          </ol>
          <p className="muted">{t('ui.soil_key')}</p>
        </>
      )}
    </section>
  );
}
