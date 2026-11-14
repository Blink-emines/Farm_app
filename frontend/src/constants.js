export const BOX = { south: 33.7, north: 34.2, west: -5.7, east: -4.7 };
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
export function buildRequest(form) {
  return {
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
}
