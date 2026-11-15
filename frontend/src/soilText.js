// Soil in plain words when the farmer answered "I don't know": SoilGrids clay/sand for the
// map point (features.soil, served from the cache or the fallback file by data/), averaged over
// the layers, then a simplified USDA soil texture triangle. Never a measurement of the field.
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;

export function soilFromMap(features) {
  const layers = (features?.soil?.layers ?? []).filter((l) => typeof l.clay_pct === 'number' && typeof l.sand_pct === 'number');
  if (!layers.length) return null;
  const clay = mean(layers.map((l) => l.clay_pct));
  const sand = mean(layers.map((l) => l.sand_pct));
  let kind;
  if (clay >= 40) kind = 'heavy_clay'; // USDA "clay"
  else if (sand >= 70 && clay < 15) kind = 'sandy'; // "sand" / "loamy sand"
  else if (clay >= 27) kind = 'fairly_heavy'; // "clay loam" family
  else if (sand >= 50) kind = 'light'; // "sandy loam"
  else kind = 'medium'; // "loam" / "silt loam"
  return { kind, clay: Math.round(clay), sand: Math.round(sand), regional: features.soil.status === 'fallback' };
}
