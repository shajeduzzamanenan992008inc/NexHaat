export type AppLanguage = 'en' | 'bn' | 'ar' | 'hi';

export interface LanguageConfig {
  code: AppLanguage;
  name: string;
  nativeName: string;
  flag: string;
  dir: 'ltr' | 'rtl';
}

export const SUPPORTED_LANGUAGES: Record<AppLanguage, LanguageConfig> = {
  en: {
    code: 'en',
    name: 'English',
    nativeName: 'English',
    flag: '🇺🇸',
    dir: 'ltr',
  },
  bn: {
    code: 'bn',
    name: 'Bengali',
    nativeName: 'বাংলা',
    flag: '🇧🇩',
    dir: 'ltr',
  },
  ar: {
    code: 'ar',
    name: 'Arabic',
    nativeName: 'العربية',
    flag: '🇸🇦',
    dir: 'rtl',
  },
  hi: {
    code: 'hi',
    name: 'Hindi',
    nativeName: 'हिन्दी',
    flag: '🇮🇳',
    dir: 'ltr',
  },
};

export const COMMON_TRANSLATIONS: Record<string, Record<AppLanguage, string>> = {
  'nav.search': {
    en: 'Search 50,000+ local fresh goods, spices & fashion...',
    bn: '৫০,০০০+ তাজা খাবার, মসলা ও দেশি পণ্য খুঁজুন...',
    ar: 'ابحث في أكثر من 50,000 منتج طازج ومحلي...',
    hi: '50,000+ ताज़ा भोजन, मसाले और उत्पाद खोजें...',
  },
  'nav.cart': {
    en: 'Cart',
    bn: 'কার্ট',
    ar: 'السلة',
    hi: 'कार्ट',
  },
  'nav.wishlist': {
    en: 'Wishlist',
    bn: 'উইশলিস্ট',
    ar: 'المفضلة',
    hi: 'इच्छा सूची',
  },
  'nav.notifications': {
    en: 'Notifications',
    bn: 'বিজ্ঞপ্তি',
    ar: 'الإشعارات',
    hi: 'सूचनाएं',
  },
  'nav.portals': {
    en: 'Portals',
    bn: 'পোর্টাল',
    ar: 'البوابات',
    hi: 'पोर्टल',
  },
  'badge.instant_digital': {
    en: 'Instant Digital Delivery',
    bn: 'তাৎক্ষণিক ডিজিটাল ডেলিভারি',
    ar: 'تسليم رقمي فوري',
    hi: 'त्वरित डिजिटल डिलीवरी',
  },
  'badge.global_shipping': {
    en: 'Global Air Cargo',
    bn: 'আন্তর্জাতিক বিমান কার্গো',
    ar: 'شحن جوي دولي',
    hi: 'अंतर्राष्ट्रीय एयर कार्गो',
  },
  'badge.cold_chain': {
    en: 'Cold-Chain IoT Protected',
    bn: 'কোল্ড-চেইন আইওটি সুরক্ষিত',
    ar: 'محمي بسلسلة التبريد الذكية',
    hi: 'कोल्ड-चेन सुरक्षित',
  },
};

/**
 * Resolves a translated string based on active language.
 * Backward compatible with existing t(en, bn) calls while enabling Arabic and Hindi.
 */
export function translate(
  language: AppLanguage,
  enText: string,
  bnText: string,
  arText?: string,
  hiText?: string
): string {
  if (language === 'bn') return bnText || enText;
  if (language === 'ar') return arText || enText;
  if (language === 'hi') return hiText || enText;
  return enText;
}
