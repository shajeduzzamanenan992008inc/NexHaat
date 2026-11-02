import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { ProductVariant, Product } from '../types';
import { ProductCard } from '../components/ProductCard';
import { PriceIntelligenceCard } from '../components/PriceIntelligenceCard';
import { PriceTrendChart } from '../components/PriceTrendChart';
import { ProductReviewsSection } from '../components/ProductReviewsSection';
import { PriceAlertModal } from '../components/PriceAlertModal';
import { 
  Star, Heart, ShoppingBag, Truck, ShieldCheck, 
  RotateCcw, CheckCircle2, ChevronRight, Share2, 
  Plus, Minus, ArrowLeft, MessageSquarePlus, Layers, 
  Sparkles, HelpCircle, Send, Check, Eye, Clock, 
  ThumbsUp, CheckSquare, Square, PackageCheck, Zap, RefreshCw, Store, Scale,
  Bell, BellRing 
} from 'lucide-react';
import { 
  calculateBundlePrice, 
  calculateReviewDistribution, 
  calculateDeliveryPromise 
} from '../lib/amazonFeatures';

export const ProductDetailPage: React.FC = () => {
  const {
    selectedProductSlug,
    products,
    formatPrice,
    addToCart,
    toggleWishlist,
    isInWishlist,
    toggleCompare,
    comparedProductIds,
    setIsCompareModalOpen,
    setCurrentView,
    getProductReviews,
    getProductQuestions,
    addQuestion,
    isPrimeMember,
    setIsPrimeModalOpen,
    getPriceAlert,
    showToast,
    t,
    language,
  } = useApp();

  const product = products.find(p => p.slug === selectedProductSlug) || products[0];
  const reviews = getProductReviews(product.id);
  const questions = getProductQuestions(product.id);

  // States
  const [selectedVariant, setSelectedVariant] = useState<ProductVariant | undefined>(
    product.variants && product.variants.length > 0 ? product.variants[0] : undefined
  );
  const [quantity, setQuantity] = useState<number>(1);
  const [activeImage, setActiveImage] = useState<string>(product.image);

  // Amazon Purchase Type: One-time vs Subscribe & Save (10% discount)
  const [purchaseType, setPurchaseType] = useState<'one-time' | 'subscribe'>('one-time');

  // Price Drop Alert Modal State
  const [isPriceAlertModalOpen, setIsPriceAlertModalOpen] = useState(false);
  const existingAlert = getPriceAlert(product.id);

  // Amazon Delivery Promise Countdown
  const [countdown, setCountdown] = useState<{ hours: number; minutes: number; seconds: number }>({
    hours: 2,
    minutes: 48,
    seconds: 20,
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev.seconds > 0) {
          return { ...prev, seconds: prev.seconds - 1 };
        } else if (prev.minutes > 0) {
          return { ...prev, minutes: prev.minutes - 1, seconds: 59 };
        } else if (prev.hours > 0) {
          return { hours: prev.hours - 1, minutes: 59, seconds: 59 };
        }
        return { hours: 3, minutes: 30, seconds: 0 };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Amazon Frequently Bought Together bundle items
  const complementaryProducts = products
    .filter((p) => p.id !== product.id && p.category_slug === product.category_slug)
    .slice(0, 2);
  const bundlePool: Product[] = [product, ...complementaryProducts];
  const [bundleSelectedIds, setBundleSelectedIds] = useState<number[]>(() =>
    bundlePool.map((p) => p.id)
  );

  const toggleBundleItem = (id: number) => {
    setBundleSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const selectedBundleProducts = bundlePool.filter((p) => bundleSelectedIds.includes(p.id));
  const bundlePricing = calculateBundlePrice(selectedBundleProducts, 10);

  // Tabs: Details, Specs, Pricing, Reviews, Q&A
  const [activeTab, setActiveTab] = useState<'details' | 'specs' | 'pricing' | 'reviews' | 'qa'>('details');

  // Q&A Form
  const [questionInput, setQuestionInput] = useState('');

  const isFavorited = isInWishlist(product.id);
  const isCompared = comparedProductIds.includes(product.id);

  const basePrice = product.discount_price ?? product.price;
  const modifier = selectedVariant?.priceModifier || 0;
  let unitPrice = basePrice + modifier;

  // Bulk Discount calculation
  let bulkDiscountPercent = 0;
  if (product.bulk_discounts && product.bulk_discounts.length > 0) {
    const tier = product.bulk_discounts
      .filter(t => quantity >= t.minQty)
      .sort((a, b) => b.minQty - a.minQty)[0];
    if (tier) {
      bulkDiscountPercent = tier.discountPercent;
      unitPrice = unitPrice * (1 - bulkDiscountPercent / 100);
    }
  }

  const effectiveUnitPrice = purchaseType === 'subscribe'
    ? Math.round(unitPrice * 0.90)
    : unitPrice;
  const totalItemPrice = effectiveUnitPrice * quantity;
  const availableStock = selectedVariant ? selectedVariant.stock : product.stock_quantity;

  const handleAddToCart = () => {
    const itemToAdd = purchaseType === 'subscribe'
      ? { ...product, discount_price: effectiveUnitPrice }
      : product;
    addToCart(itemToAdd, selectedVariant, quantity);
    if (purchaseType === 'subscribe') {
      showToast(t('Added monthly subscription with 10% discount to cart!', '১০% ছাড়সহ মাসিক সাবস্ক্রিপশন কার্টে যোগ হয়েছে!'), 'success');
    }
  };

  const handleBuyNow = () => {
    const itemToAdd = purchaseType === 'subscribe'
      ? { ...product, discount_price: effectiveUnitPrice }
      : product;
    addToCart(itemToAdd, selectedVariant, quantity);
    setCurrentView('checkout');
  };

  const handleAddBundleToCart = () => {
    if (selectedBundleProducts.length === 0) return;
    selectedBundleProducts.forEach((p) => {
      const discountedPrice = Math.round((p.discount_price ?? p.price) * 0.90);
      addToCart(
        { ...p, discount_price: discountedPrice },
        p.variants && p.variants.length > 0 ? p.variants[0] : undefined,
        1
      );
    });
    showToast(
      t(
        `Added ${selectedBundleProducts.length} bundle items to cart! (10% Bundle Discount Applied)`,
        `বান্ডেলের ${selectedBundleProducts.length}টি পণ্য কার্টে যোগ হয়েছে! (১০% বিশেষ ছাড়)`
      ),
      'success'
    );
  };


  const handleQuestionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionInput.trim()) return;
    addQuestion(product.id, questionInput.trim());
    setQuestionInput('');
  };

  const relatedProducts = products
    .filter(p => p.category_slug === product.category_slug && p.id !== product.id)
    .slice(0, 4);

  return (
    <div className="space-y-10 pb-16">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-muted">
        <button onClick={() => setCurrentView('home')} className="hover:text-primary transition-colors">
          {t('Home', 'হোম')}
        </button>
        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        <button onClick={() => setCurrentView('catalog')} className="hover:text-primary transition-colors">
          {t('Catalog', 'ক্যাটালগ')}
        </button>
        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        <span className="text-ink font-semibold truncate max-w-xs">
          {language === 'bn' && product.name_bn ? product.name_bn : product.name}
        </span>
      </div>

      {/* Main Product Showcase Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Gallery Column */}
        <div className="lg:col-span-6 space-y-3">
          <div className="relative aspect-square w-full rounded-3xl overflow-hidden bg-white border border-border shadow-card flex items-center justify-center p-4">
            <img
              src={activeImage}
              alt={product.name}
              className="w-full h-full object-cover rounded-2xl"
            />

            {/* Badges */}
            <div className="absolute top-5 left-5 flex flex-col gap-1.5 items-start">
              {product.is_nexhaat_choice && (
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-black bg-slate-900 text-white shadow-sm">
                  <span>NexHaat's</span>
                  <span className="text-amber-400">Choice</span>
                </span>
              )}
              {product.discount_price && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-danger text-white shadow-sm">
                  {t('SAVE', 'ছাড়')} {formatPrice(product.price - product.discount_price)}
                </span>
              )}
            </div>

            {/* 360 preview badge */}
            <div className="absolute bottom-5 right-5 px-3 py-1 rounded-xl bg-slate-900/70 text-white backdrop-blur-md text-xs font-semibold flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-amber-400" />
              <span>Verified 360° Quality</span>
            </div>
          </div>

          {/* Thumbnails */}
          {product.additionalImages && product.additionalImages.length > 1 && (
            <div className="flex gap-2.5 overflow-x-auto pb-1">
              {product.additionalImages.map((img, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveImage(img)}
                  className={`w-20 h-20 rounded-xl overflow-hidden border-2 shrink-0 transition-all ${
                    activeImage === img ? 'border-primary ring-2 ring-primary/20' : 'border-border opacity-70 hover:opacity-100'
                  }`}
                >
                  <img src={img} alt="Thumbnail" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Details Column */}
        <div className="lg:col-span-6 space-y-5">
          <div>
            {/* Seller & Rating */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-md bg-primary-light text-primary">
                Store: {product.seller_name}
              </span>
              <div className="flex items-center gap-1.5 text-xs text-amber-500 font-bold">
                <Star className="w-4 h-4 fill-current" />
                <span>{product.rating}</span>
                <span className="text-slate-400 font-normal">
                  ({product.review_count} {t('ratings', 'টি রেটিং')} • {questions.length} {t('answered Q&As', 'টি প্রশ্নোত্তর')})
                </span>
              </div>
            </div>

            {/* Product Title */}
            <h1 className="text-2xl sm:text-3xl font-extrabold text-ink leading-snug">
              {language === 'bn' && product.name_bn ? product.name_bn : product.name}
            </h1>

            <div className="flex items-center gap-3 mt-1.5 text-xs text-muted">
              <span>SKU: <strong className="font-mono text-ink">{product.sku}</strong></span>
              <span>•</span>
              <span>Unit: <strong className="text-ink">{language === 'bn' && product.unit_bn ? product.unit_bn : product.unit}</strong></span>
            </div>
          </div>

          {/* Price Box */}
          <div className="p-4 rounded-2xl bg-surface-raised border border-border space-y-2.5">
            <div className="flex items-baseline justify-between">
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-black text-ink">
                    {formatPrice(effectiveUnitPrice)}
                  </span>
                  {product.discount_price && (
                    <span className="text-base text-slate-400 line-through">
                      {formatPrice(product.price + modifier)}
                    </span>
                  )}
                  {purchaseType === 'subscribe' ? (
                    <span className="px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 text-xs font-bold flex items-center gap-1">
                      <RefreshCw className="w-3 h-3 text-amber-700 animate-spin" />
                      <span>10% Subscribe & Save Discount</span>
                    </span>
                  ) : (
                    bulkDiscountPercent > 0 && (
                      <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 text-xs font-bold">
                        {bulkDiscountPercent}% Bulk Discount Applied!
                      </span>
                    )
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {t('Inclusive of all VAT and platform escrow protection', 'ভ্যাট ও প্ল্যাটফর্ম সুরক্ষা অন্তর্ভুক্ত')}
                </p>
              </div>

              <div className="text-right">
                {availableStock > 0 ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span>{t('In Stock', 'মজুদ আছে')} ({availableStock})</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800">
                    {t('Out of Stock', 'মজুদ শেষ')}
                  </span>
                )}
              </div>
            </div>

            {/* Price Alert Action Strip */}
            <div className="pt-2 border-t border-border/70 flex items-center justify-between text-xs">
              <span className="text-muted flex items-center gap-1.5">
                <Bell className="w-3.5 h-3.5 text-amber-500" />
                <span>{t('Want to buy at a lower price?', 'কম মূল্যে কিনতে চান?')}</span>
              </span>
              <button
                type="button"
                onClick={() => setIsPriceAlertModalOpen(true)}
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold transition-all shadow-xs ${
                  existingAlert && existingAlert.is_active
                    ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300 border border-amber-300'
                    : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-primary hover:text-primary'
                }`}
              >
                {existingAlert && existingAlert.is_active ? (
                  <BellRing className="w-3.5 h-3.5 text-amber-600 animate-bounce" />
                ) : (
                  <Bell className="w-3.5 h-3.5" />
                )}
                <span>
                  {existingAlert && existingAlert.is_active
                    ? `${t('Alert: ', 'সতর্কতা: ')}${formatPrice(existingAlert.target_price)}`
                    : t('Set Price Alert', 'মূল্য সতর্কতা')}
                </span>
              </button>
            </div>
          </div>

          {/* Amazon-style Purchase Options: One-Time Purchase vs Subscribe & Save */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => setPurchaseType('one-time')}
              className={`p-3 rounded-2xl border text-left transition-all ${
                purchaseType === 'one-time'
                  ? 'bg-primary/5 border-primary ring-2 ring-primary/20 shadow-xs'
                  : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-ink">{t('One-time purchase', 'এককালীন ক্রয়')}</span>
                <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${
                  purchaseType === 'one-time' ? 'border-primary bg-primary' : 'border-slate-300'
                }`}>
                  {purchaseType === 'one-time' && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
                </span>
              </div>
              <span className="text-sm font-black text-ink">{formatPrice(unitPrice)}</span>
              <p className="text-[10px] text-muted mt-0.5">{t('Standard one-time checkout', 'সাধারণ একক অর্ডার')}</p>
            </button>

            <button
              type="button"
              onClick={() => setPurchaseType('subscribe')}
              className={`p-3 rounded-2xl border text-left transition-all relative overflow-hidden ${
                purchaseType === 'subscribe'
                  ? 'bg-amber-50/70 border-amber-500 ring-2 ring-amber-500/20 shadow-xs'
                  : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="absolute top-0 right-0 bg-gradient-to-l from-amber-500 to-amber-600 text-slate-900 text-[9px] font-black px-2 py-0.5 rounded-bl-lg">
                SAVE 10%
              </div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-ink flex items-center gap-1">
                  <RefreshCw className="w-3 h-3 text-amber-600" />
                  <span>{t('Subscribe & Save', 'সাবস্ক্রাইব ও সঞ্চয়')}</span>
                </span>
                <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${
                  purchaseType === 'subscribe' ? 'border-amber-600 bg-amber-600' : 'border-slate-300'
                }`}>
                  {purchaseType === 'subscribe' && <span className="w-1.5 h-1.5 rounded-full bg-white" />}
                </span>
              </div>
              <span className="text-sm font-black text-amber-700">{formatPrice(Math.round(unitPrice * 0.90))}</span>
              <p className="text-[10px] text-slate-600 mt-0.5">{t('Auto-delivered every month. Cancel anytime.', 'প্রতি মাসে অটো ডেলিভারি। যেকোনো সময় বাতিলযোগ্য।')}</p>
            </button>
          </div>

          {/* Amazon Prime Delivery Promise & Live Countdown Box */}
          <div className="p-3.5 rounded-2xl bg-gradient-to-r from-blue-50/90 via-slate-50 to-amber-50/60 border border-blue-200/80 space-y-2.5">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="font-black italic text-primary text-sm">prime</span>
                <span className="font-bold text-slate-800">
                  {t('Fastest Guaranteed Delivery', 'দ্রুততম গ্যারান্টিযুক্ত ডেলিভারি')}
                </span>
              </div>
              <div className="flex items-center gap-1 font-mono text-[11px] font-bold bg-white px-2 py-0.5 rounded-lg border border-slate-200 text-slate-800 shadow-2xs">
                <Clock className="w-3 h-3 text-amber-500" />
                <span>
                  {countdown.hours}h {countdown.minutes}m {countdown.seconds}s
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-600">
              {t(
                `Order within ${countdown.hours} hrs ${countdown.minutes} mins and choose Prime Express for delivery by Today 8:00 PM!`,
                `${countdown.hours} ঘণ্টা ${countdown.minutes} মিনিটের মধ্যে অর্ডার করলে আজ রাত ৮টার মধ্যে ডেলিভারি পাবেন!`
              )}
            </p>

            <div className="pt-2 border-t border-slate-200/80 grid grid-cols-2 gap-2 text-[11px] text-slate-600">
              <div className="flex items-center gap-1.5">
                <PackageCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span>NexHaat Hub Fulfillment</span>
              </div>
              <div className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-primary shrink-0" />
                <span>7-Day Return Guarantee</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Store className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                <span className="truncate">Sold by {product.seller_name} (4.8 ★)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                <span>Secure Escrow Protection</span>
              </div>
            </div>
          </div>

          {/* Bulk Buying / Wholesale Tier (Amazon B2B feature) */}
          {product.bulk_discounts && product.bulk_discounts.length > 0 && (
            <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
              <span className="font-bold text-slate-700 block">
                {t('Bulk Order / Wholesale Savings:', 'পাইকারি বা বেশি পরিমাণে ক্রয়ে বিশেষ ছাড়:')}
              </span>
              <div className="flex flex-wrap gap-2">
                {product.bulk_discounts.map((tier, idx) => (
                  <span
                    key={idx}
                    className={`px-2.5 py-1 rounded-lg border text-[11px] font-semibold ${
                      quantity >= tier.minQty
                        ? 'bg-emerald-100 border-emerald-300 text-emerald-900 font-bold ring-1 ring-emerald-400'
                        : 'bg-white border-slate-200 text-slate-600'
                    }`}
                  >
                    Buy {tier.minQty}+ units: <strong>{tier.discountPercent}% OFF</strong>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Variants Selector */}
          {product.variants && product.variants.length > 0 && (
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                {t('Select Option / Weight:', 'অপশন বা ওজন নির্বাচন করুন:')}
              </label>
              <div className="flex flex-wrap gap-2">
                {product.variants.map((v) => {
                  const isSelected = selectedVariant?.id === v.id;
                  return (
                    <button
                      key={v.id}
                      onClick={() => setSelectedVariant(v)}
                      className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all border ${
                        isSelected
                          ? 'bg-primary text-white border-primary shadow-sm'
                          : 'bg-white text-slate-700 border-border hover:border-slate-400'
                      }`}
                    >
                      <span>{language === 'bn' && v.name_bn ? v.name_bn : v.name}</span>
                      {v.priceModifier > 0 && (
                        <span className="ml-1 opacity-80">(+{formatPrice(v.priceModifier)})</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quantity Selector & Action Buttons */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                {t('Quantity:', 'পরিমাণ:')}
              </span>
              <div className="flex items-center border border-slate-200 rounded-xl bg-slate-50 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  disabled={quantity <= 1}
                  className="p-2 hover:bg-slate-200 text-slate-600 disabled:opacity-40 transition-colors"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <span className="px-4 text-sm font-bold text-ink">{quantity}</span>
                <button
                  type="button"
                  onClick={() => setQuantity(Math.min(availableStock, quantity + 1))}
                  disabled={quantity >= availableStock}
                  className="p-2 hover:bg-slate-200 text-slate-600 disabled:opacity-40 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>

              <span className="text-xs text-muted">
                {t('Total:', 'মোট মূল্য:')} <strong className="text-ink">{formatPrice(totalItemPrice)}</strong>
              </span>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={handleAddToCart}
                disabled={availableStock <= 0}
                className="neu-button flex-1 py-3.5 px-6 rounded-2xl bg-primary text-white font-bold text-sm shadow-md hover:bg-primary-hover disabled:bg-slate-200 disabled:text-slate-400 flex items-center justify-center gap-2"
              >
                <ShoppingBag className="w-5 h-5" />
                <span>{t('Add to Cart', 'কার্টে যোগ করুন')}</span>
              </button>

              <button
                type="button"
                onClick={handleBuyNow}
                disabled={availableStock <= 0}
                className="neu-button py-3.5 px-6 rounded-2xl bg-amber-400 hover:bg-amber-500 text-slate-950 font-black text-sm shadow-md disabled:bg-slate-200 disabled:text-slate-400 flex items-center justify-center gap-1.5"
              >
                <Zap className="w-4 h-4 fill-slate-950" />
                <span>{t('Buy Now', 'এখনই কিনুন')}</span>
              </button>

              <button
                type="button"
                onClick={() => toggleWishlist(product.id)}
                className={`p-3.5 rounded-2xl border transition-all ${
                  isFavorited
                    ? 'bg-rose-50 border-rose-200 text-rose-500'
                    : 'bg-white border-border text-muted hover:text-rose-500 hover:border-rose-200'
                }`}
                title="Save to Wishlist"
              >
                <Heart className={`w-5 h-5 ${isFavorited ? 'fill-current' : ''}`} />
              </button>

              <button
                type="button"
                onClick={() => {
                  toggleCompare(product.id);
                  setIsCompareModalOpen(true);
                }}
                className={`p-3.5 rounded-2xl border transition-all ${
                  isCompared
                    ? 'bg-primary text-white border-primary'
                    : 'bg-white border-border text-muted hover:text-primary hover:border-primary'
                }`}
                title="Compare with similar items"
              >
                <Layers className="w-5 h-5" />
              </button>

              <button
                type="button"
                onClick={() => setIsPriceAlertModalOpen(true)}
                className={`p-3.5 rounded-2xl border transition-all ${
                  existingAlert && existingAlert.is_active
                    ? 'bg-amber-100 border-amber-300 text-amber-700 shadow-sm'
                    : 'bg-white border-border text-muted hover:text-amber-600 hover:border-amber-300'
                }`}
                title={existingAlert && existingAlert.is_active ? `Price Alert Active (৳${existingAlert.target_price})` : t('Set Price Drop Alert', 'মূল্য সতর্কতা')}
              >
                {existingAlert && existingAlert.is_active ? (
                  <BellRing className="w-5 h-5 text-amber-600" />
                ) : (
                  <Bell className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>

          {/* AI Review Summary (Amazon-style Gemini feature) */}
          <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-200/80 text-xs space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold text-primary">
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>{t('HaatAI Review Summary (Powered by Gemini)', 'রিভিউ সারাংশ (জেমিনাই এআই)')}</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              {t(
                `Customers praise this ${product.name} for its verified freshness, authentic regional taste, and secure cold-chain delivery. 96% of buyers reported zero spoilage. Ideal for family celebrations and daily dining.`,
                `ক্রেতারা এই পণ্যের অসাধারণ সতেজতা, খাঁটি আঞ্চলিক স্বাদ এবং সুরক্ষিত প্যাকেজিংয়ের দারুণ প্রশংসা করেছেন। ৯৬% ক্রেতা সন্তোষ প্রকাশ করেছেন।`
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Price Intelligence & Historical Trend Feature */}
      <PriceIntelligenceCard product={product} />

      {/* Tabs Section: Overview, Specifications, Price & Comparison, Customer Reviews, Q&A */}
      <div className="bg-white rounded-3xl border border-border shadow-card p-6 sm:p-8 space-y-6">
        <div className="flex gap-4 border-b border-slate-100 pb-3 overflow-x-auto text-xs font-bold">
          <button
            onClick={() => setActiveTab('details')}
            className={`pb-2 transition-colors shrink-0 ${
              activeTab === 'details' ? 'border-b-2 border-primary text-primary' : 'text-slate-500 hover:text-ink'
            }`}
          >
            {t('Overview & Halal Safety', 'বিবরণ ও হালাল নিরাপত্তা')}
          </button>
          <button
            onClick={() => setActiveTab('specs')}
            className={`pb-2 transition-colors shrink-0 ${
              activeTab === 'specs' ? 'border-b-2 border-primary text-primary' : 'text-slate-500 hover:text-ink'
            }`}
          >
            {t('Technical Specifications', 'বিস্তারিত বিবরণী')}
          </button>
          <button
            onClick={() => setActiveTab('pricing')}
            className={`pb-2 transition-colors shrink-0 flex items-center gap-1.5 ${
              activeTab === 'pricing' ? 'border-b-2 border-primary text-primary' : 'text-slate-500 hover:text-ink'
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            <span>{t('Price Comparison & Trends', 'মূল্য তুলনা ও ট্রেন্ড')}</span>
          </button>
          <button
            onClick={() => setActiveTab('reviews')}
            className={`pb-2 transition-colors shrink-0 ${
              activeTab === 'reviews' ? 'border-b-2 border-primary text-primary' : 'text-slate-500 hover:text-ink'
            }`}
          >
            {t(`Verified Reviews (${reviews.length})`, `রিভিউ (${reviews.length})`)}
          </button>
          <button
            onClick={() => setActiveTab('qa')}
            className={`pb-2 transition-colors shrink-0 ${
              activeTab === 'qa' ? 'border-b-2 border-primary text-primary' : 'text-slate-500 hover:text-ink'
            }`}
          >
            {t(`Customer Q&A (${questions.length})`, `প্রশ্নোত্তর (${questions.length})`)}
          </button>
        </div>

        {/* Tab: Overview */}
        {activeTab === 'details' && (
          <div className="space-y-4 text-xs sm:text-sm text-slate-700 leading-relaxed">
            <p className="whitespace-pre-line">
              {language === 'bn' && product.description_bn ? product.description_bn : product.description}
            </p>

            {product.food_details && (
              <div className="p-4 rounded-2xl bg-emerald-50/60 border border-emerald-200 text-xs space-y-2 mt-4">
                <div className="flex items-center gap-2 font-bold text-emerald-900">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>{t('NexHaat Certified Food Standards', 'খাদ্যমান ও হালাল সনদ')}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-slate-700">
                  <div>
                    <span className="text-slate-500">Origin: </span>
                    <strong className="text-ink">{product.food_details.origin}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Shelf Life: </span>
                    <strong className="text-ink">{product.food_details.shelfLife}</strong>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Technical Specifications (Amazon-style table) */}
        {activeTab === 'specs' && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <tbody className="divide-y divide-slate-100">
                <tr className="bg-slate-50">
                  <td className="py-2.5 px-3 font-bold text-slate-600 w-48">SKU Code</td>
                  <td className="py-2.5 px-3 text-ink font-mono">{product.sku}</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-bold text-slate-600">Category</td>
                  <td className="py-2.5 px-3 text-ink capitalize">{product.category_slug.replace('-', ' ')}</td>
                </tr>
                <tr className="bg-slate-50">
                  <td className="py-2.5 px-3 font-bold text-slate-600">Merchant / Seller</td>
                  <td className="py-2.5 px-3 text-ink">{product.seller_name} ({product.seller_location})</td>
                </tr>
                {product.specifications && Object.entries(product.specifications).map(([key, val], idx) => (
                  <tr key={key} className={idx % 2 === 1 ? 'bg-slate-50' : ''}>
                    <td className="py-2.5 px-3 font-bold text-slate-600">{key}</td>
                    <td className="py-2.5 px-3 text-ink">{val}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab: Price & Comparison Hub */}
        {activeTab === 'pricing' && (
          <div className="space-y-6">
            <PriceTrendChart product={product} />
            <PriceIntelligenceCard product={product} />
          </div>
        )}

        {/* Tab: Customer Ratings & Verified Reviews */}
        {activeTab === 'reviews' && (
          <ProductReviewsSection product={product} />
        )}

        {/* Tab: Customer Q&A (Amazon-style) */}
        {activeTab === 'qa' && (
          <div className="space-y-6">
            <form onSubmit={handleQuestionSubmit} className="flex gap-2">
              <input
                type="text"
                value={questionInput}
                onChange={(e) => setQuestionInput(e.target.value)}
                placeholder={t('Have a question? Search answers or ask the seller...', 'এই পণ্য সম্পর্কে আপনার প্রশ্ন লিখুন...')}
                className="flex-1 p-2.5 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:bg-white"
              />
              <button
                type="submit"
                className="px-4 py-2.5 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{t('Ask Question', 'প্রশ্ন করুন')}</span>
              </button>
            </form>

            <div className="space-y-4">
              {questions.length === 0 ? (
                <p className="text-xs text-muted italic">No questions asked yet.</p>
              ) : (
                questions.map((q) => (
                  <div key={q.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-2 text-xs">
                    <div className="flex items-start gap-2">
                      <HelpCircle className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-ink">{q.question}</strong>
                        <span className="text-[10px] text-slate-400 block mt-0.5">Asked by {q.user_name} on {q.created_at}</span>
                      </div>
                    </div>

                    {q.answer && (
                      <div className="pl-6 border-l-2 border-emerald-400 ml-2 mt-2 pt-1 text-slate-700">
                        <p>{q.answer}</p>
                        <span className="text-[10px] text-emerald-700 font-bold block mt-1">Answered by: {q.answered_by}</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Amazon-style Frequently Bought Together Interactive Bundle Box */}
      {complementaryProducts.length > 0 && (
        <section className="bg-white rounded-3xl border border-border shadow-card p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-lg sm:text-xl font-bold text-ink">
                {t('Frequently Bought Together', 'একত্রে বেশি বিক্রিত পণ্যসমূহ')}
              </h3>
              <p className="text-xs text-muted">
                {t('Buy these items together and get an automatic 10% bundle discount', 'একসাথে কিনুন এবং পান অতিরিক্ত ১০% বান্ডেল ছাড়')}
              </p>
            </div>
            <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-md bg-amber-100 text-amber-900">
              Bundle Savings 10%
            </span>
          </div>

          <div className="flex flex-col lg:flex-row items-center gap-6 justify-between">
            {/* Visual Products joined by '+' signs */}
            <div className="flex items-center gap-3 sm:gap-4 overflow-x-auto pb-2 w-full lg:w-auto justify-center lg:justify-start">
              {bundlePool.map((bProduct, idx) => {
                const isSelected = bundleSelectedIds.includes(bProduct.id);
                return (
                  <React.Fragment key={bProduct.id}>
                    {idx > 0 && (
                      <span className="text-slate-400 font-black text-xl shrink-0">+</span>
                    )}
                    <div
                      onClick={() => toggleBundleItem(bProduct.id)}
                      className={`relative w-24 h-24 sm:w-28 sm:h-28 rounded-2xl border-2 p-1.5 cursor-pointer transition-all shrink-0 bg-slate-50 flex items-center justify-center ${
                        isSelected
                          ? 'border-primary ring-2 ring-primary/20 shadow-xs'
                          : 'border-slate-200 opacity-40 hover:opacity-75'
                      }`}
                    >
                      <img
                        src={bProduct.image}
                        alt={bProduct.name}
                        className="w-full h-full object-cover rounded-xl"
                      />
                      <div className="absolute top-1.5 right-1.5 bg-white/90 rounded-md p-0.5 shadow-xs">
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-primary" />
                        ) : (
                          <Square className="w-4 h-4 text-slate-400" />
                        )}
                      </div>
                    </div>
                  </React.Fragment>
                );
              })}
            </div>

            {/* Price & Add to Cart calculation column */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 w-full lg:w-80 shrink-0 space-y-3">
              <div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xs font-bold text-slate-500 uppercase">
                    {t('Bundle Price:', 'বান্ডেল মূল্য:')}
                  </span>
                  <span className="text-2xl font-black text-ink">
                    {formatPrice(bundlePricing.discountedTotal)}
                  </span>
                </div>
                {bundlePricing.savings > 0 && (
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-400 line-through">
                      {formatPrice(bundlePricing.originalTotal)}
                    </span>
                    <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                      {t(`Save ${formatPrice(bundlePricing.savings)}`, `সাশ্রয় ${formatPrice(bundlePricing.savings)}`)}
                    </span>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={handleAddBundleToCart}
                disabled={selectedBundleProducts.length === 0}
                className="neu-button w-full py-3 px-4 rounded-xl bg-amber-400 hover:bg-amber-500 text-slate-950 font-black text-xs shadow-md disabled:bg-slate-200 disabled:text-slate-400 flex items-center justify-center gap-2"
              >
                <ShoppingBag className="w-4 h-4 fill-slate-950" />
                <span>
                  {t(
                    `Add all ${selectedBundleProducts.length} to Cart`,
                    `সব ${selectedBundleProducts.length}টি পণ্য কার্টে যোগ করুন`
                  )}
                </span>
              </button>
            </div>
          </div>

          {/* Individual Checkbox selection rows */}
          <div className="pt-4 border-t border-slate-100 space-y-2 text-xs">
            {bundlePool.map((bProduct, idx) => {
              const isSelected = bundleSelectedIds.includes(bProduct.id);
              const price = bProduct.discount_price ?? bProduct.price;
              return (
                <label
                  key={bProduct.id}
                  className="flex items-center gap-2.5 cursor-pointer text-slate-700 hover:text-ink select-none"
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleBundleItem(bProduct.id)}
                    className="w-4 h-4 rounded text-primary focus:ring-primary border-slate-300"
                  />
                  <span>
                    <strong>{idx === 0 ? t('This item: ', 'এই পণ্য: ') : ''}</strong>
                    <span>{language === 'bn' && bProduct.name_bn ? bProduct.name_bn : bProduct.name}</span>
                    <span className="font-bold text-primary ml-1.5">{formatPrice(price)}</span>
                  </span>
                </label>
              );
            })}
          </div>
        </section>
      )}

      {/* Customers Also Viewed / Related Products Shelf */}
      {relatedProducts.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-ink">
                {t('Customers Also Viewed', 'অন্যান্য ক্রেতারা যা দেখেছেন')}
              </h3>
              <p className="text-xs text-muted">
                {t('Popular complementary items in this category', 'এই ক্যাটাগরির অন্যান্য জনপ্রিয় পণ্যসমূহ')}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
            {relatedProducts.map(rel => (
              <ProductCard key={rel.id} product={rel} />
            ))}
          </div>
        </section>
      )}

      {/* Price Alert Modal */}
      <PriceAlertModal
        product={product}
        isOpen={isPriceAlertModalOpen}
        onClose={() => setIsPriceAlertModalOpen(false)}
      />
    </div>
  );
};

