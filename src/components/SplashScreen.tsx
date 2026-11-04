import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowRight, ShoppingBag, Sparkles } from 'lucide-react';

interface SplashScreenProps {
  onComplete: () => void;
  brandName?: string;
  tagline?: string;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({
  onComplete,
  brandName = 'NexHaat',
  tagline = "Bangladesh's Premier Multi-Vendor Marketplace",
}) => {
  const [isFadingOut, setIsFadingOut] = useState(false);
  const onCompleteRef = useRef(onComplete);
  const autoDismissRef = useRef<number | undefined>(undefined);
  const completionRef = useRef<number | undefined>(undefined);
  const dismissedRef = useRef(false);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const dismiss = useCallback(() => {
    if (dismissedRef.current) return;
    dismissedRef.current = true;
    if (autoDismissRef.current !== undefined) window.clearTimeout(autoDismissRef.current);
    setIsFadingOut(true);

    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    completionRef.current = window.setTimeout(() => onCompleteRef.current(), reducedMotion ? 0 : 150);
  }, []);

  useEffect(() => {
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    if (reducedMotion) {
      dismissedRef.current = true;
      onCompleteRef.current();
      return;
    }

    // Keep the branded entrance brief; page content remains clickable underneath it.
    autoDismissRef.current = window.setTimeout(dismiss, 300);
    return () => {
      if (autoDismissRef.current !== undefined) window.clearTimeout(autoDismissRef.current);
      if (completionRef.current !== undefined) window.clearTimeout(completionRef.current);
    };
  }, [dismiss]);

  return (
    <>
      <span className="sr-only" role="status" aria-live="polite">
        Welcome to {brandName}.
      </span>
      <div
        className={`pointer-events-none fixed inset-0 z-[10000] flex flex-col items-center justify-center bg-slate-950/95 text-white transition-opacity duration-150 ${
          isFadingOut ? 'opacity-0' : 'opacity-100'
        }`}
      >
        <button
          type="button"
          onClick={dismiss}
          className="pointer-events-auto absolute right-6 top-6 flex items-center gap-1.5 rounded-full bg-white/10 px-3.5 py-1.5 text-xs font-semibold text-slate-300 backdrop-blur-md transition-colors hover:bg-white/20 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300"
          aria-label="Skip NexHaat introduction"
        >
          <span>Skip</span>
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </button>

        <div className="relative z-10 flex max-w-sm flex-col items-center space-y-6 px-6 text-center" aria-hidden="true">
          <div className="relative">
            <div className="absolute -inset-4 rounded-3xl bg-primary/20 blur-xl animate-pulse" />
            <div className="absolute -inset-1 rounded-2xl bg-gradient-to-tr from-primary to-[#4D91FF] opacity-60 blur-sm" />
            <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl border border-white/20 bg-slate-900 shadow-2xl animate-float-slow">
              <ShoppingBag className="h-10 w-10 text-primary" />
              <Sparkles className="absolute right-2 top-2 h-4 w-4 text-amber-400" />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-center gap-2">
              <h1 className="bg-gradient-to-r from-white via-blue-100 to-sky-300 bg-clip-text text-3xl font-black tracking-tight text-transparent">
                {brandName}
              </h1>
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/20 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-widest text-emerald-400">
                Ultra
              </span>
            </div>
            <p className="text-xs font-medium text-slate-400">{tagline}</p>
          </div>
        </div>
      </div>
    </>
  );
};
