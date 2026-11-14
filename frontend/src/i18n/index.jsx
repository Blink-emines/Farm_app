import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import fr from './fr.js';
import ar from './ar.js';

const DICTS = { fr, ar };
export const LANGS = [
  { id: 'fr', label: 'Français' },
  { id: 'ar', label: 'العربية' },
];

const Ctx = createContext(null);

function readSaved() {
  try {
    const v = localStorage.getItem('lang');
    return DICTS[v] ? v : 'fr';
  } catch {
    return 'fr';
  }
}

// Engine params can be plain ids ("wheat"), lists ("faba_bean,wheat", "wheat > faba_bean",
// "wheat:medium"), or month lists ("3,4,5"). Translate the words, keep the numbers.
function param(key, v, dict) {
  if (typeof v !== 'string') {
    return key === 'month' && dict[`month.${v}`] ? dict[`month.${v}`] : String(v);
  }
  if (key === 'months') {
    return v.split(',').map((m) => dict[`month.${m.trim()}`] ?? m).join(dict['ui.list_sep']);
  }
  return v
    .replace(/[a-z_]+/g, (w) => dict[`crop.${w}`]
      ?? (key === 'levels' || key === 'level' ? dict[`level.${w}`] : undefined)
      ?? (key === 'flag' ? dict[`flag.${w}`] : undefined)
      ?? w)
    .replace(/ > /g, ' \u2192 ')
    .replace(/,/g, dict['ui.list_sep']);
}

function fill(text, params, dict) {
  return text.replace(/\{(\w+)\}/g, (whole, key) => {
    const v = params?.[key];
    return v === undefined || v === null ? whole : param(key, v, dict);
  });
}

// "crops.wheat.kc_mid" -> "Blé : besoin en eau"; falls back to the raw path.
function featureLabel(path, dict, crop) {
  if (dict[`feat.${path}`]) return dict[`feat.${path}`];
  const m = path.match(/^crops\.([a-z_]+)\.([a-z_0-9]+)$/);
  if (m && dict[`attr.${m[2]}`]) return `${crop(m[1])} : ${dict[`attr.${m[2]}`]}`;
  return path;
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(readSaved);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  }, [lang]);

  const value = useMemo(() => {
    const dict = DICTS[lang];
    return {
      lang,
      setLang(next) {
        setLangState(next);
        try { localStorage.setItem('lang', next); } catch { /* storage may be blocked */ }
      },
      // t('ui.title', {n: 2}) for interface text
      t: (key, params) => fill(dict[key] ?? key, params, dict),
      // tm(message) for {code, params, default_text} from the engine
      tm: (msg) => (dict[msg.code] ? fill(dict[msg.code], msg.params, dict) : msg.default_text),
      crop: (id) => dict[`crop.${id}`] ?? id,
      month: (n) => dict[`month.${n}`] ?? String(n),
      gap: (g) => dict[`gap.${g.code}`] ?? g.message,
      feature: (path) => featureLabel(path, dict, (id) => dict[`crop.${id}`] ?? id),
      value: (v) => (typeof v === 'string' ? dict[`val.${v}`] ?? v : v),
      unit: (u) => dict[`unit.${u}`] ?? u,
    };
  }, [lang]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
