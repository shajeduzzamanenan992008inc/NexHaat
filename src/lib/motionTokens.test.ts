import { test } from 'node:test';
import assert from 'node:assert/strict';
import { 
  MOTION_DURATIONS, 
  MOTION_EASINGS, 
  calculateCardTilt, 
  evaluatePasswordStrength 
} from './motionTokens.ts';

test('MOTION_DURATIONS keeps interactions responsive and major changes under 500ms', () => {
  assert.equal(MOTION_DURATIONS.instant, 100);
  assert.equal(MOTION_DURATIONS.fast, 150);
  assert.equal(MOTION_DURATIONS.normal, 280);
  assert.equal(MOTION_DURATIONS.page, 320);
  assert.equal(MOTION_DURATIONS.deliberate, 450);
  assert.equal(MOTION_DURATIONS.complex, 450);
});

test('MOTION_EASINGS defines standard cubic-bezier curves', () => {
  assert.ok(MOTION_EASINGS.spring.includes('cubic-bezier'));
  assert.ok(MOTION_EASINGS.decelerate.includes('cubic-bezier'));
  assert.ok(MOTION_EASINGS.accelerate.includes('cubic-bezier'));
  assert.ok(MOTION_EASINGS.standard.includes('cubic-bezier'));
});

test('calculateCardTilt computes correct bounded 3D tilt coordinates', () => {
  const rect = { left: 100, top: 100, width: 200, height: 200 };
  
  // Center of card -> 0 tilt
  const centerTilt = calculateCardTilt(200, 200, rect, 8);
  assert.equal(centerTilt.rotateX, 0);
  assert.equal(centerTilt.rotateY, 0);
  assert.ok(centerTilt.transformStyle.includes('perspective(1000px)'));

  // Top right corner -> rotateX > 0, rotateY > 0
  const topRightTilt = calculateCardTilt(300, 100, rect, 8);
  assert.equal(topRightTilt.rotateX, 8);
  assert.equal(topRightTilt.rotateY, 8);

  // Bottom left corner -> rotateX < 0, rotateY < 0
  const bottomLeftTilt = calculateCardTilt(100, 300, rect, 8);
  assert.equal(bottomLeftTilt.rotateX, -8);
  assert.equal(bottomLeftTilt.rotateY, -8);
});

test('calculateCardTilt handles zero or negative rect dimensions safely', () => {
  const zeroRect = { left: 0, top: 0, width: 0, height: 0 };
  const safeTilt = calculateCardTilt(50, 50, zeroRect, 8);
  assert.equal(safeTilt.rotateX, 0);
  assert.equal(safeTilt.rotateY, 0);
});

test('evaluatePasswordStrength rates complexity and assigns visual classes', () => {
  const empty = evaluatePasswordStrength('');
  assert.equal(empty.score, 0);
  assert.equal(empty.widthPercent, 0);

  const weak = evaluatePasswordStrength('simple');
  assert.equal(weak.score, 0);

  const fair = evaluatePasswordStrength('Password');
  assert.equal(fair.score, 2); // >=8 chars and uppercase
  assert.equal(fair.widthPercent, 50);

  const secure = evaluatePasswordStrength('P@ssw0rd99!');
  assert.equal(secure.score, 4); // len, upper, digit, symbol
  assert.equal(secure.colorClass, 'bg-emerald-500');
  assert.equal(secure.widthPercent, 100);
});
