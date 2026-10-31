/**
 * Search Analytics & User Search Trends Logic
 * Computes metrics, aggregations, conversion rates, and insights for search dashboard
 */

export interface SearchTrendPoint {
  date: string;
  fullDate?: string;
  searches: number;
  conversions: number;
  mobile: number;
  desktop: number;
}

export interface KeywordPerformance {
  keyword: string;
  keyword_bn?: string;
  category: string;
  searchVolume: number;
  clickThroughRate: number; // percentage, e.g. 72.4
  conversionRate: number; // percentage, e.g. 16.5
  revenueGenerated: number; // in BDT
  trend: 'trending' | 'rising' | 'stable' | 'zero_result';
  zeroResultCount?: number;
}

export interface CategorySearchShare {
  name: string;
  searches: number;
  percentage: number;
  color: string;
}

export interface SearchMetricsSummary {
  totalSearches: number;
  totalConversions: number;
  averageCTR: number;
  averageConversionRate: number;
  totalSearchRevenue: number;
  zeroResultRate: number;
}

export interface DateRange {
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  preset?: string;
}

export function computeSearchMetricsSummary(keywords: KeywordPerformance[]): SearchMetricsSummary {
  if (keywords.length === 0) {
    return {
      totalSearches: 0,
      totalConversions: 0,
      averageCTR: 0,
      averageConversionRate: 0,
      totalSearchRevenue: 0,
      zeroResultRate: 0,
    };
  }

  const totalSearches = keywords.reduce((acc, k) => acc + k.searchVolume, 0);
  const totalSearchRevenue = keywords.reduce((acc, k) => acc + k.revenueGenerated, 0);
  
  // Weighted averages based on volume
  const totalClicks = keywords.reduce((acc, k) => acc + (k.searchVolume * (k.clickThroughRate / 100)), 0);
  const totalConversions = keywords.reduce((acc, k) => acc + (k.searchVolume * (k.conversionRate / 100)), 0);

  const averageCTR = totalSearches > 0 ? Number(((totalClicks / totalSearches) * 100).toFixed(1)) : 0;
  const averageConversionRate = totalSearches > 0 ? Number(((totalConversions / totalSearches) * 100).toFixed(1)) : 0;

  const zeroResultKeywords = keywords.filter(k => k.trend === 'zero_result');
  const zeroResultSearches = zeroResultKeywords.reduce((acc, k) => acc + (k.zeroResultCount || k.searchVolume), 0);
  const zeroResultRate = totalSearches > 0 ? Number(((zeroResultSearches / totalSearches) * 100).toFixed(1)) : 0;

  return {
    totalSearches,
    totalConversions: Math.round(totalConversions),
    averageCTR,
    averageConversionRate,
    totalSearchRevenue,
    zeroResultRate,
  };
}

export function filterKeywordsByQuery(
  keywords: KeywordPerformance[],
  query: string,
  categoryFilter: string = 'all'
): KeywordPerformance[] {
  const q = query.trim().toLowerCase();
  return keywords.filter(k => {
    const matchesQuery = !q || k.keyword.toLowerCase().includes(q) || (k.keyword_bn && k.keyword_bn.includes(q));
    const matchesCategory = categoryFilter === 'all' || k.category.toLowerCase() === categoryFilter.toLowerCase();
    return matchesQuery && matchesCategory;
  });
}

export function getTopConvertingKeywords(keywords: KeywordPerformance[], limit: number = 5): KeywordPerformance[] {
  return [...keywords]
    .filter(k => k.trend !== 'zero_result')
    .sort((a, b) => b.conversionRate - a.conversionRate)
    .slice(0, limit);
}

/**
 * Format date YYYY-MM-DD into readable string "Oct 24, 2026"
 */
export function formatDateDisplay(dateStr: string): string {
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  } catch {}
  return dateStr;
}

/**
 * Format a DateRange object for display, e.g. "Oct 24, 2026 – Oct 31, 2026"
 */
export function formatDateRangeDisplay(range: DateRange): string {
  return `${formatDateDisplay(range.startDate)} – ${formatDateDisplay(range.endDate)}`;
}

/**
 * Calculates number of days between two YYYY-MM-DD dates inclusive
 */
export function calculateDaysBetween(startDate: string, endDate: string): number {
  const s = new Date(startDate).getTime();
  const e = new Date(endDate).getTime();
  const diffTime = Math.abs(e - s);
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
}

/**
 * Returns a standardized DateRange for quick presets
 */
export function getDateRangePreset(preset: string, refDate: Date = new Date('2026-10-31T00:00:00')): DateRange {
  const formatISO = (d: Date) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const end = new Date(refDate);

  switch (preset) {
    case 'today': {
      const start = new Date(refDate);
      return { startDate: formatISO(start), endDate: formatISO(end), preset: 'today' };
    }
    case 'yesterday': {
      const start = new Date(refDate);
      start.setDate(start.getDate() - 1);
      const yEnd = new Date(start);
      return { startDate: formatISO(start), endDate: formatISO(yEnd), preset: 'yesterday' };
    }
    case 'last7days': {
      const start = new Date(refDate);
      start.setDate(start.getDate() - 6);
      return { startDate: formatISO(start), endDate: formatISO(end), preset: 'last7days' };
    }
    case 'last14days': {
      const start = new Date(refDate);
      start.setDate(start.getDate() - 13);
      return { startDate: formatISO(start), endDate: formatISO(end), preset: 'last14days' };
    }
    case 'last30days': {
      const start = new Date(refDate);
      start.setDate(start.getDate() - 29);
      return { startDate: formatISO(start), endDate: formatISO(end), preset: 'last30days' };
    }
    case 'thisMonth': {
      const start = new Date(refDate.getFullYear(), refDate.getMonth(), 1);
      return { startDate: formatISO(start), endDate: formatISO(end), preset: 'thisMonth' };
    }
    case 'lastMonth': {
      const start = new Date(refDate.getFullYear(), refDate.getMonth() - 1, 1);
      const prevEnd = new Date(refDate.getFullYear(), refDate.getMonth(), 0);
      return { startDate: formatISO(start), endDate: formatISO(prevEnd), preset: 'lastMonth' };
    }
    case 'last90days':
    case 'qtd': {
      const start = new Date(refDate);
      start.setDate(start.getDate() - 89);
      return { startDate: formatISO(start), endDate: formatISO(end), preset: 'last90days' };
    }
    default: {
      const start = new Date(refDate);
      start.setDate(start.getDate() - 6);
      return { startDate: formatISO(start), endDate: formatISO(end), preset: 'last7days' };
    }
  }
}

/**
 * Generates realistic daily trend points for the selected date range
 */
export function generateTrendDataForDateRange(range: DateRange): SearchTrendPoint[] {
  const points: SearchTrendPoint[] = [];
  const start = new Date(range.startDate);
  const end = new Date(range.endDate);

  // If invalid range, fallback
  if (isNaN(start.getTime()) || isNaN(end.getTime()) || start > end) {
    return [
      { date: 'Oct 31', fullDate: range.startDate, searches: 5200, conversions: 840, mobile: 3900, desktop: 1300 },
    ];
  }

  const current = new Date(start);
  let dayIndex = 0;

  while (current <= end) {
    const monthShort = current.toLocaleDateString('en-US', { month: 'short' });
    const day = current.getDate();
    const dateLabel = `${monthShort} ${day}`;
    const year = current.getFullYear();
    const month = String(current.getMonth() + 1).padStart(2, '0');
    const dayStr = String(day).padStart(2, '0');
    const fullDate = `${year}-${month}-${dayStr}`;

    // Weekend boost (Friday / Saturday in Bangladesh)
    const dayOfWeek = current.getDay();
    const isWeekend = dayOfWeek === 5 || dayOfWeek === 6;
    const baseTraffic = 3800 + ((dayIndex * 140) % 2200);
    const multiplier = isWeekend ? 1.25 : 1.0;
    const searches = Math.round(baseTraffic * multiplier);
    const conversionRate = 0.15 + ((dayIndex % 5) * 0.008);
    const conversions = Math.round(searches * conversionRate);
    const mobile = Math.round(searches * 0.76);
    const desktop = searches - mobile;

    points.push({
      date: dateLabel,
      fullDate,
      searches,
      conversions,
      mobile,
      desktop,
    });

    current.setDate(current.getDate() + 1);
    dayIndex++;

    // Safety guard max 120 points
    if (dayIndex > 120) break;
  }

  return points;
}

/**
 * Scales keyword search volumes and revenue based on date range duration
 */
export function scaleKeywordsForDateRange(
  baseKeywords: KeywordPerformance[],
  range: DateRange
): KeywordPerformance[] {
  const days = calculateDaysBetween(range.startDate, range.endDate);
  const scaleFactor = Math.max(0.15, days / 7); // Base was configured for 7 days

  return baseKeywords.map(k => {
    const scaledVolume = Math.round(k.searchVolume * scaleFactor);
    const scaledRevenue = Math.round(k.revenueGenerated * scaleFactor);
    const scaledZero = k.zeroResultCount ? Math.round(k.zeroResultCount * scaleFactor) : undefined;

    return {
      ...k,
      searchVolume: scaledVolume,
      revenueGenerated: scaledRevenue,
      zeroResultCount: scaledZero,
    };
  });
}
