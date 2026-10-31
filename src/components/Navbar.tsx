import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { UserRole } from '../types';
import { 
  Search, ShoppingCart, Heart, Bell, Menu, X, ChevronDown, 
  User, Shield, Truck, Store, Phone, Sparkles, Tag, ArrowRight,
  Sun, Moon, Layers, Mic, Camera, Clock, TrendingUp, History, Trash2
} from 'lucide-react';
import { manageSearchHistory } from '../lib/amazonFeatures';

export const Navbar: React.FC = () => {
  const {
    currentView,
    setCurrentView,
    cartCount,
    cartSubtotal,
    setIsCartDrawerOpen,
    wishlistCount,
    unreadNotificationCount,
    comparedProductIds,
    setIsCompareModalOpen,
    isPrimeMember,
    setIsPrimeModalOpen,
    isDarkMode,
    toggleDarkMode,
    setIsAIAssistantOpen,
    language,
    setLanguage,
    t,
    formatPrice,
    currentUser,
    setUserRole,
    categories,
    products,
    navigateToProduct,
    navigateToCategory,
    searchQuery,
    setSearchQuery,
    setActiveCategorySlug,
    showToast,
    firebaseUser,
    loginWithGoogle,
    logoutFirebase,
    isFirebaseAuthLoading,
  } = useApp();

  const [isCategoryMenuOpen, setIsCategoryMenuOpen] = useState(false);
  const [isRoleMenuOpen, setIsRoleMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [isDepartmentMenuOpen, setIsDepartmentMenuOpen] = useState(false);

  // Search History from localStorage
  const [recentSearches, setRecentSearches] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem('nexhaat_recent_searches');
      return stored ? JSON.parse(stored) : ['Padma Ilish', 'Chinigura Rice', 'Cold-Pressed Mustard Oil'];
    } catch {
      return ['Padma Ilish', 'Chinigura Rice', 'Cold-Pressed Mustard Oil'];
    }
  });

  const trendingKeywords = [
    'Padma Ilish',
    'Chinigura Rice',
    'Cold-Pressed Mustard Oil',
    'Fazli Mango',
    'Sundarbans Honey',
    'Organic Ghee',
  ];

  const searchRef = useRef<HTMLDivElement>(null);

  // Close search suggestions and department menu on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsSearchFocused(false);
        setIsDepartmentMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const saveSearchQuery = (term: string) => {
    const updated = manageSearchHistory(recentSearches, term);
    setRecentSearches(updated);
    try {
      localStorage.setItem('nexhaat_recent_searches', JSON.stringify(updated));
    } catch (e) {
      // Storage unavailable or disabled
    }
  };

  const removeSearchItem = (term: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = recentSearches.filter(q => q.toLowerCase() !== term.toLowerCase());
    setRecentSearches(updated);
    try {
      localStorage.setItem('nexhaat_recent_searches', JSON.stringify(updated));
    } catch (e) {}
  };

  const clearAllSearchHistory = (e: React.MouseEvent) => {
    e.stopPropagation();
    setRecentSearches([]);
    try {
      localStorage.removeItem('nexhaat_recent_searches');
    } catch (e) {}
  };

  const executeSearch = (term: string) => {
    const trimmed = term.trim();
    if (trimmed) {
      saveSearchQuery(trimmed);
      setSearchQuery(trimmed);
      if (selectedDepartment !== 'all') {
        setActiveCategorySlug(selectedDepartment);
      }
      setIsSearchFocused(false);
      setIsDepartmentMenuOpen(false);
      setCurrentView('catalog');
    }
  };

  // Filter search suggestions with department filter
  const searchSuggestions = searchQuery.trim() === ''
    ? []
    : products.filter(p => {
        const matchesDept = selectedDepartment === 'all' || p.category_slug === selectedDepartment;
        const matchesQuery = 
          p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          p.name_bn?.includes(searchQuery) ||
          p.category_slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
          p.brand_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          p.seller_name.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesDept && matchesQuery;
      }).slice(0, 6);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(searchQuery);
  };

  const handleVoiceSearch = () => {
    setIsVoiceListening(true);
    showToast(t('Listening for voice search...', 'ভয়েস অনুসন্ধান চালু হয়েছে...'), 'info');
    setTimeout(() => {
      setIsVoiceListening(false);
      setSearchQuery('Padma Ilish');
      setIsSearchFocused(true);
      showToast(t('Heard: "Padma Ilish"', 'শনাক্ত হয়েছে: "Padma Ilish"'), 'success');
    }, 1800);
  };

  const handleImageSearch = () => {
    showToast(t('Analyzing image with Gemini Vision...', 'ছবি বিশ্লেষণ চলছে...'), 'info');
    setTimeout(() => {
      setSearchQuery('Mango');
      setCurrentView('catalog');
      showToast(t('Found matching fresh mangoes!', 'অনুরূপ তাজা আম পাওয়া গেছে!'), 'success');
    }, 1200);
  };

  const roles: { role: UserRole; label: string; label_bn: string; icon: React.ReactNode; color: string }[] = [
    { role: 'customer', label: 'Customer View', label_bn: 'ক্রেতা ভিউ', icon: <User className="w-4 h-4" />, color: 'text-primary' },
    { role: 'seller', label: 'Seller Portal', label_bn: 'বিক্রেতা পোর্টাল', icon: <Store className="w-4 h-4" />, color: 'text-amber-600' },
    { role: 'rider', label: 'Rider Portal', label_bn: 'রাইডার পোর্টাল', icon: <Truck className="w-4 h-4" />, color: 'text-emerald-600' },
    { role: 'admin', label: 'Admin Hub', label_bn: 'অ্যাডমিন হাব', icon: <Shield className="w-4 h-4" />, color: 'text-rose-600' },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-border dark:border-slate-800 shadow-xs transition-colors">
      {/* Top Utility Announcement Bar */}
      <div className="bg-slate-900 dark:bg-black text-slate-300 text-xs py-1.5 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Prime Membership Link */}
            <button
              onClick={() => setIsPrimeModalOpen(true)}
              className="inline-flex items-center gap-1.5 font-bold text-amber-300 hover:text-amber-200 transition-colors"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>
                {isPrimeMember 
                  ? t('NexHaat Prime Member (Active)', 'নেক্সহাট প্রাইম সক্রিয়')
                  : t('Join NexHaat Prime for FREE Express Delivery', 'প্রাইমে যোগ দিন: ফ্রি এক্সপ্রেস ডেলিভারি')}
              </span>
            </button>

            <span className="hidden md:flex items-center gap-1 text-slate-300">
              <Phone className="w-3 h-3 text-emerald-400" />
              <span>{t('Support:', 'সহায়তা:')} <strong className="text-white">+880 9612 000 000</strong></span>
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Dark Mode Toggle */}
            <button
              type="button"
              onClick={toggleDarkMode}
              className="p-1 rounded-md text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
              title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {isDarkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
            </button>

            {/* Language Switcher */}
            <div className="flex items-center bg-slate-800 rounded-md p-0.5 text-[11px] font-semibold border border-slate-700">
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`px-2 py-0.5 rounded transition-colors ${
                  language === 'en' ? 'bg-primary text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                ENG
              </button>
              <button
                type="button"
                onClick={() => setLanguage('bn')}
                className={`px-2 py-0.5 rounded transition-colors ${
                  language === 'bn' ? 'bg-primary text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                বাংলা
              </button>
            </div>

            {/* Role Switcher Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsRoleMenuOpen(!isRoleMenuOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 rounded-md border border-slate-700 text-white text-xs font-medium transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="capitalize">{currentUser.role}</span>
                <ChevronDown className="w-3 h-3 text-slate-400" />
              </button>

              {isRoleMenuOpen && (
                <div 
                  className="absolute right-0 mt-1.5 w-52 bg-white dark:bg-slate-800 rounded-xl shadow-elevated border border-slate-100 dark:border-slate-700 py-2 z-50 animate-fade-in"
                  onMouseLeave={() => setIsRoleMenuOpen(false)}
                >
                  <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-700">
                    {t('Switch Workspace', 'পোর্টাল পরিবর্তন করুন')}
                  </div>
                  {roles.map(r => (
                    <button
                      key={r.role}
                      type="button"
                      onClick={() => {
                        setUserRole(r.role);
                        setIsRoleMenuOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-left hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ${
                        currentUser.role === r.role ? 'bg-primary-light text-primary font-bold' : 'text-ink dark:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className={r.color}>{r.icon}</span>
                        <span>{language === 'bn' ? r.label_bn : r.label}</span>
                      </div>
                      {currentUser.role === r.role && (
                        <span className="text-[10px] font-bold text-primary">Active</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {/* Google Firebase Auth */}
            {firebaseUser ? (
              <div className="flex items-center gap-1.5 bg-slate-800 rounded-md px-2 py-1 border border-slate-700 text-xs text-white">
                {firebaseUser.photoURL ? (
                  <img src={firebaseUser.photoURL} alt="User" className="w-4 h-4 rounded-full" />
                ) : (
                  <span className="w-4 h-4 rounded-full bg-emerald-500 text-[10px] flex items-center justify-center font-bold">
                    {firebaseUser.displayName?.[0] || 'U'}
                  </span>
                )}
                <span className="max-w-[90px] truncate hidden sm:inline text-[11px]">
                  {firebaseUser.displayName || firebaseUser.email}
                </span>
                <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1 rounded font-semibold">Firestore</span>
                <button
                  type="button"
                  onClick={logoutFirebase}
                  className="text-[10px] text-slate-400 hover:text-white ml-1 underline"
                  title="Sign Out"
                >
                  Exit
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={loginWithGoogle}
                disabled={isFirebaseAuthLoading}
                className="flex items-center gap-1.5 px-2 py-1 bg-white hover:bg-slate-100 text-slate-900 rounded-md text-xs font-semibold shadow-xs transition-colors shrink-0"
                title="Sign in with Google via Firebase Auth"
              >
                <svg className="w-3.5 h-3.5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.15z"/>
                  <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"/>
                  <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.17 0 10.03 0 12s.45 3.83 1.25 5.42l4.03-3.15z"/>
                  <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
                </svg>
                <span className="hidden sm:inline">{t('Google Sign-In', 'গুগল সাইন ইন')}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3">
        <div className="flex items-center justify-between gap-3 sm:gap-6">
          {/* Brand Logo with animated circle */}
          <div 
            onClick={() => {
              setCurrentView('home');
              setActiveCategorySlug(null);
            }} 
            className="flex items-center gap-2.5 cursor-pointer shrink-0 select-none group"
          >
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-2xl bg-gradient-to-br from-primary to-primary-hover p-1.5 shadow-md flex items-center justify-center transition-transform group-hover:scale-105">
              <img src="/logo.svg" alt="NexHaat" className="w-full h-full object-contain" />
            </div>
            <div>
              <div className="flex items-center gap-1">
                <span className="text-xl sm:text-2xl font-black tracking-tight text-ink dark:text-white">
                  Nex<span className="text-primary">Haat</span>
                </span>
                <span className="text-[10px] font-extrabold px-1.5 py-0.5 rounded-full bg-accent-light text-accent">
                  BD
                </span>
                {isPrimeMember && (
                  <span className="text-[10px] font-black px-1.5 py-0.5 rounded-full bg-amber-400 text-slate-900 ml-1">
                    PRIME
                  </span>
                )}
              </div>
              <p className="text-[10px] font-semibold text-muted -mt-1 hidden sm:block">
                {t('Amazon-Grade Multi-Vendor Marketplace', 'আমাজন-মানের মাল্টি-ভেন্ডর মার্কেটপ্লেস')}
              </p>
            </div>
          </div>

          {/* Search bar with Amazon Department Selector, Search History, Voice & Image Search */}
          <div ref={searchRef} className="relative flex-1 max-w-2xl hidden md:block">
            <form onSubmit={handleSearchSubmit} className="relative flex items-center bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-inset focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all">
              {/* Amazon Department Selector */}
              <div className="relative shrink-0">
                <button
                  type="button"
                  onClick={() => setIsDepartmentMenuOpen(!isDepartmentMenuOpen)}
                  className="h-full px-3 py-2.5 bg-slate-100 dark:bg-slate-700/80 text-slate-700 dark:text-slate-200 border-r border-slate-200 dark:border-slate-700 rounded-l-2xl text-xs font-semibold flex items-center gap-1 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors whitespace-nowrap"
                  title="Filter by Department"
                >
                  <span className="max-w-[90px] truncate">
                    {selectedDepartment === 'all' 
                      ? t('All', 'সকল') 
                      : (categories.find(c => c.slug === selectedDepartment)?.name || selectedDepartment)}
                  </span>
                  <ChevronDown className="w-3 h-3 opacity-60" />
                </button>

                {isDepartmentMenuOpen && (
                  <div className="absolute left-0 top-full mt-1.5 w-52 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 py-1.5 z-50 animate-fade-in max-h-64 overflow-y-auto">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedDepartment('all');
                        setIsDepartmentMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs font-semibold ${
                        selectedDepartment === 'all'
                          ? 'bg-primary/10 text-primary font-bold'
                          : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700'
                      }`}
                    >
                      {t('All Departments', 'সকল ডিপার্টমেন্ট')}
                    </button>
                    {categories.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => {
                          setSelectedDepartment(c.slug);
                          setIsDepartmentMenuOpen(false);
                        }}
                        className={`w-full text-left px-3 py-1.5 text-xs truncate ${
                          selectedDepartment === c.slug
                            ? 'bg-primary/10 text-primary font-bold'
                            : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700'
                        }`}
                      >
                        {language === 'bn' ? c.name_bn : c.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="relative flex-1 flex items-center">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onFocus={() => setIsSearchFocused(true)}
                  placeholder={t(
                    'Search fresh fish, organic rice, cold-pressed oil, farm produce...',
                    'তাজা ইলিশ, সুগন্ধি চাল, সরিষার তেল, খামারের পণ্য খুঁজুন...'
                  )}
                  className="w-full pl-3 pr-28 py-2.5 bg-transparent text-sm focus:outline-hidden text-ink dark:text-white placeholder:text-slate-400"
                />
              </div>

              {/* Mic & Visual Search Icons inside search bar */}
              <div className="absolute right-20 flex items-center gap-1">
                <button
                  type="button"
                  onClick={handleVoiceSearch}
                  className={`p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-primary transition-colors ${
                    isVoiceListening ? 'text-danger animate-pulse' : ''
                  }`}
                  title="Voice Search"
                >
                  <Mic className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={handleImageSearch}
                  className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400 hover:text-primary transition-colors"
                  title="Search by Image"
                >
                  <Camera className="w-4 h-4" />
                </button>
              </div>

              <button
                type="submit"
                className="mr-1.5 px-4 py-1.5 bg-primary text-white text-xs font-bold rounded-xl hover:bg-primary-hover transition-colors shadow-sm flex items-center gap-1"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{t('Search', 'খুঁজুন')}</span>
              </button>
            </form>

            {/* Dropdown: Recent Search History & Trending or Live Matching Suggestions */}
            {isSearchFocused && (
              <div className="absolute left-0 right-0 top-full mt-2 bg-white dark:bg-slate-800 rounded-2xl shadow-elevated border border-slate-100 dark:border-slate-700 overflow-hidden z-50 animate-fade-in divide-y divide-slate-100 dark:divide-slate-700">
                {searchQuery.trim() === '' ? (
                  /* Amazon-style Recent Search History & Trending Suggestions */
                  <div className="p-3 space-y-3">
                    {recentSearches.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider px-1">
                          <span className="flex items-center gap-1.5">
                            <History className="w-3.5 h-3.5 text-primary" />
                            {t('Recent Searches', 'সাম্প্রতিক অনুসন্ধান')}
                          </span>
                          <button
                            type="button"
                            onClick={clearAllSearchHistory}
                            className="text-slate-400 hover:text-rose-500 font-semibold lowercase transition-colors"
                          >
                            {t('Clear all', 'সব মুছুন')}
                          </button>
                        </div>

                        <div className="space-y-0.5">
                          {recentSearches.map((term, idx) => (
                            <div
                              key={idx}
                              onClick={() => executeSearch(term)}
                              className="group flex items-center justify-between px-2.5 py-1.5 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700/60 cursor-pointer text-xs transition-colors"
                            >
                              <div className="flex items-center gap-2.5 text-slate-700 dark:text-slate-200">
                                <Clock className="w-3.5 h-3.5 text-slate-400 group-hover:text-primary transition-colors" />
                                <span className="font-medium group-hover:text-primary">{term}</span>
                              </div>
                              <button
                                type="button"
                                onClick={(e) => removeSearchItem(term, e)}
                                className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-500 rounded-md hover:bg-slate-200 dark:hover:bg-slate-600 transition-all"
                                title="Remove from history"
                              >
                                <X className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Trending searches */}
                    <div className="pt-2 border-t border-slate-100 dark:border-slate-700 space-y-2">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider px-1">
                        <TrendingUp className="w-3.5 h-3.5 text-amber-500" />
                        <span>{t('Trending on NexHaat', 'জনপ্রিয় অনুসন্ধান')}</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {trendingKeywords.map((kw, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => executeSearch(kw)}
                            className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs hover:bg-primary/10 hover:text-primary transition-colors font-medium flex items-center gap-1"
                          >
                            <span>{kw}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Matching Products */
                  <div>
                    <div className="p-2 border-b border-slate-100 dark:border-slate-700 flex items-center justify-between text-xs text-muted">
                      <span>{t('Matching Products', 'সম্পর্কিত পণ্যসমূহ')}</span>
                      <span className="text-[11px]">{searchSuggestions.length} {t('results', 'ফলাফল')}</span>
                    </div>
                    {searchSuggestions.length === 0 ? (
                      <div className="p-4 text-center text-xs text-slate-400">
                        {t('No direct matches found. Press Search to view catalog.', 'কোন সরাসরি পণ্য পাওয়া যায়নি।')}
                      </div>
                    ) : (
                      <div className="max-h-72 overflow-y-auto divide-y divide-slate-50 dark:divide-slate-700">
                        {searchSuggestions.map((item) => (
                          <div
                            key={item.id}
                            onClick={() => {
                              saveSearchQuery(item.name);
                              navigateToProduct(item.slug);
                              setIsSearchFocused(false);
                            }}
                            className="flex items-center gap-3 p-2.5 hover:bg-slate-50 dark:hover:bg-slate-700 cursor-pointer transition-colors"
                          >
                            <img
                              src={item.image}
                              alt={item.name}
                              className="w-12 h-12 rounded-lg object-cover bg-slate-100 shrink-0"
                            />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-semibold text-ink dark:text-white truncate">
                                {language === 'bn' && item.name_bn ? item.name_bn : item.name}
                              </p>
                              <p className="text-[11px] text-muted truncate">
                                {item.seller_name} • {item.unit}
                              </p>
                            </div>
                            <div className="text-right shrink-0">
                              <span className="text-xs font-bold text-primary">
                                {formatPrice(item.discount_price ?? item.price)}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="p-2.5 bg-slate-50 dark:bg-slate-800 text-center border-t border-slate-100 dark:border-slate-700">
                      <button
                        type="button"
                        onClick={() => executeSearch(searchQuery)}
                        className="text-xs font-semibold text-primary hover:underline flex items-center justify-center gap-1 mx-auto"
                      >
                        <span>{t('View all search results', 'সব ফলাফল দেখুন')}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Icons: AI Copilot, Compare, Wishlist, Notification, Cart */}
          <div className="flex items-center gap-2 sm:gap-2.5">
            {/* Gemini HaatAI Assistant Trigger */}
            <button
              type="button"
              onClick={() => setIsAIAssistantOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 via-primary to-indigo-600 text-white font-bold text-xs shadow-md hover:opacity-95 transition-all animate-pulse"
              title="HaatAI Shopping Assistant"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span className="hidden sm:inline">HaatAI ✨</span>
            </button>

            {/* Compare items count */}
            {comparedProductIds.length > 0 && (
              <button
                type="button"
                onClick={() => setIsCompareModalOpen(true)}
                className="relative p-2.5 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Product Comparison"
              >
                <Layers className="w-5 h-5 text-primary" />
                <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-primary text-white text-[10px] font-bold flex items-center justify-center shadow-xs">
                  {comparedProductIds.length}
                </span>
              </button>
            )}

            {/* Wishlist */}
            <button
              type="button"
              onClick={() => setCurrentView('wishlist')}
              className={`relative p-2.5 rounded-xl transition-all ${
                currentView === 'wishlist' 
                  ? 'bg-rose-50 text-rose-600' 
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
              aria-label="Wishlist"
              title="Wishlist"
            >
              <Heart className="w-5 h-5" />
              {wishlistCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center shadow-xs">
                  {wishlistCount}
                </span>
              )}
            </button>

            {/* Notifications */}
            <button
              type="button"
              onClick={() => setCurrentView('notifications')}
              className={`relative p-2.5 rounded-xl transition-all ${
                currentView === 'notifications' 
                  ? 'bg-blue-50 text-primary' 
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {unreadNotificationCount > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-amber-500 text-white text-[10px] font-bold flex items-center justify-center shadow-xs">
                  {unreadNotificationCount}
                </span>
              )}
            </button>

            {/* Cart Trigger */}
            <button
              type="button"
              onClick={() => setIsCartDrawerOpen(true)}
              className="neu-button flex items-center gap-2 px-3.5 py-2 rounded-xl bg-primary text-white shadow-sm hover:bg-primary-hover"
              aria-label="Open cart"
            >
              <div className="relative">
                <ShoppingCart className="w-5 h-5" />
                {cartCount > 0 && (
                  <span className="absolute -top-2 -right-2 w-4 h-4 rounded-full bg-accent text-white text-[10px] font-extrabold flex items-center justify-center">
                    {cartCount}
                  </span>
                )}
              </div>
              <span className="text-xs font-bold hidden sm:inline">
                {formatPrice(cartSubtotal)}
              </span>
            </button>

            {/* Mobile menu hamburger */}
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 md:hidden text-slate-600 hover:text-ink"
              aria-label="Toggle menu"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Search input */}
        <div className="mt-2.5 md:hidden">
          <form onSubmit={handleSearchSubmit} className="relative flex items-center">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('Search products...', 'পণ্য খুঁজুন...')}
              className="w-full pl-9 pr-16 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-hidden focus:border-primary"
            />
            <Search className="absolute left-3 w-4 h-4 text-slate-400" />
            <button
              type="submit"
              className="absolute right-1 px-3 py-1 bg-primary text-white text-[11px] font-bold rounded-lg"
            >
              {t('Search', 'খুঁজুন')}
            </button>
          </form>
        </div>
      </div>

      {/* Categories & Sub-nav Bar */}
      <div className="hidden md:block bg-surface-raised dark:bg-slate-800/80 border-t border-slate-100 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2 flex items-center justify-between">
          <div className="flex items-center gap-5 text-xs font-semibold">
            {/* Category Mega Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsCategoryMenuOpen(!isCategoryMenuOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/15 transition-colors font-bold"
              >
                <Menu className="w-4 h-4" />
                <span>{t('All Haat Categories', 'সব হাট ক্যাটাগরি')}</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isCategoryMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {isCategoryMenuOpen && (
                <div 
                  className="absolute left-0 mt-2 w-64 bg-white dark:bg-slate-800 rounded-2xl shadow-elevated border border-slate-100 dark:border-slate-700 py-2 z-50 animate-fade-in"
                  onMouseLeave={() => setIsCategoryMenuOpen(false)}
                >
                  {categories.map(cat => (
                    <button
                      key={cat.id}
                      onClick={() => {
                        navigateToCategory(cat.slug);
                        setIsCategoryMenuOpen(false);
                      }}
                      className="w-full flex items-center justify-between px-3.5 py-2 text-xs font-medium text-left hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 hover:text-primary transition-colors"
                    >
                      <span>{language === 'bn' ? cat.name_bn : cat.name}</span>
                      <ArrowRight className="w-3 h-3 text-slate-300" />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Quick Links */}
            <button
              onClick={() => {
                setActiveCategorySlug(null);
                setCurrentView('catalog');
              }}
              className={`hover:text-primary transition-colors ${currentView === 'catalog' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
            >
              {t('Browse Catalog', 'সম্পূর্ণ ক্যাটালগ')}
            </button>

            <button
              onClick={() => setCurrentView('deals')}
              className={`flex items-center gap-1 hover:text-primary transition-colors ${currentView === 'deals' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
            >
              <Tag className="w-3.5 h-3.5 text-accent" />
              <span>{t('Mega Deals & Offers', 'মেগা ডিল ও ছাড়')}</span>
            </button>

            <button
              onClick={() => setIsPrimeModalOpen(true)}
              className="text-amber-500 font-bold hover:underline flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3" />
              <span>{t('Prime Hub', 'প্রাইম হাব')}</span>
            </button>

            <button
              onClick={() => navigateToCategory('fruits-vegetables')}
              className="text-slate-600 dark:text-slate-300 hover:text-primary transition-colors"
            >
              {t('Fresh Produce', 'তাজা ফল ও সবজি')}
            </button>

            <button
              onClick={() => navigateToCategory('meat-seafood')}
              className="text-slate-600 dark:text-slate-300 hover:text-primary transition-colors"
            >
              {t('Padma Fish & Meat', 'পদ্মার মাছ ও মাংস')}
            </button>

            <button
              onClick={() => navigateToCategory('dairy-eggs')}
              className="text-slate-600 dark:text-slate-300 hover:text-primary transition-colors"
            >
              {t('Bogra Curd & Dairy', 'বগুড়ার দই ও দুগ্ধপণ্য')}
            </button>
          </div>

          <div className="flex items-center gap-4 text-xs font-semibold">
            <button
              onClick={() => setCurrentView('my-orders')}
              className={`hover:text-primary transition-colors ${currentView === 'my-orders' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
            >
              {t('Track My Orders', 'অর্ডার ট্র্যাক করুন')}
            </button>

            <button
              onClick={() => setCurrentView('support')}
              className={`hover:text-primary transition-colors ${currentView === 'support' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
            >
              {t('Customer Support', 'গ্রাহক সেবা')}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-2 pb-3 border-b border-slate-100">
            <button
              onClick={() => {
                setCurrentView('catalog');
                setIsMobileMenuOpen(false);
              }}
              className="p-2.5 rounded-xl bg-slate-50 text-xs font-semibold text-center text-slate-700"
            >
              {t('Catalog', 'ক্যাটালগ')}
            </button>
            <button
              onClick={() => {
                setCurrentView('deals');
                setIsMobileMenuOpen(false);
              }}
              className="p-2.5 rounded-xl bg-amber-50 text-xs font-semibold text-center text-accent"
            >
              {t('Deals & Offers', 'মেগা ডিল')}
            </button>
            <button
              onClick={() => {
                setCurrentView('my-orders');
                setIsMobileMenuOpen(false);
              }}
              className="p-2.5 rounded-xl bg-slate-50 text-xs font-semibold text-center text-slate-700"
            >
              {t('My Orders', 'আমার অর্ডার')}
            </button>
            <button
              onClick={() => {
                setIsAIAssistantOpen(true);
                setIsMobileMenuOpen(false);
              }}
              className="p-2.5 rounded-xl bg-blue-50 text-xs font-semibold text-center text-primary"
            >
              HaatAI Copilot ✨
            </button>
          </div>

          <div>
            <p className="text-xs font-bold text-slate-400 mb-2 uppercase">
              {t('Browse Categories', 'ক্যাটাগরি')}
            </p>
            <div className="space-y-1">
              {categories.map(c => (
                <button
                  key={c.id}
                  onClick={() => {
                    navigateToCategory(c.slug);
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full text-left py-1.5 px-2 text-xs font-medium text-slate-700 hover:text-primary"
                >
                  {language === 'bn' ? c.name_bn : c.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
