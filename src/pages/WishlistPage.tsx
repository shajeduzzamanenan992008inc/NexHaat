import React from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import { Heart, ShoppingBag, ArrowRight } from 'lucide-react';

export const WishlistPage: React.FC = () => {
  const { wishlist, products, addToCart, setCurrentView, setIsCartDrawerOpen, t } = useApp();

  const savedProducts = products.filter(p => wishlist.includes(p.id));

  const handleMoveAllToCart = () => {
    savedProducts.forEach(prod => {
      if (prod.is_available) {
        addToCart(prod, undefined, 1);
      }
    });
    setIsCartDrawerOpen(true);
  };

  return (
    <div className="space-y-6 pb-16">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl bg-white border border-border shadow-card">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-50 text-rose-600 font-bold text-xs mb-1.5">
            <Heart className="w-3.5 h-3.5 fill-current" />
            <span>{t('Saved for Later', 'সংরক্ষিত পণ্যসমূহ')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-ink">
            {t('Your Wishlist', 'আমার উইশলিস্ট')}
          </h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            {t('Keep track of seasonal delicacies and move them to cart anytime', 'পছন্দের পণ্যগুলো জমিয়ে রাখুন এবং যেকোনো সময় অর্ডার করুন')}
          </p>
        </div>

        {savedProducts.length > 0 && (
          <button
            onClick={handleMoveAllToCart}
            className="neu-button px-5 py-3 rounded-2xl bg-primary text-white text-xs font-bold hover:bg-primary-hover flex items-center gap-2 self-start sm:self-auto shadow-md"
          >
            <ShoppingBag className="w-4 h-4" />
            <span>{t('Move All to Cart', 'সবগুলো কার্টে যোগ করুন')}</span>
          </button>
        )}
      </div>

      {savedProducts.length === 0 ? (
        <div className="p-16 text-center bg-white rounded-3xl border border-border shadow-card space-y-4">
          <div className="w-16 h-16 rounded-full bg-rose-50 text-rose-400 flex items-center justify-center mx-auto">
            <Heart className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-ink">
            {t('Your wishlist is empty', 'আপনার উইশলিস্ট খালি')}
          </h2>
          <p className="text-xs text-muted max-w-sm mx-auto">
            {t(
              'Click the heart icon on any product to save it here for later purchase.',
              'যেকোনো পণ্যের হৃদপিণ্ড আইকনে ক্লিক করে সহজেই সংরক্ষণ করুন।'
            )}
          </p>
          <button
            onClick={() => setCurrentView('catalog')}
            className="px-6 py-2.5 rounded-xl bg-primary text-white font-bold text-xs"
          >
            {t('Explore Marketplace', 'মার্কেটপ্লেস দেখুন')}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          {savedProducts.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
};
