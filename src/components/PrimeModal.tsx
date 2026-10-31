import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Sparkles, Check, X, Truck, DollarSign, 
  Clock, ShieldCheck, Heart, Award, ArrowRight 
} from 'lucide-react';

export const PrimeModal: React.FC = () => {
  const { 
    isPrimeModalOpen, 
    setIsPrimeModalOpen, 
    isPrimeMember, 
    togglePrimeMembership, 
    formatPrice, 
    t 
  } = useApp();

  const [plan, setPlan] = useState<'monthly' | 'yearly'>('yearly');

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
            <span>NEXHAAT PRIME</span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-black text-ink">
            {isPrimeMember ? t('Manage NexHaat Prime', 'নেক্সহাট প্রাইম মেম্বারশিপ') : t('Unlock Free Express Delivery & Cashback', 'আনলিমিটেড ফ্রি ডেলিভারি ও ক্যাশব্যাক')}
          </h2>

          <p className="text-xs sm:text-sm text-muted max-w-md mx-auto">
            {t(
              'Enjoy Bangladesh’s most rewarding shopping subscription with zero delivery fees and exclusive VIP discounts.',
              'বাংলাদেশের সেরা শপিং সাবস্ক্রিপশন: শূন্য ডেলিভারি ফি এবং বিশেষ ক্যাশব্যাক সুবিধা।'
            )}
          </p>
        </div>

        {/* Benefits Grid */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-amber-900">
              <Truck className="w-4 h-4 text-accent" />
              <span>{t('Free Express Delivery', 'ফ্রি ৩-ঘণ্টা এক্সপ্রেস')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('Unlimited free 3-hour doorstep delivery across Dhaka.', 'ঢাকায় আনলিমিটেড ফ্রি ডেলিভারি।')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-emerald-900">
              <DollarSign className="w-4 h-4 text-emerald-600" />
              <span>{t('5% Wallet Cashback', '৫% ওয়ালেট ক্যাশব্যাক')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('Earn 5% back on all purchases into your Haat balance.', 'প্রতি অর্ডারে ৫% ক্যাশব্যাক।')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-blue-900">
              <Clock className="w-4 h-4 text-primary" />
              <span>{t('Early Access to Deals', 'আগে ভাগে ফ্ল্যাশ ডিল')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('Shop mega Eid and festival discounts 2 hours early.', 'উৎসবের অফারগুলোতে প্রথম সুযোগ।')}
            </p>
          </div>

          <div className="p-3.5 rounded-2xl bg-purple-50/70 border border-purple-200/60 space-y-1">
            <div className="flex items-center gap-2 font-bold text-purple-900">
              <ShieldCheck className="w-4 h-4 text-purple-600" />
              <span>{t('VIP Priority Support', 'ভিআইপি অগ্রাধিকার')}</span>
            </div>
            <p className="text-[11px] text-slate-600">
              {t('Dedicated customer agent line with zero wait time.', 'সরাসরি ডেডিকেটেড এজেন্ট হটলাইন।')}
            </p>
          </div>
        </div>

        {/* Plan Selector */}
        <div className="grid grid-cols-2 gap-3 pt-2">
          <button
            type="button"
            onClick={() => setPlan('monthly')}
            className={`p-4 rounded-2xl border text-left transition-all relative ${
              plan === 'monthly'
                ? 'border-primary bg-primary-light/40 ring-2 ring-primary/20'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <span className="block text-xs font-bold text-slate-700">{t('Monthly Plan', 'মাসিক প্ল্যান')}</span>
            <span className="block text-lg font-black text-ink mt-0.5">৳199 / mo</span>
            <span className="block text-[10px] text-slate-500 mt-1">{t('Billed monthly, cancel anytime', 'যেকোনো সময় বাতিলযোগ্য')}</span>
          </button>

          <button
            type="button"
            onClick={() => setPlan('yearly')}
            className={`p-4 rounded-2xl border text-left transition-all relative ${
              plan === 'yearly'
                ? 'border-primary bg-primary-light/40 ring-2 ring-primary/20'
                : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <span className="absolute -top-2.5 right-3 px-2 py-0.5 rounded-full text-[10px] font-black bg-accent text-slate-900">
              {t('SAVE 16%', '১৬% ছাড়')}
            </span>
            <span className="block text-xs font-bold text-slate-700">{t('Yearly Plan', 'বার্ষিক প্ল্যান')}</span>
            <span className="block text-lg font-black text-ink mt-0.5">৳1,999 / yr</span>
            <span className="block text-[10px] text-emerald-600 font-semibold mt-1">{t('Only ৳166/month equivalent', 'মাসে মাত্র ৳১৬৬')}</span>
          </button>
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
              <span>{t('Cancel Prime Membership', 'প্রাইম মেম্বারশিপ বাতিল করুন')}</span>
            ) : (
              <>
                <span>{t('Join NexHaat Prime Now', 'এখনই প্রাইমে যোগ দিন')}</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
