import test from 'node:test';
import assert from 'node:assert/strict';
import {
  convertFromBDT,
  convertToBDT,
  formatCurrencyPrice,
  CURRENCY_CONFIGS,
  SUPPORTED_CURRENCIES,
} from './currency';

test('convertFromBDT accurately converts BDT to foreign currencies', () => {
  assert.equal(convertFromBDT(1000, 'BDT'), 1000);
  assert.equal(convertFromBDT(1000, 'USD'), 8.3);
  assert.equal(convertFromBDT(1000, 'EUR'), 7.8);
  assert.equal(convertFromBDT(1000, 'AED'), 30.5);
  assert.equal(convertFromBDT(1000, 'INR'), 720);
});

test('convertFromBDT returns 0 for invalid or negative amounts', () => {
  assert.equal(convertFromBDT(0, 'USD'), 0);
  assert.equal(convertFromBDT(-50, 'USD'), 0);
  assert.equal(convertFromBDT(NaN, 'USD'), 0);
});

test('convertToBDT correctly converts foreign currency back to BDT', () => {
  const usdAmount = 8.3;
  const backToBDT = convertToBDT(usdAmount, 'USD');
  assert.equal(Math.round(backToBDT), 1000);
});

test('formatCurrencyPrice formats BDT and foreign currencies with proper symbols', () => {
  const formattedBDT = formatCurrencyPrice(1250, 'BDT', 'en');
  assert.ok(formattedBDT.includes('৳'));
  assert.ok(formattedBDT.includes('1,250.00'));

  const formattedUSD = formatCurrencyPrice(1000, 'USD', 'en');
  assert.ok(formattedUSD.startsWith('$'));
  assert.ok(formattedUSD.includes('8.30'));

  const formattedEUR = formatCurrencyPrice(1000, 'EUR', 'en');
  assert.ok(formattedEUR.startsWith('€'));

  const formattedAED = formatCurrencyPrice(1000, 'AED', 'en');
  assert.ok(formattedAED.startsWith('AED '));
});

test('supported currencies include all 5 designated international hubs', () => {
  assert.deepEqual(SUPPORTED_CURRENCIES, ['BDT', 'USD', 'EUR', 'AED', 'INR']);
  assert.equal(Object.keys(CURRENCY_CONFIGS).length, 5);
});
