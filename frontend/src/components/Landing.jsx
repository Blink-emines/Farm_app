import { useEffect, useState } from 'react';
import { MapContainer, useMap } from 'react-leaflet';
import { useI18n } from '../i18n/index.jsx';
import { DEFAULT_POINT, buildRequest } from '../constants.js';
import { getFeatures, getStrategies } from '../api.js';
import { monthsPerYear, useTween, whole } from '../util.js';
import { SatelliteTiles } from './tiles.jsx';

const START = [34.1, -5.0];
const TARGET = [DEFAULT_POINT.lat, DEFAULT_POINT.lon];

// The camera starts wide over the Saïss and glides down onto the default point.
function Glide() {
  const map = useMap();
  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) { map.setView(TARGET, 12, { animate: false }); return undefined; }
    const id = setTimeout(() => map.flyTo(TARGET, 12, { duration: 7 }), 500);
    return () => clearTimeout(id);
  }, [map]);
  return null;
}

function Counter({ value, suffix = '' }) {
  const v = useTween(value, 1400);
  return <>{Math.round(v ?? 0)}{suffix}</>;
}

// The three numbers come from the real climate for the default point and from the engine
// run for wheat then fallow. Nothing here is typed in by hand.
function useProblem() {
  const [facts, setFacts] = useState(null);
  useEffect(() => {
    let stale = false;
    const request = buildRequest({
      lat: DEFAULT_POINT.lat,
      lon: DEFAULT_POINT.lon,
      seasons: [{ crop_id: 'wheat' }, { crop_id: 'fallow' }],
      priorities: { save_water: 3, improve_soil: 3, extra_income: 3, reduce_erosion: 3, forage: 3 },
    });
    Promise.allSettled([getFeatures(DEFAULT_POINT.lat, DEFAULT_POINT.lon), getStrategies(request)]).then(([f, s]) => {
      if (stale) return;
      const out = {};
      const m = f.status === 'fulfilled' ? f.value.climate.monthly : null;
      if (m) {
        const rain = m.precipitation.values;
        const et0 = m.et0.values;
        out.dry = rain.filter((r, i) => r < et0[i]).length;
        const heat = m.heat_days['35'].values;
        const hottest = heat.indexOf(Math.max(...heat));
        out.heat = Math.round(heat[hottest]);
        out.heatMonth = hottest + 1;
      }
      if (s.status === 'fulfilled') {
        const current = s.value.strategies.find((x) => x.is_current);
        if (current) out.bare = Math.round(monthsPerYear(current, 'bare'));
      }
      setFacts(out);
    });
    return () => { stale = true; };
  }, []);
  return facts;
}

export default function Landing({ head, onStart }) {
  const { t, month } = useI18n();
  const facts = useProblem();
  const cards = facts && [
    facts.bare != null && { n: facts.bare, text: t('ui.fact_bare') },
    facts.dry != null && { n: facts.dry, text: t('ui.fact_dry') },
    facts.heat != null && { n: facts.heat, text: t('ui.fact_heat', { month: facts.heatMonth }) },
  ].filter(Boolean);

  return (
    <div className="landing">
      <div className="landing-map" aria-hidden="true">
        <MapContainer center={START} zoom={9} zoomControl={false} dragging={false} scrollWheelZoom={false} doubleClickZoom={false} touchZoom={false} keyboard={false} attributionControl style={{ height: '100%', width: '100%' }}>
          <SatelliteTiles />
          <Glide />
        </MapContainer>
      </div>
      <div className="landing-scrim" />
      {head}
      <div className="landing-copy">
        <h1>{t('ui.title')}</h1>
        <p className="landing-sub">{t('ui.landing_sub')}</p>
        {cards && cards.length > 0 && (
          <section aria-labelledby="problem-h" className="problem">
            <h2 id="problem-h">{t('ui.problem_title')}</h2>
            <ul>
              {cards.map((c, i) => (
                <li key={i}>
                  <strong><Counter value={c.n} /></strong>
                  <span>{c.text}</span>
                </li>
              ))}
            </ul>
            <p className="problem-source">
              {t('ui.problem_source', { lat: DEFAULT_POINT.lat, lon: DEFAULT_POINT.lon })}
            </p>
          </section>
        )}
        <button type="button" className="btn btn-primary landing-cta" onClick={onStart}>{t('ui.analyse')}</button>
      </div>
    </div>
  );
}
