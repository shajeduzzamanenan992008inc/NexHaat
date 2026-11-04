import React, { useState, useRef } from 'react';
import { Product } from '../types';
import { useApp } from '../context/AppContext';
import { Star, Heart, ShoppingBag, Layers, Check, Sparkles, ImageOff } from 'lucide-react';
import { calculateCardTilt } from '../lib/motionTokens';

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
    t, 
    language 
  } = useApp();

  const isFavorited = isInWishlist(product.id);
  const isCompared = comparedProductIds.includes(product.id);
  const [justFavorited, setJustFavorited] = useState(false);
  const [justAddedCart, setJustAddedCart] = useState(false);
  const [tiltStyle, setTiltStyle] = useState<React.CSSProperties>({});
  const cardRef = useRef<HTMLDivElement>(null);

  const discountPercent = product.discount_price 
    ? Math.round(((product.price - product.discount_price) / product.price) * 100)
    : 0;

  const currentPrice = product.discount_price ?? product.price;

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    cardRef.current.style.setProperty('--mouse-x', `${x}px`);
    cardRef.current.style.setProperty('--mouse-y', `${y}px`);

    const tilt = calculateCardTilt(e.clientX, e.clientY, rect, 5);
    setTiltStyle({ transform: tilt.transformStyle });
  };

  const handleMouseLeave = () => {
    setTiltStyle({ transform: 'perspective(1000px) rotateX(0deg) rotateY(0deg)' });
  };

  const handleWishlistClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setJustFavorited(true);
    toggleWishlist(product.id);
    setTimeout(() => setJustFavorited(false), 500);
  };

  const handleAddToCartClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (product.stock_quantity <= 0) return;
    setJustAddedCart(true);
    addToCart(product);
    setTimeout(() => setJustAddedCart(false), 650);
  };

  return (
    <div 
      ref={cardRef}
      style={tiltStyle}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className="marketplace-product-card group relative flex flex-col rounded-2xl bg-white border border-border/70 p-3.5 shadow-card hover:shadow-elevated transition-all duration-300 hover:-translate-y-1 overflow-hidden card-3d-tilt spotlight-card"
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

          {product.is_digital && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-600 text-white shadow-xs pointer-events-auto animate-pulse-soft">
              ⚡ {t('Digital listing', 'ডিজিটাল পণ্য', 'منتج رقمي', 'डिजिटल सूची')}
            </span>
          )}

          {product.international_shipping && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-700 text-white shadow-xs pointer-events-auto">
              🌍 {t('International shipping listed', 'আন্তর্জাতিক শিপিং উল্লেখ আছে', 'الشحن الدولي مدرج', 'अंतरराष्ट्रीय शिपिंग सूचीबद्ध')}
            </span>
          )}

          {discountPercent > 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-danger text-white shadow-sm pointer-events-auto">
              -{discountPercent}% {t('OFF', 'ছাড়', 'خصم', 'छूट')}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-1.5 items-end pointer-events-auto">
          <button
            type="button"
            aria-label={isFavorited ? 'Remove from wishlist' : 'Add to wishlist'}
            onClick={handleWishlistClick}
            className={`p-2 rounded-full transition-all duration-200 active:scale-75 ${
              isFavorited 
                ? 'bg-rose-50 text-rose-500 shadow-sm' 
                : 'bg-white/80 hover:bg-white text-muted hover:text-rose-500 shadow-sm backdrop-blur-sm'
            } ${justFavorited ? 'animate-heart-pop' : ''}`}
          >
            <Heart className={`w-4 h-4 ${isFavorited ? 'fill-current text-rose-500' : ''}`} />
          </button>

          {/* Quick Compare Toggle */}
          <button
            type="button"
            aria-label={isCompared ? 'Remove product from comparison' : 'Compare product'}
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
      <button
        type="button"
        onClick={() => navigateToProduct(product.slug)}
        aria-label={`${t('View product', 'পণ্য দেখুন')}: ${language === 'bn' && product.name_bn ? product.name_bn : product.name}`}
        className="relative mb-3 flex aspect-square w-full items-center justify-center overflow-hidden rounded-xl bg-slate-50 text-left"
      >
        {product.image ? (
          <img
            src={product.image}
            alt=""
            className="w-full h-full object-cover object-center group-hover:scale-105 motion-image-zoom"
            loading="lazy"
          />
        ) : (
          <span className="flex h-full w-full flex-col items-center justify-center gap-1.5 text-slate-400">
            <ImageOff className="h-7 w-7" aria-hidden="true" />
            <span className="px-2 text-center text-[10px] font-semibold leading-tight">
              {t('No product photo', 'পণ্যের ছবি নেই')}
            </span>
          </span>
        )}
        {product.stock_quantity <= 0 && (
          <span className="absolute inset-0 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs">
            <span className="px-3 py-1 bg-white/95 rounded-lg text-xs font-bold text-slate-800">
              {t('Out of Stock', 'মজুদ নেই')}
            </span>
          </span>
        )}
      </button>

      {/* Product Details */}
      <div className="flex flex-col flex-1">
        {/* Category & Seller */}
          <div className="flex items-center justify-between text-xs text-muted mb-1 gap-1">
          <span className="truncate max-w-[130px] font-medium text-slate-500">
            {product.brand_name || product.seller_name}
          </span>
            {product.review_count !== undefined && product.review_count > 0 && product.rating !== undefined && <div className="flex items-center gap-1 shrink-0 text-amber-500 font-semibold text-xs">
            <Star className="w-3.5 h-3.5 fill-current" />
            <span>{product.rating}</span>
            <span className="text-slate-400 font-normal">({product.review_count})</span>
            </div>}
        </div>

        {/* Title */}
        <h3 className="mb-1 line-clamp-2 text-sm font-semibold text-ink transition-colors group-hover:text-primary sm:text-base">
          <button
            type="button"
            onClick={() => navigateToProduct(product.slug)}
            className="text-left focus-visible:rounded-sm"
          >
            {language === 'bn' && product.name_bn ? product.name_bn : product.name}
          </button>
        </h3>

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
            onClick={handleAddToCartClick}
            aria-label="Add to cart"
            className={`marketplace-cart-cta neu-button px-2.5 sm:px-3 rounded-xl text-white shadow-sm flex items-center justify-center gap-1.5 shrink-0 active:scale-90 transition-all duration-200 ${
              justAddedCart
                ? 'bg-emerald-600 animate-cart-bounce'
                : 'bg-primary hover:bg-primary-hover'
            } disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed`}
          >
            {justAddedCart ? <Check className="w-4 h-4 stroke-[3]" /> : <ShoppingBag className="w-4 h-4" />}
            <span className="hidden sm:inline text-[11px] font-bold">{justAddedCart ? t('Added', 'যোগ হয়েছে') : t('Add', 'নিন')}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
