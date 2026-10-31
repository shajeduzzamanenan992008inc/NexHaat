import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateBundlePrice,
  calculateFreeShippingProgress,
  calculateReviewDistribution,
  manageSearchHistory,
  calculateDeliveryPromise,
} from './amazonFeatures';
import { Product } from '../types';

test('calculateBundlePrice computes accurate bundle savings and total', () => {
  const mockProducts = [
    { id: 1, price: 1200, discount_price: 1000 } as Product,
    { id: 2, price: 300 } as Product,
  ];

  const result = calculateBundlePrice(mockProducts, 10);
  assert.equal(result.originalTotal, 1300);
  assert.equal(result.bundleDiscountPercent, 10);
  assert.equal(result.savings, 130);
  assert.equal(result.discountedTotal, 1170);
});

test('calculateFreeShippingProgress returns 100% and zero remaining for Prime members', () => {
  const result = calculateFreeShippingProgress(200, 1500, true);
  assert.equal(result.progressPercent, 100);
  assert.equal(result.remainingAmount, 0);
  assert.equal(result.isFreeEligible, true);
});

test('calculateFreeShippingProgress computes threshold progress for standard customers', () => {
  const result = calculateFreeShippingProgress(750, 1500, false);
  assert.equal(result.progressPercent, 50);
  assert.equal(result.remainingAmount, 750);
  assert.equal(result.isFreeEligible, false);

  const qualifiedResult = calculateFreeShippingProgress(1600, 1500, false);
  assert.equal(qualifiedResult.progressPercent, 100);
  assert.equal(qualifiedResult.remainingAmount, 0);
  assert.equal(qualifiedResult.isFreeEligible, true);
});

test('calculateReviewDistribution computes star breakdown percentages accurately', () => {
  const reviews = [
    { rating: 5 },
    { rating: 5 },
    { rating: 5 },
    { rating: 4 },
  ];

  const distribution = calculateReviewDistribution(reviews);
  assert.equal(distribution.total, 4);
  assert.equal(distribution.average, 4.8);
  const fiveStar = distribution.breakdown.find(b => b.star === 5);
  const fourStar = distribution.breakdown.find(b => b.star === 4);
  assert.equal(fiveStar?.count, 3);
  assert.equal(fiveStar?.percentage, 75);
  assert.equal(fourStar?.count, 1);
  assert.equal(fourStar?.percentage, 25);
});

test('manageSearchHistory handles deduplication, case-insensitivity, and max limit', () => {
  let history = ['Ilish', 'Rice', 'Mango'];
  history = manageSearchHistory(history, 'oil');
  assert.deepEqual(history, ['oil', 'Ilish', 'Rice', 'Mango']);

  // Case insensitive re-add
  history = manageSearchHistory(history, 'RICE');
  assert.deepEqual(history, ['RICE', 'oil', 'Ilish', 'Mango']);

  // Capped at maxItems
  const smallLimit = manageSearchHistory(['a', 'b', 'c', 'd'], 'new', 3);
  assert.deepEqual(smallLimit, ['new', 'a', 'b']);
});

test('calculateDeliveryPromise returns valid countdown hours and minutes', () => {
  const testTime = new Date('2026-10-31T14:30:00'); // 2:30 PM
  const promise = calculateDeliveryPromise(testTime);
  assert.equal(promise.isSameDayAvailable, true);
  assert.equal(promise.hoursLeft, 4); // 7 PM - 1 - 2 PM = 4 hrs
  assert.equal(promise.minutesLeft, 30);
  assert.equal(promise.deliveryDateText, 'Today by 8:00 PM');
});
