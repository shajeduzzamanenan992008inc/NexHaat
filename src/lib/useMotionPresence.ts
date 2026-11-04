import { useEffect, useState } from 'react';
import { MOTION_DURATIONS } from './motionTokens';

/** Keeps an overlay mounted just long enough to finish its close animation. */
export function useMotionPresence(isOpen: boolean, exitDurationMs = MOTION_DURATIONS.normal) {
  const [isPresent, setIsPresent] = useState(isOpen);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsPresent(true);
      setIsExiting(false);
      return;
    }

    if (!isPresent) return;

    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    if (reducedMotion) {
      setIsPresent(false);
      setIsExiting(false);
      return;
    }

    setIsExiting(true);
    const timeout = window.setTimeout(() => {
      setIsPresent(false);
      setIsExiting(false);
    }, exitDurationMs);

    return () => window.clearTimeout(timeout);
  }, [exitDurationMs, isOpen, isPresent]);

  return { isPresent, isExiting };
}
