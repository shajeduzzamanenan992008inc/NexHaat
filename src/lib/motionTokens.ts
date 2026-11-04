/**
 * NexHaat Unified Motion Tokens & Calculation Engine
 * 
 * Consistent motion curves, durations, and physics calculations
 * shared between Web (CSS/JS) and Android (Jetpack Compose).
 */

import confetti from 'canvas-confetti';

export const MOTION_DURATIONS = {
  instant: 100,     // Tooltips and micro-indicators
  fast: 150,        // Button press and badge feedback
  normal: 280,      // Card and drawer interactions
  page: 320,        // Lightweight view entrance
  deliberate: 450,  // Dialog and major state changes
  complex: 450,     // Compatibility alias; choreography stays below 500ms
} as const;

export const MOTION_EASINGS = {
  // Snappy spring-like rebound for interactive buttons and hearts
  spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  // Deceleration curve for elements entering the viewport
  decelerate: 'cubic-bezier(0.0, 0.0, 0.2, 1.0)',
  // Acceleration curve for elements leaving the viewport
  accelerate: 'cubic-bezier(0.4, 0.0, 1.0, 1.0)',
  // Natural standard curve for movement and transitions
  standard: 'cubic-bezier(0.4, 0.0, 0.2, 1.0)',
} as const;

export interface CardTiltResult {
  rotateX: number;
  rotateY: number;
  transformStyle: string;
}

/**
 * Calculates 3D card perspective tilt based on mouse coordinates relative to element bounding box.
 * Maximum tilt is bounded to avoid disorientation.
 */
export function calculateCardTilt(
  clientX: number,
  clientY: number,
  rect: { left: number; top: number; width: number; height: number },
  maxTiltDegrees = 8
): CardTiltResult {
  if (rect.width <= 0 || rect.height <= 0) {
    return { rotateX: 0, rotateY: 0, transformStyle: 'perspective(1000px) rotateX(0deg) rotateY(0deg)' };
  }

  const relativeX = clientX - rect.left;
  const relativeY = clientY - rect.top;

  const normalizedX = (relativeX / rect.width) * 2 - 1; // -1 to 1
  const normalizedY = (relativeY / rect.height) * 2 - 1; // -1 to 1

  // Invert Y for natural tilt towards mouse
  const rotateX = Number((-normalizedY * maxTiltDegrees).toFixed(2));
  const rotateY = Number((normalizedX * maxTiltDegrees).toFixed(2));

  return {
    rotateX,
    rotateY,
    transformStyle: `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
  };
}

/**
 * Calculates dynamic password strength score and visual meter parameters
 */
export interface PasswordStrengthResult {
  score: number; // 0 to 4
  label: string;
  colorClass: string;
  widthPercent: number;
}

export function evaluatePasswordStrength(password: string): PasswordStrengthResult {
  if (!password) {
    return { score: 0, label: 'Too short', colorClass: 'bg-slate-200', widthPercent: 0 };
  }

  let score = 0;
  if (password.length >= 8) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  switch (score) {
    case 1:
      return { score: 1, label: 'Weak', colorClass: 'bg-rose-500', widthPercent: 25 };
    case 2:
      return { score: 2, label: 'Fair', colorClass: 'bg-amber-500', widthPercent: 50 };
    case 3:
      return { score: 3, label: 'Good', colorClass: 'bg-blue-500', widthPercent: 75 };
    case 4:
      return { score: 4, label: 'Ultra Secure', colorClass: 'bg-emerald-500', widthPercent: 100 };
    default:
      return { score: 0, label: 'Very Weak', colorClass: 'bg-rose-500', widthPercent: 15 };
  }
}

/**
 * Triggers a celebratory confetti particle explosion for order completion or security achievements.
 */
export function triggerCelebrationConfetti(): void {
  try {
    if (typeof window === 'undefined') return;

    // Check prefers-reduced-motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    // Double cannon blast from left and right
    const count = 80;
    const defaults = {
      origin: { y: 0.65 },
      zIndex: 99999,
      colors: ['#1769FF', '#1b7a43', '#FF9900', '#fbbf24', '#4D91FF'],
    };

    confetti({
      ...defaults,
      particleCount: Math.floor(count * 0.5),
      spread: 60,
      origin: { x: 0.3, y: 0.6 },
    });

    confetti({
      ...defaults,
      particleCount: Math.floor(count * 0.5),
      spread: 60,
      origin: { x: 0.7, y: 0.6 },
    });
  } catch {
    // Graceful fallback if canvas is restricted
  }
}
