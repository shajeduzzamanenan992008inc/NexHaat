import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeSearchMetricsSummary,
  filterKeywordsByQuery,
  getTopConvertingKeywords,
  getDateRangePreset,
  calculateDaysBetween,
  formatDateRangeDisplay,
  generateTrendDataForDateRange,
  scaleKeywordsForDateRange,
  KeywordPerformance,
} from './searchAnalytics';

const sampleKeywords: KeywordPerformance[] = [
  {
    keyword: 'Padma Ilish',
    category: 'Meat & Seafood',
    searchVolume: 8500,
    clickThroughRate: 80,
    conversionRate: 20,
    revenueGenerated: 320000,
    trend: 'trending',
  },
  {
    keyword: 'Chinigura Rice',
    category: 'Rice, Grains & Pasta',
    searchVolume: 4000,
    clickThroughRate: 70,
    conversionRate: 15,
    revenueGenerated: 140000,
    trend: 'rising',
  },
  {
    keyword: 'Organic Dragonfruit',
    category: 'Fruits & Vegetables',
    searchVolume: 500,
    clickThroughRate: 10,
    conversionRate: 0,
    revenueGenerated: 0,
    trend: 'zero_result',
    zeroResultCount: 500,
  },
];

test('computeSearchMetricsSummary correctly aggregates volume, weighted CTR, and conversion rates', () => {
  const summary = computeSearchMetricsSummary(sampleKeywords);
  assert.equal(summary.totalSearches, 13000);
  assert.equal(summary.totalSearchRevenue, 460000);
  assert.equal(summary.totalConversions, 2300);
  assert.equal(summary.zeroResultRate, 3.8);
});

test('filterKeywordsByQuery filters by keyword text and category', () => {
  const matchedRice = filterKeywordsByQuery(sampleKeywords, 'rice');
  assert.equal(matchedRice.length, 1);
  assert.equal(matchedRice[0].keyword, 'Chinigura Rice');

  const matchedCat = filterKeywordsByQuery(sampleKeywords, '', 'Meat & Seafood');
  assert.equal(matchedCat.length, 1);
  assert.equal(matchedCat[0].keyword, 'Padma Ilish');
});

test('getTopConvertingKeywords ranks by conversion rate', () => {
  const top = getTopConvertingKeywords(sampleKeywords, 2);
  assert.equal(top[0].keyword, 'Padma Ilish');
  assert.equal(top[0].conversionRate, 20);
});

test('getDateRangePreset generates accurate start and end dates', () => {
  const ref = new Date('2026-10-31T00:00:00');
  const todayRange = getDateRangePreset('today', ref);
  assert.equal(todayRange.startDate, '2026-10-31');
  assert.equal(todayRange.endDate, '2026-10-31');

  const last7Days = getDateRangePreset('last7days', ref);
  assert.equal(last7Days.startDate, '2026-10-25');
  assert.equal(last7Days.endDate, '2026-10-31');
  assert.equal(calculateDaysBetween(last7Days.startDate, last7Days.endDate), 7);
});

test('generateTrendDataForDateRange produces continuous trend points', () => {
  const points = generateTrendDataForDateRange({
    startDate: '2026-10-24',
    endDate: '2026-10-30',
  });
  assert.equal(points.length, 7);
  assert.equal(points[0].date, 'Oct 24');
  assert.equal(points[6].date, 'Oct 30');
  assert.ok(points[0].searches > 0);
  assert.ok(points[0].conversions > 0);
});

test('scaleKeywordsForDateRange scales volume based on duration', () => {
  const scaled = scaleKeywordsForDateRange(sampleKeywords, {
    startDate: '2026-10-01',
    endDate: '2026-10-14', // 14 days = 2x multiplier
  });
  assert.equal(scaled[0].searchVolume, 17000); // 8500 * 2 = 17000
  assert.equal(scaled[0].revenueGenerated, 640000); // 320000 * 2 = 640000
});
