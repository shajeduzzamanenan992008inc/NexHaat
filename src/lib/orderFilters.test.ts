import test from 'node:test';
import assert from 'node:assert/strict';
import { filterOrders, getOrderStatusCounts } from './orderFilters';
import { Order } from '../types';

const sampleOrders: Order[] = [
  {
    id: 'ord_1',
    order_number: 'NH-2026-1001',
    created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
    customer_name: 'Tanvir Ahmed',
    customer_phone: '01711000000',
    customer_email: 'tanvir@example.com',
    delivery_address: {
      division: 'Dhaka',
      district: 'Dhaka',
      thana: 'Dhanmondi',
      street: 'Road 27',
    },
    delivery_speed: 'standard',
    payment_method: 'bkash',
    payment_status: 'paid',
    status: 'pending',
    items: [
      {
        product_id: 1,
        product_name: 'Premium Hilsa Fish',
        product_name_bn: 'পদ্মার ইলিশ',
        seller_id: 1,
        seller_name: 'Chandpur Fresh River Fisheries',
        image: '/img/hilsa.jpg',
        unit_price: 1800,
        quantity: 1,
        total_price: 1800,
      },
    ],
    subtotal: 1800,
    delivery_fee: 60,
    discount_amount: 0,
    total_amount: 1860,
  },
  {
    id: 'ord_2',
    order_number: 'NH-2026-1002',
    created_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(), // 10 days ago
    customer_name: 'Tanvir Ahmed',
    customer_phone: '01711000000',
    customer_email: 'tanvir@example.com',
    delivery_address: {
      division: 'Dhaka',
      district: 'Dhaka',
      thana: 'Gulshan',
      street: 'Gulshan Avenue',
    },
    delivery_speed: 'express',
    payment_method: 'cod',
    payment_status: 'paid',
    status: 'delivered',
    items: [
      {
        product_id: 2,
        product_name: 'Organic Kalijira Aromatic Rice',
        product_name_bn: 'কালিজিরা চাল',
        seller_id: 2,
        seller_name: 'Dinajpur Heritage Agro',
        image: '/img/rice.jpg',
        unit_price: 320,
        quantity: 2,
        total_price: 640,
      },
    ],
    subtotal: 640,
    delivery_fee: 100,
    discount_amount: 50,
    total_amount: 690,
  },
  {
    id: 'ord_3',
    order_number: 'NH-2026-1003',
    created_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(), // 45 days ago
    customer_name: 'Tanvir Ahmed',
    customer_phone: '01711000000',
    customer_email: 'tanvir@example.com',
    delivery_address: {
      division: 'Dhaka',
      district: 'Dhaka',
      thana: 'Mirpur',
      street: 'Section 10',
    },
    delivery_speed: 'standard',
    payment_method: 'card',
    payment_status: 'paid',
    status: 'cancelled',
    items: [
      {
        product_id: 3,
        product_name: 'Mustard Oil Pure Kachi Ghani',
        product_name_bn: 'খাঁটি সরিষার তেল',
        seller_id: 3,
        seller_name: 'Shorisha Agro',
        image: '/img/oil.jpg',
        unit_price: 450,
        quantity: 1,
        total_price: 450,
      },
    ],
    subtotal: 450,
    delivery_fee: 60,
    discount_amount: 0,
    total_amount: 510,
  },
];

test('getOrderStatusCounts accurately aggregates status totals', () => {
  const counts = getOrderStatusCounts(sampleOrders);
  assert.equal(counts.all, 3);
  assert.equal(counts.pending, 1);
  assert.equal(counts.delivered, 1);
  assert.equal(counts.cancelled, 1);
  assert.equal(counts.active, 1); // ord_1 is pending
});

test('filterOrders filters by specific status correctly', () => {
  const pendingOrders = filterOrders(sampleOrders, { status: 'pending' });
  assert.equal(pendingOrders.length, 1);
  assert.equal(pendingOrders[0].order_number, 'NH-2026-1001');

  const deliveredOrders = filterOrders(sampleOrders, { status: 'delivered' });
  assert.equal(deliveredOrders.length, 1);
  assert.equal(deliveredOrders[0].order_number, 'NH-2026-1002');

  const cancelledOrders = filterOrders(sampleOrders, { status: 'cancelled' });
  assert.equal(cancelledOrders.length, 1);
  assert.equal(cancelledOrders[0].order_number, 'NH-2026-1003');
});

test('filterOrders searches by order number, product name, or location', () => {
  // Search by order number fragment
  const byNumber = filterOrders(sampleOrders, { searchQuery: '1002' });
  assert.equal(byNumber.length, 1);
  assert.equal(byNumber[0].order_number, 'NH-2026-1002');

  // Search by product name
  const byProduct = filterOrders(sampleOrders, { searchQuery: 'Hilsa' });
  assert.equal(byProduct.length, 1);
  assert.equal(byProduct[0].order_number, 'NH-2026-1001');

  // Search by Bengali name
  const byProductBn = filterOrders(sampleOrders, { searchQuery: 'সরিষার' });
  assert.equal(byProductBn.length, 1);
  assert.equal(byProductBn[0].order_number, 'NH-2026-1003');

  // Search by Thana
  const byThana = filterOrders(sampleOrders, { searchQuery: 'Gulshan' });
  assert.equal(byThana.length, 1);
  assert.equal(byThana[0].order_number, 'NH-2026-1002');
});

test('filterOrders applies timeRange and sorting', () => {
  // 30d should exclude ord_3 (which is 45 days old)
  const recentOrders = filterOrders(sampleOrders, { timeRange: '30d' });
  assert.equal(recentOrders.length, 2);

  // Sorting by amount desc
  const sortedByAmount = filterOrders(sampleOrders, { sortBy: 'amount_desc' });
  assert.equal(sortedByAmount[0].total_amount, 1860);
  assert.equal(sortedByAmount[2].total_amount, 510);
});
