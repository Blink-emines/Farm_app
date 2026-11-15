import L from 'leaflet';
import { MapContainer, Marker } from 'react-leaflet';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { useI18n } from '../i18n/index.jsx';
import { SatelliteTiles } from './tiles.jsx';
import { CropIcon } from './icons.jsx';
import { SoilArt } from './FarmSetup.jsx';

const icon = L.icon({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow, iconSize: [25, 41], iconAnchor: [12, 41] });
const total = (xs) => xs.reduce((a, b) => a + b, 0);
const known = (xs) => Array.isArray(xs) && xs.length === 12 && xs.every((v) => typeof v === 'number');

// Simple indicators from GET /api/features for the farm's point. Nothing is invented: a missing
// series shows "unknown".
function indicators(features) {
  const m = features?.climate?.monthly;
  const rain = m?.precipitation?.values;
  const balance = m?.water_balance?.values;
  const frost = m?.frost_days?.values;
  return [
    { id: 'rain', value: known(rain) ? Math.round(total(rain)) : null, unit: 'mm' },
    { id: 'dry', value: known(balance) ? balance.filter((v) => v < 0).length : null, unit: '' },
    { id: 'frost', value: known(frost) ? Math.round(total(frost)) : null, unit: '' },
    { id: 'alt', value: features?.location?.elevation_m != null ? Math.round(features.location.elevation_m) : null, unit: 'm' },
  ];
}

// "My farm" tab: where the farm is, its fields, soil and crops, and a few plain indicators.
export default function Dashboard({ farm, features, onOptimise }) {
  const { t, crop } = useI18n();
  const area = Math.round(total(farm.parcels.map((p) => p.area_ha ?? 0)) * 100) / 100;
  const period = features?.climate?.period;

  return (
    <div className="dash stack">
      <header className="dash-head">
        <h1>{farm.name}</h1>
        <p className="lead">{t('ui.dash_summary', { n: farm.parcels.length, ha: area })}</p>
      </header>

      <div className="dash-grid">
        <section className="dash-card dash-map" aria-labelledby="dash-place">
          <h2 id="dash-place">{t('ui.dash_place')}</h2>
          <div className="dash-map-box" aria-hidden="true">
            <MapContainer center={[farm.latitude, farm.longitude]} zoom={14} zoomControl={false} dragging={false} scrollWheelZoom={false} doubleClickZoom={false} touchZoom={false} keyboard={false} style={{ height: '100%', width: '100%' }}>
              <SatelliteTiles />
              <Marker position={[farm.latitude, farm.longitude]} icon={icon} />
            </MapContainer>
          </div>
          <bdi dir="ltr" className="muted">{farm.latitude}, {farm.longitude}</bdi>
        </section>

        <section className="dash-card" aria-labelledby="dash-fields">
          <h2 id="dash-fields">{t('ui.dash_fields')}</h2>
          <ul className="dash-fields">
            {farm.parcels.map((p) => (
              <li key={p.id}><span>{p.name}</span><b>{p.area_ha} {t('ui.unit_ha')}</b></li>
            ))}
          </ul>
        </section>

        <section className="dash-card dash-soil" aria-labelledby="dash-soil">
          <h2 id="dash-soil">{t('ui.dash_soil')}</h2>
          <SoilArt id={farm.soil_type} />
          <p><strong>{t(`ui.soil_${farm.soil_type}`)}</strong></p>
        </section>

        <section className="dash-card" aria-labelledby="dash-crops">
          <h2 id="dash-crops">{t('ui.dash_crops')}</h2>
          {farm.crops?.length ? (
            <ul className="dash-crops">
              {farm.crops.map((c) => <li key={c}><CropIcon id={c} size={36} /><span>{crop(c)}</span></li>)}
            </ul>
          ) : (
            <p className="help">{t('ui.dash_crops_none')}</p>
          )}
        </section>
      </div>

      <section className="dash-card" aria-labelledby="dash-ind">
        <h2 id="dash-ind">{t('ui.dash_indicators')}</h2>
        {features ? (
          <>
            <ul className="dash-ind">
              {indicators(features).map((x) => (
                <li key={x.id}>
                  <b>{x.value == null ? t('ui.dash_unknown') : `${x.value}${x.unit ? ` ${x.unit}` : ''}`}</b>
                  <span>{t(`ui.dash_ind_${x.id}`)}</span>
                </li>
              ))}
            </ul>
            {period && <p className="muted">{t('ui.dash_source', { start: period.start_year, end: period.end_year })}</p>}
          </>
        ) : <p className="help" role="status">{t('ui.checking_place')}</p>}
      </section>

      <button type="button" className="btn btn-primary btn-big dash-cta" onClick={onOptimise}>{t('ui.dash_cta')}</button>
    </div>
  );
}
