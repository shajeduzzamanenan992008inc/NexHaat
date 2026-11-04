import React, { useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  X, Trash2, Plus, Minus, ShoppingBag, ArrowRight, 
  Tag, ShieldCheck, Bookmark, Sparkles, Check, Zap 
} from 'lucide-react';
import { useMotionPresence } from '../lib/useMotionPresence';

export const CartDrawer: React.FC = () => {
  const {
    isCartDrawerOpen,
    setIsCartDrawerOpen,
    cart,
    savedForLater,
    cartSubtotal,
    updateCartQuantity,
    removeFromCart,
    saveForLater,
    moveToCartFromSaved,
    removeFromSaved,
    clearCart,
    formatPrice,
    activeCoupon,
    appliedPromoDiscount,
    applyCoupon,
    removeCoupon,
    setCurrentView,
    products,
    addToCart,
    t,
  } = useApp();

  const [couponInput, setCouponInput] = useState('');
  const { isPresent, isExiting } = useMotionPresence(isCartDrawerOpen);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (overlayRef.current) overlayRef.current.inert = isExiting || !isCartDrawerOpen;
  }, [isCartDrawerOpen, isExiting]);

  if (!isPresent) return null;

  const estimatedItemsTotal = Math.max(0, cartSubtotal - appliedPromoDiscount);

  const handleApplyPromo = (e: React.FormEvent) => {
    e.preventDefault();
    if (!couponInput) return;
    const success = applyCoupon(couponInput);
    if (success) setCouponInput('');
  };

  return (
    <div
      ref={overlayRef}
      className={`fixed inset-0 z-50 overflow-hidden motion-drawer-overlay motion-overlay-enter ${
        isExiting ? 'motion-overlay-exit pointer-events-none' : ''
      }`}
      aria-hidden={isExiting || !isCartDrawerOpen}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={() => setIsCartDrawerOpen(false)}
      />

      {/* Drawer content */}
      <div className={`absolute inset-y-0 right-0 max-w-full flex pl-10 motion-drawer-enter ${isExiting ? 'motion-drawer-exit' : ''}`}>
        <div className="w-screen max-w-md bg-white shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-surface-raised">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-primary-light rounded-xl text-primary">
                <ShoppingBag className="w-5 h-5" />
              </div>
              <div>
                <h2 className="font-bold text-ink text-lg">
                  {t('Shopping Cart', 'শপিং কার্ট')}
                </h2>
                <p className="text-xs text-muted">
                  {cart.length} {cart.length === 1 ? t('item', 'টি পণ্য') : t('items', 'টি পণ্য')}
                </p>
              </div>
            </div>

            <button
              onClick={() => setIsCartDrawerOpen(false)}
              className="p-2 text-muted hover:text-ink rounded-lg hover:bg-slate-100 transition-colors"
              aria-label="Close cart"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="mx-4 mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-[11px] leading-relaxed text-amber-900" role="note">
            {t(
              'Delivery, promotions, and membership benefits are confirmed by marketplace checkout. Preview values here are not final.',
              'ডেলিভারি, অফার ও মেম্বারশিপ সুবিধা মার্কেটপ্লেস চেকআউটে নিশ্চিত হবে। এখানে প্রিভিউ মান চূড়ান্ত নয়।'
            )}
          </div>

          {/* Cart Item List */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
            {cart.length === 0 ? (
              <div className="py-8 flex flex-col items-center justify-center text-center text-muted">
                <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mb-3 text-slate-400">
                  <ShoppingBag className="w-7 h-7" />
                </div>
                <h3 className="font-bold text-ink text-sm mb-1">
                  {t('Your cart is empty', 'আপনার কার্ট খালি রয়েছে')}
                </h3>
                <p className="text-xs text-slate-500 max-w-xs mb-4">
                  {t(
                    'Explore fresh foods, organic produce, and daily essentials.',
                    'তাজা খাবার এবং নিত্যপ্রয়োজনীয় জিনিসপত্র বেছে নিন।'
                  )}
                </p>
                <button
                  onClick={() => {
                    setIsCartDrawerOpen(false);
                    setCurrentView('catalog');
                  }}
                  className="px-4 py-2 bg-primary text-white font-semibold rounded-xl text-xs shadow-sm hover:bg-primary-hover"
                >
                  {t('Explore Marketplace', 'মার্কেটপ্লেস ব্রাউজ করুন')}
                </button>
              </div>
            ) : (
              cart.map((item) => {
                const itemPrice = item.product.discount_price ?? item.product.price;
                const modifier = item.selectedVariant?.priceModifier || 0;
                const unitPrice = itemPrice + modifier;
                const lineTotal = unitPrice * item.quantity;

                return (
                  <div
                    key={`${item.product.id}-${item.selectedVariant?.id || 'base'}`}
                    className="flex gap-3 p-3 rounded-xl border border-slate-100 bg-white shadow-xs hover:border-slate-200 transition-colors"
                  >
                    <img
                      src={item.product.image}
                      alt={item.product.name}
                      className="w-18 h-18 sm:w-20 sm:h-20 rounded-lg object-cover bg-slate-50 shrink-0"
                    />

                    <div className="flex-1 flex flex-col justify-between min-w-0">
                      <div>
                        <div className="flex items-start justify-between gap-1">
                          <h4 className="font-semibold text-xs sm:text-sm text-ink line-clamp-1">
                            {item.product.name}
                          </h4>
                          <button
                            onClick={() => removeFromCart(item.product.id, item.selectedVariant?.id)}
                            className="text-slate-400 hover:text-danger p-1 transition-colors"
                            aria-label="Remove item"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {item.selectedVariant && (
                          <span className="text-[11px] text-primary font-medium">
                            {item.selectedVariant.name}
                          </span>
                        )}
                        {item.product.seller_name && (
                          <p className="text-xs text-muted truncate">
                            {item.product.seller_name}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center justify-between mt-2 pt-1">
                        {/* Stepper */}
                        <div className="flex items-center border border-slate-200 rounded-lg bg-slate-50 overflow-hidden">
                          <button
                            onClick={() =>
                              updateCartQuantity(
                                item.product.id,
                                item.selectedVariant?.id,
                                item.quantity - 1
                              )
                            }
                            className="p-1 hover:bg-slate-200 text-slate-600 transition-colors"
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <span className="px-2.5 text-xs font-bold text-ink">
                            {item.quantity}
                          </span>
                          <button
                            onClick={() =>
                              updateCartQuantity(
                                item.product.id,
                                item.selectedVariant?.id,
                                item.quantity + 1
                              )
                            }
                            className="p-1 hover:bg-slate-200 text-slate-600 transition-colors"
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>

                        {/* Price & Save for Later */}
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => saveForLater(item.product.id, item.selectedVariant?.id)}
                            className="text-[10px] text-slate-500 hover:text-primary font-semibold underline"
                            title="Save for Later"
                          >
                            {t('Save for later', 'পরে কিনুন')}
                          </button>
                          <span className="font-bold text-sm text-ink">
                            {formatPrice(lineTotal)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}

            {/* Amazon-style "Saved for Later" Shelf */}
            {savedForLater.length > 0 && (
              <div className="pt-4 border-t border-slate-200 space-y-2.5">
                <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                  <Bookmark className="w-3.5 h-3.5 text-primary" />
                  <span>{t('Saved for Later', 'পরে কেনার জন্য সংরক্ষিত')} ({savedForLater.length})</span>
                </div>

                <div className="space-y-2">
                  {savedForLater.map((savedItem) => (
                    <div
                      key={`saved-${savedItem.product.id}`}
                      className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <img
                          src={savedItem.product.image}
                          alt={savedItem.product.name}
                          className="w-10 h-10 rounded-lg object-cover shrink-0"
                        />
                        <div className="truncate">
                          <p className="font-bold text-ink truncate">{savedItem.product.name}</p>
                          <p className="text-[11px] text-primary font-semibold">
                            {formatPrice(savedItem.product.discount_price ?? savedItem.product.price)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => moveToCartFromSaved(savedItem.product.id, savedItem.selectedVariant?.id)}
                          className="px-2.5 py-1 rounded-lg bg-primary text-white font-bold text-[11px] hover:bg-primary-hover"
                        >
                          {t('Move to Cart', 'কার্টে নিন')}
                        </button>
                        <button
                          onClick={() => removeFromSaved(savedItem.product.id, savedItem.selectedVariant?.id)}
                          className="text-slate-400 hover:text-danger p-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Amazon-style "Customers Also Added" Cross-sell Shelf */}
            {cart.length > 0 && (
              <div className="pt-4 border-t border-slate-200 space-y-2.5">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700">
                  <span className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                    <span>{t('Customers Also Added', 'অন্যান্য ক্রেতারা আরও নিয়েছেন')}</span>
                  </span>
                </div>
                <div className="space-y-2">
                  {products
                    .filter((p) => !cart.some((ci) => ci.product.id === p.id))
                    .slice(0, 2)
                    .map((item) => (
                      <div
                        key={`cross-sell-${item.id}`}
                        className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-3 text-xs"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <img
                            src={item.image}
                            alt={item.name}
                            className="w-10 h-10 rounded-lg object-cover shrink-0"
                          />
                          <div className="truncate">
                            <p className="font-bold text-ink truncate">{item.name}</p>
                            <p className="text-[11px] text-primary font-semibold">
                              {formatPrice(item.discount_price ?? item.price)}
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => addToCart(item, item.variants && item.variants.length > 0 ? item.variants[0] : undefined, 1)}
                          className="px-2.5 py-1 rounded-lg bg-slate-900 text-white font-bold text-[11px] hover:bg-primary transition-colors flex items-center gap-1 shrink-0"
                        >
                          <Plus className="w-3 h-3" />
                          <span>{t('Add', 'যোগ')}</span>
                        </button>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>

          {/* Footer calculation & checkout */}
          {cart.length > 0 && (
            <div className="p-4 sm:p-5 border-t border-slate-200 bg-surface-raised space-y-3">
              {/* Promo code */}
              {activeCoupon ? (
                <div className="flex items-center justify-between p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <Tag className="w-3.5 h-3.5" />
                    <span>{activeCoupon.code} applied (-{formatPrice(appliedPromoDiscount)})</span>
                  </div>
                  <button onClick={removeCoupon} className="text-xs font-bold text-danger hover:underline">
                    {t('Remove', 'মুছুন')}
                  </button>
                </div>
              ) : (
                <form onSubmit={handleApplyPromo} className="flex gap-2">
                  <input
                    type="text"
                    value={couponInput}
                    onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                    placeholder={t('Enter promo code (e.g. NEXHAAT10)', 'কুপন কোড লিখুন')}
                    className="flex-1 px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white focus:outline-hidden focus:border-primary uppercase font-mono"
                  />
                  <button
                    type="submit"
                    className="px-3.5 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-xl"
                  >
                    {t('Apply', 'প্রয়োগ')}
                  </button>
                </form>
              )}

              {/* Price Breakdown */}
              <div className="space-y-1.5 text-xs text-slate-600 pt-1">
                <div className="flex justify-between">
                  <span>{t('Subtotal', 'সাবটোটাল')}</span>
                  <span className="font-semibold text-ink">{formatPrice(cartSubtotal)}</span>
                </div>
                {appliedPromoDiscount > 0 && (
                  <div className="flex justify-between text-emerald-600">
                    <span>{t('Voucher Discount', 'ভাউচার ডিসকাউন্ট')}</span>
                    <span className="font-semibold">-{formatPrice(appliedPromoDiscount)}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span>{t('Delivery preview', 'ডেলিভারি প্রিভিউ')}</span>
                  <span className="font-semibold text-ink">{t('Confirmed at checkout', 'চেকআউটে নিশ্চিত হবে')}</span>
                </div>
                <div className="flex justify-between text-sm font-bold text-ink pt-2 border-t border-slate-200">
                  <span>{t('Items total before delivery', 'ডেলিভারির আগের পণ্য মূল্য')}</span>
                  <span className="text-base text-primary">{formatPrice(estimatedItemsTotal)}</span>
                </div>
              </div>
              <p className="pt-1 text-[10px] leading-relaxed text-muted">
                {t('The marketplace validates the final delivery charge and total during checkout.', 'চেকআউটে মার্কেটপ্লেস চূড়ান্ত ডেলিভারি চার্জ ও মোট মূল্য যাচাই করবে।')}
              </p>

              {/* Action buttons */}
              <div className="pt-2 flex flex-col gap-2">
                <button
                  onClick={() => {
                    setIsCartDrawerOpen(false);
                    setCurrentView('checkout');
                  }}
                  className="neu-button w-full py-3 px-4 bg-primary text-white font-bold rounded-xl text-sm shadow-md hover:bg-primary-hover flex items-center justify-center gap-2"
                >
                  <span>{t('Proceed to Checkout', 'চেকআউটে যান')}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 px-1">
                  <span className="flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-success" />
                    {t('Checkout validation required', 'চেকআউটে যাচাই হবে')}
                  </span>
                  <button
                    onClick={clearCart}
                    className="text-slate-400 hover:text-danger underline"
                  >
                    {t('Clear Cart', 'কার্ট খালি করুন')}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
