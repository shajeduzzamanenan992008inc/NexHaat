import React, { useState } from 'react';
import { Product, PriceAlert } from '../types';
import { useApp } from '../context/AppContext';
import { 
  Bell, BellRing, Check, X, TrendingDown, Sparkles, 
  Trash2, ShieldCheck, ArrowRight, Zap, AlertCircle 
} from 'lucide-react';

interface PriceAlertModalProps {
  product: Product;
  isOpen: boolean;
  onClose: () => void;
}

export const PriceAlertModal: React.FC<PriceAlertModalProps> = ({
  product,
  isOpen,
  onClose,
}) => {
  const {
    formatPrice,
    setPriceAlert,
    removePriceAlert,
    getPriceAlert,
    simulatePriceDrop,
    showToast,
    t,
    language,
  } = useApp();

  const currentPrice = product.discount_price ?? product.price;
  const existingAlert = getPriceAlert(product.id);

  // Default target price is 10% below current price
  const [targetPrice, setTargetPrice] = useState<number>(() => {
    return existingAlert?.target_price ?? Math.round(currentPrice * 0.9);
  });

  const [isEditing, setIsEditing] = useState<boolean>(!existingAlert);

  if (!isOpen) return null;

  const presets = [
    { label: '-5%', discount: 0.05 },
    { label: '-10%', discount: 0.10 },
    { label: '-15%', discount: 0.15 },
    { label: '-20%', discount: 0.20 },
  ];

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (targetPrice <= 0) {
      showToast(t('Please enter a valid target price greater than ৳0', '০ টাকার বেশি সঠিক লক্ষ্যমূল্য লিখুন'), 'warning');
      return;
    }

    setPriceAlert(product.id, targetPrice);
    setIsEditing(false);
    onClose();
  };

  const handleDelete = () => {
    removePriceAlert(product.id);
    onClose();
  };

  const handleTestSimulate = () => {
    const alertTarget = existingAlert ? existingAlert.target_price : targetPrice;
    simulatePriceDrop(product.id, alertTarget);
    onClose();
  };

  const savingsAmount = Math.max(0, currentPrice - targetPrice);
  const savingsPercent = currentPrice > 0 ? Math.round((savingsAmount / currentPrice) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fade-in">
      <div className="bg-white dark:bg-slate-800 rounded-3xl max-w-md w-full p-6 sm:p-7 space-y-5 shadow-2xl border border-border">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border pb-3.5">
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300">
              <BellRing className="w-5 h-5" />
            </span>
            <div>
              <h3 className="text-base sm:text-lg font-bold text-ink">
                {t('Set Price Drop Alert', 'মূল্য হ্রাস সতর্কতা')}
              </h3>
              <p className="text-[11px] text-muted">
                {t('Receive real-time notifications when the price drops', 'দাম কমলে সরাসরি নোটিফিকেশন পান')}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 hover:text-ink"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Product Summary Mini Card */}
        <div className="flex items-center gap-3 p-3 rounded-2xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700">
          <img
            src={product.image}
            alt={product.name}
            className="w-14 h-14 rounded-xl object-cover bg-white border border-slate-200 shrink-0"
          />
          <div className="flex-1 min-w-0">
            <h4 className="text-xs font-bold text-ink truncate">
              {language === 'bn' && product.name_bn ? product.name_bn : product.name}
            </h4>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-xs text-muted">{t('Current Price:', 'বর্তমান দর:')}</span>
              <span className="text-sm font-black text-primary">
                {formatPrice(currentPrice)}
              </span>
            </div>
          </div>
        </div>

        {/* Existing Active Alert Status */}
        {existingAlert && !isEditing ? (
          <div className="space-y-4">
            <div className="p-4 rounded-2xl bg-amber-50/80 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-amber-900 dark:text-amber-200">
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  <span>{t('Alert Active & Monitoring', 'সতর্কতা সক্রিয় ও পর্যবেক্ষণাধীন')}</span>
                </span>
                <span className="text-[10px] text-muted">
                  Set on {new Date(existingAlert.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="flex items-baseline justify-between pt-1">
                <div>
                  <span className="text-[11px] text-slate-600 dark:text-slate-400 block">
                    {t('Target Price', 'আপনার লক্ষ্যমূল্য')}
                  </span>
                  <span className="text-xl font-black text-ink dark:text-white">
                    {formatPrice(existingAlert.target_price)}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[11px] text-emerald-600 font-bold block">
                    {currentPrice > existingAlert.target_price
                      ? `Save ${formatPrice(currentPrice - existingAlert.target_price)} (-${Math.round(((currentPrice - existingAlert.target_price) / currentPrice) * 100)}%)`
                      : 'Target Reached!'}
                  </span>
                  <span className="text-[10px] text-muted">
                    {currentPrice <= existingAlert.target_price ? 'Triggered!' : 'Waiting for drop'}
                  </span>
                </div>
              </div>
            </div>

            {/* Test Button for Immediate Evaluation */}
            <div className="p-3.5 rounded-2xl bg-blue-50/70 dark:bg-blue-950/40 border border-blue-200/80 dark:border-blue-800/80 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-blue-900 dark:text-blue-300">
                <Zap className="w-3.5 h-3.5 text-blue-600" />
                <span>{t('Instant Notification Simulator', 'তাৎক্ষণিক নোটিফিকেশন টেস্ট')}</span>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                {t(
                  `Simulate a marketplace price drop to ৳${existingAlert.target_price} to immediately verify the real-time notification alert.`,
                  `বাজারদর হ্রাস টেস্ট করে দেখতে পারেন কিভাবে দাম ৳${existingAlert.target_price}-এ নামলে নোটিফিকেশন আসে।`
                )}
              </p>
              <button
                type="button"
                onClick={handleTestSimulate}
                className="w-full py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-xs transition-colors flex items-center justify-center gap-1.5"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>{t('⚡ Test Notification (Simulate Price Drop)', '⚡ নোটিফিকেশন টেস্ট করুন (মূল্য হ্রাস)')}</span>
              </button>
            </div>

            {/* Actions: Edit / Delete */}
            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="flex-1 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-colors"
              >
                {t('Change Target Price', 'লক্ষ্যমূল্য পরিবর্তন')}
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="p-2.5 rounded-xl border border-rose-200 hover:bg-rose-50 text-rose-600 text-xs font-bold transition-colors"
                title="Delete Price Alert"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          /* Set or Edit Target Price Form */
          <form onSubmit={handleSave} className="space-y-4">
            {/* Quick Discount Presets */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block">
                {t('Quick Presets (% Below Current):', 'দ্রুত নির্বাচন (বর্তমান দরের চেয়ে ছাড়):')}
              </label>
              <div className="grid grid-cols-4 gap-2">
                {presets.map((preset) => {
                  const calculated = Math.round(currentPrice * (1 - preset.discount));
                  const isSelected = targetPrice === calculated;
                  return (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => setTargetPrice(calculated)}
                      className={`p-2 rounded-xl text-xs font-bold border transition-all ${
                        isSelected
                          ? 'bg-primary text-white border-primary shadow-xs'
                          : 'bg-slate-50 dark:bg-slate-700/60 border-slate-200 dark:border-slate-600 text-slate-700 dark:text-slate-200 hover:border-primary'
                      }`}
                    >
                      <span className="block">{preset.label}</span>
                      <span className={`text-[10px] font-normal block ${isSelected ? 'text-blue-100' : 'text-slate-400'}`}>
                        ৳{calculated}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Target Price Numeric Input */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                  {t('Target Price (৳ BDT):', 'আপনার লক্ষ্যমূল্য (টাকা):')}
                </label>
                {savingsAmount > 0 && (
                  <span className="text-[11px] font-bold text-emerald-600">
                    Save {formatPrice(savingsAmount)} ({savingsPercent}%)
                  </span>
                )}
              </div>
              <div className="relative flex items-center">
                <span className="absolute left-3.5 font-bold text-slate-400 text-sm">৳</span>
                <input
                  type="number"
                  min={1}
                  max={currentPrice * 2}
                  value={targetPrice}
                  onChange={(e) => setTargetPrice(Number(e.target.value))}
                  required
                  className="w-full pl-8 pr-4 py-2.5 text-base font-black border border-slate-200 dark:border-slate-700 rounded-xl bg-slate-50 dark:bg-slate-900 text-ink dark:text-white focus:bg-white focus:outline-hidden focus:border-primary"
                />
              </div>
              <p className="text-[11px] text-muted">
                {targetPrice >= currentPrice
                  ? t('Target is at or above current price! An alert will trigger immediately upon saving.', 'লক্ষ্য বর্তমান দরের সমান বা বেশি! সেভ করলেই সঙ্গে সঙ্গে নোটিফিকেশন যাবে।')
                  : t(`We'll notify you when the price drops to ৳${targetPrice} or lower.`, `দর ৳${targetPrice} বা তার নিচে নামলে নোটিফিকেশন পাবেন।`)}
              </p>
            </div>

            {/* Notification Channel Information */}
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-600 dark:text-slate-300 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>
                {t(
                  'NexHaat monitors seller prices and flash deals 24/7 to guarantee you never miss a drop.',
                  'নেক্সহাট সার্বক্ষণিক পণ্যের দর পর্যবেক্ষণ করে যেন আপনি কোনো মূল্য হ্রাস মিস না করেন।'
                )}
              </span>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  if (existingAlert) setIsEditing(false);
                  else onClose();
                }}
                className="flex-1 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition-colors"
              >
                {t('Cancel', 'বাতিল')}
              </button>
              <button
                type="submit"
                className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-bold shadow-xs transition-colors"
              >
                {t('Save Price Alert', 'সতর্কতা সক্রিয় করুন')}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
