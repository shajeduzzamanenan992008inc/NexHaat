import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let vite;
let api;
let originalFetch;
let originalWindow;

before(async () => {
  originalFetch = globalThis.fetch;
  originalWindow = globalThis.window;
  globalThis.window = { location: { origin: 'http://nexhaat.test' } };
  vite = await createServer({
    configFile: false,
    envPrefix: 'NEXHAAT_TEST_',
    logLevel: 'silent',
    server: { middlewareMode: true },
    appType: 'custom',
  });
  api = await vite.ssrLoadModule('/src/lib/marketplaceApi.ts');
});

after(async () => {
  globalThis.fetch = originalFetch;
  if (originalWindow === undefined) delete globalThis.window;
  else globalThis.window = originalWindow;
  await vite?.close();
});

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function mockFetch(handler) {
  const calls = [];
  globalThis.fetch = async (input, init = {}) => {
    const call = { url: String(input), init };
    calls.push(call);
    if (call.url.endsWith('/api/v1/auth/csrf')) {
      return jsonResponse({ success: true, data: { csrf_token: 'disposable-csrf-token' } });
    }
    return handler(call, calls.length);
  };
  return calls;
}

function apiOrder(paymentMethod = 'sslcommerz') {
  return {
    id: 1,
    order_number: 'FB-CHECKOUT-TEST-1',
    status: 'pending',
    payment_method: paymentMethod,
    payment_status: paymentMethod === 'cod' ? null : 'pending',
    customer_name: 'Disposable test customer',
    phone: '01000000000',
    email: 'checkout@example.invalid',
    address: 'Disposable test address',
    total: '12.50',
    delivery_fee: '2.50',
    discount_amount: '0.00',
    promotion_code: null,
    items_subtotal: '10.00',
    created_at: '2026-11-04T00:00:00+00:00',
    items: [{
      product_id: 10,
      name: 'Disposable test item',
      variant_label: null,
      price: '10.00',
      quantity: 1,
      subtotal: '10.00',
    }],
  };
}

function apiReview(overrides = {}) {
  return {
    id: 3,
    product_id: 10,
    rating: 5,
    comment: 'Disposable review fixture',
    author_name: 'Test Reviewer',
    created_at: '2026-11-04T00:00:00+00:00',
    status: 'approved',
    verified_purchase: true,
    helpful_count: 2,
    viewer_helpful: false,
    ...overrides,
  };
}

function apiProduct(overrides = {}) {
  return {
    id: 10,
    name: 'Disposable catalog item',
    description: 'API adapter test fixture',
    slug: 'disposable-catalog-item',
    price: '10.00',
    display_price: '10.00',
    stock: 4,
    is_available: true,
    is_featured: false,
    category_id: 3,
    seller_id: 7,
    image: null,
    display_image: null,
    ...overrides,
  };
}

async function expectMarketplaceError(action, status, code) {
  await assert.rejects(action, (error) => {
    assert.ok(error instanceof api.MarketplaceApiError);
    assert.equal(error.status, status);
    assert.equal(error.code, code);
    return true;
  });
}

test('online checkout preserves payment metadata and nullable provider URL', async () => {
  const calls = mockFetch((call) => {
    if (call.url.endsWith('/api/v1/auth/csrf')) {
      return jsonResponse({ success: true, data: { csrf_token: 'disposable-csrf-token' } });
    }
    assert.ok(call.url.endsWith('/api/v1/checkout'));
    const body = JSON.parse(call.init.body);
    assert.equal(body.payment_method, 'sslcommerz');
    const headers = new Headers(call.init.headers);
    assert.equal(headers.get('X-CSRFToken'), 'disposable-csrf-token');
    return jsonResponse({
      success: true,
      data: {
        orders: [apiOrder()],
        checkout_group: 'FB-CHECKOUT-TEST',
        payment_status: 'pending',
        checkout_url: null,
        payment_status_url: '/api/v1/payments/FB-CHECKOUT-TEST',
      },
    });
  });

  const result = await api.createMarketplaceCheckout({
    customerName: 'Disposable test customer',
    phone: '01000000000',
    address: 'Disposable test address',
    city: 'Test City',
    paymentMethod: 'sslcommerz',
  });

  assert.equal(calls.length, 2);
  assert.equal(result.orders.length, 1);
  assert.equal(result.checkout_group, 'FB-CHECKOUT-TEST');
  assert.equal(result.payment_status, 'pending');
  assert.equal(result.checkout_url, null);
  assert.equal(result.payment_status_url, '/api/v1/payments/FB-CHECKOUT-TEST');
});

test('online checkout keeps omitted optional metadata omitted and supports empty catalogs', async () => {
  mockFetch((call) => {
    if (call.url.endsWith('/api/v1/checkout')) {
      return jsonResponse({ success: true, data: { orders: [apiOrder()], checkout_url: null } });
    }
    if (call.url.endsWith('/api/v1/categories')) {
      return jsonResponse({ success: true, data: [] });
    }
    return jsonResponse({ success: true, data: [], pagination: { page: 1, limit: 100, total: 0 } });
  });

  const result = await api.createMarketplaceCheckout({
    customerName: 'Disposable test customer',
    phone: '01000000000',
    address: 'Disposable test address',
    city: 'Test City',
    paymentMethod: 'sslcommerz',
  });
  assert.equal(result.checkout_url, null);
  assert.equal(Object.hasOwn(result, 'checkout_group'), false);
  assert.equal(Object.hasOwn(result, 'payment_status'), false);
  assert.equal(Object.hasOwn(result, 'payment_status_url'), false);

  const catalog = await api.fetchMarketplaceCatalog();
  assert.deepEqual(catalog.products, []);
  assert.deepEqual(catalog.categories, []);
  assert.equal(catalog.total, 0);
});

test('COD checkout keeps its order-only contract', async () => {
  const calls = mockFetch((call) => jsonResponse({ success: true, data: { orders: [apiOrder('cod')] } }));
  const order = await api.submitMarketplaceCheckout({
    customerName: 'Disposable test customer',
    phone: '01000000000',
    address: 'Disposable test address',
    city: 'Test City',
  });
  assert.equal(order.payment_method, 'cod');
  assert.equal(order.order_number, 'FB-CHECKOUT-TEST-1');
    const checkoutCall = calls.find((call) => call.url.endsWith('/api/v1/checkout'));
    assert.equal(JSON.parse(checkoutCall.init.body).payment_method, 'cod');
});

test('checkout rejects missing or malformed orders and unknown payment statuses', async (t) => {
  await t.test('missing order list', async () => {
    mockFetch(() => jsonResponse({ success: true, data: { checkout_url: null } }));
    await expectMarketplaceError(
      () => api.createMarketplaceCheckout({ customerName: 'x', phone: 'x', address: 'x', city: 'x', paymentMethod: 'sslcommerz' }),
      502,
      'INVALID_RESPONSE',
    );
  });
  await t.test('invalid order price', async () => {
    mockFetch(() => jsonResponse({ success: true, data: { orders: [{ ...apiOrder(), total: 'not-money' }] } }));
    await expectMarketplaceError(
      () => api.createMarketplaceCheckout({ customerName: 'x', phone: 'x', address: 'x', city: 'x', paymentMethod: 'sslcommerz' }),
      502,
      'INVALID_RESPONSE',
    );
  });
  await t.test('unknown payment state', async () => {
    mockFetch(() => jsonResponse({
      success: true,
      data: { orders: [apiOrder()], payment_status: 'settled' },
    }));
    await expectMarketplaceError(
      () => api.createMarketplaceCheckout({ customerName: 'x', phone: 'x', address: 'x', city: 'x', paymentMethod: 'sslcommerz' }),
      502,
      'INVALID_RESPONSE',
    );
  });
});

test('catalog filters map to the server query and missing review summaries stay absent', async () => {
  let requestedUrl;
  mockFetch((call) => {
    requestedUrl = new URL(call.url);
    return jsonResponse({
      success: true,
      data: [apiProduct()],
      pagination: { page: 2, limit: 1, total: 5 },
    });
  });

  const result = await api.fetchMarketplaceCatalogPage({
    page: 2,
    limit: 1,
    query: ' kiwi ',
    categorySlug: 'local pantry',
    minPrice: 2,
    maxPrice: 12,
    minRating: 4,
    inStockOnly: true,
    discountOnly: true,
    sort: 'price_asc',
  }, []);

  assert.equal(requestedUrl.pathname, '/api/v1/categories/local%20pantry');
  assert.equal(requestedUrl.searchParams.get('q'), 'kiwi');
  assert.equal(requestedUrl.searchParams.get('page'), '2');
  assert.equal(requestedUrl.searchParams.get('limit'), '1');
  assert.equal(requestedUrl.searchParams.get('min_price'), '2');
  assert.equal(requestedUrl.searchParams.get('max_price'), '12');
  assert.equal(requestedUrl.searchParams.get('min_rating'), '4');
  assert.equal(requestedUrl.searchParams.get('in_stock'), '1');
  assert.equal(requestedUrl.searchParams.get('discount'), '1');
  assert.equal(requestedUrl.searchParams.get('sort'), 'price_asc');
  assert.deepEqual(result.page, 2);
  assert.equal(result.limit, 1);
  assert.equal(result.total, 5);
  assert.equal(Object.hasOwn(result.products[0], 'rating'), false);
  assert.equal(Object.hasOwn(result.products[0], 'review_count'), false);
});

test('catalog rejects invalid backend product prices instead of displaying zero', async () => {
  mockFetch(() => jsonResponse({ success: true, data: [apiProduct({ price: 'invalid' })], pagination: { page: 1, limit: 24, total: 1 } }));
  await expectMarketplaceError(
    () => api.fetchMarketplaceCatalogPage({ page: 1, sort: 'featured' }, []),
    502,
    'INVALID_RESPONSE',
  );
});

test('review retrieval and creation map server-authoritative fields', async (t) => {
  await t.test('retrieval', async () => {
    mockFetch(() => jsonResponse({
      success: true,
      data: { product_id: 10, summary: { count: 1, average: 5 }, reviews: [apiReview()] },
    }));
    const reviews = await api.fetchMarketplaceProductReviews(10);
    assert.equal(reviews.length, 1);
    assert.equal(reviews[0].user_name, 'Test Reviewer');
    assert.equal(reviews[0].rating, 5);
    assert.equal(reviews[0].verified_purchase, true);
    assert.equal(reviews[0].helpful_count, 2);
  });

  await t.test('creation', async () => {
    const calls = mockFetch((call) => {
      assert.ok(call.url.endsWith('/api/v1/products/10/reviews'));
      return jsonResponse({ success: true, data: apiReview({ status: 'pending' }) }, 201);
    });
    const review = await api.submitMarketplaceProductReview(10, 4, 'A real test payload.');
    assert.equal(review.rating, 5);
    const reviewCall = calls.find((call) => call.url.endsWith('/api/v1/products/10/reviews'));
    assert.equal(JSON.parse(reviewCall.init.body).rating, 4);
    assert.equal(JSON.parse(reviewCall.init.body).comment, 'A real test payload.');
    assert.equal(new Headers(reviewCall.init.headers).get('X-CSRFToken'), 'disposable-csrf-token');
  });
});

test('review adapters reject malformed success payloads instead of returning fake empty data', async (t) => {
  await t.test('review list missing', async () => {
    mockFetch(() => jsonResponse({ success: true, data: { product_id: 10 } }));
    await expectMarketplaceError(() => api.fetchMarketplaceProductReviews(10), 502, 'INVALID_RESPONSE');
  });
  await t.test('review submission missing', async () => {
    mockFetch(() => jsonResponse({ success: true, data: null }, 201));
    await expectMarketplaceError(() => api.submitMarketplaceProductReview(10, 5, 'x'), 502, 'INVALID_RESPONSE');
  });
});

test('HTTP validation, authentication and server errors keep status and safe API codes', async (t) => {
  for (const [status, code] of [[401, 'UNAUTHENTICATED'], [422, 'VALIDATION_ERROR'], [500, 'INTERNAL_ERROR']]) {
    await t.test(`${status} ${code}`, async () => {
      mockFetch(() => jsonResponse({ success: false, error: { code, message: 'Safe server response.' } }, status));
      await expectMarketplaceError(() => api.fetchMarketplaceProductReviews(10), status, code);
    });
  }
});

test('network failures use a safe normalized marketplace error', async () => {
  mockFetch(() => Promise.reject(new TypeError('network failure containing a request URL')));
  await assert.rejects(api.fetchMarketplaceProductReviews(10), (error) => {
    assert.ok(error instanceof api.MarketplaceApiError);
    assert.equal(error.status, 0);
    assert.equal(error.code, 'NETWORK_ERROR');
    assert.equal(error.message.includes('request URL'), false);
    return true;
  });
});
