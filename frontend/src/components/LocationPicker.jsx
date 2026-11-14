import { useEffect, useState } from 'react';
import L from 'leaflet';
import { MapContainer, Marker, useMapEvents } from 'react-leaflet';
import { SatelliteTiles, StreetTiles } from './tiles.jsx';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { useI18n } from '../i18n/index.jsx';
import { BOX, inBox } from '../constants.js';
import { getFeatures } from '../api.js';
import { PinIcon } from './icons.jsx';

const icon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});
const bounds = [[BOX.south, BOX.west], [BOX.north, BOX.east]];

function ClickToPick({ onPick }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) });
  return null;
}

export default function LocationPicker({ lat, lon, onChange, onFeatures, children }) {
  const { t } = useI18n();
  const [latText, setLatText] = useState(String(lat));
  const [lonText, setLonText] = useState(String(lon));
  const [problem, setProblem] = useState(null);
  const [check, setCheck] = useState({ state: 'loading' });
  const [layer, setLayer] = useState('sat');

  useEffect(() => {
    setLatText(String(lat));
    setLonText(String(lon));
  }, [lat, lon]);

  // Ask the server about the chosen point: elevation and data limits.
  useEffect(() => {
    let stale = false;
    setCheck({ state: 'loading' });
    getFeatures(lat, lon)
      .then((f) => { if (!stale) { setCheck({ state: 'ok', features: f }); onFeatures(f); } })
      .catch((e) => { if (!stale) { setCheck({ state: 'error', code: e.code }); onFeatures(null); } });
    return () => { stale = true; };
  }, [lat, lon]); // eslint-disable-line react-hooks/exhaustive-deps

  const pick = (la, lo) => {
    const r = (x) => Math.round(x * 100) / 100;
    setProblem(null);
    onChange(r(la), r(lo));
  };

  const useTyped = (e) => {
    e.preventDefault();
    const la = Number(latText.replace(',', '.'));
    const lo = Number(lonText.replace(',', '.'));
    if (!latText.trim() || !lonText.trim() || !Number.isFinite(la) || !Number.isFinite(lo)) {
      setProblem('ui.coords_invalid');
    } else if (!inBox(la, lo)) {
      setProblem('ui.coords_outside');
    } else {
      pick(la, lo);
    }
  };

  const elevation = check.state === 'ok' ? check.features.location?.elevation_m : null;

  return (
    <div className="where">
      <div className="map-hero">
        <div className="map" role="application" aria-label={t('ui.map_label')}>
          <MapContainer
            bounds={bounds}
            maxBounds={bounds}
            maxBoundsViscosity={1}
            minZoom={9}
            maxZoom={17}
            center={[lat, lon]}
            zoom={12}
            style={{ height: '100%', width: '100%' }}
          >
            {layer === 'sat' ? <SatelliteTiles key="sat" /> : <StreetTiles key="osm" />}
            <ClickToPick onPick={pick} />
            <Marker position={[lat, lon]} icon={icon} />
          </MapContainer>
        </div>
        <div className="layer-toggle" role="group" aria-label={t('ui.map_layer')}>
          {[['sat', 'ui.map_satellite'], ['osm', 'ui.map_streets']].map(([id, key]) => (
            <button key={id} type="button" aria-pressed={layer === id} onClick={() => setLayer(id)}>{t(key)}</button>
          ))}
        </div>
        <p className="map-tap">{t('ui.map_tap')}</p>
      </div>

      <div className="where-panel">
        <div className="point-card" aria-live="polite">
          <span className="point-pin"><PinIcon /></span>
          <div>
            <strong>{t('ui.chosen_point')}</strong>
            <bdi dir="ltr" className="coords-text">{lat}, {lon}</bdi>
            <span className="muted">
              {check.state === 'loading' && t('ui.checking_place')}
              {elevation != null && t('ui.elevation', { value: Math.round(elevation) })}
            </span>
          </div>
        </div>
        {check.state === 'error' && <p className="notice notice-error" role="alert">{t(`err.${check.code}`)}</p>}

        <details className="coords">
          <summary>{t('ui.write_coords')}</summary>
          <form onSubmit={useTyped} noValidate className="stack">
            <div className="row">
              <label className="field">
                <span>{t('ui.latitude')}</span>
                <input inputMode="decimal" dir="ltr" value={latText} onChange={(e) => setLatText(e.target.value)} />
              </label>
              <label className="field">
                <span>{t('ui.longitude')}</span>
                <input inputMode="decimal" dir="ltr" value={lonText} onChange={(e) => setLonText(e.target.value)} />
              </label>
            </div>
            {problem && <p className="notice notice-error" role="alert">{t(problem)}</p>}
            <button type="submit" className="btn btn-quiet">{t('ui.use_coords')}</button>
          </form>
        </details>
        {children}
      </div>
    </div>
  );
}
