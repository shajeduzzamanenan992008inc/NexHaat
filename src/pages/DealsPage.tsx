import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import { INITIAL_PROMOTIONS } from '../data/mockData';
import { Tag, Sparkles, Clock, Copy, Check, Percent } from 'lucide-react';

export const DealsPage: React.FC = () => {
  const { products, applyCoupon, activeCoupon, t, formatPrice } = useApp();
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  // Countdown timer
  const [timeLeft, setTimeLeft] = useState({ hours: 14, minutes: 35, seconds: 40 });

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev.seconds > 0) return { ...prev, seconds: prev.seconds - 1 };
        if (prev.minutes > 0) return { ...prev, minutes: 59, seconds: 59 };
        if (prev.hours > 0) return { ...prev, hours: prev.hours - 1, minutes: 59, seconds: 59 };
        return { hours: 24, minutes: 0, seconds: 0 };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const dealProducts = products.filter(p => p.discount_price && p.is_available);

  const handleCopy = (code: string) => {
    navigator.clipboard?.writeText(code);
    applyCoupon(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2500);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-amber-600 via-orange-600 to-rose-600 text-white p-6 sm:p-10 shadow-elevated">
        <div className="relative z-10 max-w-xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 backdrop-blur-md text-xs font-bold mb-3">
            <Percent className="w-4 h-4" />
            <span>{t('NEXHAAT MEGA HAAT DISCOUNTS', 'নেক্সহাট মেগা হাট বিশেষ ছাড়')}</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-black mb-3">
            {t('Daily Flash Deals & Exclusive Vouchers', 'দৈনিক ফ্ল্যাশ ডিল ও ডিসকাউন্ট ভাউচার')}
          </h1>

          <p className="text-sm text-amber-100 leading-relaxed mb-6">
            {t(
              'Save big on freshly harvested fruits, wild river fish, pure kitchen spices, and electronics. Exclusive coupons apply directly at checkout.',
              'তাজা মৌসুমি ফল, পদ্মার ইলিশ, মশলা ও গ্যাজেটে পান দারুণ মূল্যছাড়। কুপন কোড ব্যবহার করে নিন অতিরিক্ত ক্যাশব্যাক।'
            )}
          </p>

          <div className="flex items-center gap-2 bg-black/30 backdrop-blur-md px-4 py-2 rounded-2xl w-fit">
            <Clock className="w-4 h-4 text-amber-300" />
            <span className="text-xs font-semibold text-slate-200">{t('Offer expires in:', 'অফারের সময় বাকি:')}</span>
            <span className="font-mono text-sm font-extrabold text-amber-300">
              {String(timeLeft.hours).padStart(2, '0')}h : {String(timeLeft.minutes).padStart(2, '0')}m : {String(timeLeft.seconds).padStart(2, '0')}s
            </span>
          </div>
        </div>
      </div>

      {/* Available Coupon Codes */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-ink flex items-center gap-2">
          <Tag className="w-5 h-5 text-accent" />
          <span>{t('Active Marketplace Coupons', 'সক্রিয় ডিসকাউন্ট কুপনসমূহ')}</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {INITIAL_PROMOTIONS.map((promo) => {
            const isApplied = activeCoupon?.code === promo.code;
            return (
              <div
                key={promo.id}
                className="p-4 rounded-2xl bg-white border border-border shadow-card hover:shadow-elevated transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-3 py-1 rounded-lg bg-primary-light text-primary font-mono font-extrabold text-sm tracking-wide">
                      {promo.code}
                    </span>
                    <span className="text-[11px] font-semibold text-slate-400">
                      {t('Min spend:', 'নূন্যতম খরচ:')} {formatPrice(promo.min_spend)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 font-medium mb-4">
                    {promo.description}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => handleCopy(promo.code)}
                  className={`w-full py-2 px-3 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-colors ${
                    isApplied
                      ? 'bg-emerald-100 text-emerald-800'
                      : copiedCode === promo.code
                      ? 'bg-emerald-600 text-white'
                      : 'bg-slate-900 text-white hover:bg-primary'
                  }`}
                >
                  {isApplied ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>{t('Applied to Cart', 'কার্টে সক্রিয় রয়েছে')}</span>
                    </>
                  ) : copiedCode === promo.code ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>{t('Applied & Copied!', 'কুপন প্রয়োগ হয়েছে!')}</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>{t('Apply Coupon', 'কুপন প্রয়োগ করুন')}</span>
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Discounted Product Grid */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-ink">
            {t('All Discounted Listings', 'সকল ছাড়যুক্ত পণ্য')} ({dealProducts.length})
          </h3>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          {dealProducts.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>
    </div>
  );
};
