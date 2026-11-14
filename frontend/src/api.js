// Real endpoints by default. Mock files are used only when the dev server is
// started with VITE_USE_MOCK=1 (see MockBanner). Never offered to the user.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === '1';

export class ApiError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

async function request(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new ApiError('network');
  }
  let body = null;
  try {
    body = await res.json();
  } catch { /* not JSON */ }
  if (!res.ok) throw new ApiError(body?.error?.code ?? 'internal_error');
  return body;
}

// Dev only: until the real pipeline returns yearly and vegetation, ?mockextras=1 (or VITE_USE_MOCK=1)
// adds synthetic ones, flagged with _mockExtras so the app shows the MOCK DATA banner.
// In a production build this whole branch is removed.
const EXTRAS = import.meta.env.DEV && (USE_MOCK || new URLSearchParams(window.location.search).has('mockextras'));

async function withExtras(features) {
  if (!EXTRAS || (features.yearly && features.vegetation)) return features;
  const x = (await import('./mock/mockExtras.json')).default;
  return { ...features, yearly: features.yearly ?? x.yearly, vegetation: features.vegetation ?? x.vegetation, _mockExtras: true };
}

export async function getFeatures(lat, lon) {
  if (USE_MOCK) return withExtras((await import('./mock/mockFeatures.json')).default);
  return withExtras(await request(`/api/features?lat=${lat}&lon=${lon}`));
}

export async function getStrategies(requestBody) {
  if (USE_MOCK) return (await import('./mock/mockStrategies.json')).default;
  return request('/api/strategies', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  });
}
