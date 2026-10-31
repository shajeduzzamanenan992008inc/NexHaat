import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Order, OrderStatus } from '../types';
import { 
  Package, Clock, CheckCircle2, XCircle, RotateCcw, 
  ChevronDown, ChevronUp, ShoppingBag, Truck, Phone, AlertCircle 
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

  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'delivered' | 'cancelled'>('all');
  const [expandedOrders, setExpandedOrders] = useState<Record<string, boolean>>({});
  const [returnModalOrder, setReturnModalOrder] = useState<Order | null>(null);
  const [returnReason, setReturnReason] = useState<string>('Damaged or freshness issue');

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

  const filteredOrders = orders.filter(ord => {
    if (activeTab === 'all') return true;
    if (activeTab === 'active') return ['pending', 'confirmed', 'processing', 'shipped'].includes(ord.status);
    if (activeTab === 'delivered') return ord.status === 'delivered';
    if (activeTab === 'cancelled') return ord.status === 'cancelled';
    return true;
  });

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

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-16">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-ink">
          {t('My Orders & Tracking', 'আমার অর্ডার ও ট্র্যাকিং')}
        </h1>
        <p className="text-xs sm:text-sm text-muted mt-0.5">
          {t('Review active deliveries, request returns, and track shipments in real-time', 'অর্ডারের অগ্রগতি দেখুন এবং দ্রুত রি-অর্ডার করুন')}
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-border pb-2 overflow-x-auto">
        {[
          { id: 'all', label: t('All Orders', 'সব অর্ডার') },
          { id: 'active', label: t('Active & In Transit', 'চলমান অর্ডার') },
          { id: 'delivered', label: t('Delivered', 'ডেলিভারিকৃত') },
          { id: 'cancelled', label: t('Cancelled', 'বাতিলকৃত') },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
              activeTab === tab.id
                ? 'bg-primary text-white shadow-sm'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Orders List */}
      <div className="space-y-4">
        {filteredOrders.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-3xl border border-border shadow-card space-y-3">
            <div className="w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Package className="w-8 h-8" />
            </div>
            <h3 className="font-bold text-ink text-base">
              {t('No orders found in this view', 'কোনো অর্ডার পাওয়া যায়নি')}
            </h3>
            <p className="text-xs text-muted max-w-xs mx-auto">
              {t('Browse the marketplace to find fresh foods and daily goods.', 'মার্কেটপ্লেস ব্রাউজ করে পছন্দের পণ্য অর্ডার করুন।')}
            </p>
            <button
              onClick={() => setCurrentView('catalog')}
              className="px-5 py-2.5 rounded-xl bg-primary text-white text-xs font-bold shadow-sm"
            >
              {t('Start Shopping', 'কেনাকাটা শুরু করুন')}
            </button>
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
