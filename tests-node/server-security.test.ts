import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import express from 'express';
import type { AddressInfo } from 'node:net';
import {
  createConcurrencyLimit,
  createCorsMiddleware,
  createRateLimit,
  getAllowedOrigins,
  requireJsonObject,
  safeErrorName,
  safeJsonErrorHandler,
  sendSafeError,
  validateJsonBody,
} from '../serverSecurity.ts';

const allowedOrigins = getAllowedOrigins('https://shop.example.test', true);
const app = express();
const concurrencyLimit = createConcurrencyLimit(1);
let server: ReturnType<typeof app.listen>;
let baseUrl: string;

app.use(createCorsMiddleware(allowedOrigins));
app.use('/limited', createRateLimit(2, 60_000));
app.use(express.json({ limit: '2kb' }));
app.post(
  '/json',
  requireJsonObject,
  validateJsonBody((body) =>
    typeof body.prompt === 'string' && body.prompt.length <= 20
      ? undefined
      : 'Prompt must be a string of at most 20 characters.',
  ),
  (_request, response) => response.json({ success: true }),
);
app.post('/limited', requireJsonObject, (_request, response) => response.json({ success: true }));
app.post('/busy', concurrencyLimit, async (_request, response) => {
  await new Promise((resolve) => setTimeout(resolve, 100));
  response.json({ success: true });
});
app.get('/failure', (_request, response) => {
  sendSafeError(response, 'Provider failed', new Error('private provider response'), 'AI request failed.');
});
app.use(safeJsonErrorHandler);

before(async () => {
  server = app.listen(0);
  await new Promise<void>((resolve) => server.once('listening', resolve));
  const address = server.address() as AddressInfo;
  baseUrl = `http://127.0.0.1:${address.port}`;
});

after(async () => {
  await new Promise<void>((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
});

test('allows only exact configured origins and omits credentials', async () => {
  const response = await fetch(`${baseUrl}/json`, {
    method: 'OPTIONS',
    headers: {
      Origin: 'https://shop.example.test',
      'Access-Control-Request-Method': 'POST',
      'Access-Control-Request-Headers': 'content-type',
    },
  });

  assert.equal(response.status, 204);
  assert.equal(response.headers.get('access-control-allow-origin'), 'https://shop.example.test');
  assert.equal(response.headers.get('access-control-allow-credentials'), null);
});

test('does not grant CORS access or preflight permission to an unknown origin', async () => {
  const response = await fetch(`${baseUrl}/json`, {
    method: 'OPTIONS',
    headers: {
      Origin: 'https://untrusted.example.test',
      'Access-Control-Request-Method': 'POST',
    },
  });

  assert.equal(response.headers.get('access-control-allow-origin'), null);
});

test('rejects wildcard and non-origin CORS configuration', () => {
  assert.throws(() => getAllowedOrigins('*', true));
  assert.throws(() => getAllowedOrigins('https://shop.example.test/path', true));
});

test('enables localhost origins only in development', () => {
  assert.equal(getAllowedOrigins(undefined, false).has('http://localhost:5173'), true);
  assert.equal(getAllowedOrigins(undefined, true).has('http://localhost:5173'), false);
});

test('requires a JSON object and validates field shape', async () => {
  const unsupported = await fetch(`${baseUrl}/json`, { method: 'POST' });
  assert.equal(unsupported.status, 415);

  const invalid = await fetch(`${baseUrl}/json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: 42 }),
  });
  assert.equal(invalid.status, 400);
});

test('returns a safe 413 for bodies exceeding the parser limit', async () => {
  const response = await fetch(`${baseUrl}/json`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: 'x'.repeat(4_000) }),
  });
  assert.equal(response.status, 413);
  assert.deepEqual(await response.json(), { error: 'Request body exceeds the allowed size.' });
});

test('applies route rate limits and bounds concurrent provider work', async () => {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const response = await fetch(`${baseUrl}/limited`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{',
    });
    assert.equal(response.status, 400);
  }
  const rateLimited = await fetch(`${baseUrl}/limited`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{',
  });
  assert.equal(rateLimited.status, 429);

  const first = fetch(`${baseUrl}/busy`, { method: 'POST' });
  await new Promise((resolve) => setTimeout(resolve, 15));
  const second = await fetch(`${baseUrl}/busy`, { method: 'POST' });
  assert.equal(second.status, 503);
  assert.equal((await first).status, 200);
});

test('does not return or log provider error messages', async () => {
  const logged: string[] = [];
  const originalError = console.error;
  console.error = (...values: unknown[]) => logged.push(values.join(' '));
  try {
    const response = await fetch(`${baseUrl}/failure`);
    assert.equal(response.status, 500);
    assert.deepEqual(await response.json(), { error: 'AI request failed.' });
    assert.equal(logged.join(' ').includes('private provider response'), false);
    assert.equal(logged.join(' '), 'Provider failed: Error');
  } finally {
    console.error = originalError;
  }

  assert.equal(safeErrorName(new Error('secret')), 'Error');
  assert.equal(safeErrorName('secret'), 'UnknownError');
  const namedError = new Error('secret');
  namedError.name = 'private-token';
  assert.equal(safeErrorName(namedError), 'Error');
});
