import React from 'react';
import { Product } from '../types';
import { useApp } from '../context/AppContext';
import { Star, Heart, ShoppingBag, Layers, Check, Sparkles } from 'lucide-react';

interface ProductCardProps {
  product: Product;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const { 
    formatPrice, 
    addToCart, 
    toggleWishlist, 
    isInWishlist, 
    navigateToProduct, 
    toggleCompare, 
    comparedProductIds, 
    isPrimeMember, 
    t, 
    language 
  } = useApp();

  const isFavorited = isInWishlist(product.id);
  const isCompared = comparedProductIds.includes(product.id);

  const discountPercent = product.discount_price 
    ? Math.round(((product.price - product.discount_price) / product.price) * 100)
    : 0;

  const currentPrice = product.discount_price ?? product.price;

  return (
    <div 
      className="group relative flex flex-col rounded-2xl bg-white border border-border/70 p-3.5 shadow-card hover:shadow-elevated transition-all duration-300 hover:-translate-y-1.5 cursor-pointer overflow-hidden"
      onClick={() => navigateToProduct(product.slug)}
    >
      {/* Badges & Wishlist Header */}
      <div className="absolute top-5 left-5 right-5 z-10 flex items-start justify-between pointer-events-none">
        <div className="flex flex-col gap-1 items-start">
          {product.is_nexhaat_choice && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-black bg-slate-900 text-white shadow-xs pointer-events-auto">
              <span>NexHaat's</span>
              <span className="text-amber-400">Choice</span>
            </span>
          )}

          {product.is_best_seller && !product.is_nexhaat_choice && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-black bg-amber-500 text-slate-900 shadow-xs pointer-events-auto">
              #1 Best Seller
            </span>
          )}

          {product.is_sponsored && (
            <span className="inline-block text-[10px] font-semibold text-slate-400 bg-white/90 px-1.5 py-0.5 rounded backdrop-blur-xs pointer-events-auto">
              Sponsored
            </span>
          )}

          {discountPercent > 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-danger text-white shadow-sm pointer-events-auto">
              -{discountPercent}% {t('OFF', 'ছাড়')}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-1.5 items-end pointer-events-auto">
          <button
            type="button"
            aria-label={isFavorited ? 'Remove from wishlist' : 'Add to wishlist'}
            onClick={(e) => {
              e.stopPropagation();
              toggleWishlist(product.id);
            }}
            className={`p-2 rounded-full transition-all duration-200 ${
              isFavorited 
                ? 'bg-rose-50 text-rose-500 shadow-sm' 
                : 'bg-white/80 hover:bg-white text-muted hover:text-rose-500 shadow-sm backdrop-blur-sm'
            }`}
          >
            <Heart className={`w-4 h-4 ${isFavorited ? 'fill-current' : ''}`} />
          </button>

          {/* Quick Compare Toggle */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              toggleCompare(product.id);
            }}
            title={isCompared ? 'Remove from compare' : 'Compare product'}
            className={`p-1.5 rounded-full transition-all text-xs font-bold ${
              isCompared
                ? 'bg-primary text-white shadow-xs'
                : 'bg-white/80 text-slate-500 hover:text-primary shadow-xs backdrop-blur-sm'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Product Image */}
      <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-50 mb-3 flex items-center justify-center">
        <img
          src={product.image}
          alt={product.name}
          className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />
        {product.stock_quantity <= 0 && (
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center">
            <span className="px-3 py-1 bg-white/95 rounded-lg text-xs font-bold text-slate-800">
              {t('Out of Stock', 'মজুদ নেই')}
            </span>
          </div>
        )}
      </div>

      {/* Product Details */}
      <div className="flex flex-col flex-1">
        {/* Category & Seller */}
        <div className="flex items-center justify-between text-xs text-muted mb-1 gap-1">
          <span className="truncate max-w-[130px] font-medium text-slate-500">
            {product.brand_name || product.seller_name}
          </span>
          <div className="flex items-center gap-1 shrink-0 text-amber-500 font-semibold text-xs">
            <Star className="w-3.5 h-3.5 fill-current" />
            <span>{product.rating}</span>
            <span className="text-slate-400 font-normal">({product.review_count})</span>
          </div>
        </div>

        {/* Title */}
        <h3 className="font-semibold text-ink text-sm sm:text-base line-clamp-2 mb-1 group-hover:text-primary transition-colors">
          {language === 'bn' && product.name_bn ? product.name_bn : product.name}
        </h3>

        {/* Prime Delivery Tag */}
        <div className="flex items-center gap-2 mb-1">
          <span className="inline-flex items-center gap-1 text-[11px] font-black text-primary">
            <span className="italic">prime</span>
            <span className="font-medium text-slate-500 text-[10px]">FREE 3-hr delivery</span>
          </span>
        </div>

        {/* Bulk discount tag if applicable */}
        {product.bulk_discounts && product.bulk_discounts.length > 0 && (
          <p className="text-[11px] font-semibold text-emerald-600 mb-1">
            {t(`Bulk Save: Buy ${product.bulk_discounts[0].minQty}+ get ${product.bulk_discounts[0].discountPercent}% off`, `পাইকারি সাশ্রয়: ${product.bulk_discounts[0].minQty}+ কিনলে ${product.bulk_discounts[0].discountPercent}% ছাড়`)}
          </p>
        )}

        {/* Price & Action */}
        <div className="mt-auto pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="font-bold text-base text-ink sm:text-lg">
                {formatPrice(currentPrice)}
              </span>
              {product.discount_price && (
                <span className="text-xs text-slate-400 line-through">
                  {formatPrice(product.price)}
                </span>
              )}
            </div>
            <span className="text-[10px] text-slate-400 block -mt-0.5">
              {language === 'bn' && product.unit_bn ? product.unit_bn : product.unit}
            </span>
          </div>

          <button
            type="button"
            disabled={product.stock_quantity <= 0}
            onClick={(e) => {
              e.stopPropagation();
              addToCart(product);
            }}
            aria-label="Add to cart"
            className="neu-button p-2.5 rounded-xl bg-primary text-white hover:bg-primary-hover disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed shadow-sm flex items-center justify-center shrink-0"
          >
            <ShoppingBag className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
