import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import { 
  Sparkles, Flame, Clock, ArrowRight, ShieldCheck, 
  Truck, Award, Store, ChevronRight, ChevronLeft, CheckCircle2, History,
  Apple, Fish, Smartphone, Shirt, Wheat, Egg, Cookie, Grid, Tag, Zap, ShoppingBag
} from 'lucide-react';

export const HomePage: React.FC = () => {
  const { 
    products, 
    categories, 
    recentlyViewed, 
    navigateToCategory, 
    navigateToProduct,
    addToCart,
    setCurrentView, 
    isPrimeMember, 
    setIsPrimeModalOpen, 
    t, 
    formatPrice, 
    language 
  } = useApp();

  // Flash deals countdown timer
  const [timeLeft, setTimeLeft] = useState({ hours: 7, minutes: 24, seconds: 18 });

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev.seconds > 0) return { ...prev, seconds: prev.seconds - 1 };
        if (prev.minutes > 0) return { ...prev, minutes: 59, seconds: 59 };
        if (prev.hours > 0) return { ...prev, hours: prev.hours - 1, minutes: 59, seconds: 59 };
        return { hours: 12, minutes: 0, seconds: 0 };
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const dealProducts = products.filter(p => p.discount_price && p.is_available);
  const nexhaatChoiceProducts = products.filter(p => p.is_nexhaat_choice && p.is_available).slice(0, 4);
  const featuredProducts = products.filter(p => p.is_featured && p.is_available).slice(0, 8);

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
    { id: 'fresh-food', label: 'Fresh Food', label_bn: 'তাজা খাবার', icon: Apple, slugs: ['fruits-vegetables', 'meat-seafood'], color: 'text-emerald-600' },
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

  const sellers = [
    {
      id: 1,
      name: 'Dhaka Fresh & Agro Haat',
      specialty: 'Farm Fresh Fruits, Greens & Deshi Vegetables',
      location: 'Karwan Bazar, Dhaka',
      rating: 4.9,
      sales: '12,400+ orders',
      image: 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=400&q=80',
    },
    {
      id: 2,
      name: 'Padma River Fish Emporium',
      specialty: 'Authentic Wild-caught Hilsa & Sweetwater Fish',
      location: 'Mawa Ghat / Jatrabari, Dhaka',
      rating: 4.95,
      sales: '8,900+ orders',
      image: 'https://images.unsplash.com/photo-1534482421-64566f976cfa?auto=format&fit=crop&w=400&q=80',
    },
    {
      id: 3,
      name: 'Bogra Heritage Dairy',
      specialty: 'Original Shahi Misti Doi & Pure Artisanal Ghee',
      location: 'Bogra / Gulshan-2, Dhaka',
      rating: 4.98,
      sales: '6,200+ orders',
      image: 'https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=400&q=80',
    },
    {
      id: 4,
      name: 'Tangail Weavers Collective',
      specialty: '100-count Fine Handloom Cotton Sarees & Panjabis',
      location: 'Tangail / Dhanmondi, Dhaka',
      rating: 4.88,
      sales: '3,100+ orders',
      image: 'https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=400&q=80',
    },
  ];

  return (
    <div className="space-y-12 sm:space-y-16 pb-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-900 via-primary to-blue-800 text-white shadow-elevated p-6 sm:p-12">
        <div className="absolute top-0 right-0 w-96 h-96 bg-accent/20 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-blue-400/20 rounded-full blur-3xl -ml-20 -mb-20 pointer-events-none" />

        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/15 backdrop-blur-md text-amber-300 font-bold text-xs mb-4">
            <Sparkles className="w-4 h-4" />
            <span>{t('BANGLADESH HYPER-LOCAL MEGA HAAT', 'বাংলাদেশের সেরা হাইপার-লোকাল মেগা হাট')}</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight text-white mb-4">
            {t(
              'Farm-Fresh Food, River Ilish & Daily Haat at Your Doorstep',
              'খামারের তাজা খাবার, পদ্মার ইলিশ ও নিত্যপণ্য ঘরে বসেই'
            )}
          </h1>

          <p className="text-slate-200 text-sm sm:text-base leading-relaxed mb-8 max-w-xl">
            {t(
              'Order fresh Rajshahi mangoes, wild Padma fish, Dinajpur Chinigura rice, and authentic sweets directly from verified local merchants. Guaranteed 3-hour hyper-local delivery.',
              'রাজশাহীর মিষ্টি আম, মাওয়ার রূপালী ইলিশ, দিনাজপুরের চিনিগুঁড়া চাল আর ঐতিহ্যবাহী মিষ্টি সরাসরি সংগ্রহ করুন বিশ্বস্ত চাষী ও বিক্রেতাদের কাছ থেকে।'
            )}
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setCurrentView('catalog')}
              className="neu-button px-6 py-3.5 rounded-xl bg-accent text-slate-900 font-bold text-sm shadow-lg hover:bg-amber-400 flex items-center gap-2"
            >
              <span>{t('Explore Full Haat Catalog', 'সম্পূর্ণ হাট ব্রাউজ করুন')}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => setCurrentView('deals')}
              className="px-6 py-3.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-sm backdrop-blur-md border border-white/20 transition-colors"
            >
              {t('Flash Deals (Up to 30% Off)', 'মেগা ফ্ল্যাশ ডিলসমূহ')}
            </button>
          </div>

          {/* Quick trust badges */}
          <div className="mt-8 pt-6 border-t border-white/10 grid grid-cols-3 gap-4 text-xs text-slate-200 font-medium">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{t('100% Halal Verified', '১০০% হালাল')}</span>
            </div>
            <div className="flex items-center gap-2">
              <Truck className="w-4 h-4 text-amber-300 shrink-0" />
              <span>{t('3-Hr Dhaka Express', '৩ ঘণ্টায় ডেলিভারি')}</span>
            </div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-300 shrink-0" />
              <span>{t('Cash On Delivery', 'ক্যাশ অন ডেলিভারি')}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Amazon Prime Strip Banner */}
      <section className="rounded-2xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 p-4 sm:p-5 text-slate-950 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-slate-950 text-amber-400 rounded-xl font-black italic text-base">
            prime
          </div>
          <div>
            <h3 className="font-extrabold text-sm sm:text-base leading-snug">
              {isPrimeMember 
                ? t('You are enjoying NexHaat Prime Free 3-Hour Delivery!', 'আপনি নেক্সহাট প্রাইমের ফ্রি ৩-ঘণ্টা এক্সপ্রেস সুবিধা উপভোগ করছেন!')
                : t('Join NexHaat Prime: Unlimited FREE 3-Hour Delivery & 5% Cashback', 'নেক্সহাট প্রাইমে যুক্ত হোন: আনলিমিটেড ফ্রি ডেলিভারি ও ৫% ক্যাশব্যাক')}
            </h3>
            <p className="text-xs text-slate-900/80">
              {t('Fastest delivery across all metropolitan areas of Dhaka & Chittagong', 'ঢাকা ও চট্টগ্রামের সমগ্র মেট্রোপলিটন এলাকায় দ্রুততম সেবা')}
            </p>
          </div>
        </div>

        <button
          onClick={() => setIsPrimeModalOpen(true)}
          className="neu-button px-5 py-2.5 rounded-xl bg-slate-950 text-white font-bold text-xs hover:bg-slate-900 shrink-0 shadow-md"
        >
          {isPrimeMember ? t('Manage Prime', 'প্রাইম ম্যানেজ') : t('Try Prime for ৳199/mo', 'প্রাইম শুরু করুন (৳১৯৯/মাস)')}
        </button>
      </section>

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
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-extrabold ${isSelected ? 'bg-white/20 text-white' : 'bg-emerald-100 text-emerald-800'}`}>
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
            const categoryItemCount = products.filter(p => p.category_slug === cat.slug).length;

            return (
              <div
                key={cat.id}
                onClick={() => navigateToCategory(cat.slug)}
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
                      <span>{categoryItemCount > 0 ? `${categoryItemCount}+ ${t('Products', 'পণ্য')}` : t('Available', 'উপলব্ধ')}</span>
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
                  <span className="text-slate-500 font-semibold text-[10px]">
                    {t('Direct from verified sellers', 'যাচাইকৃত বিক্রেতা')}
                  </span>
                  <span className="flex items-center gap-0.5 group-hover:underline">
                    {t('Browse', 'ব্রাউজ')} →
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* NexHaat's Choice & Best Sellers (Amazon-style Shelf) */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 rounded-md text-xs font-black bg-slate-900 text-white">
                NexHaat's <span className="text-amber-400">Choice</span>
              </span>
              <span className="text-xs text-muted font-semibold">• Highly rated & priced right</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-ink">
              {t('Top Rated & Certified Bestsellers', 'সেরা রেটিংপ্রাপ্ত পণ্য')}
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

      {/* Featured Deals Section with Countdown Timer and Horizontal Carousel */}
      <section className="rounded-3xl bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-rose-500/10 border border-amber-300/60 p-5 sm:p-8 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-accent/20 text-accent font-bold text-xs uppercase tracking-wider">
              <Zap className="w-3.5 h-3.5 fill-current animate-pulse text-amber-600" />
              <span className="text-amber-800">{t('Time-Sensitive Offers', 'সীমিত সময়ের মেগা অফার')}</span>
            </div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-xl sm:text-3xl font-black text-ink">
                {t('Featured Deals', 'ফিচার্ড ডিলসমূহ')}
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-black bg-rose-600 text-white uppercase tracking-wider animate-pulse">
                Live
              </span>
            </div>
            <p className="text-xs sm:text-sm text-slate-600">
              {t('Deep discounts on verified local produce and top sellers. Grab yours before time runs out!', 'যাচাইকৃত চাষী ও সেরা ভেন্ডরদের পণ্যে বিশেষ মূল্যছাড়। সময় শেষ হওয়ার আগেই লুফে নিন!')}
            </p>
          </div>

          {/* Countdown Clock and Carousel Navigation Controls */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Countdown Clock */}
            <div className="flex items-center gap-2 bg-white px-4 py-2.5 rounded-2xl border border-amber-200/90 shadow-xs">
              <Clock className="w-4 h-4 text-rose-500 animate-spin-slow" />
              <div className="text-left">
                <span className="text-[10px] font-bold text-slate-400 block -mb-0.5 uppercase tracking-wide">
                  {t('Deal Expires In', 'মেয়াদ বাকি')}
                </span>
                <div className="flex items-center gap-1 font-mono text-sm font-black text-ink">
                  <span className="px-1.5 py-0.5 rounded-md bg-slate-100 text-rose-600 min-w-[26px] text-center">
                    {String(timeLeft.hours).padStart(2, '0')}h
                  </span>
                  <span>:</span>
                  <span className="px-1.5 py-0.5 rounded-md bg-slate-100 text-rose-600 min-w-[26px] text-center">
                    {String(timeLeft.minutes).padStart(2, '0')}m
                  </span>
                  <span>:</span>
                  <span className="px-1.5 py-0.5 rounded-md bg-slate-100 text-rose-600 min-w-[26px] text-center">
                    {String(timeLeft.seconds).padStart(2, '0')}s
                  </span>
                </div>
              </div>
            </div>

            {/* Carousel Controls */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => scrollDeals('left')}
                className="neu-button p-2.5 rounded-xl bg-white border border-slate-200 text-slate-700 hover:text-primary hover:bg-slate-50 shadow-xs transition-colors"
                title="Scroll Left"
                aria-label="Scroll Deals Left"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => scrollDeals('right')}
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
            // Simulated claim percentage based on stock_quantity
            const claimPercent = Math.min(95, Math.max(45, (100 - (product.stock_quantity % 40) * 2)));

            return (
              <div
                key={product.id}
                className="group w-[280px] sm:w-[300px] shrink-0 snap-start bg-white rounded-2xl border border-slate-200/90 p-4 shadow-card hover:shadow-elevated transition-all duration-300 hover:-translate-y-1 flex flex-col justify-between"
              >
                <div>
                  {/* Image & Discount Badge */}
                  <div 
                    className="relative aspect-4/3 w-full rounded-xl overflow-hidden mb-3 bg-slate-100 cursor-pointer"
                    onClick={() => navigateToProduct(product.slug)}
                  >
                    <img
                      src={product.image}
                      alt={product.name}
                      className="w-full h-full object-cover group-hover:scale-106 transition-transform duration-500"
                    />
                    
                    {/* Discount Pill */}
                    <div className="absolute top-2.5 left-2.5 px-2.5 py-1 rounded-lg bg-rose-600 text-white text-xs font-black shadow-md flex items-center gap-1">
                      <Flame className="w-3.5 h-3.5 fill-current" />
                      <span>{discountPercent}% OFF</span>
                    </div>

                    {/* Fast Express Delivery Tag */}
                    <div className="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded-md bg-slate-900/85 backdrop-blur-xs text-amber-300 text-[10px] font-extrabold flex items-center gap-1">
                      <Truck className="w-3 h-3" />
                      <span>3-Hr Express</span>
                    </div>
                  </div>

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

                  {/* Deal Progress Meter */}
                  <div className="mt-3 space-y-1">
                    <div className="flex items-center justify-between text-[10px] font-bold text-slate-500">
                      <span>{claimPercent}% {t('Claimed', 'বিক্রি সম্পন্ন')}</span>
                      <span className="text-rose-600">{t('Only few left', 'সীমিত স্টক')}</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-amber-500 to-rose-600 rounded-full transition-all duration-500"
                        style={{ width: `${claimPercent}%` }}
                      />
                    </div>
                  </div>
                </div>

                {/* Add to Cart button */}
                <button
                  type="button"
                  onClick={() => addToCart(product)}
                  className="neu-button mt-4 w-full py-2.5 px-3 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-xs flex items-center justify-center gap-2 transition-colors"
                >
                  <ShoppingBag className="w-3.5 h-3.5" />
                  <span>{t('Claim Deal & Add', 'ডিল লুফে নিন')}</span>
                </button>
              </div>
            );
          })}
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

      {/* Spotlight on Local Verified Sellers */}
      <section className="rounded-3xl bg-white border border-border p-6 sm:p-8 shadow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 font-bold text-xs mb-1.5">
              <Award className="w-3.5 h-3.5" />
              <span>{t('VERIFIED VENDORS', 'যাচাইকৃত বিক্রেতা')}</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-ink">
              {t('Direct from Bangladesh’s Heritage Merchants', 'বাংলাদেশের ঐতিহ্যবাহী বিক্রেতাদের সরাসরি শপ')}
            </h2>
            <p className="text-xs sm:text-sm text-muted">
              {t('Shop directly from verified regional markets and farmers cooperatives', 'আঞ্চলিক বাজার ও খামারিদের কাছ থেকে সরাসরি কেনাকাটা করুন')}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {sellers.map((seller) => (
            <div
              key={seller.id}
              className="p-4 rounded-2xl bg-surface-raised border border-slate-100 hover:border-primary/40 hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div className="flex items-center gap-3 mb-3">
                <img
                  src={seller.image}
                  alt={seller.name}
                  className="w-12 h-12 rounded-xl object-cover border border-slate-200"
                />
                <div>
                  <h4 className="font-bold text-xs sm:text-sm text-ink">{seller.name}</h4>
                  <p className="text-[11px] text-muted">{seller.location}</p>
                </div>
              </div>
              <p className="text-xs text-slate-600 mb-3">{seller.specialty}</p>
              <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-xs font-semibold">
                <span className="text-amber-500">★ {seller.rating} rating</span>
                <span className="text-slate-500">{seller.sales}</span>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
