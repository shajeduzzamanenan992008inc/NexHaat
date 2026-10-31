import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Bell, CheckCheck, Package, Tag, Truck, Info, ArrowRight } from 'lucide-react';

export const NotificationsPage: React.FC = () => {
  const { 
    notifications, 
    markNotificationAsRead, 
    markAllNotificationsAsRead, 
    setCurrentView, 
    t, 
    language 
  } = useApp();

  const [filterType, setFilterType] = useState<'all' | 'order' | 'promotion' | 'delivery'>('all');

  const filtered = notifications.filter(n => filterType === 'all' || n.type === filterType);

  const getIcon = (type: string) => {
    switch (type) {
      case 'order':
        return <Package className="w-4 h-4 text-primary" />;
      case 'promotion':
        return <Tag className="w-4 h-4 text-accent" />;
      case 'delivery':
        return <Truck className="w-4 h-4 text-emerald-600" />;
      default:
        return <Info className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-16">
      {/* Header */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-border shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-primary font-bold text-xs mb-1.5">
            <Bell className="w-3.5 h-3.5" />
            <span>{t('NexHaat Updates', 'নেক্সহাট নোটিফিকেশন')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-ink">
            {t('Notifications & Alerts', 'বিজ্ঞপ্তি ও আপডেট')}
          </h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            {t('Real-time order statuses, exclusive flash vouchers, and delivery updates', 'অর্ডারের অবস্থা এবং বিশেষ ছাড়ের তথ্য')}
          </p>
        </div>

        <button
          onClick={markAllNotificationsAsRead}
          className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-bold text-slate-700 flex items-center gap-1.5 transition-colors self-start sm:self-auto"
        >
          <CheckCheck className="w-4 h-4" />
          <span>{t('Mark All Read', 'সব পঠিত হিসেবে চিহ্নিত করুন')}</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-border pb-2 overflow-x-auto">
        {[
          { id: 'all', label: t('All Notifications', 'সব বিজ্ঞপ্তি') },
          { id: 'order', label: t('Orders', 'অর্ডারসমূহ') },
          { id: 'promotion', label: t('Deals & Offers', 'অফার ও ছাড়') },
          { id: 'delivery', label: t('Delivery', 'ডেলিভারি') },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setFilterType(tab.id as any)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
              filterType === tab.id
                ? 'bg-primary text-white shadow-xs'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Notifications List */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-3xl border border-border shadow-card text-muted text-xs">
            {t('No notifications found.', 'কোনো বিজ্ঞপ্তি পাওয়া যায়নি।')}
          </div>
        ) : (
          filtered.map(item => (
            <div
              key={item.id}
              onClick={() => {
                if (!item.is_read) markNotificationAsRead(item.id);
                if (item.link) setCurrentView(item.link as any);
              }}
              className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-start justify-between gap-3 ${
                item.is_read
                  ? 'bg-white border-slate-200/80 hover:border-slate-300'
                  : 'bg-blue-50/50 border-primary/30 shadow-xs'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-white border border-slate-200 shadow-xs mt-0.5 shrink-0">
                  {getIcon(item.type)}
                </div>
                <div>
                  <h4 className="font-bold text-xs sm:text-sm text-ink">
                    {language === 'bn' ? item.title_bn : item.title}
                  </h4>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    {language === 'bn' ? item.message_bn : item.message}
                  </p>
                  <span className="text-[10px] text-slate-400 mt-2 block">
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
              </div>

              {!item.is_read && (
                <span className="w-2.5 h-2.5 rounded-full bg-primary shrink-0 mt-1" />
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
