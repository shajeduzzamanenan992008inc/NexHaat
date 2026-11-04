import express, { type RequestHandler, type Router } from 'express';
import {
  createConcurrencyLimit,
  createRateLimit,
  requireJsonObject,
  safeJsonErrorHandler,
  sendSafeError,
  validateJsonBody,
} from './serverSecurity.ts';

export type VisualSearchLanguage = 'bn' | 'en';

export interface VisualSearchImage {
  data: string;
  mimeType: 'image/jpeg' | 'image/png' | 'image/webp';
}

export type VisualSearchAnalyzer = (
  image: VisualSearchImage,
  language: VisualSearchLanguage,
) => Promise<string>;

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const MAX_SOURCE_IMAGE_LENGTH = 11_200_000;
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const;

export function parseVisualSearchImage(sourceImage: string, declaredMimeType: string): VisualSearchImage {
  const match = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/]+={0,2})$/.exec(sourceImage);
  if (!match || match[1] !== declaredMimeType) {
    throw new Error('Invalid visual-search image data');
  }

  const base64Data = match[2];
  const bytes = Buffer.from(base64Data, 'base64');
  if (
    bytes.length === 0 ||
    bytes.length > MAX_IMAGE_BYTES ||
    bytes.toString('base64').replace(/=+$/, '') !== base64Data.replace(/=+$/, '')
  ) {
    throw new Error('Invalid visual-search image data');
  }

  const detectedMimeType = bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
    ? 'image/png'
    : bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff
      ? 'image/jpeg'
      : bytes.subarray(0, 4).toString('ascii') === 'RIFF' &&
          bytes.subarray(8, 12).toString('ascii') === 'WEBP'
        ? 'image/webp'
        : undefined;

  if (detectedMimeType !== declaredMimeType) {
    throw new Error('Visual-search image content does not match its declared type');
  }

  return { data: base64Data, mimeType: declaredMimeType as VisualSearchImage['mimeType'] };
}

export function validateVisualSearchBody(body: Record<string, unknown>): string | undefined {
  if (Object.keys(body).some((field) => !['sourceImage', 'mimeType', 'language'].includes(field))) {
    return 'Request contains unsupported fields.';
  }
  if (typeof body.sourceImage !== 'string' || body.sourceImage.trim().length === 0) {
    return 'sourceImage must be a supported base64-encoded image.';
  }
  if (body.sourceImage.length > MAX_SOURCE_IMAGE_LENGTH) {
    return 'sourceImage exceeds the allowed length.';
  }
  if (typeof body.mimeType !== 'string' || !ALLOWED_MIME_TYPES.includes(body.mimeType as VisualSearchImage['mimeType'])) {
    return 'mimeType must be image/jpeg, image/png, or image/webp.';
  }
  if (body.language !== 'bn' && body.language !== 'en') {
    return 'language must be bn or en.';
  }

  try {
    parseVisualSearchImage(body.sourceImage, body.mimeType);
  } catch {
    return 'sourceImage must be a supported base64-encoded image.';
  }
  return undefined;
}

export function normalizeVisualSearchQuery(value: string): string | undefined {
  const withoutCodeFence = value
    .trim()
    .replace(/^```(?:text)?\s*/i, '')
    .replace(/\s*```$/, '');
  const firstLine = withoutCodeFence.split(/\r?\n/, 1)[0] ?? '';
  const normalized = firstLine
    .replace(/^\s*(?:search\s+query|query)\s*:\s*/i, '')
    .replace(/^[\s"'`*]+|[\s"'`*]+$/g, '')
    .replace(/[^\p{L}\p{M}\p{N}\s&+./-]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 96);

  return [...normalized].length >= 2 ? normalized : undefined;
}

export function createVisualSearchRouter(analyzeImage: VisualSearchAnalyzer): Router {
  const router = express.Router();
  const providerConcurrencyLimit: RequestHandler = createConcurrencyLimit(4);

  router.use(createRateLimit(5, 60_000));
  router.use(express.json({ limit: '12mb', strict: true }));
  router.post(
    '/',
    requireJsonObject,
    validateJsonBody(validateVisualSearchBody),
    providerConcurrencyLimit,
    async (request, response) => {
      try {
        const body = request.body as {
          sourceImage: string;
          mimeType: string;
          language: VisualSearchLanguage;
        };
        const image = parseVisualSearchImage(body.sourceImage, body.mimeType);
        const generatedText = await analyzeImage(image, body.language);
        const query = normalizeVisualSearchQuery(generatedText);

        if (!query) {
          return response.status(422).json({ error: 'No searchable product details were found in the image.' });
        }

        // The image is held only in this request and is never persisted or returned.
        return response.json({ query });
      } catch (error) {
        return sendSafeError(
          response,
          'Visual search failed',
          error,
          'Visual search is unavailable. Try searching by product name or code.',
        );
      }
    },
  );
  router.use(safeJsonErrorHandler);

  return router;
}
