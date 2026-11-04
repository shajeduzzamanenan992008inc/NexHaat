import React, { useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import {
  Sparkles, Flame, ArrowRight, Store, ChevronRight, ChevronLeft, History,
  Apple, Fish, Smartphone, Shirt, Wheat, Egg, Cookie, Grid, Tag, ShoppingBag,
} from 'lucide-react';

export const HomePage: React.FC = () => {
  const {
    products, 
    categories, 
    isMarketplaceCatalogLoading,
    marketplaceCatalogError,
    recentlyViewed, 
    navigateToCategory, 
    navigateToProduct,
    addToCart,
    setCurrentView, 
    setSearchQuery,
    t, 
    formatPrice, 
    language,
  } = useApp();

  const dealProducts = products.filter(p => p.discount_price && p.is_available && p.stock_quantity > 0);
  const nexhaatChoiceProducts = products.filter(p => p.is_nexhaat_choice && p.is_available).slice(0, 4);
  const featuredProducts = products.filter(p => p.is_featured && p.is_available).slice(0, 8);
  const spotlightProducts = products.filter(p => p.is_available && p.stock_quantity > 0).slice(0, 3);
  const featuredSellers = [...new Set(products.filter(p => p.is_available).map(p => p.seller_name))].slice(0, 4);

  // Horizontal Deals carousel scroll ref
  const dealsScrollRef = useRef<HTMLDivElement>(null);
  const scrollDeals = (direction: 'left' | 'right') => {
    if (dealsScrollRef.current) {
      dealsScrollRef.current.scrollBy({
        left: direction === 'left' ? -340 : 340,
        behavior: 'smooth',
      });
    }
  };

  // Category navigation bar state and definitions
  const [selectedCategoryType, setSelectedCategoryType] = useState<string>('all');

  const getCategoryIcon = (slug: string) => {
    switch (slug) {
      case 'fruits-vegetables':
        return Apple;
      case 'meat-seafood':
        return Fish;
      case 'electronics':
        return Smartphone;
      case 'fashion-accessories':
        return Shirt;
      case 'rice-grains-pasta':
        return Wheat;
      case 'dairy-eggs':
        return Egg;
      case 'spices-seasonings':
        return Flame;
      case 'snacks-sweets':
        return Cookie;
      default:
        return Sparkles;
    }
  };

  const categoryTypes = [
    { id: 'all', label: 'All Items', label_bn: 'সকল ধরন', icon: Grid, color: 'text-primary' },
    { id: 'fresh-food', label: 'Fresh Food', label_bn: 'তাজা খাবার', icon: Apple, slugs: ['fruits-vegetables', 'meat-seafood'], color: 'text-primary' },
    { id: 'electronics', label: 'Electronics', label_bn: 'ইলেকট্রনিক্স', icon: Smartphone, slugs: ['electronics'], color: 'text-blue-600' },
    { id: 'fashion', label: 'Fashion', label_bn: 'ফ্যাশন ও তাঁত', icon: Shirt, slugs: ['fashion-accessories'], color: 'text-purple-600' },
    { id: 'grains', label: 'Grains & Rice', label_bn: 'চাল ও খাদ্যশস্য', icon: Wheat, slugs: ['rice-grains-pasta'], color: 'text-amber-600' },
    { id: 'dairy', label: 'Dairy & Sweets', label_bn: 'দুধ ও মিষ্টি', icon: Egg, slugs: ['dairy-eggs', 'snacks-sweets'], color: 'text-cyan-600' },
    { id: 'spices', label: 'Spices & Oils', label_bn: 'মসলা ও তেল', icon: Flame, slugs: ['spices-seasonings'], color: 'text-orange-600' },
  ];

  const filteredCategories = selectedCategoryType === 'all'
    ? categories
    : categories.filter(cat => {
        const typeObj = categoryTypes.find(t => t.id === selectedCategoryType);
        return typeObj?.slugs?.includes(cat.slug);
      });

  return (
    <div className="marketplace-home space-y-9 sm:space-y-12 pb-12">
      <section className="marketplace-hero relative grid overflow-hidden rounded-[2rem] bg-gradient-to-br from-[#0B1F3A] via-[#1769FF] to-[#1748A8] p-6 text-white shadow-elevated sm:p-9 lg:grid-cols-[1.05fr_.95fr] lg:items-center lg:p-12 dark:from-[#07182B] dark:via-[#0B1F3A] dark:to-[#102947]">
        <div className="relative z-10 max-w-2xl py-2 lg:py-6">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3.5 py-1.5 text-xs font-bold text-amber-200">
            <Sparkles className="h-4 w-4" />
            <span>{t('A LOCAL MARKETPLACE FOR EVERY DAY', 'প্রতিদিনের কেনাকাটার আপন ঠিকানা')}</span>
          </div>

          <h1 className="mb-4 max-w-xl text-4xl font-black leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-6xl">
            {t('Good things, found closer to home.', 'প্রতিদিনের কেনাকাটা, কাছের মানুষের কাছ থেকে।')}
          </h1>

          <p className="mb-7 max-w-lg text-sm leading-relaxed text-blue-50/90 sm:text-base">
            {t(
              'Explore groceries, fresh food, everyday essentials, and products from local sellers in one place.',
              'এক জায়গায় খুঁজে নিন নিত্যপণ্য, তাজা খাবার, দরকারি সামগ্রী আর স্থানীয় বিক্রেতাদের পণ্য।'
            )}
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setCurrentView('catalog')}
              className="neu-button inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-bold text-slate-950 shadow-lg hover:bg-amber-400"
            >
              <span>{t('Explore the marketplace', 'মার্কেটপ্লেস দেখুন')}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setCurrentView('deals')}
              className="rounded-xl border border-white/25 bg-white/10 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/20"
            >
              {t('Browse current deals', 'চলতি অফার দেখুন')}
            </button>
          </div>

          <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2 border-t border-white/15 pt-5 text-xs font-medium text-blue-50/90">
            <span className="inline-flex items-center gap-2"><Store className="h-4 w-4 text-amber-200" />{t('Local sellers', 'স্থানীয় বিক্রেতা')}</span>
            <span className="inline-flex items-center gap-2"><ShoppingBag className="h-4 w-4 text-amber-200" />{t('Everyday essentials', 'নিত্যপ্রয়োজনীয় পণ্য')}</span>
            <span className="inline-flex items-center gap-2"><Grid className="h-4 w-4 text-amber-200" />{t('Browse by category', 'ক্যাটাগরি অনুযায়ী দেখুন')}</span>
          </div>
        </div>

        <div className="marketplace-hero__visual" aria-label={t('A selection of marketplace products', 'মার্কেটপ্লেসের কিছু পণ্য')}>
          <span className="marketplace-hero__visual-label">{t('Picked from the marketplace', 'মার্কেটপ্লেস থেকে বাছাই')}</span>
          {spotlightProducts[0] && (
            <button
              type="button"
              className="marketplace-hero__feature group"
              onClick={() => navigateToProduct(spotlightProducts[0].slug)}
              aria-label={`${t('View product', 'পণ্য দেখুন')}: ${language === 'bn' ? spotlightProducts[0].name_bn || spotlightProducts[0].name : spotlightProducts[0].name}`}
            >
              <img src={spotlightProducts[0].image} alt="" loading="eager" />
              <span className="marketplace-hero__product-copy">
                <span className="block text-[11px] font-semibold text-white/80">{spotlightProducts[0].seller_name}</span>
                <span className="mt-1 block line-clamp-2 text-lg font-extrabold leading-snug">
                  {language === 'bn' ? spotlightProducts[0].name_bn || spotlightProducts[0].name : spotlightProducts[0].name}
                </span>
                <span className="mt-1 block text-sm font-bold text-amber-200">
                  {formatPrice(spotlightProducts[0].discount_price ?? spotlightProducts[0].price)}
                </span>
              </span>
            </button>
          )}
          {spotlightProducts.slice(1, 3).map((product) => (
            <button
              type="button"
              key={product.id}
              className="marketplace-hero__tile group"
              onClick={() => navigateToProduct(product.slug)}
              aria-label={`${t('View product', 'পণ্য দেখুন')}: ${language === 'bn' ? product.name_bn || product.name : product.name}`}
            >
              <img src={product.image} alt="" loading="lazy" />
              <span className="marketplace-hero__product-copy">
                <span className="block line-clamp-2 text-xs font-bold leading-snug">
                  {language === 'bn' ? product.name_bn || product.name : product.name}
                </span>
                <span className="mt-1 block text-xs font-bold text-amber-200">
                  {formatPrice(product.discount_price ?? product.price)}
                </span>
              </span>
            </button>
          ))}
        </div>
      </section>

      {!isMarketplaceCatalogLoading && !marketplaceCatalogError && products.length === 0 && (
        <section
          className="flex items-start gap-3 rounded-2xl border border-primary/20 bg-primary-light/70 p-4 text-navy dark:border-sky-400/30 dark:bg-[#102947] dark:text-white sm:items-center sm:p-5"
          role="status"
        >
          <ShoppingBag className="mt-0.5 h-5 w-5 shrink-0 text-primary dark:text-sky-300 sm:mt-0" />
          <div>
            <h2 className="text-sm font-extrabold sm:text-base">
              {t('No products are currently listed', 'এখনো কোনো পণ্য তালিকাভুক্ত নেই')}
            </h2>
            <p className="mt-1 text-xs text-navy/75 dark:text-slate-300 sm:text-sm">
              {t(
                'This is the live catalog. Approved seller listings will appear here when available.',
                'এটি লাইভ ক্যাটালগ। অনুমোদিত বিক্রেতার পণ্য পাওয়া গেলে এখানে দেখা যাবে।',
              )}
            </p>
          </div>
        </section>
      )}

      {/* Category Navigation Bar & Quick Browse Grid */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-light text-primary text-xs font-bold mb-1.5">
              <Grid className="w-3.5 h-3.5" />
              <span>{t('CATEGORY DIRECTORY', 'হাট ক্যাটাগরি ডিরেক্টরি')}</span>
            </div>
            <h2 className="text-xl sm:text-3xl font-black text-ink">
              {t('Browse Marketplace by Category', 'ক্যাটাগরি অনুযায়ী কেনাকাটা করুন')}
            </h2>
            <p className="text-xs sm:text-sm text-muted mt-0.5">
              {t('Explore authentic Bangladeshi fresh food, electronics, fashion, and daily staples', 'খামারের খাঁটি খাবার, ইলেকট্রনিক্স, ঐতিহ্যবাহী ফ্যাশন ও নিত্যপণ্য')}
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              onClick={() => setCurrentView('catalog')}
              className="neu-button px-4 py-2 rounded-xl bg-white border border-slate-200 text-xs font-bold text-ink hover:text-primary flex items-center gap-1.5 shadow-xs"
            >
              <span>{t('Explore Full Catalog', 'সব পণ্য দেখুন')}</span>
              <ChevronRight className="w-4 h-4 text-primary" />
            </button>
          </div>
        </div>

        {/* Category Navigation Bar (Type Pills) */}
        <div className="bg-white rounded-2xl p-2.5 border border-slate-200/80 shadow-xs flex items-center gap-2 overflow-x-auto scrollbar-none">
          {categoryTypes.map((type) => {
            const Icon = type.icon;
            const isSelected = selectedCategoryType === type.id;
            return (
              <button
                key={type.id}
                onClick={() => setSelectedCategoryType(type.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition-all shrink-0 ${
                  isSelected
                    ? 'bg-primary text-white shadow-md shadow-primary/20 scale-102'
                    : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-ink'
                }`}
              >
                <Icon className={`w-4 h-4 ${isSelected ? 'text-white' : type.color}`} />
                <span>{language === 'bn' ? type.label_bn : type.label}</span>
                {type.id === 'fresh-food' && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${isSelected ? 'bg-white/20 text-white' : 'bg-primary-light text-navy'}`}>
                    Hot
                  </span>
                )}
                {type.id === 'electronics' && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${isSelected ? 'bg-white/20 text-white' : 'bg-blue-100 text-blue-800'}`}>
                    New
                  </span>
                )}
                {type.id === 'fashion' && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${isSelected ? 'bg-white/20 text-white' : 'bg-purple-100 text-purple-800'}`}>
                    Deshi
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Category Cards Grid with Icons and Rich Visuals */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3.5 sm:gap-5">
          {filteredCategories.map((cat) => {
            const CategoryIcon = getCategoryIcon(cat.slug);
            const categoryItemCount = products.filter(p => p.category_slug === cat.slug && p.is_available).length;

            return (
              <div
                key={cat.id}
                role="link"
                tabIndex={0}
                aria-label={`${t('Browse category', 'ক্যাটাগরি দেখুন')}: ${language === 'bn' ? cat.name_bn : cat.name}`}
                onClick={() => navigateToCategory(cat.slug)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') navigateToCategory(cat.slug);
                }}
                className="group relative overflow-hidden rounded-2xl bg-white border border-slate-200/90 p-3.5 sm:p-4 shadow-card hover:shadow-elevated transition-all duration-300 hover:-translate-y-1.5 cursor-pointer flex flex-col justify-between"
              >
                <div>
                  {/* Category Image with Icon Badge Overlay */}
                  <div className="relative aspect-4/3 w-full rounded-xl overflow-hidden mb-3 bg-slate-100">
                    <img
                      src={cat.image}
                      alt={cat.name}
                      className="w-full h-full object-cover group-hover:scale-108 transition-transform duration-500"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900/60 via-transparent to-transparent opacity-80 group-hover:opacity-60 transition-opacity" />

                    {/* Floating Thematic Category Icon */}
                    <div className="absolute top-2.5 left-2.5 p-2 rounded-xl bg-white/95 backdrop-blur-md shadow-md text-primary group-hover:scale-110 transition-transform">
                      <CategoryIcon className="w-4 h-4 text-primary" />
                    </div>

                    {/* Item count chip */}
                    <div className="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded-md bg-slate-950/80 backdrop-blur-xs text-white text-[10px] font-bold flex items-center gap-1">
                      <Tag className="w-3 h-3 text-amber-400" />
                      <span>{categoryItemCount} {t('products', 'টি পণ্য')}</span>
                    </div>
                  </div>

                  {/* Title & Description */}
                  <h3 className="font-extrabold text-sm sm:text-base text-ink group-hover:text-primary transition-colors flex items-center justify-between">
                    <span>{language === 'bn' ? cat.name_bn : cat.name}</span>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
                  </h3>

                  <p className="text-xs text-muted line-clamp-2 mt-1 leading-relaxed">
                    {cat.description}
                  </p>
                </div>

                {/* Card Action Footer */}
                <div className="mt-3.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] font-bold text-primary">
                  <span className="flex items-center gap-0.5 group-hover:underline">
                    {t('Explore category', 'ক্যাটাগরি দেখুন')} →
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Curated product shelf */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-md text-xs font-black bg-slate-900 text-white">
                NexHaat's <span className="text-amber-400">Choice</span>
              </span>
              <span className="text-xs text-muted font-semibold">{t('Selected from the current catalog', 'বর্তমান ক্যাটালগ থেকে বাছাই')}</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-ink">
              {t('A few good finds', 'বাছাই করা কিছু পণ্য')}
            </h2>
          </div>
          <button
            onClick={() => setCurrentView('catalog')}
            className="text-xs sm:text-sm font-bold text-primary hover:text-primary-hover flex items-center gap-1"
          >
            <span>{t('View All', 'সব দেখুন')}</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          {nexhaatChoiceProducts.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </section>

      {/* Current catalog discounts */}
      <section className="rounded-3xl bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-rose-500/10 border border-amber-300/60 p-5 sm:p-8 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/20 text-accent font-bold text-xs uppercase tracking-wider">
              <Tag className="w-3.5 h-3.5 text-amber-700" />
              <span className="text-amber-800">{t('Price drops', 'দাম কমেছে')}</span>
            </div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl sm:text-3xl font-black text-ink">
                {t('Featured Deals', 'ফিচার্ড ডিলসমূহ')}
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-slate-600">
              {t('See products currently listed with a discounted price.', 'বর্তমানে ছাড়ের দামে থাকা পণ্যগুলো দেখুন।')}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Carousel Controls */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => scrollDeals('left')}
                disabled={dealProducts.length === 0}
                className="neu-button p-2.5 rounded-xl bg-white border border-slate-200 text-slate-700 hover:text-primary hover:bg-slate-50 shadow-xs transition-colors"
                title="Scroll Left"
                aria-label="Scroll Deals Left"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => scrollDeals('right')}
                disabled={dealProducts.length === 0}
                className="neu-button p-2.5 rounded-xl bg-white border border-slate-200 text-slate-700 hover:text-primary hover:bg-slate-50 shadow-xs transition-colors"
                title="Scroll Right"
                aria-label="Scroll Deals Right"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setCurrentView('deals')}
                className="neu-button px-3.5 py-2.5 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-xs flex items-center gap-1 transition-colors"
              >
                <span>{t('All Deals', 'সব ডিল')}</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Horizontal Scrollable Deals List */}
        <div
          ref={dealsScrollRef}
          className="flex overflow-x-auto gap-4 pb-4 pt-1 scroll-smooth snap-x snap-mandatory scrollbar-thin"
        >
          {dealProducts.map((product) => {
            const discountPercent = product.discount_price 
              ? Math.round(((product.price - product.discount_price) / product.price) * 100) 
              : 0;

            return (
              <div
                key={product.id}
                className="group w-[280px] sm:w-[300px] shrink-0 snap-start bg-white rounded-2xl border border-slate-200/90 p-4 shadow-card hover:shadow-elevated transition-all duration-300 hover:-translate-y-1 flex flex-col justify-between"
              >
                <div>
                  {/* Image & Discount Badge */}
                  <button
                    type="button"
                    className="relative mb-3 aspect-4/3 w-full overflow-hidden rounded-xl bg-slate-100 text-left"
                    onClick={() => navigateToProduct(product.slug)}
                    aria-label={`${t('View product', 'পণ্য দেখুন')}: ${language === 'bn' ? product.name_bn || product.name : product.name}`}
                  >
                    <img
                      src={product.image}
                      alt=""
                      className="w-full h-full object-cover group-hover:scale-106 transition-transform duration-500"
                    />
                    
                    {/* Discount Pill */}
                    <div className="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-lg bg-rose-600 text-white text-xs font-black shadow-md flex items-center gap-1">
                      <Flame className="w-3.5 h-3.5 fill-current" />
                      <span>{discountPercent}% {t('off', 'ছাড়')}</span>
                    </div>
                  </button>

                  {/* Title & Seller */}
                  <p className="text-[11px] font-semibold text-slate-500 truncate mb-0.5">
                    {product.seller_name}
                  </p>
                  <h3 
                    onClick={() => navigateToProduct(product.slug)}
                    className="font-bold text-sm text-ink line-clamp-2 hover:text-primary transition-colors cursor-pointer leading-snug"
                  >
                    {language === 'bn' ? product.name_bn || product.name : product.name}
                  </h3>

                  {/* Rating & Stock */}
                  {product.review_count !== undefined && product.review_count > 0 && product.rating !== undefined && (
                  <div className="flex items-center gap-2 mt-2 text-xs">
                    <div className="flex items-center text-amber-500 font-bold">
                      <span>★</span>
                      <span className="ml-1 text-ink">{product.rating}</span>
                    </div>
                    <span className="text-slate-300">•</span>
                    <span className="text-muted text-[11px]">
                      {product.review_count} {t('ratings', 'মতামত')}
                    </span>
                  </div>
                  )}

                  {/* Pricing */}
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-lg font-black text-rose-600">
                      {formatPrice(product.discount_price ?? product.price)}
                    </span>
                    {product.discount_price && (
                      <span className="text-xs text-slate-400 line-through">
                        {formatPrice(product.price)}
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-[11px] font-medium text-muted">
                    {product.stock_quantity} {t('in stock', 'টি মজুদ')}
                  </p>
                </div>

                {/* Add to Cart button */}
                <button
                  type="button"
                  onClick={() => addToCart(product)}
                  className="neu-button mt-4 w-full py-2.5 px-3 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-xs flex items-center justify-center gap-2 transition-colors"
                >
                  <ShoppingBag className="w-3.5 h-3.5" />
                  <span>{t('Add to cart', 'কার্টে যোগ করুন')}</span>
                </button>
              </div>
            );
          })}
          {dealProducts.length === 0 && (
            <p className="w-full rounded-2xl border border-dashed border-amber-300 bg-white/70 p-6 text-center text-sm text-muted">
              {t('No discounted products are available in this catalog right now.', 'এই ক্যাটালগে এখন ছাড়ের পণ্য নেই।')}
            </p>
          )}
        </div>
      </section>

      {/* Amazon-style Recently Viewed Browsing History */}
      {recentlyViewed.length > 0 && (
        <section className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              <h3 className="font-bold text-base text-ink">
                {t('Your Recently Viewed Items', 'আপনার সম্প্রতি দেখা পণ্যসমূহ')}
              </h3>
            </div>
            <button
              onClick={() => setCurrentView('catalog')}
              className="text-xs font-semibold text-primary hover:underline"
            >
              {t('View Recommendations', 'আরও সুপারিশ দেখুন')}
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
            {recentlyViewed.slice(0, 4).map(item => (
              <ProductCard key={`recent-${item.id}`} product={item} />
            ))}
          </div>
        </section>
      )}

      {featuredSellers.length > 0 && (
        <section className="rounded-3xl border border-border bg-white p-6 shadow-card sm:p-8">
          <div className="mb-6">
            <div className="mb-1.5 inline-flex items-center gap-1.5 rounded-full bg-primary-light px-3 py-1 text-xs font-bold text-primary">
              <Store className="h-3.5 w-3.5" />
              <span>{t('SELLER DIRECTORY', 'বিক্রেতার তালিকা')}</span>
            </div>
            <h2 className="text-xl font-black text-ink sm:text-2xl">
              {t('Browse products by seller', 'বিক্রেতা অনুযায়ী পণ্য দেখুন')}
            </h2>
            <p className="text-xs text-muted sm:text-sm">
              {t('Seller names and item counts come from the catalog currently shown.', 'বিক্রেতার নাম ও পণ্যের সংখ্যা বর্তমান ক্যাটালগ থেকে নেওয়া।')}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {featuredSellers.map((sellerName) => {
              const sellerProducts = products.filter((product) => product.is_available && product.seller_name === sellerName);
              const sampleProduct = sellerProducts[0];
              return (
                <button
                  type="button"
                  key={sellerName}
                  onClick={() => {
                    setSearchQuery(sellerName);
                    setCurrentView('catalog');
                  }}
                  className="group flex min-w-0 items-center gap-3 rounded-2xl border border-border bg-surface-raised p-3 text-left transition-all hover:-translate-y-0.5 hover:border-primary/35 hover:shadow-soft"
                >
                  {sampleProduct && <img src={sampleProduct.image} alt="" className="h-14 w-14 shrink-0 rounded-xl object-cover" loading="lazy" />}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-bold text-ink">{sellerName}</span>
                    <span className="mt-1 block text-xs text-muted">
                      {sellerProducts.length} {t('catalog items', 'টি ক্যাটালগ পণ্য')}
                    </span>
                    <span className="mt-2 block text-xs font-bold text-primary group-hover:underline">
                      {t('Browse products', 'পণ্য দেখুন')} →
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
};
