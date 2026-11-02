/**
 * Detailed Price Trend Data Generator for NexHaat Recharts Visualizations
 * Deterministic generation of historical data points for 7d, 14d, and 30d timeframes.
 */

import { Product } from '../types';
import { calculatePriceIntelligence } from './priceIntelligence';

export interface DetailedTrendPoint {
  date: string;
  dateBn: string;
  dayLabel: string;
  dayLabelBn: string;
  price: number;
  isLowest: boolean;
  isHighest: boolean;
  isCurrent: boolean;
  eventNote?: string;
  eventNoteBn?: string;
}

export interface DetailedPriceTrendData {
  timeframe: '7d' | '14d' | '30d';
  points: DetailedTrendPoint[];
  currentPrice: number;
  lowestPrice: number;
  highestPrice: number;
  averagePrice: number;
  priceDropFromPeak: number;
  percentDropFromPeak: number;
  isAtLowest: boolean;
  trendDirection: 'falling' | 'stable' | 'rising';
}

/**
 * Generates deterministic daily price trend data for Recharts visualization.
 */
export function getDetailedPriceTrend(
  product: Product,
  timeframe: '7d' | '14d' | '30d' = '30d'
): DetailedPriceTrendData {
  const intel = calculatePriceIntelligence(product);
  const currentPrice = intel.currentPrice;

  // Determine number of days
  const numDays = timeframe === '7d' ? 7 : timeframe === '14d' ? 14 : 30;

  // Deterministic seed based on product ID
  const seed = (product.id * 16807 + 789221) % 2147483647;

  // Day names for English and Bengali
  const dayNamesEn = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const dayNamesBn = ['রবি', 'সোম', 'মঙ্গল', 'বুধ', 'বৃহঃ', 'শুক্র', 'শনি'];
  const monthNamesEn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monthNamesBn = ['জানু', 'ফেব্রু', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টে', 'অক্টো', 'নভে', 'ডিসে'];

  const points: DetailedTrendPoint[] = [];

  // Generate synthetic but realistic curve ending at currentPrice today
  // Points go from (numDays - 1) days ago to day 0 (today)
  const now = new Date();

  // Baseline start price (typically higher than current or fluctuating)
  const peakPrice = intel.highestPrice30d;
  const troughPrice = intel.lowestPrice30d;

  for (let i = numDays - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);

    const dayOfWeek = d.getDay();
    const dayNameEn = dayNamesEn[dayOfWeek];
    const dayNameBn = dayNamesBn[dayOfWeek];
    const dateFormattedEn = `${d.getDate()} ${monthNamesEn[d.getMonth()]}`;
    const dateFormattedBn = `${d.getDate()} ${monthNamesBn[d.getMonth()]}`;

    let price: number;

    if (i === 0) {
      // Today is always the current actual price
      price = currentPrice;
    } else {
      // Deterministic smooth curve with slight noise
      const progress = (numDays - 1 - i) / (numDays - 1); // 0 at oldest, 1 at today
      const pseudoNoise = Math.sin((seed + i * 17) % 360) * 0.5 + 0.5; // 0 to 1

      // Interpolate between peak and current with occasional promotional dips
      const baseInterpolation = peakPrice - (peakPrice - currentPrice) * progress;
      const variationRange = (peakPrice - troughPrice) * 0.25;
      const fluctuatingPrice = baseInterpolation + (pseudoNoise - 0.5) * variationRange;

      price = Math.round(Math.max(troughPrice, Math.min(peakPrice, fluctuatingPrice)));
    }

    points.push({
      date: dateFormattedEn,
      dateBn: dateFormattedBn,
      dayLabel: i === 0 ? 'Today' : dateFormattedEn,
      dayLabelBn: i === 0 ? 'আজ' : dateFormattedBn,
      price,
      isLowest: false,
      isHighest: false,
      isCurrent: i === 0,
    });
  }

  // Ensure current price is exact
  points[points.length - 1].price = currentPrice;

  // Calculate stats
  const prices = points.map((p) => p.price);
  const lowestPrice = Math.min(...prices);
  const highestPrice = Math.max(...prices);
  const sum = prices.reduce((acc, p) => acc + p, 0);
  const averagePrice = Math.round(sum / prices.length);

  // Mark highest and lowest points
  for (const pt of points) {
    if (pt.price === lowestPrice && !pt.isLowest) {
      pt.isLowest = true;
      pt.eventNote = 'Lowest Price';
      pt.eventNoteBn = 'সর্বনিম্ন দর';
    }
    if (pt.price === highestPrice && !pt.isHighest) {
      pt.isHighest = true;
      pt.eventNote = 'Peak Price';
      pt.eventNoteBn = 'সর্বোচ্চ দর';
    }
  }

  const priceDropFromPeak = Math.max(0, highestPrice - currentPrice);
  const percentDropFromPeak = highestPrice > 0 ? Math.round((priceDropFromPeak / highestPrice) * 100) : 0;
  const isAtLowest = currentPrice <= lowestPrice;

  const firstPrice = points[0].price;
  const trendDirection: DetailedPriceTrendData['trendDirection'] =
    currentPrice < firstPrice ? 'falling' : currentPrice > firstPrice ? 'rising' : 'stable';

  return {
    timeframe,
    points,
    currentPrice,
    lowestPrice,
    highestPrice,
    averagePrice,
    priceDropFromPeak,
    percentDropFromPeak,
    isAtLowest,
    trendDirection,
  };
}
