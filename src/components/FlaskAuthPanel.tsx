import React, { useState } from 'react';
import {
  FlaskAuthError,
  redirectToFlaskRegistrationVerification,
  RegistrationRequest,
} from '../lib/flaskAuth';
import { useApp } from '../context/AppContext';

interface FlaskAuthPanelProps {
  onClose: () => void;
}

type PanelMode = 'login' | 'register';

export const FlaskAuthPanel: React.FC<FlaskAuthPanelProps> = ({ onClose }) => {
  const {
    flaskUser,
    isFlaskAuthLoading,
    loginWithFlask,
    logoutFlask,
    startFlaskRegistration,
    t,
  } = useApp();
  const [mode, setMode] = useState<PanelMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [storeName, setStoreName] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await loginWithFlask(email, password);
      onClose();
    } catch (requestError) {
      setError(requestError instanceof FlaskAuthError ? requestError.message : 'Sign-in failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitRegistration = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    const requestBody: RegistrationRequest = {
      role: 'customer',
      email,
      full_name: fullName,
      phone,
      password,
    };
    if (storeName.trim()) {
      requestBody.role = 'seller';
      requestBody.store_name = storeName.trim();
    }
    try {
      await startFlaskRegistration(requestBody);
      redirectToFlaskRegistrationVerification();
    } catch (requestError) {
      setError(requestError instanceof FlaskAuthError ? requestError.message : 'Registration failed. Please try again.');
      setIsSubmitting(false);
    }
  };

  const signOut = async () => {
    setError('');
    try {
      await logoutFlask();
      onClose();
    } catch (requestError) {
      setError(requestError instanceof FlaskAuthError ? requestError.message : 'Sign-out failed. Please try again.');
    }
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-slate-950/50 px-4 pt-20" role="dialog" aria-modal="true" aria-labelledby="flask-auth-title">
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-elevated dark:bg-slate-800">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-primary">NexHaat Flask session</p>
            <h2 id="flask-auth-title" className="mt-1 text-xl font-bold text-ink dark:text-white">
              {flaskUser ? t('Marketplace account', 'মার্কেটপ্লেস অ্যাকাউন্ট') : mode === 'login' ? t('Sign in securely', 'নিরাপদে সাইন ইন') : t('Create an account', 'অ্যাকাউন্ট তৈরি করুন')}
            </h2>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-ink dark:hover:text-white" aria-label={t('Close', 'বন্ধ করুন')}>×</button>
        </div>

        {flaskUser ? (
          <div className="space-y-4">
            <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600 dark:bg-slate-900 dark:text-slate-300">
              {flaskUser.email} · <span className="font-semibold">{flaskUser.role}</span>
            </p>
            <button type="button" onClick={signOut} disabled={isFlaskAuthLoading} className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-bold text-white disabled:opacity-60">
              {t('Sign out of marketplace', 'মার্কেটপ্লেস থেকে সাইন আউট')}
            </button>
            {error && <p className="text-sm text-rose-600" role="alert">{error}</p>}
          </div>
        ) : (
          <>
            <div className="mb-4 flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900">
              {(['login', 'register'] as PanelMode[]).map((nextMode) => (
                <button key={nextMode} type="button" onClick={() => { setMode(nextMode); setError(''); }} className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold ${mode === nextMode ? 'bg-white text-primary shadow-sm dark:bg-slate-700' : 'text-slate-500'}`}>
                  {nextMode === 'login' ? t('Sign in', 'সাইন ইন') : t('Register', 'রেজিস্টার')}
                </button>
              ))}
            </div>
            <form onSubmit={mode === 'login' ? submitLogin : submitRegistration} className="space-y-3">
              {mode === 'register' && (
                <>
                  <input value={fullName} onChange={(event) => setFullName(event.target.value)} required minLength={2} maxLength={120} placeholder={t('Full name', 'পূর্ণ নাম')} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                  <input value={phone} onChange={(event) => setPhone(event.target.value)} required minLength={7} maxLength={30} placeholder={t('Phone number', 'ফোন নম্বর')} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                  <input value={storeName} onChange={(event) => setStoreName(event.target.value)} maxLength={120} placeholder={t('Store name (optional seller account)', 'স্টোরের নাম (ঐচ্ছিক seller account)')} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
                </>
              )}
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={255} placeholder={t('Email address', 'ইমেইল ঠিকানা')} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} maxLength={128} placeholder={t('Password', 'পাসওয়ার্ড')} className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white" />
              <p className="text-xs text-slate-500">{mode === 'register' ? t('After registration, the existing secure Flask OTP screen will open.', 'রেজিস্ট্রেশনের পর বিদ্যমান নিরাপদ Flask OTP স্ক্রিন খুলবে।') : t('Your Flask session is stored in a secure cookie; no token is saved in browser storage.', 'আপনার Flask session নিরাপদ cookie-তে থাকে; browser storage-এ কোনো token রাখা হয় না।')}</p>
              {error && <p className="text-sm text-rose-600" role="alert">{error}</p>}
              <button type="submit" disabled={isSubmitting || isFlaskAuthLoading} className="w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-hover disabled:opacity-60">
                {isSubmitting ? t('Please wait…', 'অপেক্ষা করুন…') : mode === 'login' ? t('Sign in to NexHaat', 'NexHaat-এ সাইন ইন') : t('Continue to OTP verification', 'OTP verification-এ যান')}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
};
