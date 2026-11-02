/**
 * Order filtering, search, and status aggregation engine for NexHaat
 */

import { Order, OrderStatus } from '../types';

export type OrderStatusFilter = 'all' | OrderStatus | 'active';
export type OrderTimeRange = 'all' | '30d' | '90d' | 'year';
export type OrderSortBy = 'date_desc' | 'date_asc' | 'amount_desc' | 'amount_asc';

export interface OrderFilterOptions {
  status?: OrderStatusFilter;
  searchQuery?: string;
  timeRange?: OrderTimeRange;
  sortBy?: OrderSortBy;
}

export interface OrderStatusCounts {
  all: number;
  pending: number;
  confirmed: number;
  processing: number;
  shipped: number;
  delivered: number;
  cancelled: number;
  active: number;
}

/**
 * Computes counts for each order status for tab badges
 */
export function getOrderStatusCounts(orders: Order[]): OrderStatusCounts {
  const counts: OrderStatusCounts = {
    all: orders.length,
    pending: 0,
    confirmed: 0,
    processing: 0,
    shipped: 0,
    delivered: 0,
    cancelled: 0,
    active: 0,
  };

  const activeStatuses: OrderStatus[] = ['pending', 'confirmed', 'processing', 'shipped'];

  for (const order of orders) {
    if (order.status in counts) {
      counts[order.status]++;
    }
    if (activeStatuses.includes(order.status)) {
      counts.active++;
    }
  }

  return counts;
}

/**
 * Filters and sorts orders according to user selections
 */
export function filterOrders(orders: Order[], options: OrderFilterOptions = {}): Order[] {
  const {
    status = 'all',
    searchQuery = '',
    timeRange = 'all',
    sortBy = 'date_desc',
  } = options;

  const trimmedQuery = searchQuery.trim().toLowerCase();
  const now = Date.now();

  return orders
    .filter((order) => {
      // 1. Status Filter
      if (status !== 'all') {
        if (status === 'active') {
          const activeStatuses: OrderStatus[] = ['pending', 'confirmed', 'processing', 'shipped'];
          if (!activeStatuses.includes(order.status)) return false;
        } else if (order.status !== status) {
          return false;
        }
      }

      // 2. Time Range Filter
      if (timeRange !== 'all') {
        const orderTime = new Date(order.created_at).getTime();
        if (isNaN(orderTime)) {
          // If unparseable date, keep it
        } else {
          const ageMs = now - orderTime;
          if (timeRange === '30d' && ageMs > 30 * 24 * 60 * 60 * 1000) return false;
          if (timeRange === '90d' && ageMs > 90 * 24 * 60 * 60 * 1000) return false;
          if (timeRange === 'year' && ageMs > 365 * 24 * 60 * 60 * 1000) return false;
        }
      }

      // 3. Search Query Filter (order number, product names, seller names, street/district)
      if (trimmedQuery) {
        const matchOrderNumber = order.order_number.toLowerCase().includes(trimmedQuery);
        const matchAddress =
          order.delivery_address.district.toLowerCase().includes(trimmedQuery) ||
          order.delivery_address.thana.toLowerCase().includes(trimmedQuery) ||
          order.delivery_address.street.toLowerCase().includes(trimmedQuery);
        const matchItems = order.items.some(
          (item) =>
            item.product_name.toLowerCase().includes(trimmedQuery) ||
            (item.product_name_bn && item.product_name_bn.toLowerCase().includes(trimmedQuery)) ||
            item.seller_name.toLowerCase().includes(trimmedQuery)
        );

        if (!matchOrderNumber && !matchAddress && !matchItems) {
          return false;
        }
      }

      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'date_asc') {
        return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      }
      if (sortBy === 'amount_desc') {
        return b.total_amount - a.total_amount;
      }
      if (sortBy === 'amount_asc') {
        return a.total_amount - b.total_amount;
      }
      // default: date_desc
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
}
