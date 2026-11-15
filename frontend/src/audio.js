// Spoken help. First the server voice for the whole text (/api/tts, OpenAI), then recorded clips: /audio/{lang}/{id}.mp3 (see docs/audio-script.md). A
// sentence is a list of clip ids (e.g. month_11, to, month_12, act_sow, crop_wheat). If any clip of
// that sentence is missing, the browser's speech voice reads the text instead.
import { speechAudio } from './api.js';

const exists = new Map();
let current = null; // the Audio element or utterance playing now
let seq = 0; // bumped by every say/stop, so a late answer never starts after Stop

async function hasClip(url) {
  if (!exists.has(url)) {
    // The dev server answers unknown paths with index.html, so check the type, not just the status.
    exists.set(url, fetch(url, { method: 'HEAD' })
      .then((r) => r.ok && (r.headers.get('content-type') || '').startsWith('audio/'))
      .catch(() => false));
  }
  return exists.get(url);
}

const VOICE_LANGS = { ar: ['ar-MA', 'ar'], fr: ['fr-FR', 'fr'], en: ['en-US', 'en-GB', 'en'] };

export function voiceFor(lang) {
  const voices = window.speechSynthesis?.getVoices() ?? [];
  return VOICE_LANGS[lang].map((code) => voices.find((v) => v.lang.toLowerCase().startsWith(code.toLowerCase()))).find(Boolean) ?? null;
}

export function stopAudio() {
  seq += 1;
  if (current instanceof Audio) current.pause();
  window.speechSynthesis?.cancel();
  current = null;
}

function playUrls(urls, onEnd) {
  let i = 0;
  const next = () => {
    if (i >= urls.length) { current = null; onEnd(); return; }
    const a = new Audio(urls[i]);
    i += 1;
    current = a;
    a.onended = next;
    a.onerror = () => { current = null; onEnd(); };
    a.play().catch(() => { current = null; onEnd(); });
  };
  next();
}

// Server voice for the whole text, else the clips if they all exist, else the phone's voice.
// Returns 'server', 'clips', 'voice' or 'none'.
export async function say(lang, clipIds, text, onEnd = () => {}) {
  stopAudio();
  const mine = seq;
  const url = await speechAudio(text, lang);
  if (mine !== seq) { if (url) URL.revokeObjectURL(url); return 'server'; }
  if (url) {
    playUrls([url], () => { URL.revokeObjectURL(url); onEnd(); });
    return 'server';
  }
  const urls = clipIds.map((id) => `/audio/${lang}/${id}.mp3`);
  if (urls.length && (await Promise.all(urls.map(hasClip))).every(Boolean)) {
    playUrls(urls, onEnd);
    return 'clips';
  }
  const voice = voiceFor(lang);
  if (!voice) return 'none';
  const u = new SpeechSynthesisUtterance(text);
  u.voice = voice;
  u.lang = voice.lang;
  u.rate = 0.9;
  u.onend = () => { current = null; onEnd(); };
  u.onerror = () => { current = null; onEnd(); };
  current = u;
  window.speechSynthesis.speak(u);
  return 'voice';
}
