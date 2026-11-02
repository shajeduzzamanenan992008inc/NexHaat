import test from 'node:test';
import assert from 'node:assert/strict';
import { getDetailedPriceTrend } from './priceTrend';
import { Product } from '../types';

const testProduct: Product = {
  id: 42,
  sku: 'NH-PROD-42',
  seller_id: 1,
  seller_name: 'Chandpur Fresh River Fisheries',
  seller_location: 'Chandpur, Chattogram',
  category_id: 1,
  category_slug: 'fish-seafood',
  name: 'Premium Padma Hilsa 1.2kg',
  name_bn: 'পদ্মার তাজা বড় ইলিশ ১.২ কেজি',
  slug: 'premium-padma-hilsa-1-2kg',
  description: 'Freshly caught authentic Padma Hilsa.',
  description_bn: 'পদ্মার তাজা বড় ইলিশ।',
  price: 2200,
  discount_price: 1850,
  stock_quantity: 25,
  is_available: true,
  is_featured: true,
  rating: 4.9,
  review_count: 88,
  image: '/img/hilsa.jpg',
  unit: '1.2 kg',
  unit_bn: '১.২ কেজি',
};

test('getDetailedPriceTrend generates correct number of points for 7d, 14d, and 30d', () => {
  const trend7 = getDetailedPriceTrend(testProduct, '7d');
  assert.equal(trend7.points.length, 7);
  assert.equal(trend7.timeframe, '7d');

  const trend14 = getDetailedPriceTrend(testProduct, '14d');
  assert.equal(trend14.points.length, 14);

  const trend30 = getDetailedPriceTrend(testProduct, '30d');
  assert.equal(trend30.points.length, 30);
});

test('getDetailedPriceTrend ends with the current product price today', () => {
  const trend = getDetailedPriceTrend(testProduct, '30d');
  const todayPoint = trend.points[trend.points.length - 1];

  // Effective current price should match discount_price
  assert.equal(todayPoint.price, 1850);
  assert.equal(todayPoint.isCurrent, true);
  assert.equal(trend.currentPrice, 1850);
});

test('getDetailedPriceTrend correctly identifies min, max, average, and peak drop', () => {
  const trend = getDetailedPriceTrend(testProduct, '30d');

  assert.ok(trend.lowestPrice <= trend.highestPrice);
  assert.ok(trend.averagePrice >= trend.lowestPrice);
  assert.ok(trend.averagePrice <= trend.highestPrice);
  assert.ok(trend.priceDropFromPeak >= 0);
  assert.ok(trend.points.some((p) => p.isLowest));
  assert.ok(trend.points.some((p) => p.isHighest));
});

test('getDetailedPriceTrend is deterministic across runs', () => {
  const run1 = getDetailedPriceTrend(testProduct, '14d');
  const run2 = getDetailedPriceTrend(testProduct, '14d');

  assert.deepEqual(
    run1.points.map((p) => p.price),
    run2.points.map((p) => p.price)
  );
});
