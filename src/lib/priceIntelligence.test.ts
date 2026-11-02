import assert from 'node:assert/strict';
import { test } from 'node:test';
import { calculatePriceIntelligence, getSimilarProductComparisons } from './priceIntelligence.ts';
import { Product } from '../types';

const mockProductA: Product = {
  id: 101,
  sku: 'NH-101',
  seller_id: 1,
  seller_name: 'Test Seller',
  seller_location: 'Dhaka',
  category_id: 1,
  category_slug: 'fruits-vegetables',
  name: 'Rajshahi Mangoes',
  name_bn: 'রাজশাহীর আম',
  slug: 'rajshahi-mangoes',
  description: 'Sweet fresh mangoes',
  description_bn: 'মিষ্টি আম',
  image: 'https://example.com/mango.jpg',
  price: 800,
  discount_price: 720,
  stock_quantity: 50,
  is_available: true,
  is_featured: true,
  rating: 4.8,
  review_count: 32,
  unit: '5kg',
  unit_bn: '৫ কেজি',
};

const mockProductB: Product = {
  id: 102,
  sku: 'NH-102',
  seller_id: 2,
  seller_name: 'Green Haat',
  seller_location: 'Rajshahi',
  category_id: 1,
  category_slug: 'fruits-vegetables',
  name: 'Organic Bananas',
  name_bn: 'কলা',
  slug: 'organic-bananas',
  description: 'Ripe bananas',
  description_bn: 'পাকা কলা',
  image: 'https://example.com/banana.jpg',
  price: 250,
  discount_price: 200,
  stock_quantity: 100,
  is_available: true,
  is_featured: false,
  rating: 4.6,
  review_count: 15,
  unit: '1 Dozen',
  unit_bn: '১ ডজন',
};

test('calculatePriceIntelligence returns structured price analysis and 5 history points', () => {
  const intel = calculatePriceIntelligence(mockProductA);
  assert.equal(intel.currentPrice, 720);
  assert.equal(intel.originalPrice, 800);
  assert.equal(intel.history.length, 5);
  assert.equal(intel.history[4].price, 720); // Today price matches current
  assert.ok(intel.lowestPrice30d <= intel.highestPrice30d);
  assert.ok(intel.averagePrice30d > 0);
  assert.ok(['great-deal', 'good-price', 'standard-price'].includes(intel.verdict));
  assert.ok(intel.verdictTitle.length > 0);
});

test('getSimilarProductComparisons correctly computes price differences and assigns badges', () => {
  const comparisons = getSimilarProductComparisons(mockProductA, [mockProductA, mockProductB]);
  assert.equal(comparisons.length, 1);
  assert.equal(comparisons[0].product.id, 102);
  assert.equal(comparisons[0].currentPrice, 200);
  assert.equal(comparisons[0].priceDifference, 200 - 720); // -520
  assert.equal(comparisons[0].valueBadge, 'Budget Pick');
});
