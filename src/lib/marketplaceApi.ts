import { FlaskAuthError, getCsrfToken, getFlaskAuthOrigin } from './flaskAuth';
import { Category, CartItem, Notification, Order, OrderStatus, Product, Review } from '../types';

interface ApiEnvelope<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: { code?: string; message?: string };
  pagination?: { page: number; limit: number; total: number };
}

export class MarketplaceApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'MarketplaceApiError';
    this.status = status;
    this.code = code;
  }
}

interface ApiProduct {
  id: number;
  name: string;
  localized_name?: string;
  description: string;
  localized_description?: string;
  slug: string;
  brand_name?: string | null;
  seller_name?: string | null;
  price: string;
  discount_price?: string | null;
  display_price: string;
  stock: number;
  sku?: string | null;
  image?: string | null;
  display_image?: string | null;
  is_available: boolean;
  is_featured: boolean;
  moderation_status?: Product['moderation_status'];
  category_id: number;
  seller_id: number;
  rating?: number | null;
  review_count?: number | null;
  variants?: Array<{
    id: number;
    option_name?: string | null;
    option_value?: string | null;
    price: string;
    stock: number;
    sku?: string | null;
  }>;
}

interface ApiCategory {
  id: number;
  name: string;
  slug: string;
  description: string;
  image?: string | null;
  display_image?: string | null;
  is_active: boolean;
}

interface ApiOrder {
  id: number;
  order_number: string;
  status: string;
  payment_method: string;
  payment_status?: string | null;
  customer_name: string;
  phone: string;
  email: string;
  address: string;
  total: string;
  delivery_fee: string;
  discount_amount: string;
  promotion_code?: string | null;
  items_subtotal: string;
  created_at: string;
  items: Array<{
    product_id: number;
    name: string;
    variant_label?: string | null;
    price: string;
    quantity: number;
    subtotal: string;
  }>;
}

interface ApiNotification {
  id: number;
  type: string;
  message: string;
  link?: string | null;
  is_read: boolean;
  created_at: string;
}

interface ApiReview {
  id: number;
  product_id: number;
  rating: number;
  comment: string | null;
  author_name: string;
  created_at: string;
  status: string;
  verified_purchase?: boolean;
  helpful_count?: number;
  viewer_helpful?: boolean;
}

export type MarketplacePaymentStatus =
  | 'pending'
  | 'paid'
  | 'review_required'
  | 'partially_refunded'
  | 'refunded'
  | 'expired'
  | 'cancelled';

export interface MarketplaceCheckoutResult {
  orders: Order[];
  checkout_url: string | null;
  checkout_group?: string | null;
  payment_status?: MarketplacePaymentStatus | null;
  payment_status_url?: string | null;
}

const money = (value: string | null | undefined): number | undefined => {
  if (value == null) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

function invalidResponse(message: string): MarketplaceApiError {
  return new MarketplaceApiError(message, 502, 'INVALID_RESPONSE');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isMoneyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value));
}

function isApiProduct(value: unknown): value is ApiProduct {
  if (!isRecord(value)) return false;
  const validVariant = (variant: unknown) => isRecord(variant)
    && typeof variant.id === 'number'
    && typeof variant.price === 'string'
    && isMoneyString(variant.price)
    && typeof variant.stock === 'number'
    && Number.isSafeInteger(variant.stock)
    && variant.stock >= 0
    && (variant.option_name === undefined || variant.option_name === null || typeof variant.option_name === 'string')
    && (variant.option_value === undefined || variant.option_value === null || typeof variant.option_value === 'string')
    && (variant.sku === undefined || variant.sku === null || typeof variant.sku === 'string');

  return typeof value.id === 'number'
    && Number.isSafeInteger(value.id)
    && value.id > 0
    && typeof value.name === 'string'
    && typeof value.description === 'string'
    && typeof value.slug === 'string'
    && isMoneyString(value.price)
    && isMoneyString(value.display_price)
    && (value.discount_price === undefined || value.discount_price === null || isMoneyString(value.discount_price))
    && typeof value.stock === 'number'
    && Number.isSafeInteger(value.stock)
    && value.stock >= 0
    && typeof value.is_available === 'boolean'
    && typeof value.is_featured === 'boolean'
    && typeof value.category_id === 'number'
    && (value.rating === undefined || value.rating === null
      || (typeof value.rating === 'number' && Number.isFinite(value.rating) && value.rating >= 0 && value.rating <= 5))
    && (value.review_count === undefined || value.review_count === null
      || (typeof value.review_count === 'number' && Number.isSafeInteger(value.review_count) && value.review_count >= 0))
    && (value.variants === undefined || (Array.isArray(value.variants) && value.variants.every(validVariant)));
}

function isApiOrder(value: unknown): value is ApiOrder {
  if (!isRecord(value) || !Array.isArray(value.items)) return false;
  return typeof value.id === 'number'
    && typeof value.order_number === 'string'
    && value.status === 'pending'
    && (value.payment_method === 'cod' || value.payment_method === 'sslcommerz')
    && (value.payment_status === undefined || value.payment_status === null || isMarketplacePaymentStatus(value.payment_status))
    && typeof value.customer_name === 'string'
    && typeof value.phone === 'string'
    && typeof value.email === 'string'
    && typeof value.address === 'string'
    && isMoneyString(value.total)
    && isMoneyString(value.delivery_fee)
    && isMoneyString(value.discount_amount)
    && (value.promotion_code === undefined || value.promotion_code === null || typeof value.promotion_code === 'string')
    && isMoneyString(value.items_subtotal)
    && typeof value.created_at === 'string'
    && value.items.every((item) => isRecord(item)
      && typeof item.product_id === 'number'
      && typeof item.name === 'string'
      && (item.variant_label === undefined || item.variant_label === null || typeof item.variant_label === 'string')
      && isMoneyString(item.price)
      && typeof item.quantity === 'number'
      && Number.isSafeInteger(item.quantity)
      && item.quantity > 0
      && isMoneyString(item.subtotal));
}

function isApiReview(value: unknown): value is ApiReview {
  if (!isRecord(value)) return false;
  return typeof value.id === 'number'
    && typeof value.product_id === 'number'
    && typeof value.rating === 'number'
    && Number.isFinite(value.rating)
    && value.rating >= 1
    && value.rating <= 5
    && (typeof value.comment === 'string' || value.comment === null)
    && typeof value.author_name === 'string'
    && typeof value.created_at === 'string'
    && typeof value.status === 'string'
    && (value.verified_purchase === undefined || typeof value.verified_purchase === 'boolean')
    && (value.helpful_count === undefined || (typeof value.helpful_count === 'number' && Number.isSafeInteger(value.helpful_count)))
    && (value.viewer_helpful === undefined || typeof value.viewer_helpful === 'boolean');
}

function isMarketplacePaymentStatus(value: unknown): value is MarketplacePaymentStatus {
  return value === 'pending'
    || value === 'paid'
    || value === 'review_required'
    || value === 'partially_refunded'
    || value === 'refunded'
    || value === 'expired'
    || value === 'cancelled';
}

function isOptionalNullableString(value: unknown): value is string | null | undefined {
  return value === undefined || value === null || typeof value === 'string';
}

function checkoutOrders(value: unknown): ApiOrder[] {
  if (!Array.isArray(value) || value.length === 0 || !value.every(isApiOrder)) {
    throw invalidResponse('The server returned invalid checkout orders.');
  }
  return value;
}

export function mapMarketplaceProduct(
  item: ApiProduct,
  category?: Pick<ApiCategory, 'slug'>,
): Product {
  if (!isApiProduct(item)) throw invalidResponse('The server returned an invalid product.');
  const price = money(item.price);
  const displayPrice = money(item.display_price);
  if (price === undefined || displayPrice === undefined) {
    throw invalidResponse('The server returned an invalid product price.');
  }
  if (item.rating != null && (!Number.isFinite(item.rating) || item.rating < 0 || item.rating > 5)) {
    throw invalidResponse('The server returned an invalid product rating.');
  }
  if (item.review_count != null && (!Number.isSafeInteger(item.review_count) || item.review_count < 0)) {
    throw invalidResponse('The server returned an invalid review count.');
  }
  return {
    id: item.id,
    sku: item.sku || '',
    seller_id: item.seller_id,
    seller_name: item.seller_name || '',
    seller_location: '',
    category_id: item.category_id,
    category_slug: category?.slug || `category-${item.category_id}`,
    brand_name: item.brand_name || undefined,
    name: item.localized_name || item.name,
    name_bn: item.localized_name || item.name,
    slug: item.slug,
    description: item.localized_description || item.description,
    description_bn: item.localized_description || item.description,
    image: item.display_image || item.image || '',
    additionalImages: [],
    price,
    discount_price: displayPrice < price ? displayPrice : undefined,
    stock_quantity: item.stock,
    is_available: item.is_available,
    is_featured: item.is_featured,
    moderation_status: item.moderation_status,
    ...(item.rating != null ? { rating: item.rating } : {}),
    ...(item.review_count != null ? { review_count: item.review_count } : {}),
    unit: 'unit',
    unit_bn: 'টি',
    variants: (item.variants || []).map((variant) => ({
      id: String(variant.id),
      name: variant.option_name || 'Option',
      name_bn: variant.option_name || 'অপশন',
      priceModifier: (() => {
        return Number(variant.price) - displayPrice;
      })(),
      stock: variant.stock,
    })),
  };
}

async function requestApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<ApiEnvelope<T>> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const method = (init.method || 'GET').toUpperCase();
  let response: Response;
  try {
    if (method !== 'GET' && method !== 'HEAD') {
      headers.set('X-CSRFToken', await getCsrfToken());
    }
    response = await fetch(`${getFlaskAuthOrigin()}${path}`, {
      ...init,
      headers,
      credentials: 'include',
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    if (error instanceof FlaskAuthError) {
      throw new MarketplaceApiError(error.message, error.status, error.code);
    }
    throw new MarketplaceApiError(
      'Unable to reach the marketplace. Please check your connection and try again.',
      0,
      'NETWORK_ERROR',
    );
  }
  const payload = (await response.json().catch(() => ({}))) as ApiEnvelope<T>;
  if (!response.ok || !payload.success) {
    throw new MarketplaceApiError(
      payload.error?.message || payload.message || 'Marketplace request failed.',
      response.status,
      payload.error?.code,
    );
  }
  return payload;
}

export async function fetchMarketplaceCatalog(): Promise<{
  products: Product[];
  categories: Category[];
  total: number;
}> {
  const [categoryResponse, productResponse] = await Promise.all([
    requestApi<ApiCategory[]>('/api/v1/categories'),
    requestApi<ApiProduct[]>('/api/v1/products?limit=100&sort=featured'),
  ]);
  const apiCategories = categoryResponse.data;
  if (!Array.isArray(apiCategories) || !Array.isArray(productResponse.data)) {
    throw invalidResponse('The server returned invalid catalog data.');
  }
  const categoryById = new Map(apiCategories.map((category) => [category.id, category]));
  return {
    products: productResponse.data.map((item) =>
      mapMarketplaceProduct(item, categoryById.get(item.category_id)),
    ),
    categories: apiCategories
      .filter((category) => category.is_active)
      .map((category) => ({
        id: category.id,
        name: category.name,
        name_bn: category.name,
        slug: category.slug,
        description: category.description,
        image: category.display_image || category.image || undefined,
      })),
    total: productResponse.pagination?.total ?? productResponse.data.length,
  };
}

export interface MarketplaceCatalogQuery {
  page: number;
  limit?: number;
  query?: string;
  categorySlug?: string | null;
  minPrice?: number;
  maxPrice?: number;
  minRating?: number;
  inStockOnly?: boolean;
  discountOnly?: boolean;
  sort: 'featured' | 'relevance' | 'newest' | 'price_asc' | 'price_desc';
}

export async function fetchMarketplaceCatalogPage(
  query: MarketplaceCatalogQuery,
  categories: Category[],
  signal?: AbortSignal,
): Promise<{ products: Product[]; page: number; limit: number; total: number }> {
  const limit = query.limit ?? 24;
  const params = new URLSearchParams({
    page: String(query.page),
    limit: String(limit),
    sort: query.query?.trim() && query.sort === 'featured' ? 'relevance' : query.sort,
  });
  const normalizedQuery = query.query?.trim();
  if (normalizedQuery) params.set('q', normalizedQuery);
  if (query.minPrice !== undefined) params.set('min_price', String(query.minPrice));
  if (query.maxPrice !== undefined) params.set('max_price', String(query.maxPrice));
  if (query.minRating !== undefined && query.minRating > 0) {
    params.set('min_rating', String(query.minRating));
  }
  if (query.inStockOnly) params.set('in_stock', '1');
  if (query.discountOnly) params.set('discount', '1');

  const path = query.categorySlug
    ? `/api/v1/categories/${encodeURIComponent(query.categorySlug)}`
    : '/api/v1/products';
  const response = await requestApi<ApiProduct[]>(`${path}?${params.toString()}`, { signal });
  const data = response.data;
  if (!Array.isArray(data)) throw invalidResponse('The server returned invalid catalog data.');
  const categoryById = new Map(categories.map((category) => [category.id, category]));

  return {
    products: data.map((item) => mapMarketplaceProduct(item, categoryById.get(item.category_id))),
    page: response.pagination?.page ?? query.page,
    limit: response.pagination?.limit ?? limit,
    total: response.pagination?.total ?? data.length,
  };
}

export async function addMarketplaceCartItem(
  product: Product,
  variant: CartItem['selectedVariant'],
  quantity: number,
): Promise<void> {
  await requestApi('/api/v1/cart/items', {
    method: 'POST',
    body: JSON.stringify({
      product_id: product.id,
      variant_id: variant ? Number(variant.id) : null,
      quantity,
    }),
  });
}

export async function updateMarketplaceCartItem(
  productId: number,
  variantId: string | undefined,
  quantity: number,
): Promise<void> {
  const key = variantId ? `${productId}:${variantId}` : String(productId);
  await requestApi(`/api/v1/cart/items/${encodeURIComponent(key)}`, {
    method: 'PATCH',
    body: JSON.stringify({ quantity }),
  });
}

export async function removeMarketplaceCartItem(
  productId: number,
  variantId?: string,
): Promise<void> {
  const key = variantId ? `${productId}:${variantId}` : String(productId);
  await requestApi(`/api/v1/cart/items/${encodeURIComponent(key)}`, {
    method: 'DELETE',
  });
}

export interface MarketplaceCartLine {
  key: string;
  product_id: number;
  variant_id: number | null;
  quantity: number;
  available_stock: number;
}

/**
 * Read the server-side cart for the signed-in customer. Flask remains the
 * authority for line quantities and stock, so the browser copy is reconciled
 * against this response rather than trusted on its own.
 */
export async function fetchMarketplaceCart(): Promise<{ items: MarketplaceCartLine[] }> {
  const response = await requestApi<{ items: unknown }>('/api/v1/cart');
  const items = response.data?.items;
  if (!Array.isArray(items)) throw invalidResponse('The server returned an invalid cart.');
  const valid = items.every((item) => isRecord(item)
    && typeof item.key === 'string'
    && typeof item.product_id === 'number'
    && Number.isSafeInteger(item.product_id)
    && item.product_id > 0
    && (item.variant_id === null
      || (typeof item.variant_id === 'number' && Number.isSafeInteger(item.variant_id)))
    && typeof item.quantity === 'number'
    && Number.isSafeInteger(item.quantity)
    && item.quantity > 0);
  if (!valid) throw invalidResponse('The server returned an invalid cart.');
  return {
    items: (items as MarketplaceCartLine[]).map((item) => ({
      key: item.key,
      product_id: item.product_id,
      variant_id: item.variant_id,
      quantity: item.quantity,
      available_stock: typeof item.available_stock === 'number' ? item.available_stock : 0,
    })),
  };
}

export async function clearMarketplaceCart(): Promise<void> {
  await requestApi('/api/v1/cart', { method: 'DELETE' });
}

export async function addMarketplaceWishlistItem(productId: number): Promise<void> {
  await requestApi('/api/v1/wishlist/items', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId }),
  });
}

export async function removeMarketplaceWishlistItem(productId: number): Promise<void> {
  await requestApi(`/api/v1/wishlist/items/${productId}`, { method: 'DELETE' });
}

export async function fetchMarketplaceWishlist(): Promise<number[]> {
  const response = await requestApi<{ count: number; products: ApiProduct[] }>('/api/v1/wishlist');
  return (response.data?.products || []).map((product) => product.id);
}

function mapOrder(item: ApiOrder): Order {
  const status: OrderStatus = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'].includes(item.status)
    ? item.status as OrderStatus
    : 'pending';
  return {
    id: String(item.id),
    order_number: item.order_number,
    created_at: item.created_at,
    customer_name: item.customer_name,
    customer_phone: item.phone,
    customer_email: item.email,
    delivery_address: { division: '', district: '', thana: '', street: item.address },
    delivery_speed: 'standard',
    payment_method: item.payment_method === 'sslcommerz' ? 'card' : 'cod',
    payment_status: item.payment_status === 'paid' ? 'paid' : 'pending',
    status,
    items: item.items.map((orderItem) => ({
      product_id: orderItem.product_id,
      product_name: orderItem.name,
      seller_id: 0,
      seller_name: 'NexHaat seller',
      image: '',
      unit_price: money(orderItem.price) ?? 0,
      quantity: orderItem.quantity,
      variant_name: orderItem.variant_label || undefined,
      total_price: money(orderItem.subtotal) ?? 0,
    })),
    subtotal: money(item.items_subtotal) ?? 0,
    delivery_fee: money(item.delivery_fee) ?? 0,
    discount_amount: money(item.discount_amount) ?? 0,
    promo_code: item.promotion_code || undefined,
    total_amount: money(item.total) ?? 0,
  };
}

export async function fetchMarketplaceOrders(): Promise<Order[]> {
  const response = await requestApi<ApiOrder[]>('/api/v1/orders');
  return (response.data || []).map(mapOrder);
}

export interface OrderTimelineEvent {
  id: number;
  event_type: string;
  previous_status?: string | null;
  new_status?: string | null;
  actor_role?: string | null;
  description?: string | null;
  tracking_reference?: string | null;
  carrier?: string | null;
  estimated_delivery_at?: string | null;
  created_at: string;
}

interface ApiOrderTimeline {
  order_number: string;
  status: string;
  delivery_status: string;
  events: OrderTimelineEvent[];
}

/**
 * Fetch the owner-scoped tracking timeline for one order. The Flask API enforces
 * ownership, so a 404 here means the order is not the caller's own order.
 */
export async function fetchMarketplaceOrderTimeline(
  orderNumber: string,
): Promise<OrderTimelineEvent[]> {
  const response = await requestApi<ApiOrderTimeline>(
    `/api/v1/orders/${encodeURIComponent(orderNumber)}/timeline`,
  );
  return response.data?.events || [];
}

function mapReview(item: ApiReview): Review {
  return {
    id: String(item.id),
    product_id: item.product_id,
    user_name: item.author_name,
    rating: item.rating,
    comment: item.comment || '',
    created_at: item.created_at,
    verified_purchase: Boolean(item.verified_purchase),
    helpful_count: item.helpful_count ?? 0,
    viewer_helpful: item.viewer_helpful,
  };
}

export async function fetchMarketplaceProductReviews(productId: number): Promise<Review[]> {
  const response = await requestApi<{ product_id: number; reviews: ApiReview[] }>(
    `/api/v1/products/${productId}/reviews`,
  );
  if (!isRecord(response.data) || !Array.isArray(response.data.reviews) || !response.data.reviews.every(isApiReview)) {
    throw invalidResponse('The server returned invalid product reviews.');
  }
  return response.data.reviews.map(mapReview);
}

export async function submitMarketplaceProductReview(
  productId: number,
  rating: number,
  comment: string,
): Promise<Review> {
  const response = await requestApi<ApiReview>(`/api/v1/products/${productId}/reviews`, {
    method: 'POST',
    body: JSON.stringify({ rating, comment }),
  });
  if (!isApiReview(response.data)) throw invalidResponse('The server did not return a valid review.');
  return mapReview(response.data);
}

export async function toggleMarketplaceReviewHelpful(
  productId: number,
  reviewId: string,
): Promise<{ helpful: boolean; count: number }> {
  const response = await requestApi<{ helpful: boolean; count: number }>(
    `/api/v1/products/${productId}/reviews/${encodeURIComponent(reviewId)}/helpful`,
    { method: 'POST' },
  );
  if (!isRecord(response.data)
    || typeof response.data.helpful !== 'boolean'
    || typeof response.data.count !== 'number'
    || !Number.isSafeInteger(response.data.count)
    || response.data.count < 0) {
    throw invalidResponse('The server did not return a valid helpful vote.');
  }
  return response.data;
}

export async function createMarketplaceCheckout(input: {
  customerName: string;
  phone: string;
  address: string;
  city: string;
  promotionCode?: string;
  paymentMethod: 'sslcommerz';
}): Promise<MarketplaceCheckoutResult> {
  const response = await requestApi<unknown>('/api/v1/checkout', {
    method: 'POST',
    body: JSON.stringify({
      customer_name: input.customerName,
      phone: input.phone,
      address: input.address,
      city: input.city,
      payment_method: input.paymentMethod,
      promotion_code: input.promotionCode || undefined,
    }),
  });
  const data = response.data;
  if (!isRecord(data)) throw invalidResponse('The server did not return checkout details.');
  const orders = checkoutOrders(data.orders);
  const checkoutUrl = data.checkout_url;
  const checkoutGroup = data.checkout_group;
  const paymentStatus = data.payment_status;
  const paymentStatusUrl = data.payment_status_url;
  if (!isOptionalNullableString(checkoutUrl)
    || !isOptionalNullableString(checkoutGroup)
    || (paymentStatus !== undefined && paymentStatus !== null && !isMarketplacePaymentStatus(paymentStatus))
    || !isOptionalNullableString(paymentStatusUrl)) {
    throw invalidResponse('The server returned invalid checkout payment details.');
  }
  return {
    orders: orders.map(mapOrder),
    checkout_url: checkoutUrl ?? null,
    ...(checkoutGroup !== undefined ? { checkout_group: checkoutGroup } : {}),
    ...(paymentStatus !== undefined ? { payment_status: paymentStatus } : {}),
    ...(paymentStatusUrl !== undefined ? { payment_status_url: paymentStatusUrl } : {}),
  };
}

export async function submitMarketplaceCheckout(input: {
  customerName: string;
  phone: string;
  address: string;
  city: string;
  promotionCode?: string;
}): Promise<Order> {
  const response = await requestApi<unknown>('/api/v1/checkout', {
    method: 'POST',
    body: JSON.stringify({
      customer_name: input.customerName,
      phone: input.phone,
      address: input.address,
      city: input.city,
      payment_method: 'cod',
      promotion_code: input.promotionCode || undefined,
    }),
  });
  if (!isRecord(response.data)) throw invalidResponse('The server did not return checkout details.');
  const order = checkoutOrders(response.data.orders)[0];
  return mapOrder(order);
}

export async function cancelMarketplaceOrder(orderNumber: string): Promise<Order> {
  const response = await requestApi<ApiOrder>(`/api/v1/orders/${encodeURIComponent(orderNumber)}/cancel`, {
    method: 'POST',
  });
  if (!response.data) throw new MarketplaceApiError('The server did not return the cancelled order.', 502);
  return mapOrder(response.data);
}

export async function requestMarketplaceReturn(orderNumber: string, reason: string): Promise<Order> {
  const response = await requestApi<ApiOrder>(`/api/v1/orders/${encodeURIComponent(orderNumber)}/return`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
  if (!response.data) throw new MarketplaceApiError('The server did not return the return request.', 502);
  return mapOrder(response.data);
}

export async function fetchMarketplaceNotifications(): Promise<Notification[]> {
  const response = await requestApi<{ notifications: ApiNotification[] }>('/api/v1/notifications');
  return (response.data?.notifications || []).map((item) => ({
    id: String(item.id),
    type: (['order', 'promotion', 'system', 'delivery', 'prime'].includes(item.type) ? item.type : 'system') as Notification['type'],
    title: item.message,
    title_bn: item.message,
    message: item.message,
    message_bn: item.message,
    link: item.link || undefined,
    is_read: item.is_read,
    created_at: item.created_at,
  }));
}

export async function markMarketplaceNotificationRead(id: string): Promise<void> {
  await requestApi(`/api/v1/notifications/${encodeURIComponent(id)}/read`, { method: 'POST' });
}

export async function markAllMarketplaceNotificationsRead(): Promise<void> {
  await requestApi('/api/v1/notifications/read-all', { method: 'POST' });
}
