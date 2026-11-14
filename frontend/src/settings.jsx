import { createContext, useContext, useEffect, useMemo, useState } from 'react';

// Dark mode and "advanced data" are remembered in localStorage. Advanced is off by default.
const Ctx = createContext(null);

function read(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v === null ? fallback : v === '1';
  } catch {
    return fallback;
  }
}

export function SettingsProvider({ children }) {
  const [dark, setDark] = useState(() => read('dark', window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false));
  const [advanced, setAdvanced] = useState(() => read('advanced', false));
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    try { localStorage.setItem('dark', dark ? '1' : '0'); } catch { /* storage may be blocked */ }
  }, [dark]);
  useEffect(() => {
    try { localStorage.setItem('advanced', advanced ? '1' : '0'); } catch { /* storage may be blocked */ }
  }, [advanced]);
  const value = useMemo(() => ({ dark, setDark, advanced, setAdvanced }), [dark, advanced]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useSettings = () => useContext(Ctx);
