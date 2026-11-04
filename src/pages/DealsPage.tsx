import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import { INITIAL_PROMOTIONS } from '../data/mockData';
import { Tag, Sparkles, Copy, Check, Percent } from 'lucide-react';

export const DealsPage: React.FC = () => {
  const { products, applyCoupon, activeCoupon, t, formatPrice } = useApp();
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

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
            <span>{t('MARKETPLACE DEALS', 'মার্কেটপ্লেসের ছাড়')}</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-black mb-3">
            {t('Current product discounts', 'বর্তমান পণ্যের ছাড়')}
          </h1>

          <p className="text-sm text-amber-100 leading-relaxed mb-6">
            {t(
              'Browse listings currently marked with a discount. The marketplace checks promotion eligibility during checkout.',
              'যেসব পণ্যে ছাড় দেখানো আছে সেগুলো দেখুন। চেকআউটে মার্কেটপ্লেস কুপনের যোগ্যতা যাচাই করবে।'
            )}
          </p>
        </div>
      </div>

      {/* Available Coupon Codes */}
      <section className="space-y-3">
        <h3 className="text-lg font-bold text-ink flex items-center gap-2">
          <Tag className="w-5 h-5 text-accent" />
          <span>{t('Coupon examples', 'কুপনের উদাহরণ')}</span>
        </h3>
        <p className="text-xs text-muted">
          {t('These codes are local preview examples. Checkout validates any entered code against current marketplace promotions.', 'এগুলো স্থানীয় প্রিভিউ কুপন। চেকআউটে বর্তমান মার্কেটপ্লেস প্রচারের সঙ্গে কোড যাচাই হবে।')}
        </p>

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
                      <span>{t('Applied in preview', 'প্রিভিউতে প্রয়োগ হয়েছে')}</span>
                    </>
                  ) : copiedCode === promo.code ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>{t('Preview updated & copied', 'প্রিভিউ বদলেছে ও কপি হয়েছে')}</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>{t('Apply preview code', 'প্রিভিউ কোড প্রয়োগ করুন')}</span>
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
