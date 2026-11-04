import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  confirmTwoFactorSetup,
  disableTwoFactor,
  FlaskAuthError,
  getTwoFactorStatus,
  redirectToFlaskRegistrationVerification,
  regenerateBackupCodes,
  RegistrationRequest,
  startTwoFactorSetup,
  TwoFactorSetupData,
  TwoFactorStatus,
} from '../lib/flaskAuth';
import { useApp } from '../context/AppContext';
<<<<<<< HEAD
import { Shield, ShieldAlert, ShieldCheck, Key, Copy, Check, RefreshCw, Lock, ArrowLeft } from 'lucide-react';
=======
import { Shield, ShieldAlert, ShieldCheck, Key, Copy, Check, RefreshCw, Lock, ArrowLeft, ScanLine } from 'lucide-react';
import { evaluatePasswordStrength } from '../lib/motionTokens';
import type { UserRole } from '../types';
>>>>>>> d5fb7ab (Fix)

interface FlaskAuthPanelProps {
  onClose: () => void;
}

type PanelMode = 'login' | 'register' | 'two_factor_challenge';
type AuthenticatedTab = 'overview' | 'security';

export const FlaskAuthPanel: React.FC<FlaskAuthPanelProps> = ({ onClose }) => {
  const {
    flaskUser,
    currentUser,
    isFlaskAuthLoading,
    setUserRole,
    loginWithFlask,
    verifyTwoFactorChallenge,
    logoutFlask,
    startFlaskRegistration,
    t,
  } = useApp();

  const [mode, setMode] = useState<PanelMode>('login');
  const [authTab, setAuthTab] = useState<AuthenticatedTab>('overview');

  // Form states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [storeName, setStoreName] = useState('');
  const [twoFactorCode, setTwoFactorCode] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 2FA Management states (for logged-in user)
  const [tfStatus, setTfStatus] = useState<TwoFactorStatus | null>(null);
  const [setupData, setSetupData] = useState<TwoFactorSetupData | null>(null);
  const [confirmCode, setConfirmCode] = useState('');
  const [reauthPassword, setReauthPassword] = useState('');
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [showRegenModal, setShowRegenModal] = useState(false);
  const [newBackupCodes, setNewBackupCodes] = useState<string[] | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);

  useEffect(() => {
    if (flaskUser) {
      load2FAStatus();
    }
  }, [flaskUser]);

  const load2FAStatus = async () => {
    try {
      const status = await getTwoFactorStatus();
      setTfStatus(status);
    } catch {
      // Non-fatal if status check fails
    }
  };

  const submitLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const result = await loginWithFlask(email, password);
      if (result.status === 'two_factor_required') {
        setMode('two_factor_challenge');
        setTwoFactorCode('');
      } else {
        onClose();
      }
    } catch (requestError) {
      setError(requestError instanceof FlaskAuthError ? requestError.message : 'Sign-in failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitChallenge = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await verifyTwoFactorChallenge(twoFactorCode);
      onClose();
    } catch (requestError) {
      setError(requestError instanceof FlaskAuthError ? requestError.message : 'Verification failed. Please check your code.');
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

  const handleStartSetup = async () => {
    setError('');
    setSuccessMsg('');
    setIsSubmitting(true);
    try {
      const data = await startTwoFactorSetup();
      setSetupData(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to initiate 2FA setup.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await confirmTwoFactorSetup(confirmCode);
      setSuccessMsg(t('Two-factor authentication is now active!', 'টু-ফ্যাক্টর অথেনটিকেশন এখন সক্রিয়!'));
      await load2FAStatus();
      setNewBackupCodes(setupData?.backup_codes || []);
      setSetupData(null);
      setConfirmCode('');
    } catch (err: any) {
      setError(err?.message || 'Invalid verification code.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDisable2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await disableTwoFactor(reauthPassword);
      setShowDisableModal(false);
      setReauthPassword('');
      setSuccessMsg(t('Two-factor authentication has been disabled.', 'টু-ফ্যাক্টর অথেনটিকেশন নিষ্ক্রিয় করা হয়েছে।'));
      await load2FAStatus();
    } catch (err: any) {
      setError(err?.message || 'Password confirmation failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegenerateCodes = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      const codes = await regenerateBackupCodes(reauthPassword);
      setShowRegenModal(false);
      setReauthPassword('');
      setNewBackupCodes(codes);
      setSuccessMsg(t('New backup codes generated.', 'নতুন ব্যাকআপ কোড তৈরি হয়েছে।'));
      await load2FAStatus();
    } catch (err: any) {
      setError(err?.message || 'Password confirmation failed.');
    } finally {
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

  const modalContent = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/60 p-4 overflow-y-auto backdrop-blur-xs" role="dialog" aria-modal="true" aria-labelledby="flask-auth-title">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-800 my-auto max-h-[90vh] overflow-y-auto">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" />
              <p className="text-[11px] font-bold uppercase tracking-wider text-primary">NexHaat Enterprise Security</p>
            </div>
            <h2 id="flask-auth-title" className="mt-1 text-xl font-bold text-ink dark:text-white">
              {flaskUser
                ? t('Account & Security Settings', 'অ্যাকাউন্ট ও নিরাপত্তা সেটিংস')
                : mode === 'two_factor_challenge'
                ? t('Two-Factor Authentication Required', 'টু-ফ্যাক্টর প্রমাণীকরণ প্রয়োজন')
                : mode === 'login'
                ? t('Sign in securely', 'নিরাপদে সাইন ইন')
                : t('Create an account', 'অ্যাকাউন্ট তৈরি করুন')}
            </h2>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-ink dark:hover:text-white text-2xl font-light" aria-label={t('Close', 'বন্ধ করুন')}>×</button>
        </div>

        {error && (
<<<<<<< HEAD
          <div className="mb-4 p-3 rounded-xl bg-rose-50 text-rose-700 text-sm border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900 flex items-start gap-2" role="alert">
=======
          <div className="mb-4 p-3 rounded-xl bg-rose-50 text-rose-700 text-sm border border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900 flex items-start gap-2 animate-error-shake" role="alert">
>>>>>>> d5fb7ab (Fix)
            <ShieldAlert className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-50 text-emerald-700 text-sm border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* 1. Logged in View */}
        {flaskUser ? (
          <div className="space-y-4">
            <div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => setAuthTab('overview')}
                className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${authTab === 'overview' ? 'bg-white text-primary shadow-sm dark:bg-slate-700 dark:text-white' : 'text-slate-500'}`}
              >
                {t('Profile', 'প্রোফাইল')}
              </button>
              <button
                type="button"
                onClick={() => setAuthTab('security')}
                className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors flex items-center justify-center gap-1.5 ${authTab === 'security' ? 'bg-white text-primary shadow-sm dark:bg-slate-700 dark:text-white' : 'text-slate-500'}`}
              >
                <Lock className="w-3.5 h-3.5" />
                {t('2FA Security', '২এফএ নিরাপত্তা')}
                {tfStatus?.enabled && <span className="w-2 h-2 rounded-full bg-emerald-500"></span>}
              </button>
            </div>

            {authTab === 'overview' && (
              <div className="space-y-4">
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-900">
                  <p className="text-xs text-slate-500 uppercase font-medium">{t('Email address', 'ইমেইল')}</p>
                  <p className="font-semibold text-ink dark:text-white">{flaskUser.email}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary/10 text-primary">
                      {flaskUser.role.toUpperCase()}
                    </span>
                    <span className="text-xs text-slate-500">
                      2FA: {tfStatus?.enabled ? t('Active', 'সক্রিয়') : t('Inactive', 'নিষ্ক্রিয়')}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={signOut}
                  disabled={isFlaskAuthLoading}
                  className="w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-bold text-white hover:bg-slate-800 disabled:opacity-60 transition-colors"
                >
                  {t('Sign out of marketplace', 'মার্কেটপ্লেস থেকে সাইন আউট')}
                </button>
              </div>
            )}

            {authTab === 'security' && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
<<<<<<< HEAD
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center ${tfStatus?.enabled ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60' : 'bg-slate-200 text-slate-600 dark:bg-slate-800'}`}>
                        {tfStatus?.enabled ? <ShieldCheck className="w-5 h-5" /> : <Shield className="w-5 h-5" />}
=======
                      <div className={`relative overflow-hidden w-10 h-10 rounded-xl flex items-center justify-center ${tfStatus?.enabled ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-950/60' : 'bg-slate-200 text-slate-600 dark:bg-slate-800'}`}>
                        {tfStatus?.enabled ? <ShieldCheck className="w-5 h-5" /> : <Shield className="w-5 h-5" />}
                        <span className="animate-radar-scan" />
>>>>>>> d5fb7ab (Fix)
                      </div>
                      <div>
                        <p className="font-bold text-sm text-ink dark:text-white">
                          {tfStatus?.enabled ? t('Two-Factor Authentication Active', 'টু-ফ্যাক্টর অথেনটিকেশন সক্রিয়') : t('Two-Factor Authentication Disabled', 'টু-ফ্যাক্টর অথেনটিকেশন নিষ্ক্রিয়')}
                        </p>
                        <p className="text-xs text-slate-500">
                          {tfStatus?.enabled
                            ? `${tfStatus.backup_codes_remaining} ${t('backup codes remaining', 'টি ব্যাকআপ কোড অবশিষ্ট')}`
                            : t('Protect your account with Google Authenticator or Microsoft Authenticator', 'Google বা Microsoft Authenticator দিয়ে অ্যাকাউন্ট সুরক্ষিত করুন')}
                        </p>
                      </div>
                    </div>
                  </div>

                  {!tfStatus?.enabled && !setupData && (
                    <button
                      type="button"
                      onClick={handleStartSetup}
                      disabled={isSubmitting}
                      className="mt-4 w-full py-2.5 px-4 bg-primary text-white rounded-xl text-sm font-bold hover:bg-primary-hover transition-colors shadow-sm"
                    >
                      {isSubmitting ? t('Starting...', 'শুরু হচ্ছে...') : t('Setup Two-Factor Authentication', 'টু-ফ্যাক্টর অথেনটিকেশন সেটআপ করুন')}
                    </button>
                  )}
                </div>

                {/* Setup flow */}
                {setupData && !tfStatus?.enabled && (
                  <div className="p-4 rounded-xl border border-primary/30 bg-primary/5 space-y-4">
                    <p className="text-sm font-bold text-ink dark:text-white">
                      {t('Step 1: Add account to your Authenticator app', 'ধাপ ১: আপনার Authenticator অ্যাপে যুক্ত করুন')}
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-300">
                      {t('Open Google Authenticator, Microsoft Authenticator, or 1Password, and enter this key manually:', 'Google Authenticator বা Microsoft Authenticator অ্যাপে গিয়ে এই সিক্রেট কোডটি ম্যানুয়ালি বসান:')}
                    </p>

                    <div className="p-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                      <code className="text-sm font-mono tracking-wider font-bold text-primary break-all select-all">
                        {setupData.secret}
                      </code>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(setupData.secret);
                          setCopiedKey(true);
                          setTimeout(() => setCopiedKey(false), 2000);
                        }}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded text-slate-600 dark:text-slate-300 ml-2"
                        title={t('Copy Key', 'কোড কপি করুন')}
                      >
                        {copiedKey ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>

                    <form onSubmit={handleConfirmSetup} className="space-y-3 pt-2">
                      <p className="text-sm font-bold text-ink dark:text-white">
                        {t('Step 2: Enter the 6-digit verification code', 'ধাপ ২: অ্যাপের ৬-ডিজিটের ভেরিফিকেশন কোড লিখুন')}
                      </p>
                      <input
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={confirmCode}
                        onChange={(e) => setConfirmCode(e.target.value.replace(/\D/g, ''))}
                        required
                        placeholder="123456"
                        className="w-full text-center tracking-widest text-lg font-mono py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                      />
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={confirmCode.length !== 6 || isSubmitting}
                          className="flex-1 py-2.5 px-4 bg-emerald-600 text-white rounded-xl text-sm font-bold hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                        >
                          {isSubmitting ? t('Verifying...', 'যাচাই হচ্ছে...') : t('Activate 2FA', '২এফএ সক্রিয় করুন')}
                        </button>
                        <button
                          type="button"
                          onClick={() => setSetupData(null)}
                          className="py-2.5 px-4 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 rounded-xl text-sm font-semibold"
                        >
                          {t('Cancel', 'বাতিল')}
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* Display Newly Generated Backup Codes */}
                {newBackupCodes && (
                  <div className="p-4 rounded-xl border border-amber-300 bg-amber-50 dark:bg-amber-950/40 dark:border-amber-800 space-y-3">
                    <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200 font-bold text-sm">
                      <Key className="w-4 h-4" />
                      <span>{t('Save Your Backup Codes (Shown Once)', 'ব্যাকআপ কোডগুলো সংরক্ষণ করুন (একবারই প্রদর্শিত হবে)')}</span>
                    </div>
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      {t('If you lose your phone or authenticator app, each code can be used once to sign in. Store them in a safe password manager.', 'ফোন হারিয়ে গেলে প্রতিটি কোড একবার ব্যবহার করে লগইন করতে পারবেন। এগুলো সুরক্ষিত স্থানে সংরক্ষণ করুন।')}
                    </p>
                    <div className="grid grid-cols-2 gap-2 p-3 bg-white dark:bg-slate-900 rounded-lg font-mono text-sm">
                      {newBackupCodes.map((code, idx) => (
                        <div key={idx} className="p-1 text-center font-bold text-slate-800 dark:text-slate-200 select-all">
                          {code}
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(newBackupCodes.join('\n'));
                          setCopiedCodes(true);
                          setTimeout(() => setCopiedCodes(false), 2000);
                        }}
                        className="flex-1 py-2 px-3 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5"
                      >
                        {copiedCodes ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedCodes ? t('Copied!', 'কপি হয়েছে!') : t('Copy All Codes', 'সব কোড কপি করুন')}
                      </button>
                      <button
                        type="button"
                        onClick={() => setNewBackupCodes(null)}
                        className="py-2 px-3 border border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-200 rounded-lg text-xs font-semibold"
                      >
                        {t('Dismiss', 'সম্পন্ন')}
                      </button>
                    </div>
                  </div>
                )}

                {/* Management actions when enabled */}
                {tfStatus?.enabled && (
                  <div className="pt-2 flex flex-col gap-2">
                    <button
                      type="button"
                      onClick={() => { setShowRegenModal(true); setShowDisableModal(false); setError(''); }}
                      className="py-2.5 px-4 rounded-xl border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center justify-center gap-2"
                    >
                      <RefreshCw className="w-4 h-4" />
                      {t('Regenerate Backup Codes', 'নতুন ব্যাকআপ কোড তৈরি করুন')}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowDisableModal(true); setShowRegenModal(false); setError(''); }}
                      className="py-2.5 px-4 rounded-xl border border-rose-200 text-rose-600 dark:border-rose-900 dark:text-rose-400 text-sm font-semibold hover:bg-rose-50 dark:hover:bg-rose-950/40"
                    >
                      {t('Disable Two-Factor Authentication', 'টু-ফ্যাক্টর অথেনটিকেশন নিষ্ক্রিয় করুন')}
                    </button>
                  </div>
                )}

                {/* Reauth modal for Disable */}
                {showDisableModal && (
                  <form onSubmit={handleDisable2FA} className="p-4 rounded-xl border border-rose-200 bg-rose-50/50 dark:bg-rose-950/20 space-y-3">
                    <p className="text-sm font-bold text-rose-900 dark:text-rose-200">
                      {t('Enter your password to disable 2FA:', '২এফএ নিষ্ক্রিয় করতে পাসওয়ার্ড দিন:')}
                    </p>
                    <input
                      type="password"
                      value={reauthPassword}
                      onChange={(e) => setReauthPassword(e.target.value)}
                      required
                      placeholder={t('Account password', 'অ্যাকাউন্ট পাসওয়ার্ড')}
                      className="w-full py-2 px-3 rounded-lg border border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:text-white text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="flex-1 py-2 bg-rose-600 text-white rounded-lg text-xs font-bold hover:bg-rose-700"
                      >
                        {isSubmitting ? t('Disabling...', 'নিষ্ক্রিয় হচ্ছে...') : t('Confirm Disable', 'নিষ্ক্রিয় নিশ্চিত করুন')}
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowDisableModal(false)}
                        className="py-2 px-3 border border-slate-300 text-slate-700 dark:text-slate-300 rounded-lg text-xs"
                      >
                        {t('Cancel', 'বাতিল')}
                      </button>
                    </div>
                  </form>
                )}

                {/* Reauth modal for Regenerate */}
                {showRegenModal && (
                  <form onSubmit={handleRegenerateCodes} className="p-4 rounded-xl border border-slate-200 bg-slate-50 dark:bg-slate-900 space-y-3">
                    <p className="text-sm font-bold text-ink dark:text-white">
                      {t('Enter your password to generate new backup codes:', 'নতুন ব্যাকআপ কোড পেতে পাসওয়ার্ড দিন:')}
                    </p>
                    <input
                      type="password"
                      value={reauthPassword}
                      onChange={(e) => setReauthPassword(e.target.value)}
                      required
                      placeholder={t('Account password', 'অ্যাকাউন্ট পাসওয়ার্ড')}
                      className="w-full py-2 px-3 rounded-lg border border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white text-sm"
                    />
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="flex-1 py-2 bg-primary text-white rounded-lg text-xs font-bold hover:bg-primary-hover"
                      >
                        {isSubmitting ? t('Generating...', 'তৈরি হচ্ছে...') : t('Generate Codes', 'কোড তৈরি করুন')}
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowRegenModal(false)}
                        className="py-2 px-3 border border-slate-300 text-slate-700 dark:text-slate-300 rounded-lg text-xs"
                      >
                        {t('Cancel', 'বাতিল')}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}
          </div>
        ) : mode === 'two_factor_challenge' ? (
          /* 2. Two-Factor Challenge Login Modal */
          <form onSubmit={submitChallenge} className="space-y-4">
            <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-xs text-primary dark:text-sky-300">
              {t('Enter the 6-digit code from your authenticator app, or an 8-digit single-use backup code.', 'আপনার Authenticator অ্যাপের ৬-ডিজিটের কোড অথবা ৮-ডিজিটের ব্যাকআপ কোড দিন।')}
            </div>

            <div className="space-y-1">
              <label htmlFor="2fa-code" className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                {t('Authentication Code', 'প্রমাণীকরণ কোড')}
              </label>
              <input
                id="2fa-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={8}
                value={twoFactorCode}
                onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ''))}
                required
                autoFocus
                placeholder="123456"
                className="w-full py-3 px-4 text-center tracking-widest text-xl font-mono rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
            </div>

            <button
              type="submit"
              disabled={twoFactorCode.length < 6 || isSubmitting || isFlaskAuthLoading}
              className="w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-hover disabled:opacity-60 transition-colors shadow-sm"
            >
              {isSubmitting ? t('Verifying…', 'যাচাই হচ্ছে…') : t('Verify & Continue', 'যাচাই ও এগিয়ে যান')}
            </button>

            <button
              type="button"
              onClick={() => { setMode('login'); setError(''); }}
              className="w-full flex items-center justify-center gap-1.5 text-xs text-slate-500 hover:text-ink dark:hover:text-white pt-1"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              {t('Back to email & password sign-in', 'ইমেইল ও পাসওয়ার্ড লগইনে ফিরে যান')}
            </button>
          </form>
        ) : (
          /* 3. Standard Login / Register form */
          <>
            <div className="mb-4 flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900">
              {(['login', 'register'] as PanelMode[]).map((nextMode) => (
                <button
                  key={nextMode}
                  type="button"
                  onClick={() => { setMode(nextMode); setError(''); }}
                  className={`flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${mode === nextMode ? 'bg-white text-primary shadow-sm dark:bg-slate-700 dark:text-white' : 'text-slate-500'}`}
                >
                  {nextMode === 'login' ? t('Sign in', 'সাইন ইন') : t('Register', 'রেজিস্টার')}
                </button>
              ))}
            </div>

            <form onSubmit={mode === 'login' ? submitLogin : submitRegistration} className="space-y-3">
              {mode === 'register' && (
                <>
                  <input
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    required
                    minLength={2}
                    maxLength={120}
                    placeholder={t('Full name', 'পূর্ণ নাম')}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                  <input
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    required
                    minLength={7}
                    maxLength={30}
                    placeholder={t('Phone number', 'ফোন নম্বর')}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                  <input
                    value={storeName}
                    onChange={(event) => setStoreName(event.target.value)}
                    maxLength={120}
                    placeholder={t('Store name (optional seller account)', 'স্টোরের নাম (ঐচ্ছিক seller account)')}
                    className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  />
                </>
              )}
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                maxLength={255}
                placeholder={t('Email address', 'ইমেইল ঠিকানা')}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
                maxLength={128}
                placeholder={t('Password', 'পাসওয়ার্ড')}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              />
<<<<<<< HEAD
=======

              {/* Dynamic Animated Password Strength Indicator in Register mode */}
              {mode === 'register' && password.length > 0 && (() => {
                const strength = evaluatePasswordStrength(password);
                return (
                  <div className="space-y-1 pt-1 animate-view-enter">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-slate-500 font-semibold">{t('Password Security:', 'পাসওয়ার্ড নিরাপত্তা:')}</span>
                      <span className="font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">{strength.label}</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${strength.colorClass} transition-all duration-300 ease-out`}
                        style={{ width: `${strength.widthPercent}%` }}
                      />
                    </div>
                  </div>
                );
              })()}
>>>>>>> d5fb7ab (Fix)
              <p className="text-xs text-slate-500">
                {mode === 'register'
                  ? t('After registration, the existing secure Flask OTP screen will open.', 'রেজিস্ট্রেশনের পর বিদ্যমান নিরাপদ Flask OTP স্ক্রিন খুলবে।')
                  : t('Your Flask session is stored in a secure cookie; 2FA is verified server-side.', 'আপনার Flask session নিরাপদ cookie-তে সংরক্ষিত থাকে; 2FA সার্ভারে যাচাই হয়।')}
              </p>
              <button
                type="submit"
                disabled={isSubmitting || isFlaskAuthLoading}
<<<<<<< HEAD
                className="w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-hover disabled:opacity-60 transition-colors shadow-sm"
=======
                className="marketplace-action-button w-full rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white hover:bg-primary-hover disabled:opacity-60 transition-colors shadow-sm"
>>>>>>> d5fb7ab (Fix)
              >
                {isSubmitting ? t('Please wait…', 'অপেক্ষা করুন…') : mode === 'login' ? t('Sign in to NexHaat', 'NexHaat-এ সাইন ইন') : t('Continue to OTP verification', 'OTP verification-এ যান')}
              </button>
            </form>
          </>
        )}

        {!flaskUser && mode === 'login' && (
          <section className="mt-5 border-t border-border pt-4" aria-labelledby="preview-workspaces-title">
            <div className="flex items-center justify-between gap-3">
              <h3 id="preview-workspaces-title" className="text-xs font-extrabold uppercase tracking-wide text-navy dark:text-blue-100">
                {t('Local preview workspaces', 'লোকাল প্রিভিউ ওয়ার্কস্পেস')}
              </h3>
              <span className="rounded-full bg-primary-light px-2 py-0.5 text-[10px] font-bold text-primary dark:bg-blue-950 dark:text-blue-200">
                {t('Preview only', 'শুধু প্রিভিউ')}
              </span>
            </div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              {t(
                'These local views do not sign you in or grant marketplace permissions.',
                'এগুলো স্থানীয় view; সাইন-ইন বা marketplace permission দেয় না।',
              )}
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {([
                ['customer', 'Customer', 'ক্রেতা'],
                ['seller', 'Seller', 'বিক্রেতা'],
                ['rider', 'Rider', 'রাইডার'],
                ['admin', 'Admin', 'অ্যাডমিন'],
              ] as Array<[UserRole, string, string]>).map(([role, label, labelBn]) => (
                <button
                  key={role}
                  type="button"
                  aria-pressed={currentUser.role === role}
                  onClick={() => {
                    setUserRole(role);
                    onClose();
                  }}
                  className={`marketplace-action-button rounded-xl border px-3 py-2 text-xs font-bold transition-colors ${
                    currentUser.role === role
                      ? 'border-primary bg-primary-light text-primary dark:border-sky-400/50 dark:bg-blue-950 dark:text-blue-100'
                      : 'border-border bg-white text-navy hover:border-primary/50 hover:bg-primary-light/60 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'
                  }`}
                >
                  {t(label, labelBn)}
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : modalContent;
};
