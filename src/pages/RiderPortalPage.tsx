import React from 'react';
import { useApp } from '../context/AppContext';
import { 
  Truck, CheckCircle2, Phone, MapPin, Navigation, 
  DollarSign, Package, AlertCircle, Clock 
} from 'lucide-react';

export const RiderPortalPage: React.FC = () => {
  const { orders, updateOrderStatus, formatPrice, t, currentUser } = useApp();

  const activeDeliveries = orders.filter(o => ['processing', 'shipped'].includes(o.status));
  const completedDeliveries = orders.filter(o => o.status === 'delivered');
  const totalCashCollected = completedDeliveries
    .filter(o => o.payment_method === 'cod')
    .reduce((sum, o) => sum + o.total_amount, 0);

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="p-6 sm:p-8 rounded-3xl bg-emerald-950 text-white shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-bold text-xs mb-2">
            <Truck className="w-4 h-4" />
            <span>{t('NEXHAAT EXPRESS RIDER HUB', 'নেক্সহাট এক্সপ্রেস রাইডার হাব')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white">
            {currentUser.name || 'Kamal Hossain'}
          </h1>
          <p className="text-xs sm:text-sm text-emerald-200 mt-1">
            Mirpur Hub 10, Dhaka • Rider ID: NH-RDR-4402 • Status: Active on Duty
          </p>
        </div>

        <div className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-white/10 backdrop-blur-md text-emerald-300 text-xs font-bold self-start sm:self-auto">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
          <span>GPS Live Tracking Online</span>
        </div>
      </div>

      {/* Rider Performance Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t('Pending Deliveries', 'চলমান ডেলিভারি')}</span>
            <Clock className="w-4 h-4 text-primary" />
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">{activeDeliveries.length}</p>
          <span className="text-[11px] text-primary font-semibold mt-1 block">Assigned in your zone</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t('Completed Drops', 'সম্পন্ন ডেলিভারি')}</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">{completedDeliveries.length}</p>
          <span className="text-[11px] text-emerald-600 font-semibold mt-1 block">100% on-time rating</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t('COD Cash Collected', 'সংগৃহীত ক্যাশ')}</span>
            <DollarSign className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">{formatPrice(totalCashCollected)}</p>
          <span className="text-[11px] text-muted mt-1 block">Ready for settlement</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t("Rider Today's Earnings", 'আজকের মোট আয়')}</span>
            <span className="text-emerald-600 font-bold">BDT</span>
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">৳ 1,450.00</p>
          <span className="text-[11px] text-emerald-600 font-semibold mt-1 block">৳70/drop + bonus</span>
        </div>
      </div>

      {/* Active Deliveries Queue */}
      <div className="space-y-4">
        <h3 className="font-bold text-base text-ink flex items-center gap-2">
          <Package className="w-5 h-5 text-primary" />
          <span>{t('Active Assigned Deliveries', 'নির্ধারিত ডেলিভারি তালিকা')} ({activeDeliveries.length})</span>
        </h3>

        {activeDeliveries.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-3xl border border-border shadow-card text-muted text-xs">
            {t('No pending deliveries assigned at the moment. Stand by for new orders.', 'বর্তমানে কোনো সক্রিয় ডেলিভারি নেই।')}
          </div>
        ) : (
          activeDeliveries.map(ord => (
            <div
              key={ord.id}
              className="p-5 sm:p-6 rounded-3xl bg-white border border-border shadow-card space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm text-ink">{ord.order_number}</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                      ord.status === 'shipped' ? 'bg-blue-100 text-blue-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {ord.status === 'shipped' ? 'Out for Delivery' : 'Awaiting Store Handover'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Order Total: <strong className="text-ink">{formatPrice(ord.total_amount)}</strong> ({ord.payment_method.toUpperCase()})
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <a
                    href={`tel:${ord.customer_phone}`}
                    className="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-ink text-xs font-bold flex items-center gap-1.5 transition-colors"
                  >
                    <Phone className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{ord.customer_phone}</span>
                  </a>
                </div>
              </div>

              {/* Delivery Destination */}
              <div className="flex items-start gap-3 p-3.5 rounded-2xl bg-slate-50 border border-slate-100 text-xs">
                <MapPin className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                <div>
                  <strong className="text-ink">{ord.customer_name}</strong>
                  <p className="text-slate-600">
                    {ord.delivery_address.street}, {ord.delivery_address.thana}, {ord.delivery_address.district}
                  </p>
                  {ord.delivery_address.notes && (
                    <p className="text-slate-500 italic mt-0.5">
                      Note: "{ord.delivery_address.notes}"
                    </p>
                  )}
                </div>
              </div>

              {/* Action Buttons for Rider */}
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <div className="text-xs text-slate-500">
                  {ord.payment_method === 'cod' ? (
                    <span className="text-amber-700 font-bold bg-amber-50 px-2 py-1 rounded-md border border-amber-200">
                      Collect Cash: {formatPrice(ord.total_amount)}
                    </span>
                  ) : (
                    <span className="text-emerald-700 font-bold bg-emerald-50 px-2 py-1 rounded-md border border-emerald-200">
                      Prepaid via {ord.payment_method.toUpperCase()}
                    </span>
                  )}
                </div>

                <div className="flex gap-2">
                  {ord.status === 'processing' && (
                    <button
                      onClick={() => updateOrderStatus(ord.order_number, 'shipped', { name: currentUser.name, phone: currentUser.phone })}
                      className="px-4 py-2.5 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-sm"
                    >
                      {t('Confirm Pickup & Go', 'পণ্য গ্রহণ করলাম')}
                    </button>
                  )}

                  {ord.status === 'shipped' && (
                    <button
                      onClick={() => updateOrderStatus(ord.order_number, 'delivered')}
                      className="px-4 py-2.5 rounded-xl bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 shadow-sm flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>{t('Mark Delivered & Settle', 'ডেলিভারি সম্পন্ন')}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
