import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  CheckCircle2, Package, Truck, Clock, ArrowRight, 
  Printer, ShoppingBag, ShieldCheck, Phone, MapPin 
} from 'lucide-react';

export const OrderConfirmationPage: React.FC = () => {
  const { lastConfirmedOrder, setCurrentView, formatPrice, t, language } = useApp();
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);

  if (!lastConfirmedOrder) {
    return (
      <div className="py-16 text-center max-w-md mx-auto space-y-4">
        <h2 className="text-xl font-bold text-ink">{t('No recent order found', 'কোনো অর্ডার পাওয়া যায়নি')}</h2>
        <button
          onClick={() => setCurrentView('catalog')}
          className="px-6 py-2.5 rounded-xl bg-primary text-white text-xs font-bold"
        >
          {t('Browse Catalog', 'ক্যাটালগ দেখুন')}
        </button>
      </div>
    );
  }

  const order = lastConfirmedOrder;

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-16">
      {/* Success Banner */}
      <div className="text-center p-8 rounded-3xl bg-emerald-50 border border-emerald-200 shadow-card space-y-3">
        <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
          <CheckCircle2 className="w-10 h-10" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-emerald-950">
          {t('Order Placed Successfully!', 'আপনার অর্ডার নিশ্চিত করা হয়েছে!')}
        </h1>
        <p className="text-xs sm:text-sm text-emerald-800 max-w-md mx-auto">
          {t(
            'Thank you for shopping on NexHaat. We have sent an SMS confirmation to',
            'নেক্সহাটে কেনাকাটার জন্য ধন্যবাদ। নিশ্চিতকরণ বার্তা পাঠানো হয়েছে:'
          )}{' '}
          <strong>{order.customer_phone}</strong>
        </p>

        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-xl bg-white border border-emerald-200 text-xs font-mono font-bold text-emerald-900 mt-2">
          <span>{t('Order Number:', 'অর্ডার নম্বর:')}</span>
          <span className="text-primary">{order.order_number}</span>
        </div>
      </div>

      {/* Live Delivery Tracker Timeline */}
      <div className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-4">
        <h3 className="font-bold text-sm text-ink flex items-center gap-2">
          <Clock className="w-4 h-4 text-primary" />
          <span>{t('Live Order Progress', 'লাইভ অর্ডার অগ্রগতি')}</span>
        </h3>

        <div className="relative flex items-center justify-between pt-2">
          {/* Progress track line */}
          <div className="absolute left-6 right-6 top-6 h-1 bg-slate-100 -z-0">
            <div className="h-full bg-primary w-2/5 transition-all duration-700" />
          </div>

          {[
            { title: t('Placed', 'অর্ডার প্লেসড'), desc: t('Received', 'গৃহীত'), active: true, done: true },
            { title: t('Confirmed', 'নিশ্চিত'), desc: t('Accepted', 'গৃহীত'), active: true, done: true },
            { title: t('Packaging', 'প্যাকেজিং'), desc: t('At Store', 'দোকানে'), active: true, done: false },
            { title: t('Out with Rider', 'রাইডারের কাছে'), desc: t('In Transit', 'চলমান'), active: false, done: false },
            { title: t('Delivered', 'পৌঁছেছে'), desc: t('Completed', 'সম্পন্ন'), active: false, done: false },
          ].map((step, idx) => (
            <div key={idx} className="relative z-10 flex flex-col items-center text-center">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs shadow-sm transition-all ${
                  step.done
                    ? 'bg-primary text-white ring-4 ring-primary-light'
                    : step.active
                    ? 'bg-amber-500 text-white ring-4 ring-amber-100 animate-pulse'
                    : 'bg-white border-2 border-slate-200 text-slate-400'
                }`}
              >
                {idx + 1}
              </div>
              <span className="text-xs font-bold text-ink mt-2">{step.title}</span>
              <span className="text-[10px] text-muted">{step.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Order Details Breakdown */}
      <div className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <h3 className="font-bold text-sm text-ink">{t('Items Ordered', 'অর্ডারের পণ্যসমূহ')}</h3>
            <p className="text-xs text-muted">{order.items.length} {t('distinct listings', 'টি পণ্য')}</p>
          </div>
          <button
            onClick={() => setShowInvoiceModal(true)}
            className="px-3.5 py-1.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>{t('View Tax Invoice', 'ইনভয়েস দেখুন')}</span>
          </button>
        </div>

        <div className="divide-y divide-slate-100">
          {order.items.map((item, i) => (
            <div key={i} className="py-3 flex items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-3">
                <img
                  src={item.image}
                  alt={item.product_name}
                  className="w-12 h-12 rounded-xl object-cover bg-slate-50 shrink-0"
                />
                <div>
                  <h4 className="font-bold text-ink">{item.product_name}</h4>
                  <p className="text-[11px] text-muted">
                    {item.seller_name} • {item.quantity} × {formatPrice(item.unit_price)}
                    {item.variant_name && ` (${item.variant_name})`}
                  </p>
                </div>
              </div>
              <span className="font-bold text-ink">{formatPrice(item.total_price)}</span>
            </div>
          ))}
        </div>

        {/* Financial calculation */}
        <div className="pt-4 border-t border-slate-100 space-y-1.5 text-xs text-slate-600">
          <div className="flex justify-between">
            <span>{t('Subtotal', 'সাবটোটাল')}</span>
            <span className="font-semibold text-ink">{formatPrice(order.subtotal)}</span>
          </div>
          {order.discount_amount > 0 && (
            <div className="flex justify-between text-emerald-600">
              <span>{t('Discount', 'ছাড়')} {order.promo_code && `(${order.promo_code})`}</span>
              <span className="font-semibold">-{formatPrice(order.discount_amount)}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span>{t('Delivery Charge', 'ডেলিভারি চার্জ')}</span>
            <span className="font-semibold text-ink">
              {order.delivery_fee === 0 ? t('FREE', 'ফ্রি') : formatPrice(order.delivery_fee)}
            </span>
          </div>
          <div className="flex justify-between text-base font-black text-ink pt-2 border-t border-slate-200">
            <span>{t('Total Paid / Due', 'সর্বমোট মূল্য')}</span>
            <span className="text-primary">{formatPrice(order.total_amount)}</span>
          </div>
          <div className="flex justify-between text-xs pt-1">
            <span>{t('Payment Method', 'পেমেন্ট মাধ্যম')}</span>
            <span className="font-bold uppercase text-slate-800">{order.payment_method} ({order.payment_status})</span>
          </div>
        </div>

        {/* Delivery Address Details */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 text-xs space-y-1.5">
          <div className="flex items-center gap-1.5 font-bold text-ink">
            <MapPin className="w-4 h-4 text-primary" />
            <span>{t('Shipping Address', 'ডেলিভারি ঠিকানা')}</span>
          </div>
          <p className="text-slate-600">
            {order.customer_name} • {order.customer_phone}
          </p>
          <p className="text-slate-600">
            {order.delivery_address.street}, {order.delivery_address.thana}, {order.delivery_address.district}, {order.delivery_address.division}
          </p>
          {order.delivery_address.notes && (
            <p className="text-slate-500 italic mt-1">
              "{order.delivery_address.notes}"
            </p>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={() => setCurrentView('my-orders')}
          className="neu-button flex-1 py-3.5 px-6 rounded-2xl bg-primary text-white font-bold text-sm shadow-md hover:bg-primary-hover flex items-center justify-center gap-2"
        >
          <span>{t('Track in My Orders', 'আমার অর্ডারে ট্র্যাক করুন')}</span>
          <ArrowRight className="w-4 h-4" />
        </button>

        <button
          onClick={() => setCurrentView('catalog')}
          className="py-3.5 px-6 rounded-2xl bg-white border border-border text-ink font-bold text-sm hover:bg-slate-50"
        >
          {t('Continue Shopping', 'আরও কেনাকাটা করুন')}
        </button>
      </div>

      {/* Printable Invoice Modal */}
      {showInvoiceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-2xl overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between border-b pb-4">
              <div className="flex items-center gap-2">
                <img src="/logo.svg" alt="NexHaat" className="w-8 h-8" />
                <span className="font-black text-xl text-ink">NexHaat Invoice</span>
              </div>
              <button
                onClick={() => setShowInvoiceModal(false)}
                className="text-xs font-bold px-3 py-1 bg-slate-100 rounded-lg hover:bg-slate-200"
              >
                Close
              </button>
            </div>

            <div className="text-xs space-y-1">
              <p><strong>Invoice No:</strong> INV-{order.order_number}</p>
              <p><strong>Date:</strong> {new Date(order.created_at).toLocaleDateString()}</p>
              <p><strong>Customer:</strong> {order.customer_name} ({order.customer_phone})</p>
              <p><strong>Address:</strong> {order.delivery_address.street}, {order.delivery_address.district}</p>
            </div>

            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="border-b bg-slate-50 text-slate-600">
                  <th className="text-left py-2 px-1">Item</th>
                  <th className="text-center py-2 px-1">Qty</th>
                  <th className="text-right py-2 px-1">Price</th>
                  <th className="text-right py-2 px-1">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {order.items.map((it, idx) => (
                  <tr key={idx}>
                    <td className="py-2 px-1">{it.product_name}</td>
                    <td className="py-2 px-1 text-center">{it.quantity}</td>
                    <td className="py-2 px-1 text-right">{formatPrice(it.unit_price)}</td>
                    <td className="py-2 px-1 text-right font-bold">{formatPrice(it.total_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="text-xs text-right space-y-1 pt-2 border-t">
              <p>Subtotal: <strong>{formatPrice(order.subtotal)}</strong></p>
              {order.discount_amount > 0 && <p className="text-emerald-600">Discount: -{formatPrice(order.discount_amount)}</p>}
              <p>Delivery: <strong>{order.delivery_fee === 0 ? 'FREE' : formatPrice(order.delivery_fee)}</strong></p>
              <p className="text-sm font-black pt-1 border-t">Total: <strong className="text-primary">{formatPrice(order.total_amount)}</strong></p>
            </div>

            <div className="text-center pt-2">
              <button
                onClick={() => window.print()}
                className="px-5 py-2 rounded-xl bg-slate-900 text-white font-bold text-xs"
              >
                Print Receipt
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
