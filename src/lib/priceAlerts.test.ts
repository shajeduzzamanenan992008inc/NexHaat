import test from 'node:test';
import assert from 'node:assert/strict';
import { PriceAlert } from '../types';

function evaluatePriceAlert(alert: PriceAlert, newPrice: number): {
  isTriggered: boolean;
  savings: number;
  savingsPercent: number;
} {
  const isTriggered = alert.is_active && newPrice <= alert.target_price;
  const savings = Math.max(0, alert.initial_price - newPrice);
  const savingsPercent = alert.initial_price > 0 ? Math.round((savings / alert.initial_price) * 100) : 0;
  return {
    isTriggered,
    savings,
    savingsPercent,
  };
}

test('evaluatePriceAlert correctly triggers when newPrice drops to or below target', () => {
  const alert: PriceAlert = {
    id: 'alert_1',
    product_id: 101,
    product_name: 'Premium Hilsa Fish (Padma)',
    product_slug: 'premium-hilsa-fish-padma',
    product_image: '/images/hilsa.jpg',
    initial_price: 1800,
    target_price: 1500,
    current_price: 1800,
    is_active: true,
    is_triggered: false,
    created_at: new Date().toISOString(),
  };

  // Higher than target
  const check1 = evaluatePriceAlert(alert, 1600);
  assert.equal(check1.isTriggered, false);
  assert.equal(check1.savings, 200);

  // Exactly target
  const check2 = evaluatePriceAlert(alert, 1500);
  assert.equal(check2.isTriggered, true);
  assert.equal(check2.savings, 300);
  assert.equal(check2.savingsPercent, 17); // (300 / 1800) * 100 ≈ 17%

  // Below target
  const check3 = evaluatePriceAlert(alert, 1400);
  assert.equal(check3.isTriggered, true);
  assert.equal(check3.savings, 400);
  assert.equal(check3.savingsPercent, 22);
});

test('evaluatePriceAlert does not trigger if alert is disabled or inactive', () => {
  const inactiveAlert: PriceAlert = {
    id: 'alert_2',
    product_id: 102,
    product_name: 'Organic Kalijira Rice',
    product_slug: 'organic-kalijira-rice',
    product_image: '/images/rice.jpg',
    initial_price: 320,
    target_price: 250,
    current_price: 320,
    is_active: false,
    is_triggered: false,
    created_at: new Date().toISOString(),
  };

  const result = evaluatePriceAlert(inactiveAlert, 200);
  assert.equal(result.isTriggered, false);
});
