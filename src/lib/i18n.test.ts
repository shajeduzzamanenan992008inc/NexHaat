import test from 'node:test';
import assert from 'node:assert/strict';
import { translate, SUPPORTED_LANGUAGES, COMMON_TRANSLATIONS } from './i18n';

test('translate falls back cleanly across supported languages', () => {
  assert.equal(translate('en', 'Hello', 'হ্যালো', 'مرحبا', 'नमस्ते'), 'Hello');
  assert.equal(translate('bn', 'Hello', 'হ্যালো', 'مرحبا', 'नमस्ते'), 'হ্যালো');
  assert.equal(translate('ar', 'Hello', 'হ্যালো', 'مرحبا', 'नमस्ते'), 'مرحبا');
  assert.equal(translate('hi', 'Hello', 'হ্যালো', 'مرحبا', 'नमस्ते'), 'नमस्ते');
});

test('translate falls back to English when optional translation is missing', () => {
  assert.equal(translate('ar', 'Only English & Bengali', 'শুধুমাত্র ইংরেজি ও বাংলা'), 'Only English & Bengali');
  assert.equal(translate('hi', 'Only English & Bengali', 'শুধুমাত্র ইংরেজি ও বাংলা'), 'Only English & Bengali');
});

test('supported languages include en, bn, ar, hi with appropriate directions', () => {
  assert.equal(SUPPORTED_LANGUAGES.en.dir, 'ltr');
  assert.equal(SUPPORTED_LANGUAGES.bn.dir, 'ltr');
  assert.equal(SUPPORTED_LANGUAGES.ar.dir, 'rtl');
  assert.equal(SUPPORTED_LANGUAGES.hi.dir, 'ltr');
});

test('common translations contain key e-commerce digital badges', () => {
  assert.ok(COMMON_TRANSLATIONS['badge.instant_digital'].en.includes('Instant Digital Delivery'));
  assert.ok(COMMON_TRANSLATIONS['badge.global_shipping'].bn.includes('আন্তর্জাতিক'));
  assert.ok(COMMON_TRANSLATIONS['badge.cold_chain'].ar.includes('التبريد'));
});
