import React, { useState } from 'react';
import { usePWAInstall } from '../lib/usePWAInstall';
import { Smartphone, Download, CheckCircle, X } from 'lucide-react';
import { DEFAULT_APK_FILENAME, downloadApk, getApkMetadata } from '../services/apkDownloadService';

interface PWAInstallButtonProps {
  variant?: 'compact' | 'full' | 'banner';
}

export const PWAInstallButton: React.FC<PWAInstallButtonProps> = ({ variant = 'compact' }) => {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);
  const [showAndroidModal, setShowAndroidModal] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState<string | null>(null);

  // If already running as an installed standalone PWA, hide install buttons
  if (isInstalled) {
    return null;
  }

  const handleInstallClick = async () => {
    if (isDownloading) return;
    setDownloadMessage(null);

    if (isIOS) {
      setShowIOSGuide(true);
      return;
    }

    setIsDownloading(true);
    try {
      const metadata = await getApkMetadata();
      if (metadata.exists) {
        const result = await downloadApk(undefined, {
          filename: metadata.displayName || DEFAULT_APK_FILENAME,
        });
        if (result.success) return;
        setDownloadMessage(result.error || 'The Android app download could not be started.');
      } else if (isInstallable) {
        await install();
        return;
      } else {
        setDownloadMessage('A downloadable Android APK is not available on this server yet.');
      }
    } catch {
      setDownloadMessage('Could not check Android app availability. Please try again later.');
    } finally {
      setIsDownloading(false);
    }

    setShowAndroidModal(true);
  };

  return (
    <>
      {variant === 'compact' && (
        <button
          type="button"
          disabled={isDownloading}
          onClick={handleInstallClick}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-primary text-white hover:bg-primary-deep shadow-sm transition active:scale-95 disabled:opacity-60"
          title="Install NexHaat Android App"
          aria-label="Install NexHaat Android App"
          aria-busy={isDownloading}
        >
          <Smartphone className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Get App</span>
          <span className="sm:hidden">App</span>
        </button>
      )}

      {variant === 'full' && (
        <button
          type="button"
          disabled={isDownloading}
          onClick={handleInstallClick}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-primary to-blue-600 text-white shadow-md hover:shadow-lg transition active:scale-98 disabled:opacity-60"
          aria-busy={isDownloading}
        >
          <Download className="w-4 h-4" />
          <span>Install NexHaat on Android</span>
        </button>
      )}

      {/* Android / PWA App Modal */}
      {showAndroidModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl bg-surface p-6 shadow-2xl border border-line dark:border-slate-800">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <img src="/logo.svg" alt="NexHaat" className="w-12 h-12 rounded-2xl shadow-md" />
                <div>
                  <h3 className="text-lg font-bold text-ink dark:text-white">NexHaat for Android</h3>
                  <p className="text-xs text-muted">Hyper-local Multivendor Marketplace</p>
                </div>
              </div>
              <button
                onClick={() => setShowAndroidModal(false)}
                className="text-muted hover:text-ink p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="mt-4 space-y-3">
              <div className="flex items-start gap-2.5 text-xs text-ink/80 dark:text-slate-300">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Instant Home Screen Access:</strong> Launch NexHaat in full screen like a native mobile app.</span>
              </div>
              <div className="flex items-start gap-2.5 text-xs text-ink/80 dark:text-slate-300">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Offline Catalog Cache:</strong> Browse fresh local haat produce even on slow or spotty 4G connections.</span>
              </div>
              <div className="flex items-start gap-2.5 text-xs text-ink/80 dark:text-slate-300">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Native Android Companion:</strong> Full Kotlin & Jetpack Compose native project available in <code>/android</code> with Retrofit API client.</span>
              </div>
            </div>

            {downloadMessage && (
              <p role="status" className="mt-4 rounded-xl bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                {downloadMessage}
              </p>
            )}

            <div className="mt-6 space-y-2">
              <button
                type="button"
                onClick={async () => {
                  if (isInstallable) {
                    await install();
                    setShowAndroidModal(false);
                  } else {
                    alert("To install on Chrome for Android:\n1. Tap the browser menu (⋮) in the top-right.\n2. Tap 'Install app' or 'Add to Home screen'.");
                    setShowAndroidModal(false);
                  }
                }}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-primary text-white font-semibold text-sm hover:bg-primary-deep shadow-md transition"
              >
                <Download className="w-4 h-4" />
                <span>Install App to Home Screen</span>
              </button>

              <button
                type="button"
                onClick={() => setShowAndroidModal(false)}
                className="w-full py-2.5 rounded-xl border border-line dark:border-slate-700 text-xs font-semibold text-muted hover:text-ink transition"
              >
                Continue in Browser
              </button>
            </div>
          </div>
        </div>
      )}

      {/* iOS Safari Guide Modal */}
      {showIOSGuide && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-2xl bg-surface p-6 shadow-2xl border border-line">
            <h3 className="text-lg font-bold text-ink">Install on iPhone / iPad</h3>
            <p className="mt-2 text-sm text-muted">
              1. Tap the <strong>Share</strong> button (box with upward arrow) in the Safari toolbar.<br />
              2. Scroll down and tap <strong>Add to Home Screen</strong>.<br />
              3. Tap <strong>Add</strong> in the top right.
            </p>
            <button
              type="button"
              onClick={() => setShowIOSGuide(false)}
              className="mt-5 w-full rounded-xl bg-slate-100 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-200 transition"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
};
