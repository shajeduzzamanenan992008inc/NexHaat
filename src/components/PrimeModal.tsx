import React from 'react';
import { useApp } from '../context/AppContext';
import { 
  Sparkles, X, Truck, DollarSign, Clock, ShieldCheck, ArrowRight
} from 'lucide-react';

export const PrimeModal: React.FC = () => {
  const { 
    isPrimeModalOpen, 
    setIsPrimeModalOpen, 
    isPrimeMember, 
    togglePrimeMembership, 
    t 
  } = useApp();

  if (!isPrimeModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 space-y-6 shadow-2xl relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-amber-400/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={() => setIsPrimeModalOpen(false)}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-ink hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white font-black text-xs shadow-xs">
            <Sparkles className="w-3.5 h-3.5" />
            <span>NEXHAAT MEMBERSHIP PREVIEW</span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black text-ink">
            {t('Preview the membership badge', 'মেম্বারশিপ ব্যাজ প্রিভিউ করুন')}
          </h2>

          <p className="text-xs sm:text-sm text-muted max-w-md mx-auto">
            {t(
              'This control only changes a preview badge on this device. Membership billing, delivery benefits, cashback, and account permissions are not connected.',
              'এই নিয়ন্ত্রণ শুধু এই ডিভাইসে প্রিভিউ ব্যাজ বদলায়। মেম্বারশিপ বিলিং, ডেলিভারি সুবিধা, ক্যাশব্যাক বা অ্যাকাউন্টের অনুমতি এর সঙ্গে যুক্ত নয়।'
            )}
          </p>
        </div>

        {/* Current preview capability status */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-amber-900">
              <Truck className="w-4 h-4 text-accent" />
              <span>{t('Delivery benefits', 'ডেলিভারি সুবিধা')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('Not connected to delivery or checkout.', 'ডেলিভারি বা চেকআউটের সঙ্গে যুক্ত নয়।')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-emerald-900">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              <span>{t('Cashback', 'ক্যাশব্যাক')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('No wallet credit is issued by this preview.', 'এই প্রিভিউতে ওয়ালেটে অর্থ যোগ হয় না।')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-blue-900">
              <Clock className="w-4 h-4 text-primary" />
              <span>{t('Deal access', 'অফারে প্রবেশ')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('No early-access rules are configured.', 'আগাম প্রবেশের নিয়ম যুক্ত নেই।')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-purple-50/70 border border-purple-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-purple-900">
              <ShieldCheck className="w-4 h-4 text-purple-600" />
              <span>{t('Priority support', 'অগ্রাধিকার সহায়তা')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('No priority support channel is configured.', 'অগ্রাধিকার সহায়তার চ্যানেল যুক্ত নেই।')}
            </p>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-surface-raised px-4 py-3 text-xs leading-relaxed text-muted" role="note">
          {t('No payment is collected and no marketplace benefit changes when you use this preview.', 'এই প্রিভিউ ব্যবহার করলে পেমেন্ট নেওয়া হয় না বা মার্কেটপ্লেসের কোনো সুবিধা বদলায় না।')}
        </div>

        {/* CTA Button */}
        <div className="pt-2">
          <button
            type="button"
            onClick={togglePrimeMembership}
            className={`neu-button w-full py-4 rounded-2xl font-black text-sm shadow-md flex items-center justify-center gap-2 ${
              isPrimeMember
                ? 'bg-rose-50 text-danger border border-rose-200 hover:bg-rose-100'
                : 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-900 hover:opacity-95'
            }`}
          >
            {isPrimeMember ? (
                <span>{t('Clear preview badge', 'প্রিভিউ ব্যাজ সরান')}</span>
            ) : (
              <>
                <span>{t('Enable preview badge', 'প্রিভিউ ব্যাজ চালু করুন')}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
