import React, { useState, useEffect } from 'react';
import { usePWAInstall } from '../lib/usePWAInstall';
import { Smartphone, X } from 'lucide-react';
import { PWAInstallButton } from './PWAInstallButton';

export const AmazonAppBanner: React.FC = () => {
  const { isInstalled } = usePWAInstall();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const isDismissed = sessionStorage.getItem('nexhaat_app_banner_dismissed') === 'true';
    if (isDismissed) setDismissed(true);
  }, []);

  if (isInstalled || dismissed) return null;

  const handleDismiss = () => {
    setDismissed(true);
    sessionStorage.setItem('nexhaat_app_banner_dismissed', 'true');
  };

  return (
    <div className="w-full border-b border-primary/10 bg-primary/5 text-ink text-xs transition-all">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-1.5 sm:px-6">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={handleDismiss}
            className="rounded-full p-1 text-muted transition-colors hover:bg-white hover:text-ink"
            aria-label="Dismiss banner"
          >
            <X className="w-4 h-4" />
          </button>
          <img src="/logo.svg" alt="" className="h-8 w-8 shrink-0 rounded-lg shadow-sm" />
          <div className="min-w-0">
            <span className="block truncate font-bold text-ink">NexHaat on your device</span>
            <p className="truncate text-[11px] text-muted">
              Add NexHaat to your home screen for quick access.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <PWAInstallButton variant="compact" />
        </div>
      </div>
    </div>
  );
};
