import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { Order, OrderStatus } from '../types';
import {
  filterOrders,
  getOrderStatusCounts,
  OrderStatusFilter,
  OrderTimeRange,
  OrderSortBy,
} from '../lib/orderFilters';
import { 
  Package, Clock, CheckCircle2, XCircle, RotateCcw, 
  ChevronDown, ChevronUp, ShoppingBag, Truck, Phone, AlertCircle,
  Search, X, SlidersHorizontal, Calendar, ArrowUpDown, Filter
} from 'lucide-react';

export const MyOrdersPage: React.FC = () => {
  const { 
    orders, 
    cancelOrder, 
    requestOrderReturn, 
    addToCart, 
    products, 
    formatPrice, 
    setCurrentView,
    setIsCartDrawerOpen, 
    t 
  } = useApp();

  const [statusFilter, setStatusFilter] = useState<OrderStatusFilter>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [timeRange, setTimeRange] = useState<OrderTimeRange>('all');
  const [sortBy, setSortBy] = useState<OrderSortBy>('date_desc');
  const [expandedOrders, setExpandedOrders] = useState<Record<string, boolean>>({});
  const [returnModalOrder, setReturnModalOrder] = useState<Order | null>(null);
  const [returnReason, setReturnReason] = useState<string>('Damaged or freshness issue');

  // Compute status counts for badges
  const statusCounts = useMemo(() => getOrderStatusCounts(orders), [orders]);

  // Compute filtered orders
  const filteredOrders = useMemo(
    () =>
      filterOrders(orders, {
        status: statusFilter,
        searchQuery,
        timeRange,
        sortBy,
      }),
    [orders, statusFilter, searchQuery, timeRange, sortBy]
  );

  const hasActiveFilters = statusFilter !== 'all' || searchQuery.trim() !== '' || timeRange !== 'all';

  const resetAllFilters = () => {
    setStatusFilter('all');
    setSearchQuery('');
    setTimeRange('all');
    setSortBy('date_desc');
  };

  const toggleExpand = (orderNumber: string) => {
    setExpandedOrders(prev => ({ ...prev, [orderNumber]: !prev[orderNumber] }));
  };

  const handleBuyAgain = (order: Order) => {
    order.items.forEach(item => {
      const liveProduct = products.find(p => p.id === item.product_id);
      if (liveProduct && liveProduct.is_available) {
        addToCart(liveProduct, undefined, item.quantity);
      }
    });
    setIsCartDrawerOpen(true);
  };

  const handleReturnSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!returnModalOrder) return;
    requestOrderReturn(returnModalOrder.order_number, returnReason);
    setReturnModalOrder(null);
  };

  const getStatusBadge = (status: OrderStatus) => {
    switch (status) {
      case 'delivered':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{t('Delivered', 'ডেলিভারি সম্পন্ন')}</span>
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800">
            <XCircle className="w-3.5 h-3.5" />
            <span>{t('Cancelled', 'বাতিল')}</span>
          </span>
        );
      case 'shipped':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 text-blue-800">
            <Truck className="w-3.5 h-3.5" />
            <span>{t('Out with Rider', 'রাইডারের কাছে')}</span>
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
            <Clock className="w-3.5 h-3.5" />
            <span>{t('Preparing', 'প্যাকেজিং হচ্ছে')}</span>
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3.5 h-3.5" />
            <span>{t('Pending Approval', 'অনুমোদনের অপেক্ষায়')}</span>
          </span>
        );
      case 'confirmed':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-800">
            <Clock className="w-3.5 h-3.5" />
            <span>{t('Confirmed', 'নিশ্চিত')}</span>
          </span>
        );
    }
  };

  const statusTabItems: { id: OrderStatusFilter; label: string; count: number }[] = [
    { id: 'all', label: t('All Orders', 'সব অর্ডার'), count: statusCounts.all },
    { id: 'pending', label: t('Pending', 'অপেক্ষমাণ'), count: statusCounts.pending },
    { id: 'processing', label: t('Processing', 'প্রক্রিয়াধীন'), count: statusCounts.processing + statusCounts.confirmed },
    { id: 'shipped', label: t('In Transit', 'চলমান'), count: statusCounts.shipped },
    { id: 'delivered', label: t('Delivered', 'ডেলিভারিকৃত'), count: statusCounts.delivered },
    { id: 'cancelled', label: t('Cancelled', 'বাতিলকৃত'), count: statusCounts.cancelled },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-16">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-ink">
          {t('My Orders & Tracking', 'আমার অর্ডার ও ট্র্যাকিং')}
        </h1>
        <p className="text-xs sm:text-sm text-muted mt-0.5">
          {t(
            'Filter and track order status, review delivery history, and request returns in real-time',
            'অর্ডারের অগ্রগতি দেখুন, স্ট্যাটাস ফিল্টার করুন এবং দ্রুত রি-অর্ডার করুন'
          )}
        </p>
      </div>

      {/* FILTER CONTROLS HUB */}
      <div className="bg-white rounded-3xl border border-border shadow-xs p-4 sm:p-5 space-y-4">
        {/* Status Filter Tabs / Chips */}
        <div>
          <div className="flex items-center justify-between text-xs font-bold text-slate-600 mb-2">
            <span className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-primary" />
              <span>{t('Filter by Order Status:', 'স্ট্যাটাস অনুযায়ী ফিল্টার:')}</span>
            </span>
            <span className="text-muted font-normal text-[11px]">
              {t(`Total: ${orders.length} orders`, `মোট: ${orders.length}টি অর্ডার`)}
            </span>
          </div>

          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
            {statusTabItems.map((tab) => {
              const isSelected = statusFilter === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setStatusFilter(tab.id)}
                  className={`px-3.5 py-2 rounded-2xl text-xs font-bold transition-all shrink-0 flex items-center gap-2 border ${
                    isSelected
                      ? 'bg-primary text-white border-primary shadow-sm'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100 hover:border-slate-300'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                      isSelected
                        ? 'bg-white/25 text-white'
                        : 'bg-white text-slate-600 border border-slate-200'
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Search Bar and Secondary Filter Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-2 border-t border-slate-100">
          {/* Search Input */}
          <div className="sm:col-span-6 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('Search order #, product, or area...', 'অর্ডার নম্বর, পণ্যের নাম বা এলাকা দিয়ে খুঁজুন...')}
              className="w-full pl-9 pr-8 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs focus:bg-white focus:border-primary transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-ink"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Time Range Filter */}
          <div className="sm:col-span-3">
            <div className="relative">
              <Calendar className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value as OrderTimeRange)}
                className="w-full pl-8 pr-6 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-700 focus:bg-white focus:border-primary appearance-none cursor-pointer"
              >
                <option value="all">{t('All Time', 'সব সময়')}</option>
                <option value="30d">{t('Last 30 Days', 'বিগত ৩০ দিন')}</option>
                <option value="90d">{t('Last 90 Days', 'বিগত ৯০ দিন')}</option>
                <option value="year">{t('Past Year', 'বিগত ১ বছর')}</option>
              </select>
              <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          {/* Sort By Selector */}
          <div className="sm:col-span-3">
            <div className="relative">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as OrderSortBy)}
                className="w-full pl-8 pr-6 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs text-slate-700 focus:bg-white focus:border-primary appearance-none cursor-pointer"
              >
                <option value="date_desc">{t('Newest First', 'নতুন আগে')}</option>
                <option value="date_asc">{t('Oldest First', 'পুরাতন আগে')}</option>
                <option value="amount_desc">{t('Highest Total', 'বেশি মূল্য')}</option>
                <option value="amount_asc">{t('Lowest Total', 'কম মূল্য')}</option>
              </select>
              <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Active Filter Indicators and Reset Action */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs">
            <div className="flex flex-wrap items-center gap-1.5 text-muted">
              <span>{t('Filtering:', 'ফিল্টার:')}</span>
              {statusFilter !== 'all' && (
                <span className="px-2 py-0.5 rounded-lg bg-primary/10 text-primary font-bold">
                  {statusTabItems.find((tab) => tab.id === statusFilter)?.label}
                </span>
              )}
              {searchQuery.trim() && (
                <span className="px-2 py-0.5 rounded-lg bg-slate-100 text-slate-700 font-semibold">
                  "{searchQuery}"
                </span>
              )}
              {timeRange !== 'all' && (
                <span className="px-2 py-0.5 rounded-lg bg-amber-100 text-amber-900 font-semibold">
                  {timeRange === '30d' ? '30 Days' : timeRange === '90d' ? '90 Days' : '1 Year'}
                </span>
              )}
              <span className="text-slate-400 ml-1">
                • {t(`Showing ${filteredOrders.length} of ${orders.length} orders`, `${orders.length}টির মধ্যে ${filteredOrders.length}টি প্রদর্শিত`)}
              </span>
            </div>

            <button
              type="button"
              onClick={resetAllFilters}
              className="text-primary hover:text-primary-hover font-bold flex items-center gap-1 text-xs"
            >
              <RotateCcw className="w-3 h-3" />
              <span>{t('Reset Filters', 'সব ফিল্টার মুছুন')}</span>
            </button>
          </div>
        )}
      </div>

      {/* Orders List */}
      <div className="space-y-4">
        {filteredOrders.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-3xl border border-border shadow-card space-y-4">
            <div className="w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Package className="w-8 h-8" />
            </div>
            <div>
              <h3 className="font-bold text-ink text-base">
                {hasActiveFilters
                  ? t('No orders match your filter criteria', 'ফিল্টারের সাথে মেলে এমন কোনো অর্ডার পাওয়া যায়নি')
                  : t('No orders found in this view', 'কোনো অর্ডার পাওয়া যায়নি')}
              </h3>
              <p className="text-xs text-muted max-w-sm mx-auto mt-1">
                {hasActiveFilters
                  ? t(
                      'Try choosing a different status filter or clearing your search keywords.',
                      'অন্য কোনো স্ট্যাটাস ফিল্টার নির্বাচন করুন অথবা সার্চ কি-ওয়ার্ড মুছে চেষ্টা করুন।'
                    )
                  : t(
                      'Browse the marketplace to find fresh foods and daily goods.',
                      'মার্কেটপ্লেস ব্রাউজ করে পছন্দের পণ্য অর্ডার করুন।'
                    )}
              </p>
            </div>

            {hasActiveFilters ? (
              <button
                type="button"
                onClick={resetAllFilters}
                className="px-5 py-2.5 rounded-xl bg-primary text-white text-xs font-bold shadow-sm inline-flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>{t('Clear Filters & Show All', 'ফিল্টার মুছুন ও সব দেখুন')}</span>
              </button>
            ) : (
              <button
                onClick={() => setCurrentView('catalog')}
                className="px-5 py-2.5 rounded-xl bg-primary text-white text-xs font-bold shadow-sm"
              >
                {t('Start Shopping', 'কেনাকাটা শুরু করুন')}
              </button>
            )}
          </div>
        ) : (
          filteredOrders.map(order => {
            const isExpanded = Boolean(expandedOrders[order.order_number]);
            const canCancel = ['pending', 'confirmed'].includes(order.status);
            const canReturn = order.status === 'delivered' && (!order.return_status || order.return_status === 'none');

            return (
              <div
                key={order.id}
                className="rounded-3xl bg-white border border-border shadow-card overflow-hidden transition-all"
              >
                {/* Order Summary Row */}
                <div className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 bg-surface-raised">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono font-bold text-sm text-ink">{order.order_number}</span>
                      {getStatusBadge(order.status)}
                    </div>
                    <p className="text-xs text-slate-400">
                      {t('Placed on', 'তারিখ:')} {new Date(order.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-4">
                    <div className="text-left sm:text-right">
                      <span className="text-xs text-muted">{t('Total Amount', 'সর্বমোট মূল্য')}</span>
                      <p className="font-black text-base text-primary">{formatPrice(order.total_amount)}</p>
                    </div>

                    <button
                      onClick={() => toggleExpand(order.order_number)}
                      className="p-2 rounded-xl bg-white border border-slate-200 text-slate-600 hover:text-ink text-xs font-bold flex items-center gap-1 shadow-xs"
                    >
                      <span>{isExpanded ? t('Hide', 'লুকান') : t('Details', 'বিস্তারিত')}</span>
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="p-5 sm:p-6 space-y-5">
                    {/* Return status alert if requested */}
                    {order.return_status && order.return_status !== 'none' && (
                      <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                        <div>
                          <strong>{t('Return Status:', 'রিটার্ন স্ট্যাটাস:')} {order.return_status.toUpperCase()}</strong>
                          <p className="text-[11px] text-amber-800 mt-0.5">
                            Reason: "{order.return_reason}" • Refund Ref: {order.return_refund_ref}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Rider info if out with rider */}
                    {order.rider_name && (
                      <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200 text-xs flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <Truck className="w-4 h-4 text-primary" />
                          <div>
                            <span className="font-bold text-ink">{t('Assigned Express Rider:', 'নিযুক্ত এক্সপ্রেস রাইডার:')}</span>
                            <span className="text-slate-600 ml-1">{order.rider_name}</span>
                          </div>
                        </div>
                        <a
                          href={`tel:${order.rider_phone}`}
                          className="px-3 py-1 rounded-lg bg-primary text-white text-[11px] font-bold flex items-center gap-1"
                        >
                          <Phone className="w-3 h-3" />
                          <span>{t('Call Rider', 'ফোন করুন')}</span>
                        </a>
                      </div>
                    )}

                    {/* Item list */}
                    <div className="divide-y divide-slate-100">
                      {order.items.map((item, idx) => (
                        <div key={idx} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                          <div className="flex items-center gap-3">
                            <img
                              src={item.image}
                              alt={item.product_name}
                              className="w-11 h-11 rounded-lg object-cover bg-slate-50 shrink-0"
                            />
                            <div>
                              <p className="font-semibold text-ink">{item.product_name}</p>
                              <p className="text-[11px] text-muted">
                                {item.seller_name} • {item.quantity} × {formatPrice(item.unit_price)}
                              </p>
                            </div>
                          </div>
                          <span className="font-bold text-ink">{formatPrice(item.total_price)}</span>
                        </div>
                      ))}
                    </div>

                    {/* Address & payment details */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-slate-100 text-xs text-slate-600">
                      <div>
                        <strong className="block text-ink mb-1">{t('Delivery Address', 'ডেলিভারি ঠিকানা')}</strong>
                        <p>{order.delivery_address.street}, {order.delivery_address.thana}, {order.delivery_address.district}</p>
                      </div>
                      <div>
                        <strong className="block text-ink mb-1">{t('Payment Information', 'পেমেন্ট তথ্য')}</strong>
                        <p className="uppercase">{order.payment_method} ({order.payment_status})</p>
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex gap-2">
                        {canCancel && (
                          <button
                            onClick={() => cancelOrder(order.order_number)}
                            className="px-4 py-2 rounded-xl border border-rose-200 text-danger text-xs font-bold hover:bg-rose-50 transition-colors"
                          >
                            {t('Cancel Order', 'অর্ডার বাতিল করুন')}
                          </button>
                        )}
                        {canReturn && (
                          <button
                            onClick={() => setReturnModalOrder(order)}
                            className="px-4 py-2 rounded-xl border border-amber-300 text-amber-800 text-xs font-bold hover:bg-amber-50 transition-colors"
                          >
                            {t('Request Return / Refund', 'রিটার্ন / রিফান্ড আবেদন')}
                          </button>
                        )}
                      </div>

                      <button
                        onClick={() => handleBuyAgain(order)}
                        className="neu-button px-4 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-sm flex items-center gap-1.5"
                      >
                        <ShoppingBag className="w-3.5 h-3.5" />
                        <span>{t('Buy Again', 'আবার কিনুন')}</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Return Request Modal */}
      {returnModalOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <form onSubmit={handleReturnSubmit} className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-base text-ink">
                {t('Request Return for', 'রিটার্ন আবেদন:')} {returnModalOrder.order_number}
              </h3>
              <button
                type="button"
                onClick={() => setReturnModalOrder(null)}
                className="text-slate-400 hover:text-ink text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-muted">
              {t(
                'NexHaat provides 7-day hassle-free returns on perishable foods and goods. Please specify the reason:',
                'পণ্য পরিবর্তনের কারণ উল্লেখ করুন:'
              )}
            </p>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                {t('Reason for Return:', 'রিটার্নের কারণ:')}
              </label>
              <select
                value={returnReason}
                onChange={(e) => setReturnReason(e.target.value)}
                className="w-full p-2.5 rounded-xl border border-slate-200 text-xs bg-slate-50"
              >
                <option value="Damaged or quality issue">Damaged or freshness issue</option>
                <option value="Wrong item delivered">Wrong item delivered</option>
                <option value="Expired or near-expiry date">Quality below expectations</option>
                <option value="Not as described">Item not as pictured</option>
              </select>
            </div>

            <div className="p-3 bg-emerald-50 rounded-xl text-xs text-emerald-800">
              {t(
                'Refund will be credited to your original payment channel within 24-48 hours.',
                'অনুমোদনের পর ২৪-৪৮ ঘণ্টার মধ্যে টাকা ফেরত দেওয়া হবে।'
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setReturnModalOrder(null)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold"
              >
                {t('Cancel', 'বাতিল')}
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover"
              >
                {t('Submit Return Request', 'আবেদন জমা দিন')}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
