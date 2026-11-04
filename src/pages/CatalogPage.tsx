import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import { fetchMarketplaceCatalogPage } from '../lib/marketplaceApi';
import { Product } from '../types';
import { 
  Filter, SlidersHorizontal, ArrowUpDown, X, Check, 
  RotateCcw, Sparkles, ShoppingBag 
} from 'lucide-react';

export const CatalogPage: React.FC = () => {
  const { 
    categories, 
    activeCategorySlug, 
    setActiveCategorySlug, 
    searchQuery, 
    setSearchQuery,
    t, 
    language,
    isMarketplaceCatalogLoading,
    isMarketplaceCatalogReady,
  } = useApp();

  // Filter and server-pagination state
  const [minPrice, setMinPrice] = useState<number | ''>('');
  const [maxPrice, setMaxPrice] = useState<number | ''>('');
  const [minRating, setMinRating] = useState<number>(0);
  const [inStockOnly, setInStockOnly] = useState<boolean>(false);
  const [discountOnly, setDiscountOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<'featured' | 'relevance' | 'price_asc' | 'price_desc' | 'newest'>('featured');
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState<boolean>(false);
  const [catalogProducts, setCatalogProducts] = useState<Product[]>([]);
  const [catalogTotal, setCatalogTotal] = useState(0);
  const [catalogPage, setCatalogPage] = useState(1);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogRetryKey, setCatalogRetryKey] = useState(0);
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState(searchQuery.trim());

  const currentCategory = categories.find(c => c.slug === activeCategorySlug);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedSearchQuery(searchQuery.trim()), 250);
    return () => window.clearTimeout(timeout);
  }, [searchQuery]);

  useEffect(() => {
    setCatalogPage(1);
  }, [activeCategorySlug, debouncedSearchQuery, minPrice, maxPrice, minRating, inStockOnly, discountOnly, sortBy]);

  useEffect(() => {
    if (!isMarketplaceCatalogReady) return undefined;

    const controller = new AbortController();
    const requestedPage = catalogPage;
    setCatalogLoading(true);
    setCatalogError(null);
    fetchMarketplaceCatalogPage({
      page: requestedPage,
      limit: 24,
      query: debouncedSearchQuery,
      categorySlug: activeCategorySlug,
      minPrice: minPrice === '' ? undefined : minPrice,
      maxPrice: maxPrice === '' ? undefined : maxPrice,
      minRating: minRating || undefined,
      inStockOnly,
      discountOnly,
      sort: sortBy,
    }, categories, controller.signal)
      .then(({ products: results, total }) => {
        setCatalogProducts(current => requestedPage === 1 ? results : [...current, ...results]);
        setCatalogTotal(total);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setCatalogError(error instanceof Error ? error.message : 'Marketplace catalog is unavailable.');
        if (requestedPage === 1) {
          setCatalogProducts([]);
          setCatalogTotal(0);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setCatalogLoading(false);
      });

    return () => controller.abort();
  }, [
    isMarketplaceCatalogReady,
    catalogPage,
    categories,
    activeCategorySlug,
    debouncedSearchQuery,
    minPrice,
    maxPrice,
    minRating,
    inStockOnly,
    discountOnly,
    sortBy,
    catalogRetryKey,
  ]);

  const resetFilters = () => {
    setActiveCategorySlug(null);
    setSearchQuery('');
    setMinPrice('');
    setMaxPrice('');
    setMinRating(0);
    setInStockOnly(false);
    setDiscountOnly(false);
    setSortBy('featured');
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
    <div className="marketplace-catalog space-y-6 pb-12">
    {(isMarketplaceCatalogLoading || !isMarketplaceCatalogReady || catalogLoading) && (
      <div className="rounded-xl border border-primary/20 bg-primary-light px-4 py-2 text-xs font-semibold text-primary" role="status">
        {t('Loading the live marketplace catalog…', 'লাইভ মার্কেটপ্লেস ক্যাটালগ লোড হচ্ছে…')}
      </div>
    )}
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
            {currentCategory?.description || t('Browse the products currently available in the catalog.', 'ক্যাটালগে বর্তমানে থাকা পণ্যগুলো দেখুন।')}
          </p>
        </div>

        {/* Total found badge */}
        <div className="self-start sm:self-auto px-4 py-2 bg-primary-light text-primary font-bold text-xs rounded-xl">
          {catalogTotal} {t('products available', 'টি পণ্য পাওয়া গেছে')}
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
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="py-2.5 px-3 rounded-xl bg-white border border-border text-xs font-semibold text-ink"
          >
            <option value="featured">{t('Sort: Featured', 'সাজান: সেরা')}</option>
            <option value="relevance">{t('Sort: Relevance', 'সাজান: প্রাসঙ্গিকতা')}</option>
            <option value="newest">{t('Newest first', 'নতুন পণ্য আগে')}</option>
            <option value="price_asc">{t('Price: Low to High', 'দাম: কম থেকে বেশি')}</option>
            <option value="price_desc">{t('Price: High to Low', 'দাম: বেশি থেকে কম')}</option>
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
              {[5, 4, 3, 0].map((star) => (
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
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="py-1.5 px-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-ink focus:outline-hidden focus:border-primary"
              >
                <option value="featured">{t('Featured listings', 'বাছাইকৃত সেরা')}</option>
                <option value="relevance">{t('Most relevant', 'সবচেয়ে প্রাসঙ্গিক')}</option>
                <option value="newest">{t('Newest first', 'নতুন পণ্য আগে')}</option>
                <option value="price_asc">{t('Price: Low to High', 'দাম: কম থেকে বেশি')}</option>
                <option value="price_desc">{t('Price: High to Low', 'দাম: বেশি থেকে কম')}</option>
              </select>
            </div>
          </div>

          {/* Product Cards */}
          {catalogError ? (
            <div className="rounded-3xl border border-danger/20 bg-red-50 p-8 text-center text-sm text-danger space-y-3" role="alert">
              {t('Live product results could not be loaded. Please try again shortly.', 'লাইভ পণ্যের ফলাফল লোড করা যায়নি। কিছুক্ষণ পর আবার চেষ্টা করুন।')}
              <button
                type="button"
                onClick={() => setCatalogRetryKey((key) => key + 1)}
                disabled={catalogLoading}
                className="rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-white transition-colors hover:bg-primary-hover disabled:cursor-wait disabled:opacity-60"
              >
                {catalogLoading ? t('Retrying…', 'আবার চেষ্টা হচ্ছে…') : t('Retry', 'আবার চেষ্টা করুন')}
              </button>
            </div>
          ) : catalogProducts.length === 0 && (catalogLoading || !isMarketplaceCatalogReady) ? (
            <div className="rounded-3xl border border-primary/20 bg-white p-12 text-center text-sm font-semibold text-primary" role="status">
              {t('Loading products from the live catalog…', 'লাইভ ক্যাটালগ থেকে পণ্য লোড হচ্ছে…')}
            </div>
          ) : catalogProducts.length === 0 ? (
            <div className="bg-white rounded-3xl border border-border p-12 text-center shadow-card space-y-4">
              <div className="w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
                <ShoppingBag className="w-8 h-8" />
              </div>
              <div>
                <h3 className="font-bold text-ink text-lg">
                  {catalogTotal === 0 && !hasActiveFilters
                    ? t('No published products are available yet', 'এখনও কোনো প্রকাশিত পণ্য নেই')
                    : t('No matching products found', 'কোনো পণ্য পাওয়া যায়নি')}
                </h3>
                <p className="text-xs text-muted mt-1 max-w-md mx-auto">
                  {catalogTotal === 0 && !hasActiveFilters
                    ? t('Approved seller listings will appear here when they become available.', 'অনুমোদিত বিক্রেতার পণ্য যুক্ত হলে এখানে দেখা যাবে।')
                    : t('Try changing your search or filters, or reset them to see all available listings.', 'অনুসন্ধান বা ফিল্টার পরিবর্তন করুন, অথবা সব পণ্য দেখতে রিসেট করুন।')}
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
              {catalogProducts.map(product => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
          {!catalogError && catalogProducts.length > 0 && catalogProducts.length < catalogTotal && (
            <div className="flex justify-center pt-2">
              <button
                type="button"
                onClick={() => setCatalogPage(current => current + 1)}
                disabled={catalogLoading}
                className="rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-primary-hover disabled:cursor-wait disabled:opacity-60"
              >
                {catalogLoading ? t('Loading…', 'লোড হচ্ছে…') : t('Load more products', 'আরও পণ্য দেখুন')}
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
