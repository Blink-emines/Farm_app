import { useEffect, useRef } from 'react';
import { LANGS, useI18n } from '../i18n/index.jsx';
import { useSettings } from '../settings.jsx';

function Switch({ checked, onChange, label, help }) {
  const { t } = useI18n();
  return (
    <div className="set-row">
      <div>
        <p className="set-label" id={`sw-${label}`}>{t(`ui.${label}`)}</p>
        <p className="muted">{t(`ui.${help}`)}</p>
      </div>
      <button type="button" role="switch" aria-checked={checked} aria-labelledby={`sw-${label}`} className="switch" onClick={() => onChange(!checked)}>
        <span className="knob" aria-hidden="true" />
        <span className="switch-text">{checked ? t('ui.set_on') : t('ui.set_off')}</span>
      </button>
    </div>
  );
}

export function GearButton({ onClick }) {
  const { t } = useI18n();
  return (
    <button type="button" className="gear" onClick={onClick} aria-label={t('ui.set_open')}>
      <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
      </svg>
    </button>
  );
}

export default function SettingsPanel({ onClose }) {
  const { t, lang, setLang } = useI18n();
  const { dark, setDark } = useSettings();
  const closeRef = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); previous?.focus?.(); };
  }, [onClose]);
  return (
    <div className="sheet-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet settings" role="dialog" aria-modal="true" aria-label={t('ui.set_title')}>
        <header className="sheet-head">
          <h3>{t('ui.set_title')}</h3>
          <button ref={closeRef} type="button" className="btn btn-quiet close" onClick={onClose}>{t('ui.close')}</button>
        </header>
        <div className="sheet-body">
          <div className="set-row stack">
            <p className="set-label">{t('ui.language')}</p>
            <div className="seg" role="group" aria-label={t('ui.language')}>
              {LANGS.map((l) => (
                <button key={l.id} type="button" lang={l.id} aria-pressed={lang === l.id} onClick={() => setLang(l.id)}>{l.label}</button>
              ))}
            </div>
          </div>
          <Switch checked={dark} onChange={setDark} label="set_dark" help="set_dark_help" />
        </div>
      </div>
    </div>
  );
}
