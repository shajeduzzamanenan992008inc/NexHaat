import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useApp } from '../context/AppContext';
import { 
  Search, ShoppingCart, Heart, Bell, Menu, X, ChevronDown, 
  User, Sparkles, Tag, ArrowRight,
  Sun, Moon, Layers, Mic, Camera, Clock, TrendingUp, History, Trash2,
  Globe
} from 'lucide-react';
import { manageSearchHistory } from '../lib/amazonFeatures';
import { FlaskAuthPanel } from './FlaskAuthPanel';
import { PWAInstallButton } from './PWAInstallButton';
import { AppLanguage, AppCurrency } from '../types';
import { CURRENCY_CONFIGS, SUPPORTED_CURRENCIES } from '../lib/currency';
import { SUPPORTED_LANGUAGES } from '../lib/i18n';
import { useMotionPresence } from '../lib/useMotionPresence';

type SpeechAlternative = { transcript: string };
type SpeechResult = ArrayLike<SpeechAlternative>;
type SpeechRecognitionEventLike = { results: ArrayLike<SpeechResult> };
type SpeechRecognitionErrorLike = { error: string };
type DetectedBarcode = { rawValue: string };

interface BrowserSpeechRecognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  abort: () => void;
}

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

interface BrowserBarcodeDetector {
  detect: (source: ImageBitmap) => Promise<DetectedBarcode[]>;
}

type BarcodeDetectorConstructor = {
  new (options: { formats: string[] }): BrowserBarcodeDetector;
  getSupportedFormats: () => Promise<string[]>;
};


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
    setIsPrimeModalOpen,
    isDarkMode,
    toggleDarkMode,
    setIsAIAssistantOpen,
    language,
    setLanguage,
    currency,
    setCurrency,
    t,
    formatPrice,
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
    flaskUser,
  } = useApp();

  const [isCategoryMenuOpen, setIsCategoryMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const [isVoiceListening, setIsVoiceListening] = useState(false);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('all');
  const [isDepartmentMenuOpen, setIsDepartmentMenuOpen] = useState(false);
  const [isFlaskAuthPanelOpen, setIsFlaskAuthPanelOpen] = useState(false);
  const [isLanguageMenuOpen, setIsLanguageMenuOpen] = useState(false);
  const [isCurrencyMenuOpen, setIsCurrencyMenuOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [cartBounce, setCartBounce] = useState(false);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const voiceRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const visualSearchInputRef = useRef<HTMLInputElement>(null);
  const imageSearchTriggerRef = useRef<HTMLButtonElement | null>(null);
  const visualSearchConsentButtonRef = useRef<HTMLButtonElement>(null);
  const visualSearchDialogRef = useRef<HTMLDivElement>(null);
  const mobileMenuPresence = useMotionPresence(isMobileMenuOpen);
  const [isVisualSearching, setIsVisualSearching] = useState(false);
  const [isVisualSearchConsentOpen, setIsVisualSearchConsentOpen] = useState(false);

  useEffect(() => {
    if (mobileMenuRef.current) mobileMenuRef.current.inert = mobileMenuPresence.isExiting || !isMobileMenuOpen;
  }, [isMobileMenuOpen, mobileMenuPresence.isExiting]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => () => voiceRecognitionRef.current?.abort(), []);

  useEffect(() => {
    if (!isVisualSearchConsentOpen) {
      imageSearchTriggerRef.current?.focus();
      return;
    }

    visualSearchConsentButtonRef.current?.focus();
    const handleDialogKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setIsVisualSearchConsentOpen(false);
        return;
      }
      if (event.key !== 'Tab') return;

      const buttons = visualSearchDialogRef.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');
      if (!buttons?.length) return;
      const first = buttons[0];
      const last = buttons[buttons.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener('keydown', handleDialogKeyDown);
    return () => window.removeEventListener('keydown', handleDialogKeyDown);
  }, [isVisualSearchConsentOpen]);

  useEffect(() => {
    if (cartCount > 0) {
      setCartBounce(true);
      const timer = setTimeout(() => setCartBounce(false), 500);
      return () => clearTimeout(timer);
    }
  }, [cartCount]);

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
    const browserWindow = window as Window & {
      SpeechRecognition?: SpeechRecognitionConstructor;
      webkitSpeechRecognition?: SpeechRecognitionConstructor;
    };
    const SpeechRecognition = browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      showToast(t('Voice search is not supported in this browser.', 'এই ব্রাউজারে ভয়েস সার্চ সমর্থিত নয়।'), 'warning');
      return;
    }

    voiceRecognitionRef.current?.abort();
    const recognition = new SpeechRecognition();
    recognition.lang = language === 'bn' ? 'bn-BD' : 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || '')
        .join(' ')
        .trim();
      if (!transcript) return;
      executeSearch(transcript);
      showToast(
        t(`Voice search: ${transcript}`, `ভয়েস অনুসন্ধান: ${transcript}`),
        'success',
      );
    };
    recognition.onerror = (event) => {
      setIsVoiceListening(false);
      const message = event.error === 'not-allowed'
        ? t('Allow microphone access to use voice search.', 'ভয়েস সার্চের জন্য মাইক্রোফোন ব্যবহারের অনুমতি দিন।')
        : t('Voice search could not hear that. Please try again.', 'কথা শনাক্ত হয়নি, আবার চেষ্টা করুন।');
      showToast(message, 'warning');
    };
    recognition.onend = () => setIsVoiceListening(false);
    voiceRecognitionRef.current = recognition;
    setIsVoiceListening(true);
    showToast(t('Listening for your search…', 'আপনার অনুসন্ধান শুনছি…'), 'info');

    try {
      recognition.start();
    } catch {
      setIsVoiceListening(false);
      showToast(t('Voice search could not start. Please try again.', 'ভয়েস সার্চ চালু হয়নি, আবার চেষ্টা করুন।'), 'warning');
    }
  };

  const handleImageSearch = (event: React.MouseEvent<HTMLButtonElement>) => {
    imageSearchTriggerRef.current = event.currentTarget;
    setIsVisualSearchConsentOpen(true);
  };

  const handleImageSearchConsent = () => {
    setIsVisualSearchConsentOpen(false);
    visualSearchInputRef.current?.click();
  };

  const handleVisualSearchFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = '';
    if (!file) return;

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024) {
      showToast(t('Choose a JPG, PNG, or WebP image smaller than 10 MB.', '১০ MB-এর ছোট JPG, PNG বা WebP ছবি বাছুন।'), 'warning');
      return;
    }

    const BarcodeDetector = (window as Window & { BarcodeDetector?: BarcodeDetectorConstructor }).BarcodeDetector;
    setIsVisualSearching(true);
    let bitmap: ImageBitmap | undefined;
    let objectUrl: string | undefined;
    try {
      let imageSource: CanvasImageSource;
      let imageWidth: number;
      let imageHeight: number;
      if (typeof window.createImageBitmap === 'function') {
        bitmap = await window.createImageBitmap(file);
        imageSource = bitmap;
        imageWidth = bitmap.width;
        imageHeight = bitmap.height;
      } else {
        objectUrl = URL.createObjectURL(file);
        const image = new Image();
        image.src = objectUrl;
        await image.decode();
        imageSource = image;
        imageWidth = image.naturalWidth;
        imageHeight = image.naturalHeight;
      }

      if (!imageWidth || !imageHeight || imageWidth * imageHeight > 40_000_000) {
        showToast(
          t('This image is too large to process safely. Choose a smaller image.', 'নিরাপদে প্রসেস করার জন্য ছবিটি অনেক বড়। ছোট ছবি বাছুন।'),
          'warning',
        );
        return;
      }

      if (BarcodeDetector && bitmap) {
        try {
          const supportedFormats = await BarcodeDetector.getSupportedFormats();
          const formats = ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128'].filter((format) =>
            supportedFormats.includes(format),
          );
          if (formats.length > 0) {
            const [barcode] = await new BarcodeDetector({ formats }).detect(bitmap);
            const product = barcode?.rawValue
              ? products.find((item) => item.sku.trim().toLowerCase() === barcode.rawValue.trim().toLowerCase())
              : undefined;
            if (product) {
              setIsSearchFocused(false);
              navigateToProduct(product.slug);
              showToast(t('Product found from barcode.', 'বারকোড থেকে পণ্য পাওয়া গেছে।'), 'success');
              return;
            }
          }
        } catch {
          // Barcode scanning is an optional local shortcut; continue with visual search.
        }
      }

      const scale = Math.min(1, 1600 / Math.max(imageWidth, imageHeight));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(imageWidth * scale));
      canvas.height = Math.max(1, Math.round(imageHeight * scale));
      const context = canvas.getContext('2d');
      if (!context) throw new Error('Canvas is unavailable');
      context.fillStyle = '#ffffff';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(imageSource, 0, 0, canvas.width, canvas.height);

      const resizedImage = await new Promise<Blob>((resolve, reject) => {
        canvas.toBlob(
          (blob) => blob ? resolve(blob) : reject(new Error('Image encoding failed')),
          'image/jpeg',
          0.84,
        );
      });
      if (resizedImage.size > 8 * 1024 * 1024) {
        showToast(t('The resized image is still too large. Choose another image.', 'ছোট করার পরও ছবিটি বড়। অন্য ছবি বাছুন।'), 'warning');
        return;
      }

      const sourceImage = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Image reading failed'));
        reader.onload = () => typeof reader.result === 'string'
          ? resolve(reader.result)
          : reject(new Error('Image reading failed'));
        reader.readAsDataURL(resizedImage);
      });

      const response = await fetch('/api/gemini/visual-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sourceImage, mimeType: 'image/jpeg', language }),
      });
      if (!response.ok) {
        const message = response.status === 429
          ? t('Too many image searches. Please wait a moment and try again.', 'ছবি-সার্চের অনুরোধ বেশি হয়েছে। একটু পরে আবার চেষ্টা করুন।')
          : t('Image search is unavailable right now. Try a product name instead.', 'এখন ছবি-সার্চ চালু নেই। পণ্যের নাম দিয়ে খুঁজুন।');
        showToast(message, 'warning');
        return;
      }

      const result: unknown = await response.json();
      const query = typeof result === 'object' && result !== null && 'query' in result && typeof result.query === 'string'
        ? result.query.trim()
        : '';
      if (!query) {
        showToast(t('No searchable product details were found in the image.', 'ছবিতে খোঁজার মতো পণ্যের তথ্য পাওয়া যায়নি।'), 'info');
        return;
      }

      setIsSearchFocused(false);
      executeSearch(query);
      showToast(
        t('Image search prepared. Review the NexHaat catalog results.', 'ছবি থেকে সার্চ তৈরি হয়েছে। NexHaat ক্যাটালগের ফলাফল দেখুন।'),
        'success',
      );
    } catch {
      showToast(t('Image search failed. Try a clearer image or search by name.', 'ছবি-সার্চ হয়নি। পরিষ্কার ছবি বা পণ্যের নাম দিয়ে চেষ্টা করুন।'), 'warning');
    } finally {
      bitmap?.close();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setIsVisualSearching(false);
    }
  };

  return (
    <header className={`marketplace-navbar sticky top-0 z-40 w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b transition-all duration-300 ${isScrolled ? 'shadow-elevated border-slate-300/80 dark:border-slate-700' : 'border-border dark:border-slate-800 shadow-xs'}`}>
      <input
        ref={visualSearchInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        onChange={handleVisualSearchFile}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
      />
      {/* Compact utility bar */}
      <div className="marketplace-utility-bar text-xs py-1.5 px-3 sm:px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 sm:gap-4 shrink-0">
            <span className="hidden lg:inline text-blue-50">
              {t('A Bangladesh-first marketplace for everyday finds.', 'প্রতিদিনের কেনাকাটার বাংলাদেশি মার্কেটপ্লেস।')}
            </span>
            <button
              onClick={() => setIsPrimeModalOpen(true)}
              className="marketplace-utility-link inline-flex items-center gap-1.5 font-bold text-amber-200 hover:text-amber-100 transition-colors"
              aria-label={t('Open membership preview', 'মেম্বারশিপ প্রিভিউ খুলুন')}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t('Membership preview', 'মেম্বারশিপ প্রিভিউ')}</span>
              <span className="sm:hidden">{t('Member', 'সদস্য')}</span>
            </button>
          </div>

          <div className="flex items-center gap-1 sm:gap-3 shrink-0">
            {/* Dark Mode Toggle */}
            <button
              type="button"
              onClick={toggleDarkMode}
              className="marketplace-theme-toggle"
              title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              aria-pressed={isDarkMode}
            >
              {isDarkMode ? <Sun className="h-4 w-4 text-amber-300" aria-hidden="true" /> : <Moon className="h-4 w-4 text-blue-100" aria-hidden="true" />}
              <span className="hidden sm:inline">{isDarkMode ? t('Dark mode', 'ডার্ক মোড') : t('Light mode', 'লাইট মোড')}</span>
            </button>

            {/* International Currency Selector */}
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setIsCurrencyMenuOpen(!isCurrencyMenuOpen);
                  setIsLanguageMenuOpen(false);
                }}
                className="marketplace-utility-control flex items-center gap-1 px-1.5 sm:px-2 py-1 sm:py-0.5 rounded-md text-[11px] font-bold text-amber-100 transition-colors"
                title="Select Currency"
                aria-label="Select Currency"
              >
                <span>{CURRENCY_CONFIGS[currency]?.flag}</span>
                <span className="hidden sm:inline">{currency}</span>
                <ChevronDown className="w-2.5 h-2.5 opacity-70" />
              </button>

              {isCurrencyMenuOpen && (
                <div
                  className="absolute right-0 mt-1.5 w-44 bg-white dark:bg-slate-800 rounded-xl shadow-elevated border border-slate-100 dark:border-slate-700 py-1.5 z-50 motion-popover-enter"
                  onMouseLeave={() => setIsCurrencyMenuOpen(false)}
                >
                  <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-700">
                    {t('Select Currency', 'মুদ্রা নির্বাচন')}
                  </div>
                  {SUPPORTED_CURRENCIES.map((curr) => {
                    const conf = CURRENCY_CONFIGS[curr];
                    return (
                      <button
                        key={curr}
                        type="button"
                        onClick={() => {
                          setCurrency(curr);
                          setIsCurrencyMenuOpen(false);
                          showToast(`Currency changed to ${conf.name} (${conf.symbol})`, 'info');
                        }}
                        className={`w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold text-left hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ${
                          currency === curr ? 'bg-primary-light text-primary font-bold' : 'text-ink dark:text-white'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span>{conf.flag}</span>
                          <span>{curr}</span>
                          <span className="text-[10px] text-muted">({conf.symbol.trim()})</span>
                        </div>
                        {currency === curr && (
                          <span className="text-[10px] font-bold text-primary">✓</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* International Language Switcher */}
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setIsLanguageMenuOpen(!isLanguageMenuOpen);
                  setIsCurrencyMenuOpen(false);
                }}
                className="marketplace-utility-control flex items-center gap-1 px-1.5 sm:px-2 py-1 sm:py-0.5 rounded-md text-[11px] font-bold text-blue-50 transition-colors"
                title="Select Language"
                aria-label="Select Language"
              >
                <Globe className="w-3 h-3 text-primary-light" />
                <span className="hidden sm:inline">{SUPPORTED_LANGUAGES[language]?.nativeName || 'Language'}</span>
                <span className="sm:hidden">{language === 'bn' ? 'BN' : 'EN'}</span>
                <ChevronDown className="w-2.5 h-2.5 opacity-70" />
              </button>

              {isLanguageMenuOpen && (
                <div
                  className="absolute right-0 mt-1.5 w-40 bg-white dark:bg-slate-800 rounded-xl shadow-elevated border border-slate-100 dark:border-slate-700 py-1.5 z-50 motion-popover-enter"
                  onMouseLeave={() => setIsLanguageMenuOpen(false)}
                >
                  <div className="px-3 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-700">
                    {t('Language', 'ভাষা')}
                  </div>
                  {(Object.keys(SUPPORTED_LANGUAGES) as AppLanguage[]).map((langKey) => {
                    const l = SUPPORTED_LANGUAGES[langKey];
                    return (
                      <button
                        key={langKey}
                        type="button"
                        onClick={() => {
                          setLanguage(langKey);
                          setIsLanguageMenuOpen(false);
                          showToast(`Language switched to ${l.nativeName}`, 'info');
                        }}
                        className={`w-full flex items-center justify-between px-3 py-1.5 text-xs font-semibold text-left hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors ${
                          language === langKey ? 'bg-primary-light text-primary font-bold' : 'text-ink dark:text-white'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span>{l.flag}</span>
                          <span>{l.nativeName}</span>
                        </div>
                        {language === langKey && (
                          <span className="text-[10px] font-bold text-primary">✓</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Google Firebase Auth */}
            <button
              type="button"
              onClick={() => setIsFlaskAuthPanelOpen(true)}
              className="marketplace-action-button flex h-8 w-8 sm:h-auto sm:w-auto items-center justify-center gap-1.5 rounded-md border border-blue-200 bg-white/10 px-2 py-1 text-xs font-semibold text-white transition-colors hover:bg-white/20"
              title="Sign in with the authoritative Flask marketplace session"
              aria-label={flaskUser ? `Marketplace account: ${flaskUser.email}` : t('NexHaat Login', 'NexHaat লগইন')}
            >
              <span className="hidden sm:inline">{flaskUser ? flaskUser.email : t('NexHaat Login', 'NexHaat লগইন')}</span>
              <User className="w-4 h-4 sm:hidden" aria-hidden="true" />
            </button>
            {firebaseUser ? (
              <div className="hidden sm:flex items-center gap-1.5 bg-slate-800 rounded-md px-2 py-1 border border-slate-700 text-xs text-white">
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
                className="hidden sm:flex items-center gap-1.5 px-2 py-1 bg-white hover:bg-slate-100 text-slate-900 rounded-md text-xs font-semibold shadow-xs transition-colors shrink-0"
                title="Sign in with Google via Firebase Auth"
                aria-label="Sign in with Google via Firebase Auth"
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
      {isFlaskAuthPanelOpen && <FlaskAuthPanel onClose={() => setIsFlaskAuthPanelOpen(false)} />}

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
              </div>
              <p className="text-[10px] font-semibold text-muted -mt-1 hidden sm:block">
                {t('Bangladesh’s local marketplace', 'বাংলাদেশের স্থানীয় মার্কেটপ্লেস')}
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
                  <div className="absolute left-0 top-full mt-1.5 w-52 bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-slate-200 dark:border-slate-700 py-1.5 z-50 motion-popover-enter max-h-64 overflow-y-auto">
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

              <div className="relative flex-1 flex items-center min-w-0">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onFocus={() => setIsSearchFocused(true)}
                  placeholder={t(
                    'Search fresh fish, organic rice, cold-pressed oil, farm produce...',
                    'তাজা ইলিশ, সুগন্ধি চাল, সরিষার তেল, খামারের পণ্য খুঁজুন...'
                  )}
                  className="w-full min-w-0 pl-3 pr-2 py-2.5 bg-transparent text-sm focus:outline-hidden text-ink dark:text-white placeholder:text-slate-400"
                />
              </div>

              {/* Mic & Visual Search Icons inside search bar */}
              <div className="flex shrink-0 items-center gap-1 px-1">
                <button
                  type="button"
                  onClick={handleVoiceSearch}
                  className={`marketplace-icon-button p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-300 hover:text-primary transition-colors ${
                    isVoiceListening ? 'text-danger animate-pulse' : ''
                  }`}
                  title="Voice Search"
                >
                  <Mic className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  ref={imageSearchTriggerRef}
                  onClick={handleImageSearch}
                  disabled={isVisualSearching}
                  className="marketplace-icon-button p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-300 hover:text-primary transition-colors disabled:opacity-50"
                  title={t('Search for products using an image', 'ছবি দিয়ে পণ্য খুঁজুন')}
                  aria-label={t('Search for products using an image', 'ছবি দিয়ে পণ্য খুঁজুন')}
                >
                  <Camera className={`w-4 h-4 ${isVisualSearching ? 'animate-pulse' : ''}`} />
                </button>
              </div>

              <button
                type="submit"
                className="marketplace-action-button marketplace-search-submit mr-1.5 px-4 py-1.5 bg-primary text-white text-xs font-bold rounded-xl hover:bg-primary-hover transition-colors shadow-sm flex items-center gap-1"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{t('Search', 'খুঁজুন')}</span>
              </button>
            </form>

            {/* Dropdown: Recent Search History & Trending or Live Matching Suggestions */}
            {isSearchFocused && (
              <div className="absolute left-0 right-0 top-full mt-2 bg-white dark:bg-slate-800 rounded-2xl shadow-elevated border border-slate-100 dark:border-slate-700 overflow-hidden z-50 motion-popover-enter divide-y divide-slate-100 dark:divide-slate-700">
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
          <div className="flex items-center gap-1 sm:gap-2.5 shrink-0">
            {/* Install Android App / PWA Button */}
            <div className="hidden sm:flex"><PWAInstallButton variant="compact" /></div>

            {/* Gemini HaatAI Assistant Trigger */}
            <button

              type="button"
              onClick={() => setIsAIAssistantOpen(true)}
              className="marketplace-action-button marketplace-ai-cta flex items-center gap-1.5 px-2 sm:px-3 py-2 sm:py-1.5 rounded-xl text-white font-bold text-xs"
              title="HaatAI Shopping Assistant"
              aria-label={t('Open HaatAI shopping assistant', 'HaatAI কেনাকাটা সহকারী খুলুন')}
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span className="hidden sm:inline">HaatAI ✨</span>
            </button>

            {/* Compare items count */}
            {comparedProductIds.length > 0 && (
              <button
                type="button"
                onClick={() => setIsCompareModalOpen(true)}
                className="hidden sm:flex relative p-2.5 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
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
              className={`marketplace-icon-button hidden sm:flex relative p-2.5 rounded-xl transition-all ${
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
              className={`marketplace-icon-button hidden sm:flex relative p-2.5 rounded-xl transition-all ${
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
              className="marketplace-action-button neu-button flex items-center gap-2 px-2.5 sm:px-3.5 py-2 rounded-xl bg-primary text-white shadow-sm hover:bg-primary-hover"
              aria-label="Open cart"
            >
              <div className="relative">
                <ShoppingCart className="w-5 h-5" />
                {cartCount > 0 && (
                  <span className={`absolute -top-2 -right-2 w-4 h-4 rounded-full bg-accent text-navy text-[10px] font-extrabold flex items-center justify-center transition-transform ${cartBounce ? 'animate-cart-bounce ring-2 ring-white' : ''}`}>
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
      <div className="marketplace-category-bar hidden md:block border-t">
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
                  className="absolute left-0 mt-2 w-64 bg-white dark:bg-slate-800 rounded-2xl shadow-elevated border border-slate-100 dark:border-slate-700 py-2 z-50 motion-popover-enter"
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
              className={`motion-nav-link hover:text-primary transition-colors ${currentView === 'catalog' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
              data-active={currentView === 'catalog'}
            >
              {t('Browse Catalog', 'সম্পূর্ণ ক্যাটালগ')}
            </button>

            <button
              onClick={() => setCurrentView('deals')}
              className={`motion-nav-link flex items-center gap-1 hover:text-primary transition-colors ${currentView === 'deals' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
              data-active={currentView === 'deals'}
            >
              <Tag className="w-3.5 h-3.5 text-accent" />
              <span>{t('Mega Deals & Offers', 'মেগা ডিল ও ছাড়')}</span>
            </button>

            <button
              onClick={() => setIsPrimeModalOpen(true)}
              className="text-amber-500 font-bold hover:underline flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3" />
              <span>{t('Membership preview', 'মেম্বারশিপ প্রিভিউ')}</span>
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
              className={`motion-nav-link hover:text-primary transition-colors ${currentView === 'my-orders' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
              data-active={currentView === 'my-orders'}
            >
              {t('Track My Orders', 'অর্ডার ট্র্যাক করুন')}
            </button>

            <button
              onClick={() => setCurrentView('support')}
              className={`motion-nav-link hover:text-primary transition-colors ${currentView === 'support' ? 'text-primary font-bold' : 'text-slate-600 dark:text-slate-300'}`}
              data-active={currentView === 'support'}
            >
              {t('Customer Support', 'গ্রাহক সেবা')}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuPresence.isPresent && (
        <div
          ref={mobileMenuRef}
          aria-hidden={mobileMenuPresence.isExiting || !isMobileMenuOpen}
          className={`md:hidden bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-4 space-y-3 motion-panel-enter ${
            mobileMenuPresence.isExiting ? 'motion-panel-exit pointer-events-none' : ''
          }`}
        >
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
                setCurrentView('wishlist');
                setIsMobileMenuOpen(false);
              }}
              className="p-2.5 rounded-xl bg-slate-50 text-xs font-semibold text-center text-slate-700"
            >
              {t('Wishlist', 'পছন্দের তালিকা')}{wishlistCount > 0 ? ` (${wishlistCount})` : ''}
            </button>
            <button
              onClick={() => {
                setCurrentView('notifications');
                setIsMobileMenuOpen(false);
              }}
              className="p-2.5 rounded-xl bg-slate-50 text-xs font-semibold text-center text-slate-700"
            >
              {t('Notifications', 'বিজ্ঞপ্তি')}{unreadNotificationCount > 0 ? ` (${unreadNotificationCount})` : ''}
            </button>
            <button
              onClick={() => {
                setCurrentView('support');
                setIsMobileMenuOpen(false);
              }}
              className="p-2.5 rounded-xl bg-slate-50 text-xs font-semibold text-center text-slate-700"
            >
              {t('Customer Support', 'গ্রাহক সেবা')}
            </button>
            {comparedProductIds.length > 0 && (
              <button
                onClick={() => {
                  setIsCompareModalOpen(true);
                  setIsMobileMenuOpen(false);
                }}
                className="p-2.5 rounded-xl bg-primary/10 text-xs font-semibold text-center text-primary"
              >
                {t('Compare', 'তুলনা করুন')} ({comparedProductIds.length})
              </button>
            )}
            <button
              type="button"
              ref={imageSearchTriggerRef}
              onClick={handleImageSearch}
              disabled={isVisualSearching}
              className="p-2.5 rounded-xl bg-amber-50 text-xs font-semibold text-center text-amber-800 disabled:opacity-50"
            >
              <span className="inline-flex items-center justify-center gap-1.5">
                <Camera className="h-3.5 w-3.5" />
                {t('Search by image', 'ছবি দিয়ে খুঁজুন')}
              </span>
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

          <div className="flex flex-col gap-2 border-t border-slate-100 pt-3 sm:hidden">
            {firebaseUser ? (
              <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-700">
                <span className="truncate">{firebaseUser.displayName || firebaseUser.email}</span>
                <button type="button" onClick={logoutFirebase} className="ml-3 shrink-0 font-semibold text-primary">
                  {t('Sign out', 'সাইন আউট')}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={loginWithGoogle}
                disabled={isFirebaseAuthLoading}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-semibold text-slate-800 disabled:opacity-60"
              >
                {t('Continue with Google', 'Google দিয়ে চালিয়ে যান')}
              </button>
            )}
            <PWAInstallButton variant="full" />
          </div>
        </div>
      )}

      {isVisualSearchConsentOpen && createPortal(
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm motion-fade-in"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setIsVisualSearchConsentOpen(false);
          }}
        >
          <div
            ref={visualSearchDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="visual-search-consent-title"
            className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl dark:border-slate-700 dark:bg-slate-900 sm:p-6"
          >
            <div className="mb-3 flex items-center gap-2 text-primary">
              <Camera className="h-5 w-5" />
              <h2 id="visual-search-consent-title" className="text-base font-bold text-slate-900 dark:text-white">
                {t('Image search privacy', 'ছবি দিয়ে খোঁজার গোপনীয়তা')}
              </h2>
            </div>
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              {t(
                'NexHaat first checks for an exact local barcode/SKU match. If there is no exact match, your selected image will be resized and sent to Google Gemini to create a search phrase. NexHaat does not store the image; Google processes it under its own policies. Listings, prices, and stock shown come from the NexHaat catalog.',
                'NexHaat আগে স্থানীয়ভাবে বারকোড/SKU-এর হুবহু মিল খুঁজবে। হুবহু মিল না থাকলে নির্বাচিত ছবিটি ছোট করে Google Gemini-তে পাঠানো হবে, যাতে সার্চের শব্দ তৈরি হয়। NexHaat ছবিটি সংরক্ষণ করে না; Google নিজস্ব নীতিতে ছবিটি প্রসেস করে। ফলাফলের পণ্য, দাম ও স্টক NexHaat ক্যাটালগ থেকে আসে।',
              )}
            </p>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => setIsVisualSearchConsentOpen(false)}
                className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                {t('Cancel', 'বাতিল')}
              </button>
              <button
                ref={visualSearchConsentButtonRef}
                type="button"
                onClick={handleImageSearchConsent}
                className="rounded-xl bg-primary px-4 py-2.5 text-sm font-bold text-white shadow-sm transition-colors hover:bg-primary-hover"
              >
                {t('Continue and choose image', 'এগিয়ে গিয়ে ছবি বাছুন')}
              </button>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </header>
  );
};
