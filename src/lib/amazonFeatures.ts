/**
 * Amazon Marketplace Feature Utilities & Pure Logic
 * Calculations for bundle discounts, shipping thresholds, review breakdowns,
 * search history management, and delivery promises.
 */

import { Product } from '../types';

export interface BundlePricing {
  originalTotal: number;
  bundleDiscountPercent: number;
  discountedTotal: number;
  savings: number;
}

export interface ShippingProgress {
  threshold: number;
  progressPercent: number;
  remainingAmount: number;
  isFreeEligible: boolean;
}

export interface RatingBreakdown {
  star: number;
  count: number;
  percentage: number;
}

export interface ReviewDistribution {
  total: number;
  average: number;
  breakdown: RatingBreakdown[];
}

export interface DeliveryPromise {
  hoursLeft: number;
  minutesLeft: number;
  isSameDayAvailable: boolean;
  deliveryDateText: string;
}

/**
 * Calculates bundle price, bundle discount, and total savings for "Frequently Bought Together"
 */
export function calculateBundlePrice(
  products: Product[],
  bundleDiscountPercent: number = 10
): BundlePricing {
  const originalTotal = products.reduce((sum, p) => sum + (p.discount_price ?? p.price), 0);
  const discountMultiplier = Math.max(0, Math.min(100, bundleDiscountPercent)) / 100;
  const savings = Math.round(originalTotal * discountMultiplier);
  const discountedTotal = Math.max(0, originalTotal - savings);

  return {
    originalTotal,
    bundleDiscountPercent,
    discountedTotal,
    savings,
  };
}

/**
 * Calculates Amazon-style Free Delivery threshold progress
 */
export function calculateFreeShippingProgress(
  cartSubtotal: number,
  threshold: number = 1500,
  isPrime: boolean = false
): ShippingProgress {
  if (isPrime) {
    return {
      threshold,
      progressPercent: 100,
      remainingAmount: 0,
      isFreeEligible: true,
    };
  }

  const validSubtotal = Math.max(0, cartSubtotal);
  const progressPercent = Math.min(100, Math.round((validSubtotal / threshold) * 100));
  const remainingAmount = Math.max(0, threshold - validSubtotal);
  const isFreeEligible = remainingAmount === 0;

  return {
    threshold,
    progressPercent,
    remainingAmount,
    isFreeEligible,
  };
}

/**
 * Calculates star rating distribution (5-star down to 1-star) with percentages
 */
export function calculateReviewDistribution(
  reviews: Array<{ rating: number }>
): ReviewDistribution {
  const total = reviews.length;
  if (total === 0) {
    return {
      total: 0,
      average: 5.0,
      breakdown: [5, 4, 3, 2, 1].map((star) => ({ star, count: 0, percentage: 0 })),
    };
  }

  const counts: Record<number, number> = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
  let sum = 0;

  for (const r of reviews) {
    const rounded = Math.max(1, Math.min(5, Math.round(r.rating)));
    counts[rounded] = (counts[rounded] || 0) + 1;
    sum += r.rating;
  }

  const average = Number((sum / total).toFixed(1));
  const breakdown: RatingBreakdown[] = [5, 4, 3, 2, 1].map((star) => ({
    star,
    count: counts[star],
    percentage: Math.round((counts[star] / total) * 100),
  }));

  return {
    total,
    average,
    breakdown,
  };
}

/**
 * Updates search history with deduplication and max limit
 */
export function manageSearchHistory(
  history: string[],
  newQuery: string,
  maxItems: number = 8
): string[] {
  const cleaned = newQuery.trim();
  if (!cleaned) return history;

  const filtered = history.filter((q) => q.toLowerCase() !== cleaned.toLowerCase());
  return [cleaned, ...filtered].slice(0, maxItems);
}

/**
 * Computes Amazon Prime delivery promise countdown
 */
export function calculateDeliveryPromise(now: Date = new Date()): DeliveryPromise {
  const targetHour = 19; // 7:00 PM same-day cutoff
  const currentHour = now.getHours();
  const currentMinute = now.getMinutes();

  if (currentHour < targetHour) {
    const hoursLeft = targetHour - 1 - currentHour;
    const minutesLeft = 60 - currentMinute;
    return {
      hoursLeft,
      minutesLeft,
      isSameDayAvailable: true,
      deliveryDateText: 'Today by 8:00 PM',
    };
  } else {
    // Tomorrow morning
    const hoursLeft = 24 + targetHour - 1 - currentHour;
    const minutesLeft = 60 - currentMinute;
    return {
      hoursLeft,
      minutesLeft,
      isSameDayAvailable: false,
      deliveryDateText: 'Tomorrow by 12:00 PM',
    };
  }
}
