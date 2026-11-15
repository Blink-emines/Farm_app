import { useState } from 'react';
import { useI18n } from '../i18n/index.jsx';
import { login, register } from '../api.js';
import { BrandMark } from './icons.jsx';

// Which message to show for a refused login or sign-up.
function errorKey(err) {
  if (err.code === 'network') return 'err.network';
  if (err.code === 'bad_login') return 'ui.auth_err_login';
  if (err.code === 'invalid_signup') {
    if (err.fields?.includes('username')) return 'ui.auth_err_username';
    if (err.fields?.includes('email')) return 'ui.auth_err_email';
    // The server reports password-rule failures as non_field_errors.
    if (err.fields?.includes('password') || err.fields?.includes('non_field_errors')) return 'ui.auth_err_password';
  }
  return 'err.internal_error';
}

// Shown after "Analyse my field": log in (email or username + password) or create an account,
// so the field location and the plan can be saved for the farmer.
export default function Auth({ head, onDone, onBack }) {
  const { t } = useI18n();
  const [mode, setMode] = useState('login');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError('');
    try {
      if (mode === 'login') await login(f.get('identifier').trim(), f.get('password'));
      else await register(f.get('username').trim(), f.get('email').trim(), f.get('password'));
      onDone();
    } catch (err) {
      setError(errorKey(err));
      setBusy(false);
    }
  }

  const switchTo = (m) => { setMode(m); setError(''); };

  return (
    <div className="auth-page">
      {head}
      <main className="auth-main">
        <section className="auth-card" aria-labelledby="auth-h">
          <BrandMark size={48} />
          <h1 id="auth-h">{t(mode === 'login' ? 'ui.auth_title_login' : 'ui.auth_title_register')}</h1>
          <p className="auth-sub">{t('ui.auth_sub')}</p>

          <div className="auth-tabs" role="group" aria-label={t('ui.auth_title_login')}>
            {['login', 'register'].map((m) => (
              <button key={m} type="button" aria-pressed={mode === m} onClick={() => switchTo(m)}>{t(`ui.auth_tab_${m}`)}</button>
            ))}
          </div>

          <form className="auth-form" onSubmit={submit} key={mode}>
            {mode === 'login' ? (
              <label className="field">
                <span>{t('ui.auth_identifier')}</span>
                <input type="text" name="identifier" autoComplete="username" required />
              </label>
            ) : (
              <>
                <label className="field">
                  <span>{t('ui.auth_username')}</span>
                  <input type="text" name="username" autoComplete="username" required />
                </label>
                <label className="field">
                  <span>{t('ui.auth_email')}</span>
                  <input type="email" name="email" autoComplete="email" />
                </label>
              </>
            )}
            <label className="field">
              <span>{t('ui.auth_password')}</span>
              <input type="password" name="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required />
            </label>
            {mode === 'register' && <p className="auth-hint">{t('ui.auth_password_hint')}</p>}

            {error && <p className="notice notice-error" role="alert">{t(error)}</p>}

            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? t('ui.loading') : t(mode === 'login' ? 'ui.auth_submit_login' : 'ui.auth_submit_register')}
            </button>
          </form>

          <p className="auth-privacy">{t('ui.auth_privacy')}</p>
          <button type="button" className="btn-text" onClick={onBack}>{t('ui.auth_back')}</button>
        </section>
      </main>
    </div>
  );
}
