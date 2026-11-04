export type AppCurrency = 'BDT' | 'USD' | 'EUR' | 'AED' | 'INR';

export interface CurrencyConfig {
  code: AppCurrency;
  symbol: string;
  rate: number; // 1 BDT in foreign currency
  name: string;
  flag: string;
}

export const CURRENCY_CONFIGS: Record<AppCurrency, CurrencyConfig> = {
  BDT: {
    code: 'BDT',
    symbol: '৳',
    rate: 1.0,
    name: 'Bangladeshi Taka',
    flag: '🇧🇩',
  },
  USD: {
    code: 'USD',
    symbol: '$',
    rate: 0.0083,
    name: 'US Dollar',
    flag: '🇺🇸',
  },
  EUR: {
    code: 'EUR',
    symbol: '€',
    rate: 0.0078,
    name: 'Euro',
    flag: '🇪🇺',
  },
  AED: {
    code: 'AED',
    symbol: 'AED ',
    rate: 0.0305,
    name: 'UAE Dirham',
    flag: '🇦🇪',
  },
  INR: {
    code: 'INR',
    symbol: '₹',
    rate: 0.72,
    name: 'Indian Rupee',
    flag: '🇮🇳',
  },
};

export const SUPPORTED_CURRENCIES: AppCurrency[] = ['BDT', 'USD', 'EUR', 'AED', 'INR'];

/**
 * Converts an amount from Bangladeshi Taka (BDT) to target currency.
 */
export function convertFromBDT(amountBDT: number, targetCurrency: AppCurrency): number {
  if (isNaN(amountBDT) || amountBDT <= 0) return 0;
  const config = CURRENCY_CONFIGS[targetCurrency] || CURRENCY_CONFIGS.BDT;
  const converted = amountBDT * config.rate;
  return Math.round((converted + Number.EPSILON) * 100) / 100;
}

/**
 * Converts an amount from a foreign currency back to Bangladeshi Taka (BDT).
 */
export function convertToBDT(amountForeign: number, fromCurrency: AppCurrency): number {
  if (isNaN(amountForeign) || amountForeign <= 0) return 0;
  const config = CURRENCY_CONFIGS[fromCurrency] || CURRENCY_CONFIGS.BDT;
  if (config.rate <= 0) return 0;
  const inBDT = amountForeign / config.rate;
  return Math.round((inBDT + Number.EPSILON) * 100) / 100;
}

/**
 * Formats a BDT price according to chosen currency and language.
 */
export function formatCurrencyPrice(
  amountBDT: number,
  currency: AppCurrency = 'BDT',
  language: string = 'en'
): string {
  if (isNaN(amountBDT)) return '৳0.00';
  const config = CURRENCY_CONFIGS[currency] || CURRENCY_CONFIGS.BDT;
  const converted = convertFromBDT(amountBDT, currency);

  const locale = language === 'bn' ? 'bn-BD' : language === 'ar' ? 'ar-AE' : language === 'hi' ? 'hi-IN' : 'en-US';
  const formatted = converted.toLocaleString(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (currency === 'BDT') {
    return language === 'bn' ? `৳ ${formatted}` : `৳${formatted}`;
  }
  return `${config.symbol}${formatted}`;
}
