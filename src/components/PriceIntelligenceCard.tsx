import React, { useState } from 'react';
import { Product } from '../types';
import { useApp } from '../context/AppContext';
import { PriceAlertModal } from './PriceAlertModal';
import { 
  calculatePriceIntelligence, 
  getSimilarProductComparisons, 
  ProductPriceIntelligence, 
  SimilarProductComparison 
} from '../lib/priceIntelligence';
import { 
  TrendingDown, TrendingUp, AlertCircle, CheckCircle2, 
  Layers, ArrowRight, ShoppingCart, Bell, BellRing, 
  ChevronRight, Sparkles, Scale, Info, Star 
} from 'lucide-react';

import { PriceTrendChart } from './PriceTrendChart';

interface PriceIntelligenceCardProps {
  product: Product;
}

export const PriceIntelligenceCard: React.FC<PriceIntelligenceCardProps> = ({ product }) => {
  const { 
    products, 
    formatPrice, 
    addToCart, 
    navigateToProduct, 
    getPriceAlert,
    showToast, 
    t, 
    language 
  } = useApp();

  const [activeView, setActiveView] = useState<'history' | 'similar'>('history');
  const [showAlertModal, setShowAlertModal] = useState(false);

  const existingAlert = getPriceAlert(product.id);
  const isAlertActive = existingAlert && existingAlert.is_active;

  const intel: ProductPriceIntelligence = calculatePriceIntelligence(product);
  const similarItems: SimilarProductComparison[] = getSimilarProductComparisons(product, products, 3);


  return (
    <div className="surface rounded-3xl p-5 sm:p-6 border border-border shadow-xs space-y-6">
      {/* Header and View Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-xl bg-blue-100 dark:bg-blue-900/50 text-primary">
              <Scale className="w-4 h-4" />
            </span>
            <h3 className="text-base sm:text-lg font-bold text-ink">
              {t('Smart Price Intelligence & Buying Guide', 'মূল্য পর্যবেক্ষণ ও তুলনামূলক পর্যালোচনা')}
            </h3>
          </div>
          <p className="text-xs text-muted mt-0.5">
            {t(
              'Real-time marketplace price tracking, 30-day historical fluctuations, and catalog comparisons.',
              'মার্কেটপ্লেস প্রাইস ট্র্যাকিং, ৩০ দিনের ঐতিহাসিক তারতম্য ও বিকল্প পণ্যের তুলনা।'
            )}
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center bg-slate-100 dark:bg-slate-800 rounded-xl p-1 text-xs font-semibold self-start sm:self-auto">
          <button
            type="button"
            onClick={() => setActiveView('history')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeView === 'history'
                ? 'bg-white dark:bg-slate-700 text-primary shadow-xs font-bold'
                : 'text-slate-600 dark:text-slate-300 hover:text-ink'
            }`}
          >
            <TrendingDown className="w-3.5 h-3.5" />
            <span>{t('30-Day Price Trend', '৩০ দিনের মূল্যচিত্র')}</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveView('similar')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeView === 'similar'
                ? 'bg-white dark:bg-slate-700 text-primary shadow-xs font-bold'
                : 'text-slate-600 dark:text-slate-300 hover:text-ink'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{t(`Compare Similar Items (${similarItems.length})`, `বিকল্প পণ্যের তুলনা (${similarItems.length})`)}</span>
          </button>
        </div>
      </div>

      {/* VIEW 1: Recharts Historical Price Trend & Intelligence */}
      {activeView === 'history' && (
        <div className="animate-fade-in">
          <PriceTrendChart product={product} />
        </div>
      )}

      {/* VIEW 2: Compare Against Similar Items in Catalog */}
      {activeView === 'similar' && (
        <div className="space-y-4 animate-fade-in">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted">
              {t(
                'Comparing this item with popular alternatives in the catalog to help you choose the best value.',
                'সেরা পণ্যটি বেছে নিতে একই ক্যাটাগরির বিকল্প পণ্যের তুলনামূলক তালিকা।'
              )}
            </span>
            <span className="text-xs font-bold text-primary">
              {similarItems.length + 1} {t('Items Compared', 'পণ্য তুলনা')}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {/* 1. CURRENT PRODUCT CARD */}
            <div className="p-4 rounded-2xl border-2 border-primary bg-primary/5 space-y-3 relative flex flex-col justify-between">
              <div className="absolute -top-3 left-4 px-2.5 py-0.5 rounded-full bg-primary text-white text-[10px] font-extrabold uppercase tracking-wider">
                {t('Current Item', 'বর্তমান পণ্য')}
              </div>

              <div className="space-y-2 mt-1">
                <div className="aspect-4/3 w-full rounded-xl overflow-hidden bg-white border border-slate-200">
                  <img
                    src={product.image}
                    alt={product.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <h4 className="text-xs font-bold text-ink line-clamp-2">
                  {language === 'bn' && product.name_bn ? product.name_bn : product.name}
                </h4>
                <div className="flex items-center gap-1.5 text-xs text-amber-500 font-bold">
                  <Star className="w-3.5 h-3.5 fill-current" />
                  <span>{product.rating}</span>
                  <span className="text-slate-400 font-normal">({product.review_count} reviews)</span>
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-primary/20">
                <div className="flex items-baseline justify-between">
                  <span className="text-base font-black text-primary">
                    {formatPrice(intel.currentPrice)}
                  </span>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">
                    Baseline
                  </span>
                </div>
                <div className="text-[11px] text-slate-600 space-y-1">
                  <p><strong>Merchant:</strong> {product.seller_name}</p>
                  <p><strong>Unit:</strong> {language === 'bn' ? product.unit_bn : product.unit}</p>
                </div>
                <div className="pt-2">
                  <span className="w-full inline-block py-2 rounded-xl bg-primary/20 text-primary text-center text-xs font-bold">
                    ✓ {t('Currently Viewing', 'বর্তমানে দেখছেন')}
                  </span>
                </div>
              </div>
            </div>

            {/* 2. SIMILAR ALTERNATIVE ITEMS */}
            {similarItems.map(({ product: alt, currentPrice: altPrice, priceDifference, valueBadge, valueBadgeBn }) => {
              const isCheaper = priceDifference < 0;

              return (
                <div
                  key={alt.id}
                  className="p-4 rounded-2xl border border-border bg-surface-raised space-y-3 flex flex-col justify-between hover:border-slate-300 transition-all"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        valueBadge === 'Best Value' || valueBadge === 'Budget Pick'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {language === 'bn' ? valueBadgeBn : valueBadge}
                      </span>
                      <span className={`text-[11px] font-extrabold ${isCheaper ? 'text-emerald-600' : 'text-slate-600'}`}>
                        {isCheaper
                          ? `-${formatPrice(Math.abs(priceDifference))} cheaper`
                          : `+${formatPrice(priceDifference)}`}
                      </span>
                    </div>

                    <div className="aspect-4/3 w-full rounded-xl overflow-hidden bg-white border border-slate-200">
                      <img
                        src={alt.image}
                        alt={alt.name}
                        className="w-full h-full object-cover"
                      />
                    </div>

                    <h4
                      onClick={() => navigateToProduct(alt.slug)}
                      className="text-xs font-bold text-ink hover:text-primary cursor-pointer line-clamp-2 transition-colors"
                    >
                      {language === 'bn' && alt.name_bn ? alt.name_bn : alt.name}
                    </h4>

                    <div className="flex items-center gap-1.5 text-xs text-amber-500 font-bold">
                      <Star className="w-3.5 h-3.5 fill-current" />
                      <span>{alt.rating}</span>
                      <span className="text-slate-400 font-normal">({alt.review_count} reviews)</span>
                    </div>
                  </div>

                  <div className="space-y-2 pt-2 border-t border-border">
                    <div className="flex items-baseline justify-between">
                      <span className="text-base font-black text-ink">
                        {formatPrice(altPrice)}
                      </span>
                      {alt.discount_price && (
                        <span className="text-xs text-slate-400 line-through">
                          {formatPrice(alt.price)}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-600 space-y-1">
                      <p><strong>Merchant:</strong> {alt.seller_name}</p>
                      <p><strong>Unit:</strong> {language === 'bn' ? alt.unit_bn : alt.unit}</p>
                    </div>

                    <div className="pt-2 flex gap-2">
                      <button
                        type="button"
                        onClick={() => navigateToProduct(alt.slug)}
                        className="flex-1 py-1.5 px-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold text-center transition-colors"
                      >
                        {t('View Details', 'বিস্তারিত')}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          addToCart(alt, alt.variants?.[0], 1);
                          showToast(t(`Added ${alt.name} to cart!`, `${alt.name} কার্টে যোগ হয়েছে!`), 'success');
                        }}
                        className="p-2 rounded-xl bg-primary hover:bg-primary-hover text-white transition-colors"
                        title="Add this item to cart"
                      >
                        <ShoppingCart className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Target Price Drop Modal */}
      <PriceAlertModal
        product={product}
        isOpen={showAlertModal}
        onClose={() => setShowAlertModal(false)}
      />
    </div>
  );
};
