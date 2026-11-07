import React, { useState, useEffect } from 'react';
import { usePWAInstall } from '../lib/usePWAInstall';
import { Smartphone, Download, CheckCircle, X, ShieldCheck, Copy, Check, Info } from 'lucide-react';
import { DEFAULT_APK_FILENAME, downloadApk, getApkMetadata, ApkMetadata, ApkProgress } from '../services/apkDownloadService';

interface PWAInstallButtonProps {
  variant?: 'compact' | 'full' | 'banner';
}

export const PWAInstallButton: React.FC<PWAInstallButtonProps> = ({ variant = 'compact' }) => {
  const { isInstallable, isInstalled, isIOS, install } = usePWAInstall();
  const [showIOSGuide, setShowIOSGuide] = useState(false);
  const [showAndroidModal, setShowAndroidModal] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<ApkProgress | null>(null);
  const [downloadMessage, setDownloadMessage] = useState<string | null>(null);
  const [copiedSha, setCopiedSha] = useState(false);
  const [apkMetadata, setApkMetadata] = useState<ApkMetadata | null>(null);
  const [showManualPwaInfo, setShowManualPwaInfo] = useState(false);

  // A download is only offered when the server reports an existing, verified artifact.
  // A stale metadata file must never make a missing package look installable.
  const apkAvailable = Boolean(apkMetadata?.exists && apkMetadata?.verified);

  // Load latest APK metadata on mount
  useEffect(() => {
    let isMounted = true;
    getApkMetadata().then((data) => {
      if (isMounted) {
        setApkMetadata(data);
      }
    });
    return () => {
      isMounted = false;
    };
  }, []);

  // If already running as an installed standalone PWA, hide install buttons
  if (isInstalled) {
    return null;
  }

  const handleOpenModal = () => {
    if (isIOS) {
      setShowIOSGuide(true);
      return;
    }
    setShowAndroidModal(true);
  };

  const handleDownloadApk = async () => {
    if (isDownloading) return;
    if (!apkAvailable) {
      setDownloadMessage(
        'No verified Android build is available yet. You can still add NexHaat to your home screen as a web app.',
      );
      return;
    }
    setDownloadMessage(null);
    setIsDownloading(true);
    setDownloadProgress(null);

    try {
      const metadata = apkMetadata || (await getApkMetadata());
      const result = await downloadApk(
        (progress) => setDownloadProgress(progress),
        { filename: metadata.displayName || DEFAULT_APK_FILENAME }
      );

      if (!result.success) {
        setDownloadMessage(result.error || 'The Android app download could not be started.');
      } else {
        setDownloadMessage('Download started! Check your browser notifications or Downloads folder.');
      }
    } catch {
      setDownloadMessage('Could not initiate APK download. Please try the direct link below.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleCopySha256 = () => {
    if (!apkMetadata?.sha256) return;
    navigator.clipboard.writeText(apkMetadata.sha256).then(() => {
      setCopiedSha(true);
      setTimeout(() => setCopiedSha(false), 2000);
    });
  };

  const versionText = apkMetadata?.version ? `v${apkMetadata.version}` : 'v1.0.0';
  const sizeText = apkMetadata?.sizeFormatted && apkMetadata.sizeFormatted !== 'Unavailable'
    ? apkMetadata.sizeFormatted
    : '';

  return (
    <>
      {variant === 'compact' && (
        <button
          type="button"
          onClick={handleOpenModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-primary text-white hover:bg-primary-deep shadow-sm transition active:scale-95"
          title="Install NexHaat Android App"
          aria-label="Install NexHaat Android App"
        >
          <Smartphone className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Get App</span>
          <span className="sm:hidden">App</span>
          {sizeText && (
            <span className="hidden md:inline-block text-[10px] bg-white/20 px-1.5 py-0.2 rounded-full font-mono">
              {versionText}
            </span>
          )}
        </button>
      )}

      {variant === 'full' && (
        <button
          type="button"
          onClick={handleOpenModal}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-primary to-blue-600 text-white shadow-md hover:shadow-lg transition active:scale-98"
        >
          <Download className="w-4 h-4" />
          <span>Install NexHaat on Android {versionText && `(${versionText})`}</span>
        </button>
      )}

      {variant === 'banner' && (
        <div className="flex items-center justify-between p-3 rounded-2xl bg-primary/10 border border-primary/20">
          <div className="flex items-center gap-2.5">
            <Smartphone className="w-5 h-5 text-primary" />
            <div>
              <p className="text-xs font-bold text-ink">Get the NexHaat Android App</p>
              <p className="text-[11px] text-muted">Faster shopping, offline haat browsing & real-time order tracking.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleOpenModal}
            className="px-3 py-1.5 rounded-xl text-xs font-bold bg-primary text-white hover:bg-primary-deep transition shrink-0"
          >
            Download {sizeText ? `(${sizeText})` : ''}
          </button>
        </div>
      )}

      {/* Android / APK Release Modal */}
      {showAndroidModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-lg rounded-2xl bg-surface p-6 shadow-2xl border border-line dark:border-slate-800 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <img src="/logo.svg" alt="NexHaat" className="w-12 h-12 rounded-2xl shadow-md border border-line" />
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-bold text-ink dark:text-white">NexHaat for Android</h3>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                      {versionText}
                    </span>
                  </div>
                  <p className="text-xs text-muted flex items-center gap-1 mt-0.5">
                    <ShieldCheck className={`w-3.5 h-3.5 inline ${apkAvailable ? 'text-emerald-600' : 'text-amber-600'}`} />
                    {apkAvailable ? `Verified Release ${sizeText ? `• ${sizeText}` : ''}` : 'APK release not available yet'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowAndroidModal(false)}
                className="text-muted hover:text-ink p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Core Features */}
            <div className="mt-4 space-y-2.5 bg-slate-50 dark:bg-slate-800/50 p-3.5 rounded-xl border border-line dark:border-slate-700">
              <div className="flex items-start gap-2.5 text-xs text-ink/90 dark:text-slate-300">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Native Android Performance:</strong> Kotlin & Jetpack Compose app with offline catalog caching.</span>
              </div>
              <div className="flex items-start gap-2.5 text-xs text-ink/90 dark:text-slate-300">
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Instant Haat Updates:</strong> Real-time rider route alerts & vendor price broadcasts.</span>
              </div>
            </div>

            {/* Download Action & Progress */}
            <div className="mt-5 space-y-3">
              <button
                type="button"
                disabled={isDownloading || !apkAvailable}
                onClick={handleDownloadApk}
                aria-disabled={isDownloading || !apkAvailable}
                className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-primary text-white font-bold text-sm hover:bg-primary-deep shadow-md transition disabled:opacity-60 disabled:cursor-not-allowed active:scale-98"
              >
                <Download className="w-4 h-4" />
                <span>
                  {!apkAvailable
                    ? 'APK Download Unavailable'
                    : isDownloading
                      ? downloadProgress
                        ? `Downloading ${downloadProgress.percent}% (${downloadProgress.formattedReceived} / ${downloadProgress.formattedTotal})`
                        : 'Preparing APK Package...'
                      : `Download APK ${sizeText ? `(${sizeText})` : ''}`}
                </span>
              </button>

              {downloadMessage && (
                <div role="status" className="rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/50 p-3 text-xs text-blue-900 dark:text-blue-200 flex items-start gap-2">
                  <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <span>{downloadMessage}</span>
                </div>
              )}

              {/* Direct links are only shown for a verified artifact */}
              {apkAvailable ? (
                <div className="flex items-center justify-between text-xs text-muted px-1">
                  <span>Direct link:</span>
                  <div className="flex items-center gap-3">
                    <a
                      href="/api/download/apk"
                      download={apkMetadata?.displayName || 'NexHaat-v1.0.0.apk'}
                      className="text-primary hover:underline font-medium"
                    >
                      API Endpoint
                    </a>
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-amber-700 dark:text-amber-300 px-1">
                  {apkMetadata?.unavailableReason ||
                    'The Android package is not published yet. Use “Add to Home Screen” below to install NexHaat now.'}
                </p>
              )}
            </div>

            {/* Checksum Verification Box */}
            {apkMetadata?.sha256 && (
              <div className="mt-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-line dark:border-slate-800 text-xs">
                <div className="flex items-center justify-between font-semibold text-ink dark:text-slate-200 mb-1.5">
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Package Integrity Checksum (SHA-256)
                  </span>
                  <button
                    type="button"
                    onClick={handleCopySha256}
                    className="flex items-center gap-1 text-[11px] text-primary hover:text-primary-deep font-medium"
                    title="Copy SHA-256"
                  >
                    {copiedSha ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-600">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <code className="block text-[10px] text-muted break-all font-mono select-all bg-white dark:bg-slate-950 p-1.5 rounded border border-line dark:border-slate-800">
                  {apkMetadata.sha256}
                </code>
              </div>
            )}

            {/* Installation Instructions */}
            <div className="mt-4 border-t border-line dark:border-slate-800 pt-3 text-xs text-ink/80 dark:text-slate-300">
              <p className="font-bold text-ink dark:text-white mb-2">Android Installation Steps:</p>
              <ol className="list-decimal list-inside space-y-1.5 text-muted dark:text-slate-400">
                <li>Tap <strong>Download APK</strong> above to save the package.</li>
                <li>When download finishes, tap the notification or open your <strong>Downloads</strong> folder.</li>
                <li>If prompted, enable <strong>Allow from this source</strong> for Chrome or your file manager.</li>
                <li>Tap <strong>Install</strong> to complete setup.</li>
              </ol>
            </div>

            {/* Alternative PWA Install */}
            <div className="mt-5 border-t border-line dark:border-slate-800 pt-3 space-y-2">
              <button
                type="button"
                onClick={async () => {
                  if (isInstallable) {
                    await install();
                    setShowAndroidModal(false);
                  } else {
                    setShowManualPwaInfo(!showManualPwaInfo);
                  }
                }}
                className="w-full py-2.5 rounded-xl border border-line dark:border-slate-700 text-xs font-semibold text-ink dark:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition flex items-center justify-center gap-2"
              >
                <span>Or Add to Home Screen (Instant PWA)</span>
              </button>

              {showManualPwaInfo && (
                <div className="p-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50 text-[11px] text-amber-900 dark:text-amber-200">
                  <p className="font-bold">To install via Chrome on Android:</p>
                  <p>1. Tap the browser menu (⋮) in the top-right corner.</p>
                  <p>2. Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</p>
                </div>
              )}
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
