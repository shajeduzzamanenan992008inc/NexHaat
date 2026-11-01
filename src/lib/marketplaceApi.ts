import { getCsrfToken, getFlaskAuthOrigin } from './flaskAuth';
import { Category, CartItem, Notification, Order, OrderStatus, Product } from '../types';

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

const money = (value: string | null | undefined): number | undefined => {
  if (value == null) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

export function mapMarketplaceProduct(
  item: ApiProduct,
  category?: ApiCategory,
): Product {
  const price = money(item.price) ?? 0;
  const displayPrice = money(item.display_price) ?? price;
  return {
    id: item.id,
    sku: item.sku || `product-${item.id}`,
    seller_id: item.seller_id,
    seller_name: 'NexHaat seller',
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
    rating: 0,
    review_count: 0,
    unit: 'unit',
    unit_bn: 'টি',
    variants: (item.variants || []).map((variant) => ({
      id: String(variant.id),
      name: variant.option_name || 'Option',
      name_bn: variant.option_name || 'অপশন',
      priceModifier: (money(variant.price) ?? displayPrice) - displayPrice,
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
  if (method !== 'GET' && method !== 'HEAD') {
    headers.set('X-CSRFToken', await getCsrfToken());
  }
  const response = await fetch(`${getFlaskAuthOrigin()}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  });
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
  const apiCategories = categoryResponse.data || [];
  const categoryById = new Map(apiCategories.map((category) => [category.id, category]));
  return {
    products: (productResponse.data || []).map((item) =>
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
    total: productResponse.pagination?.total || productResponse.data?.length || 0,
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

export async function submitMarketplaceCheckout(input: {
  customerName: string;
  phone: string;
  address: string;
  city: string;
  promotionCode?: string;
}): Promise<Order> {
  const response = await requestApi<{ orders: ApiOrder[] }>('/api/v1/checkout', {
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
  const order = response.data?.orders?.[0];
  if (!order) throw new MarketplaceApiError('The server did not return an order.', 502);
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
