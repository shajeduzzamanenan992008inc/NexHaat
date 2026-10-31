import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import { 
  Filter, SlidersHorizontal, ArrowUpDown, X, Check, 
  RotateCcw, Sparkles, ShoppingBag 
} from 'lucide-react';

export const CatalogPage: React.FC = () => {
  const { 
    products, 
    categories, 
    activeCategorySlug, 
    setActiveCategorySlug, 
    searchQuery, 
    setSearchQuery,
    t, 
    language 
  } = useApp();

  // Filter States
  const [minPrice, setMinPrice] = useState<number | ''>('');
  const [maxPrice, setMaxPrice] = useState<number | ''>('');
  const [minRating, setMinRating] = useState<number>(0);
  const [inStockOnly, setInStockOnly] = useState<boolean>(false);
  const [discountOnly, setDiscountOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<'relevance' | 'price-asc' | 'price-desc' | 'rating'>('relevance');
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState<boolean>(false);

  // Active category object
  const currentCategory = categories.find(c => c.slug === activeCategorySlug);

  // Filter & Sort Logic
  const filteredProducts = useMemo(() => {
    return products.filter(product => {
      // Category filter
      if (activeCategorySlug && product.category_slug !== activeCategorySlug) {
        return false;
      }

      // Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchesName = product.name.toLowerCase().includes(query);
        const matchesBnName = product.name_bn?.includes(query);
        const matchesBrand = product.brand_name?.toLowerCase().includes(query);
        const matchesSeller = product.seller_name.toLowerCase().includes(query);
        const matchesCategory = product.category_slug.toLowerCase().includes(query);
        const matchesDesc = product.description.toLowerCase().includes(query);
        if (!matchesName && !matchesBnName && !matchesBrand && !matchesSeller && !matchesCategory && !matchesDesc) {
          return false;
        }
      }

      // Price filter
      const effectivePrice = product.discount_price ?? product.price;
      if (minPrice !== '' && effectivePrice < Number(minPrice)) return false;
      if (maxPrice !== '' && effectivePrice > Number(maxPrice)) return false;

      // Rating filter
      if (minRating > 0 && product.rating < minRating) return false;

      // In-stock filter
      if (inStockOnly && product.stock_quantity <= 0) return false;

      // Discount only filter
      if (discountOnly && !product.discount_price) return false;

      return true;
    }).sort((a, b) => {
      const priceA = a.discount_price ?? a.price;
      const priceB = b.discount_price ?? b.price;

      if (sortBy === 'price-asc') return priceA - priceB;
      if (sortBy === 'price-desc') return priceB - priceA;
      if (sortBy === 'rating') return b.rating - a.rating;
      return 0; // relevance / default
    });
  }, [products, activeCategorySlug, searchQuery, minPrice, maxPrice, minRating, inStockOnly, discountOnly, sortBy]);

  const resetFilters = () => {
    setActiveCategorySlug(null);
    setSearchQuery('');
    setMinPrice('');
    setMaxPrice('');
    setMinRating(0);
    setInStockOnly(false);
    setDiscountOnly(false);
    setSortBy('relevance');
  };

  const hasActiveFilters = 
    Boolean(activeCategorySlug) || 
    Boolean(searchQuery) || 
    minPrice !== '' || 
    maxPrice !== '' || 
    minRating > 0 || 
    inStockOnly || 
    discountOnly;

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-border shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-primary mb-1 uppercase tracking-wider">
            <ShoppingBag className="w-4 h-4" />
            <span>{t('NexHaat Marketplace Catalog', 'নেক্সহাট মার্কেটপ্লেস ক্যাটালগ')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-ink">
            {currentCategory 
              ? (language === 'bn' ? currentCategory.name_bn : currentCategory.name)
              : searchQuery 
                ? `${t('Search results for', 'অনুসন্ধানের ফলাফল:')} "${searchQuery}"`
                : t('All Marketplace Products', 'সকল পণ্য ও নিত্যবাজার')
            }
          </h1>
          <p className="text-xs sm:text-sm text-muted mt-1">
            {currentCategory?.description || t('Verified regional products with doorstep express delivery', 'যাচাইকৃত মানসম্মত পণ্য ও এক্সপ্রেস ডেলিভারি')}
          </p>
        </div>

        {/* Total found badge */}
        <div className="self-start sm:self-auto px-4 py-2 bg-primary-light text-primary font-bold text-xs rounded-xl">
          {filteredProducts.length} {t('products available', 'টি পণ্য পাওয়া গেছে')}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Mobile filter toggle */}
        <div className="lg:hidden flex items-center justify-between gap-3">
          <button
            onClick={() => setIsMobileFilterOpen(!isMobileFilterOpen)}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-white border border-border font-bold text-xs text-ink shadow-xs"
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>{t('Filters & Options', 'ফিল্টার ও অপশন')}</span>
            {hasActiveFilters && (
              <span className="w-2 h-2 rounded-full bg-primary" />
            )}
          </button>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="py-2.5 px-3 rounded-xl bg-white border border-border text-xs font-semibold text-ink"
          >
            <option value="relevance">{t('Sort: Featured', 'সাজান: সেরা')}</option>
            <option value="price-asc">{t('Price: Low to High', 'দাম: কম থেকে বেশি')}</option>
            <option value="price-desc">{t('Price: High to Low', 'দাম: বেশি থেকে কম')}</option>
            <option value="rating">{t('Highest Rated', 'সর্বোচ্চ রেটিং')}</option>
          </select>
        </div>

        {/* Sidebar Filters */}
        <aside
          className={`bg-white rounded-3xl border border-border p-5 shadow-card space-y-6 ${
            isMobileFilterOpen ? 'block' : 'hidden lg:block'
          }`}
        >
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="font-bold text-sm text-ink flex items-center gap-2">
              <Filter className="w-4 h-4 text-primary" />
              <span>{t('Filter Catalog', 'ফিল্টার করুন')}</span>
            </h3>

            {hasActiveFilters && (
              <button
                onClick={resetFilters}
                className="text-xs text-primary hover:text-primary-hover font-semibold flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                <span>{t('Reset', 'রিসেট')}</span>
              </button>
            )}
          </div>

          {/* Categories Filter */}
          <div>
            <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wider mb-2.5">
              {t('Categories', 'ক্যাটাগরি')}
            </h4>
            <div className="space-y-1">
              <button
                onClick={() => setActiveCategorySlug(null)}
                className={`w-full text-left px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${
                  activeCategorySlug === null
                    ? 'bg-primary text-white font-bold'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {t('All Categories', 'সকল ক্যাটাগরি')}
              </button>
              {categories.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategorySlug(cat.slug)}
                  className={`w-full text-left px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${
                    activeCategorySlug === cat.slug
                      ? 'bg-primary text-white font-bold'
                      : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {language === 'bn' ? cat.name_bn : cat.name}
                </button>
              ))}
            </div>
          </div>

          {/* Price Range Filter */}
          <div className="pt-4 border-t border-slate-100">
            <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wider mb-2.5">
              {t('Price Range (৳)', 'মূল্য সীমা (৳)')}
            </h4>
            <div className="flex items-center gap-2">
              <input
                type="number"
                placeholder={t('Min', 'সর্বনিম্ন')}
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-hidden focus:border-primary"
              />
              <span className="text-slate-400">-</span>
              <input
                type="number"
                placeholder={t('Max', 'সর্বোচ্চ')}
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value === '' ? '' : Number(e.target.value))}
                className="w-full px-2.5 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-hidden focus:border-primary"
              />
            </div>
          </div>

          {/* Minimum Rating */}
          <div className="pt-4 border-t border-slate-100">
            <h4 className="font-bold text-xs text-slate-700 uppercase tracking-wider mb-2.5">
              {t('Minimum Rating', 'নূন্যতম রেটিং')}
            </h4>
            <div className="space-y-1.5">
              {[4.8, 4.5, 4.0, 0].map((star) => (
                <label key={star} className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                  <input
                    type="radio"
                    name="minRating"
                    checked={minRating === star}
                    onChange={() => setMinRating(star)}
                    className="accent-primary"
                  />
                  <span>
                    {star === 0 ? t('All Ratings', 'সব রেটিং') : `★ ${star} ${t('and above', 'ও তার বেশি')}`}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Toggles: In Stock & Discounts */}
          <div className="pt-4 border-t border-slate-100 space-y-2.5">
            <label className="flex items-center gap-2.5 text-xs font-semibold text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={inStockOnly}
                onChange={(e) => setInStockOnly(e.target.checked)}
                className="w-4 h-4 rounded text-primary focus:ring-primary accent-primary"
              />
              <span>{t('In Stock Only', 'কেবল মজুদে আছে এমন')}</span>
            </label>

            <label className="flex items-center gap-2.5 text-xs font-semibold text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={discountOnly}
                onChange={(e) => setDiscountOnly(e.target.checked)}
                className="w-4 h-4 rounded text-primary focus:ring-primary accent-primary"
              />
              <span>{t('Discounted Deals Only', 'কেবল বিশেষ ছাড়যুক্ত')}</span>
            </label>
          </div>
        </aside>

        {/* Products Grid Area */}
        <main className="lg:col-span-3 space-y-4">
          {/* Top Sort & Active Filters Chips (Desktop) */}
          <div className="hidden lg:flex items-center justify-between bg-white p-3.5 rounded-2xl border border-border">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted font-medium">
                {t('Active Filters:', 'সক্রিয় ফিল্টার:')}
              </span>

              {activeCategorySlug && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-primary-light text-primary font-semibold">
                  <span>{currentCategory?.name}</span>
                  <button onClick={() => setActiveCategorySlug(null)}>
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}

              {searchQuery && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-amber-100 text-amber-800 font-semibold">
                  <span>"{searchQuery}"</span>
                  <button onClick={() => setSearchQuery('')}>
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}

              {discountOnly && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs bg-rose-100 text-danger font-semibold">
                  <span>{t('Discounts Only', 'ছাড়যুক্ত')}</span>
                  <button onClick={() => setDiscountOnly(false)}>
                    <X className="w-3 h-3" />
                  </button>
                </span>
              )}

              {!hasActiveFilters && (
                <span className="text-xs text-slate-400 italic">
                  {t('None (Showing all listings)', 'সকল পণ্য প্রদর্শিত হচ্ছে')}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-muted font-medium">{t('Sort by:', 'সাজান:')}</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="py-1.5 px-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-ink focus:outline-hidden focus:border-primary"
              >
                <option value="relevance">{t('Featured / Recommended', 'বাছাইকৃত সেরা')}</option>
                <option value="price-asc">{t('Price: Low to High', 'দাম: কম থেকে বেশি')}</option>
                <option value="price-desc">{t('Price: High to Low', 'দাম: বেশি থেকে কম')}</option>
                <option value="rating">{t('Highest Customer Rating', 'সর্বোচ্চ রেটিং')}</option>
              </select>
            </div>
          </div>

          {/* Product Cards */}
          {filteredProducts.length === 0 ? (
            <div className="bg-white rounded-3xl border border-border p-12 text-center shadow-card space-y-4">
              <div className="w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
                <ShoppingBag className="w-8 h-8" />
              </div>
              <div>
                <h3 className="font-bold text-ink text-lg">
                  {t('No matching products found', 'কোনো পণ্য পাওয়া যায়নি')}
                </h3>
                <p className="text-xs text-muted mt-1 max-w-md mx-auto">
                  {t(
                    'Try clearing some filters or searching for terms like "mango", "fish", "oil", or "rice".',
                    'ফিল্টারগুলো পরিষ্কার করুন অথবা "আম", "মাছ", "তেল", "চাল" লিখে অনুসন্ধান করুন।'
                  )}
                </p>
              </div>
              <button
                onClick={resetFilters}
                className="px-5 py-2.5 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-sm transition-colors"
              >
                {t('Reset All Filters', 'সকল ফিল্টার রিসেট করুন')}
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
              {filteredProducts.map(product => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
