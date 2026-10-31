import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { ProductVariant } from '../types';
import { ProductCard } from '../components/ProductCard';
import { 
  Star, Heart, ShoppingBag, Truck, ShieldCheck, 
  RotateCcw, CheckCircle2, ChevronRight, Share2, 
  Plus, Minus, ArrowLeft, MessageSquarePlus, Layers, 
  Sparkles, HelpCircle, Send, Check, Eye 
} from 'lucide-react';

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
    addReview,
    getProductQuestions,
    addQuestion,
    isPrimeMember,
    setIsPrimeModalOpen,
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

  // Tabs: Reviews, Q&A, Specifications
  const [activeTab, setActiveTab] = useState<'details' | 'specs' | 'reviews' | 'qa'>('details');

  // Review Form
  const [isReviewFormOpen, setIsReviewFormOpen] = useState(false);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewComment, setReviewComment] = useState('');

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

  const totalItemPrice = unitPrice * quantity;
  const availableStock = selectedVariant ? selectedVariant.stock : product.stock_quantity;

  const handleAddToCart = () => {
    addToCart(product, selectedVariant, quantity);
  };

  const handleBuyNow = () => {
    addToCart(product, selectedVariant, quantity);
    setCurrentView('checkout');
  };

  const handleReviewSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewComment.trim()) return;
    addReview(product.id, reviewRating, reviewComment.trim());
    setReviewComment('');
    setIsReviewFormOpen(false);
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
          <div className="p-4 rounded-2xl bg-surface-raised border border-border flex items-baseline justify-between">
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-black text-ink">
                  {formatPrice(unitPrice)}
                </span>
                {product.discount_price && (
                  <span className="text-base text-slate-400 line-through">
                    {formatPrice(product.price + modifier)}
                  </span>
                )}
                {bulkDiscountPercent > 0 && (
                  <span className="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-800 text-xs font-bold">
                    {bulkDiscountPercent}% Bulk Discount Applied!
                  </span>
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

          {/* Prime Delivery Tag */}
          <div className="p-3.5 rounded-2xl bg-gradient-to-r from-blue-50 to-amber-50/50 border border-blue-200/60 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="font-black italic text-primary text-sm">prime</span>
              <span className="text-slate-700">
                {isPrimeMember 
                  ? t('You get FREE 3-Hour Express Doorstep Delivery on this item!', 'প্রাইম মেম্বার: ৩ ঘণ্টায় সম্পূর্ণ ফ্রি ডেলিভারি!')
                  : t('Get FREE Express Delivery with NexHaat Prime', 'প্রাইম মেম্বার হয়ে উপভোগ করুন ফ্রি ডেলিভারি')}
              </span>
            </div>
            {!isPrimeMember && (
              <button
                onClick={() => setIsPrimeModalOpen(true)}
                className="font-bold text-primary hover:underline shrink-0"
              >
                {t('Learn more', 'বিস্তারিত')}
              </button>
            )}
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
                className="neu-button py-3.5 px-6 rounded-2xl bg-accent hover:bg-amber-500 text-slate-900 font-bold text-sm shadow-md disabled:bg-slate-200 disabled:text-slate-400"
              >
                {t('Buy Now', 'এখনই কিনুন')}
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

      {/* Tabs Section: Specifications, Q&A, Customer Reviews */}
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

        {/* Tab: Reviews */}
        {activeTab === 'reviews' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-sm text-ink">{t('Verified Purchase Reviews', 'যাচাইকৃত ক্রেতাদের মতামত')}</h3>
              <button
                onClick={() => setIsReviewFormOpen(!isReviewFormOpen)}
                className="px-4 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover"
              >
                {isReviewFormOpen ? t('Cancel', 'বাতিল') : t('Write a Review', 'রিভিউ লিখুন')}
              </button>
            </div>

            {isReviewFormOpen && (
              <form onSubmit={handleReviewSubmit} className="p-4 rounded-2xl bg-surface-raised border border-border space-y-3">
                <div className="flex gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button key={star} type="button" onClick={() => setReviewRating(star)}>
                      <Star className={`w-5 h-5 ${star <= reviewRating ? 'text-amber-400 fill-current' : 'text-slate-300'}`} />
                    </button>
                  ))}
                </div>
                <textarea
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  placeholder="Share details of your experience with this product..."
                  rows={3}
                  required
                  className="w-full p-3 text-xs border rounded-xl"
                />
                <button type="submit" className="px-5 py-2 rounded-xl bg-primary text-white text-xs font-bold">
                  {t('Post Review', 'পোস্ট করুন')}
                </button>
              </form>
            )}

            <div className="space-y-3">
              {reviews.map((rev) => (
                <div key={rev.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-ink">{rev.user_name}</span>
                    <span className="text-slate-400 text-[11px]">{rev.created_at}</span>
                  </div>
                  <div className="flex text-amber-400">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Star key={i} className={`w-3.5 h-3.5 ${i < rev.rating ? 'fill-current' : 'text-slate-200'}`} />
                    ))}
                  </div>
                  <p className="text-xs text-slate-700">{rev.comment}</p>
                </div>
              ))}
            </div>
          </div>
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

      {/* Frequently Bought Together Shelf */}
      {relatedProducts.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-ink">
              {t('Frequently Bought Together', 'সম্পর্কিত অন্যান্য পণ্য')}
            </h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
            {relatedProducts.map(rel => (
              <ProductCard key={rel.id} product={rel} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
};
