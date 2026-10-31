import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { ProductCard } from '../components/ProductCard';
import { 
  Sparkles, Flame, Clock, ArrowRight, ShieldCheck, 
  Truck, Award, Store, ChevronRight, CheckCircle2, History 
} from 'lucide-react';

export const HomePage: React.FC = () => {
  const { 
    products, 
    categories, 
    recentlyViewed, 
    navigateToCategory, 
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

  const dealProducts = products.filter(p => p.discount_price && p.is_available).slice(0, 4);
  const nexhaatChoiceProducts = products.filter(p => p.is_nexhaat_choice && p.is_available).slice(0, 4);
  const featuredProducts = products.filter(p => p.is_featured && p.is_available).slice(0, 8);

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

      {/* Categories Grid */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl sm:text-2xl font-black text-ink">
              {t('Popular Marketplace Categories', 'জনপ্রিয় হাট ক্যাটাগরি')}
            </h2>
            <p className="text-xs sm:text-sm text-muted mt-0.5">
              {t('Fresh essentials hand-picked by local specialists', 'বিশেষজ্ঞদের বাছাইকৃত তাজা খাদ্য ও নিত্যপণ্য')}
            </p>
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
          {categories.map((cat) => (
            <div
              key={cat.id}
              onClick={() => navigateToCategory(cat.slug)}
              className="group relative overflow-hidden rounded-2xl bg-white border border-border p-4 shadow-card hover:shadow-elevated transition-all duration-300 hover:-translate-y-1 cursor-pointer flex flex-col justify-between"
            >
              <div className="aspect-video w-full rounded-xl overflow-hidden mb-3 bg-slate-100">
                <img
                  src={cat.image}
                  alt={cat.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
              </div>
              <div>
                <h3 className="font-bold text-sm sm:text-base text-ink group-hover:text-primary transition-colors">
                  {language === 'bn' ? cat.name_bn : cat.name}
                </h3>
                <p className="text-xs text-muted line-clamp-1 mt-0.5">
                  {cat.description}
                </p>
              </div>
            </div>
          ))}
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

      {/* Flash Deals Section */}
      <section className="rounded-3xl bg-amber-500/10 border border-amber-200/80 p-6 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-accent text-white rounded-2xl shadow-sm">
              <Flame className="w-6 h-6 animate-bounce" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl sm:text-2xl font-black text-ink">
                  {t('Flash Deals & Haat Discounts', 'ফ্ল্যাশ ডিল ও মেগা ছাড়')}
                </h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-black bg-danger text-white uppercase">
                  Live
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-600">
                {t('Limited-time discounts directly supported by our verified vendors', 'সীমিত সময়ের জন্য বিশেষ মূল্যছাড়')}
              </p>
            </div>
          </div>

          {/* Countdown Clock */}
          <div className="flex items-center gap-1.5 self-start sm:self-auto bg-white px-4 py-2 rounded-2xl border border-amber-200 shadow-sm">
            <Clock className="w-4 h-4 text-accent mr-1" />
            <span className="text-xs font-semibold text-slate-500 mr-1">{t('Ends in:', 'বাকি:')}</span>
            <div className="flex items-center gap-1 font-mono text-sm font-extrabold text-ink">
              <span className="p-1 rounded bg-slate-100 min-w-[26px] text-center">
                {String(timeLeft.hours).padStart(2, '0')}
              </span>
              <span>:</span>
              <span className="p-1 rounded bg-slate-100 min-w-[26px] text-center">
                {String(timeLeft.minutes).padStart(2, '0')}
              </span>
              <span>:</span>
              <span className="p-1 rounded bg-slate-100 min-w-[26px] text-center">
                {String(timeLeft.seconds).padStart(2, '0')}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          {dealProducts.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
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
