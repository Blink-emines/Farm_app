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

export async function optimize(requestBody) {
  if (USE_MOCK) return (await import('./mock/mockOptimize.json')).default;
  return request('/api/optimize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  });
}

// ---------- accounts: login, sign up, saved plans ----------
// The login tokens stay in this browser (localStorage) so a reload keeps the farmer signed in.
const TOKENS = 'auth';
function readTokens() {
  try { return JSON.parse(localStorage.getItem(TOKENS)); } catch { return null; }
}
function writeTokens(tokens) {
  try {
    if (tokens) localStorage.setItem(TOKENS, JSON.stringify(tokens));
    else localStorage.removeItem(TOKENS);
  } catch { /* storage blocked: the login lasts for this page only */ }
}

// Mock mode has no backend, so there is nothing to log in to.
export const isLoggedIn = () => USE_MOCK || Boolean(readTokens()?.access);
export const logout = () => writeTokens(null);

async function send(url, { method = 'GET', body, access } = {}) {
  try {
    return await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('network');
  }
}

// identifier: a username or an email address.
export async function login(identifier, password) {
  const res = await send('/api/token/', { method: 'POST', body: { username: identifier, password } });
  if (res.status === 401) throw new ApiError('bad_login');
  if (!res.ok) throw new ApiError('internal_error');
  const { access, refresh } = await res.json();
  writeTokens({ access, refresh });
}

// On a refused sign-up, err.fields lists which fields were wrong (username, email, password).
export async function register(username, email, password) {
  const res = await send('/api/register/', { method: 'POST', body: { username, email, password } });
  if (res.status === 400) {
    const err = new ApiError('invalid_signup');
    err.fields = Object.keys(await res.json().catch(() => ({})));
    throw err;
  }
  if (!res.ok) throw new ApiError('internal_error');
  await login(username, password);
}

// Calls an endpoint as the logged-in user. Renews the short-lived access token once if needed.
async function authed(url, options = {}) {
  const tokens = readTokens();
  if (!tokens) throw new ApiError('auth');
  let res = await send(url, { ...options, access: tokens.access });
  if (res.status === 401) {
    const renew = await send('/api/token/refresh/', { method: 'POST', body: { refresh: tokens.refresh } });
    if (!renew.ok) { writeTokens(null); throw new ApiError('auth'); }
    const { access } = await renew.json();
    writeTokens({ ...tokens, access });
    res = await send(url, { ...options, access });
  }
  if (!res.ok) throw new ApiError('internal_error');
  return res.json();
}

// Saves the field location (reused if already saved) and the plan the farmer just received.
export async function savePlan(lat, lon, plan) {
  if (USE_MOCK) return null;
  const fields = await authed('/api/fields/');
  const field = fields.find((f) => f.latitude === lat && f.longitude === lon)
    ?? await authed('/api/fields/', { method: 'POST', body: { name: `${lat.toFixed(4)}, ${lon.toFixed(4)}`, latitude: lat, longitude: lon } });
  return authed('/api/results/', { method: 'POST', body: { field: field.id, data: plan } });
}
