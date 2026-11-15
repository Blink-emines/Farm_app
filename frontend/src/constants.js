export const BOX = { south: 20.7, north: 35.95, west: -17.2, east: -0.95 };
export const DEFAULT_POINT = { lat: 33.96, lon: -5.27 };
export const CROPS = [
  'wheat', 'barley', 'chickpea', 'lentil', 'faba_bean', 'alfalfa',
  'vetch_oat_cover', 'sunflower', 'potato', 'olive_intercrop', 'fallow',
];
export const GOALS = ['save_water', 'improve_soil', 'extra_income', 'reduce_erosion', 'forage'];
export const MAX_SEASONS = 6;
// Crops whose months the engine fixes itself (12-month slot), so the farmer is not asked.
export const NO_MONTHS = ['fallow', 'alfalfa', 'olive_intercrop'];

export const inBox = (lat, lon) =>
  lat >= BOX.south && lat <= BOX.north && lon >= BOX.west && lon <= BOX.east;

// Build the StrategyRequest. Empty months are left out so the engine fills them.
// form.allowedCrops (optional): crops the farmer can get; empty = no filter.
export function buildRequest(form) {
  const req = {
    latitude: form.lat,
    longitude: form.lon,
    current_rotation: {
      seasons: form.seasons.map((s) => {
        const out = { crop_id: s.crop_id };
        if (NO_MONTHS.includes(s.crop_id)) return out;
        if (s.sow_month) out.sow_month = Number(s.sow_month);
        if (s.harvest_month) out.harvest_month = Number(s.harvest_month);
        return out;
      }),
    },
    priorities: form.priorities,
  };
  if (form.allowedCrops?.length) req.allowed_crops = form.allowedCrops;
  return req;
}

// Slider presets, same as engine/weights.yaml (optimiser.profiles).
export const PROFILES = {
  economic: { save_water: 1, improve_soil: 1, extra_income: 5, reduce_erosion: 0, forage: 1 },
  balanced: { save_water: 3, improve_soil: 3, extra_income: 3, reduce_erosion: 3, forage: 3 },
  ecological: { save_water: 4, improve_soil: 5, extra_income: 1, reduce_erosion: 4, forage: 1 },
};

const num = (v) => Number(String(v).replace(',', '.'));

// Build the OptimizeRequest. parcels[i].id is P1, P2, ... (the name is for display only).
export function buildOptimizeRequest({ lat, lon, parcels, priorities, waterM3, budget }) {
  const body = {
    latitude: lat,
    longitude: lon,
    parcels: parcels.map((p, i) => ({
      id: `P${i + 1}`,
      area_ha: num(p.area_ha),
      irrigated: p.irrigated,
      current_rotation: buildRequest({ lat, lon, seasons: p.seasons, priorities }).current_rotation,
    })),
    pareto_points: 6,
  };
  const preset = Object.entries(PROFILES).find(([, v]) => Object.keys(v).every((k) => v[k] === priorities[k]));
  if (preset) body.profile = preset[0]; else body.priorities = priorities;
  if (String(waterM3).trim() !== '' && num(waterM3) >= 0) body.water = { monthly_irrigation_m3: Array(12).fill(num(waterM3)) };
  if (String(budget).trim() !== '' && num(budget) >= 0) body.budget_mad = num(budget);
  return body;
}
