export type UserRole = 'customer' | 'seller' | 'rider' | 'admin';

export interface User {
  id: string;
  name: string;
  email: string;
  phone: string;
  role: UserRole;
  storeName?: string;
  avatar?: string;
  address?: string;
  city?: string;
  isVerified?: boolean;
  isPrimeMember?: boolean;
  walletBalance?: number;
}

export interface Category {
  id: number;
  name: string;
  name_bn: string;
  slug: string;
  description: string;
  image?: string;
  iconName?: string;
}

export interface ProductVariant {
  id: string;
  name: string;
  name_bn?: string;
  priceModifier: number;
  stock: number;
}

export interface FoodDetails {
  isHalal: boolean;
  isOrganic?: boolean;
  origin?: string;
  shelfLife?: string;
  netWeight?: string;
  nutritionalHighlights?: string[];
}

export interface BulkDiscountTier {
  minQty: number;
  discountPercent: number;
}

export interface Product {
  id: number;
  sku: string;
  seller_id: number;
  seller_name: string;
  seller_location: string;
  category_id: number;
  category_slug: string;
  brand_name?: string;
  name: string;
  name_bn: string;
  slug: string;
  description: string;
  description_bn: string;
  image: string;
  additionalImages?: string[];
  price: number;
  discount_price?: number;
  stock_quantity: number;
  is_available: boolean;
  is_featured: boolean;
  is_nexhaat_choice?: boolean;
  is_best_seller?: boolean;
  is_sponsored?: boolean;
  prime_eligible?: boolean;
  rating: number;
  review_count: number;
  unit: string;
  unit_bn: string;
  food_details?: FoodDetails;
  specifications?: Record<string, string>;
  bulk_discounts?: BulkDiscountTier[];
  variants?: ProductVariant[];
  moderation_status?: 'approved' | 'pending' | 'rejected';
}

export interface CartItem {
  product: Product;
  selectedVariant?: ProductVariant;
  quantity: number;
}

export type OrderStatus = 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled';

export interface OrderItem {
  product_id: number;
  product_name: string;
  product_name_bn?: string;
  seller_id: number;
  seller_name: string;
  image: string;
  unit_price: number;
  quantity: number;
  variant_name?: string;
  total_price: number;
}

export interface Order {
  id: string;
  order_number: string;
  created_at: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  delivery_address: {
    division: string;
    district: string;
    thana: string;
    street: string;
    notes?: string;
  };
  delivery_speed: 'standard' | 'express';
  payment_method: 'cod' | 'bkash' | 'nagad' | 'card';
  payment_status: 'paid' | 'pending';
  status: OrderStatus;
  items: OrderItem[];
  subtotal: number;
  delivery_fee: number;
  discount_amount: number;
  promo_code?: string;
  total_amount: number;
  rider_name?: string;
  rider_phone?: string;
  return_status?: 'none' | 'requested' | 'approved' | 'rejected' | 'refunded';
  return_reason?: string;
  return_refund_ref?: string;
}

export interface Review {
  id: string;
  product_id: number;
  user_name: string;
  rating: number;
  comment: string;
  created_at: string;
  verified_purchase: boolean;
  helpful_count: number;
}

export interface ProductQuestion {
  id: string;
  product_id: number;
  user_name: string;
  question: string;
  answer?: string;
  answered_by?: string;
  created_at: string;
}

export interface PriceAlert {
  id: string;
  product_id: number;
  product_name: string;
  product_name_bn?: string;
  product_image: string;
  product_slug: string;
  initial_price: number;
  target_price: number;
  current_price: number;
  is_active: boolean;
  is_triggered: boolean;
  created_at: string;
  triggered_at?: string;
}

export interface Notification {
  id: string;
  type: 'order' | 'promotion' | 'system' | 'delivery' | 'prime' | 'price_alert';
  title: string;
  title_bn: string;
  message: string;
  message_bn: string;
  link?: string;
  product_slug?: string;
  is_read: boolean;
  created_at: string;
}

export interface Promotion {
  id: string;
  code: string;
  description: string;
  discount_percent?: number;
  discount_amount?: number;
  min_spend: number;
  is_active: boolean;
  expires_at: string;
}

export interface AIChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  suggestedProductIds?: number[];
}

export interface SponsoredCampaign {
  id: string;
  seller_id: number;
  product_id: number;
  campaign_name: string;
  daily_budget: number;
  cpc: number;
  impressions: number;
  clicks: number;
  spend: number;
  status: 'active' | 'paused';
}
