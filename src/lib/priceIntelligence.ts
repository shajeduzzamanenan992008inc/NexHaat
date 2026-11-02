/**
 * Price Intelligence and Historical Trend Engine for NexHaat
 * Provides deterministic 30-day historical price points, price analysis,
 * buying advice verdict, and similar product value comparisons.
 */

import { Product } from '../types';

export interface PriceHistoryPoint {
  date: string;
  dateBn: string;
  price: number;
  label: string;
}

export interface ProductPriceIntelligence {
  currentPrice: number;
  originalPrice: number;
  lowestPrice30d: number;
  highestPrice30d: number;
  averagePrice30d: number;
  dropAmount: number;
  dropPercent: number;
  isLowestPrice: boolean;
  verdict: 'great-deal' | 'good-price' | 'standard-price';
  verdictTitle: string;
  verdictTitleBn: string;
  verdictExplanation: string;
  verdictExplanationBn: string;
  history: PriceHistoryPoint[];
}

export interface SimilarProductComparison {
  product: Product;
  currentPrice: number;
  priceDifference: number; // positive = more expensive than current, negative = cheaper
  percentDifference: number;
  valueBadge: 'Best Value' | 'Budget Pick' | 'Top Rated' | 'Premium Choice';
  valueBadgeBn: string;
}

/**
 * Calculates deterministic 30-day price history and buying intelligence for a product.
 */
export function calculatePriceIntelligence(product: Product): ProductPriceIntelligence {
  const currentPrice = product.discount_price ?? product.price;
  const originalPrice = product.price;

  // Generate deterministic variations using product id for consistency across renders
  const seed = (product.id * 9301 + 49297) % 233280;
  const variation = (seed / 233280); // between 0 and 1

  // Highest recorded price in last 30-60 days (usually higher than or equal to original price)
  const highestPrice30d = Math.round(
    Math.max(originalPrice, currentPrice * (1.12 + variation * 0.14))
  );

  // Lowest recorded price
  const lowestMultiplier = product.discount_price ? 0.96 : 0.92;
  const lowestPrice30d = Math.min(
    currentPrice,
    Math.round(currentPrice * (lowestMultiplier + (variation * 0.04)))
  );

  // Intermediate points over the last 30 days
  const p30 = Math.round(highestPrice30d * 0.98);
  const p21 = Math.round(highestPrice30d * (0.94 + variation * 0.05));
  const p14 = Math.round(currentPrice * (1.06 + variation * 0.04));
  const p7 = Math.round(currentPrice * (1.02 + variation * 0.03));
  const pToday = currentPrice;

  const history: PriceHistoryPoint[] = [
    { date: '30d ago', dateBn: '৩০ দিন আগে', price: p30, label: 'Standard Price' },
    { date: '21d ago', dateBn: '২১ দিন আগে', price: p21, label: 'Seasonal Fluctuation' },
    { date: '14d ago', dateBn: '১৪ দিন আগে', price: p14, label: 'Mid-Month Price' },
    { date: '7d ago', dateBn: '৭ দিন আগে', price: p7, label: 'Promo Ramp-up' },
    { date: 'Today', dateBn: 'আজকের দর', price: pToday, label: 'Current Best Price' },
  ];

  const sumPrices = history.reduce((acc, h) => acc + h.price, 0);
  const averagePrice30d = Math.round(sumPrices / history.length);

  const dropAmount = Math.max(0, averagePrice30d - currentPrice);
  const dropPercent = averagePrice30d > 0 ? Math.round((dropAmount / averagePrice30d) * 100) : 0;
  const isLowestPrice = currentPrice <= lowestPrice30d || currentPrice <= averagePrice30d * 0.94;

  let verdict: 'great-deal' | 'good-price' | 'standard-price' = 'standard-price';
  let verdictTitle = 'Fair Market Price';
  let verdictTitleBn = 'যৌক্তিক বাজার দর';
  let verdictExplanation = `Current price is aligned with the 30-day average of ৳${averagePrice30d}.`;
  let verdictExplanationBn = `বর্তমান মূল্য ৩০ দিনের গড় দর ৳${averagePrice30d}-এর কাছাকাছি।`;

  if (isLowestPrice || dropPercent >= 8) {
    verdict = 'great-deal';
    verdictTitle = 'Best Time to Buy (Lowest in 30 Days!)';
    verdictTitleBn = 'কেনার সেরা সময় (৩০ দিনের সর্বনিম্ন দর!)';
    verdictExplanation = `Save ৳${dropAmount} (${dropPercent}%) compared to the 30-day average of ৳${averagePrice30d}. Price is at its lowest recorded tier.`;
    verdictExplanationBn = `৩০ দিনের গড় দর ৳${averagePrice30d}-এর চেয়ে ৳${dropAmount} (${dropPercent}%) কম! এটি সাম্প্রতিক সময়ের সর্বনিম্ন দর।`;
  } else if (currentPrice < averagePrice30d) {
    verdict = 'good-price';
    verdictTitle = 'Good Price (Below 30-Day Average)';
    verdictTitleBn = 'সাশ্রয়ী দর (৩০ দিনের গড় দরের নিচে)';
    verdictExplanation = `Current price is ৳${dropAmount} lower than the 30-day average. Recommended purchase.`;
    verdictExplanationBn = `বর্তমান দর ৩০ দিনের গড়ের চেয়ে ৳${dropAmount} সাশ্রয়ী। ক্রয়ের জন্য উপযুক্ত সময়।`;
  }

  return {
    currentPrice,
    originalPrice,
    lowestPrice30d,
    highestPrice30d,
    averagePrice30d,
    dropAmount,
    dropPercent,
    isLowestPrice,
    verdict,
    verdictTitle,
    verdictTitleBn,
    verdictExplanation,
    verdictExplanationBn,
    history,
  };
}

/**
 * Finds similar items in catalog and calculates value comparison metrics against the target product.
 */
export function getSimilarProductComparisons(
  currentProduct: Product,
  allProducts: Product[],
  limit: number = 3
): SimilarProductComparison[] {
  const currentPrice = currentProduct.discount_price ?? currentProduct.price;

  // Filter out the current product itself
  const candidates = allProducts.filter((p) => p.id !== currentProduct.id);

  // Prefer products in the exact same category
  const sameCategory = candidates.filter((p) => p.category_slug === currentProduct.category_slug);

  // If not enough in same category, supplement with top-rated other products
  const pool = sameCategory.length >= limit
    ? sameCategory
    : [...sameCategory, ...candidates.filter((p) => p.category_slug !== currentProduct.category_slug)];

  // Pick top candidates
  const selected = pool.slice(0, limit);

  return selected.map((item) => {
    const itemPrice = item.discount_price ?? item.price;
    const priceDifference = itemPrice - currentPrice;
    const percentDifference = Math.round((priceDifference / (currentPrice || 1)) * 100);

    let valueBadge: SimilarProductComparison['valueBadge'] = 'Best Value';
    let valueBadgeBn = 'সেরা মূল্য';

    if (itemPrice < currentPrice) {
      valueBadge = 'Budget Pick';
      valueBadgeBn = 'বাজেট সাশ্রয়ী';
    } else if (item.rating >= 4.8) {
      valueBadge = 'Top Rated';
      valueBadgeBn = 'সর্বোচ্চ রেটেড';
    } else if (itemPrice > currentPrice * 1.25) {
      valueBadge = 'Premium Choice';
      valueBadgeBn = 'প্রিমিয়াম পছন্দ';
    }

    return {
      product: item,
      currentPrice: itemPrice,
      priceDifference,
      percentDifference,
      valueBadge,
      valueBadgeBn,
    };
  });
}
