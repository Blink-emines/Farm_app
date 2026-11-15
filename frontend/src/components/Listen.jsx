import { useEffect, useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { say, stopAudio } from '../audio.js';

const Speaker = () => (
  <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 9v6h4l5 4V5L8 9z" /><path d="M16.5 8.5a5 5 0 010 7M19 6a8.5 8.5 0 010 12" /></svg>
);

// Always visible. Plays recorded clips when they exist, otherwise the phone's voice; says so
// plainly when the phone has neither.
export default function Listen({ clips, text, label, compact = false }) {
  const { t, lang } = useI18n();
  const [state, setState] = useState('idle'); // idle | playing | none
  useEffect(() => () => stopAudio(), []);
  useEffect(() => { setState('idle'); }, [lang, text]);

  const toggle = async () => {
    if (state === 'playing') { stopAudio(); setState('idle'); return; }
    setState('playing');
    const how = await say(lang, clips, text, () => setState('idle'));
    if (how === 'none') setState('none');
  };

  return (
    <span className={`listen${compact ? ' is-compact' : ''}`}>
      <button type="button" className="btn btn-quiet listen-btn" aria-pressed={state === 'playing'} aria-label={compact ? (label ?? t('ui.listen')) : undefined} onClick={toggle}>
        <Speaker />
        {!compact && (state === 'playing' ? t('ui.listen_stop') : (label ?? t('ui.listen')))}
      </button>
      {state === 'none' && <span className="listen-none" role="status">{t('ui.listen_none')}</span>}
    </span>
  );
}
