import cors from 'cors';
import type { ErrorRequestHandler, Request, RequestHandler, Response } from 'express';

const DEVELOPMENT_ORIGINS = [
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:5173',
  'http://127.0.0.1:5173',
];

export function getAllowedOrigins(
  configuredOrigins: string | undefined,
  isProduction: boolean,
): Set<string> {
  const configured = (configuredOrigins ?? '')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean)
    .map((origin) => {
      let parsed: URL;
      try {
        parsed = new URL(origin);
      } catch {
        throw new Error('EXPRESS_CORS_ORIGINS must contain valid HTTP(S) origins');
      }

      if (
        !['http:', 'https:'].includes(parsed.protocol) ||
        parsed.origin !== origin ||
        parsed.username ||
        parsed.password
      ) {
        throw new Error('EXPRESS_CORS_ORIGINS entries must be exact HTTP(S) origins');
      }

      return parsed.origin;
    });

  return new Set([...(!isProduction ? DEVELOPMENT_ORIGINS : []), ...configured]);
}

export function createCorsMiddleware(allowedOrigins: ReadonlySet<string>): RequestHandler {
  return cors({
    origin(origin, callback) {
      callback(null, origin !== undefined && allowedOrigins.has(origin) ? origin : false);
    },
    credentials: false,
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type'],
    maxAge: 600,
    optionsSuccessStatus: 204,
  });
}

export function createRateLimit(maxRequests: number, windowMs: number): RequestHandler {
  const buckets = new Map<string, { count: number; resetAt: number }>();

  return (request, response, next) => {
    const now = Date.now();
    for (const [key, bucket] of buckets) {
      if (bucket.resetAt <= now) buckets.delete(key);
    }

    const key = request.ip || request.socket.remoteAddress || 'unknown';
    let bucket = buckets.get(key);
    if (!bucket || bucket.resetAt <= now) {
      bucket = { count: 0, resetAt: now + windowMs };
      buckets.set(key, bucket);
    }

    if (bucket.count >= maxRequests) {
      response.setHeader('Retry-After', Math.max(1, Math.ceil((bucket.resetAt - now) / 1000)));
      response.status(429).json({ error: 'Request limit reached. Please try again later.' });
      return;
    }

    bucket.count += 1;
    if (buckets.size > 10_000) {
      const oldestKey = buckets.keys().next().value;
      if (oldestKey) buckets.delete(oldestKey);
    }
    next();
  };
}

export function createConcurrencyLimit(
  maxConcurrent: number,
  maximumHoldMs = 320_000,
): RequestHandler {
  let active = 0;

  return (_request, response, next) => {
    if (active >= maxConcurrent) {
      response.setHeader('Retry-After', '5');
      response.status(503).json({ error: 'Service is busy. Please try again shortly.' });
      return;
    }

    active += 1;
    let released = false;
    let lease: NodeJS.Timeout;
    const release = () => {
      if (released) return;
      released = true;
      clearTimeout(lease);
      active -= 1;
    };
    lease = setTimeout(release, maximumHoldMs);
    lease.unref();

    response.once('finish', release);
    next();
  };
}

export function requireJsonObject(
  request: Request,
  response: Response,
  next: (error?: unknown) => void,
): void {
  if (!request.is('application/json')) {
    response.status(415).json({ error: 'Content-Type must be application/json.' });
    return;
  }

  if (
    request.body === null ||
    typeof request.body !== 'object' ||
    Array.isArray(request.body)
  ) {
    response.status(400).json({ error: 'A JSON object is required.' });
    return;
  }

  next();
}

export function validateJsonBody(
  validate: (body: Record<string, unknown>) => string | undefined,
): RequestHandler {
  return (request, response, next) => {
    const error = validate(request.body as Record<string, unknown>);
    if (error) {
      response.status(400).json({ error });
      return;
    }
    next();
  };
}

export function safeErrorName(error: unknown): string {
  if (!(error instanceof Error)) return 'UnknownError';
  return ['AbortError', 'TimeoutError', 'TypeError', 'RangeError'].includes(error.name)
    ? error.name
    : 'Error';
}

export function logSafeError(label: string, error: unknown): void {
  console.error(`${label}: ${safeErrorName(error)}`);
}

export function sendSafeError(
  response: Response,
  label: string,
  error: unknown,
  publicMessage: string,
): void {
  logSafeError(label, error);
  response.status(500).json({ error: publicMessage });
}

export const safeJsonErrorHandler: ErrorRequestHandler = (error, _request, response, next) => {
  if (response.headersSent) {
    next(error);
    return;
  }

  if (error?.type === 'entity.too.large') {
    response.status(413).json({ error: 'Request body exceeds the allowed size.' });
    return;
  }

  if (error?.type === 'entity.parse.failed') {
    response.status(400).json({ error: 'Request body must contain valid JSON.' });
    return;
  }

  logSafeError('Request processing failed', error);
  response.status(500).json({ error: 'Request could not be completed.' });
};
