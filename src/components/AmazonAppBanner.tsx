import React, { useState, useEffect } from 'react';
import { usePWAInstall } from '../lib/usePWAInstall';
import { Smartphone, X, Star } from 'lucide-react';
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
    <div className="w-full bg-slate-900 text-white text-xs border-b border-slate-800 transition-all">
      <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={handleDismiss}
            className="text-slate-400 hover:text-white p-0.5"
            aria-label="Dismiss banner"
          >
            <X className="w-4 h-4" />
          </button>
          <img src="/logo.svg" alt="NexHaat App" className="w-8 h-8 rounded-lg shadow-sm shrink-0" />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-bold truncate text-white">NexHaat Android App</span>
              <span className="hidden sm:inline-flex items-center text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded">
                <Star className="w-2.5 h-2.5 fill-current mr-0.5" /> 4.9 ★ FREE
              </span>
            </div>
            <p className="text-[11px] text-slate-300 truncate">
              Shop fresh haat groceries, track delivery live & enjoy Prime speed.
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
