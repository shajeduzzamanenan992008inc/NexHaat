import React, { useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { Product } from '../types';
import { useApp } from '../context/AppContext';
import { getDetailedPriceTrend, DetailedTrendPoint } from '../lib/priceTrend';
import { PriceAlertModal } from './PriceAlertModal';
import {
  TrendingDown,
  TrendingUp,
  Sparkles,
  Bell,
  BellRing,
  Calendar,
  ArrowDownRight,
  Info,
  ShieldCheck,
} from 'lucide-react';

interface PriceTrendChartProps {
  product: Product;
}

export const PriceTrendChart: React.FC<PriceTrendChartProps> = ({ product }) => {
  const { formatPrice, getPriceAlert, t, language } = useApp();
  const [timeframe, setTimeframe] = useState<'7d' | '14d' | '30d'>('30d');
  const [showAlertModal, setShowAlertModal] = useState(false);

  const trendData = getDetailedPriceTrend(product, timeframe);
  const existingAlert = getPriceAlert(product.id);
  const isAlertActive = Boolean(existingAlert && existingAlert.is_active);

  // Compute Y-Axis bounds with padding so line doesn't hit top or bottom edges
  const minVal = Math.floor(trendData.lowestPrice * 0.95);
  const maxVal = Math.ceil(trendData.highestPrice * 1.05);

  // Custom Recharts Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const pt: DetailedTrendPoint = payload[0].payload;
    const priceDiffAvg = pt.price - trendData.averagePrice;
    const isBelowAvg = priceDiffAvg < 0;

    return (
      <div className="bg-slate-900 text-white p-3 rounded-2xl shadow-xl border border-slate-700 text-xs space-y-1.5 min-w-[170px] pointer-events-none z-50">
        <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-1.5">
          <span className="font-semibold text-slate-300">
            {language === 'bn' ? pt.dateBn : pt.date}
          </span>
          {pt.isCurrent && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-black uppercase bg-primary text-white">
              {t('Today', 'আজ')}
            </span>
          )}
          {pt.isLowest && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-black uppercase bg-emerald-500 text-white">
              {t('Low', 'সর্বনিম্ন')}
            </span>
          )}
        </div>

        <div className="flex items-baseline justify-between pt-0.5">
          <span className="text-slate-400 text-[11px]">{t('Price:', 'দর:')}</span>
          <span className="text-sm font-black text-white">{formatPrice(pt.price)}</span>
        </div>

        {priceDiffAvg !== 0 && (
          <div className="flex items-center justify-between text-[10px] text-slate-300">
            <span>{t('Vs 30D Average:', '৩০ দিনের গড়ের সাথে:')}</span>
            <span className={`font-bold ${isBelowAvg ? 'text-emerald-400' : 'text-amber-400'}`}>
              {isBelowAvg ? `-${formatPrice(Math.abs(priceDiffAvg))}` : `+${formatPrice(priceDiffAvg)}`}
            </span>
          </div>
        )}

        {pt.eventNote && (
          <div className="text-[10px] text-slate-400 italic pt-1 border-t border-slate-800/80">
            • {language === 'bn' && pt.eventNoteBn ? pt.eventNoteBn : pt.eventNote}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-3xl p-5 sm:p-6 border border-border shadow-xs space-y-5">
      {/* Chart Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-xl bg-blue-100 dark:bg-blue-900/50 text-primary">
              <TrendingDown className="w-4 h-4" />
            </span>
            <h3 className="text-base sm:text-lg font-bold text-ink">
              {t('Price Trend & Historical Analysis', 'মূল্য পরিবর্তন ও ঐতিহাসিক ট্রেন্ড')}
            </h3>
          </div>
          <p className="text-xs text-muted mt-0.5">
            {t(
              'Visual price history chart powered by Recharts to identify optimal buying opportunities.',
              'স্বচ্ছ ও যৌক্তিক ক্রয়ের জন্য রিখার্টস চার্টের মাধ্যমে অতীতের মূল্য বিশ্লেষণ।'
            )}
          </p>
        </div>

        {/* Timeframe Filter Buttons */}
        <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800 p-1 rounded-2xl self-start sm:self-auto">
          {[
            { id: '7d', label: t('7 Days', '৭ দিন') },
            { id: '14d', label: t('14 Days', '১৪ দিন') },
            { id: '30d', label: t('30 Days', '৩০ দিন') },
          ].map((tf) => (
            <button
              key={tf.id}
              type="button"
              onClick={() => setTimeframe(tf.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                timeframe === tf.id
                  ? 'bg-white dark:bg-slate-700 text-primary shadow-xs'
                  : 'text-slate-600 dark:text-slate-300 hover:text-ink'
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Buying Decision Indicator Banner */}
      <div
        className={`p-4 rounded-2xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-3 ${
          trendData.isAtLowest
            ? 'bg-emerald-50/90 border-emerald-200 text-emerald-950'
            : trendData.trendDirection === 'falling'
            ? 'bg-blue-50/90 border-blue-200 text-blue-950'
            : 'bg-slate-50 border-slate-200 text-slate-800'
        }`}
      >
        <div className="flex items-start gap-3">
          <span
            className={`p-2 rounded-xl mt-0.5 shrink-0 ${
              trendData.isAtLowest
                ? 'bg-emerald-200 text-emerald-800'
                : 'bg-blue-200 text-blue-800'
            }`}
          >
            {trendData.isAtLowest ? <Sparkles className="w-5 h-5" /> : <Info className="w-5 h-5" />}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-extrabold">
                {trendData.isAtLowest
                  ? t('Great Deal: Lowest Price Recorded in 30 Days!', 'দারুণ অফার: বিগত ৩০ দিনের সর্বনিম্ন দর!')
                  : trendData.trendDirection === 'falling'
                  ? t('Price Dropping: Recommended Time to Buy', 'দর কমতির দিকে: ক্রয়ের জন্য অনুকূল সময়')
                  : t('Stable Market Price', 'স্থিতিশীল স্বাভাবিক বাজার দর')}
              </h4>
              {trendData.percentDropFromPeak > 0 && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-emerald-600 text-white">
                  -{trendData.percentDropFromPeak}% {t('vs Peak', 'সর্বোচ্চের চেয়ে')}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 leading-relaxed">
              {t(
                `Current price is ${formatPrice(trendData.currentPrice)}. ${
                  trendData.priceDropFromPeak > 0
                    ? `You save ${formatPrice(trendData.priceDropFromPeak)} compared to the period high of ${formatPrice(trendData.highestPrice)}.`
                    : 'Prices have remained stable across this evaluation period.'
                }`,
                `বর্তমান মূল্য ${formatPrice(trendData.currentPrice)}। ${
                  trendData.priceDropFromPeak > 0
                    ? `সর্বোচ্চ দর ${formatPrice(trendData.highestPrice)}-এর তুলনায় আপনি ${formatPrice(trendData.priceDropFromPeak)} সাশ্রয় করছেন।`
                    : 'এই সময়ে পণ্যের মূল্য স্থিতিশীল ছিল।'
                }`
              )}
            </p>
          </div>
        </div>

        {/* Set Price Drop Alert Button */}
        <div className="shrink-0 self-end md:self-auto">
          <button
            type="button"
            onClick={() => setShowAlertModal(true)}
            className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-xs ${
              isAlertActive
                ? 'bg-amber-100 text-amber-900 border border-amber-300'
                : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:border-primary hover:text-primary'
            }`}
          >
            {isAlertActive ? (
              <BellRing className="w-3.5 h-3.5 text-amber-600" />
            ) : (
              <Bell className="w-3.5 h-3.5" />
            )}
            <span>
              {isAlertActive
                ? t(`Alert Active (৳${existingAlert?.target_price})`, `সতর্কতা সক্রিয় (৳${existingAlert?.target_price})`)
                : t('Set Price Alert', 'মূল্য সতর্কতা সেট করুন')}
            </span>
          </button>
        </div>
      </div>

      {/* Stats Summary Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-2xl bg-surface-raised border border-border">
          <span className="text-[11px] font-semibold text-muted block">
            {t('Current Price', 'বর্তমান দর')}
          </span>
          <span className="text-lg font-black text-ink mt-0.5 block">
            {formatPrice(trendData.currentPrice)}
          </span>
          <span className="text-[11px] font-bold text-emerald-600 flex items-center gap-0.5 mt-0.5">
            <ArrowDownRight className="w-3 h-3" />
            <span>{trendData.isAtLowest ? t('Lowest recorded', 'সর্বনিম্ন দর') : t('Active listing', 'চলমান দর')}</span>
          </span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-raised border border-border">
          <span className="text-[11px] font-semibold text-muted block">
            {t('Period Lowest', 'সর্বনিম্ন দর')}
          </span>
          <span className="text-lg font-black text-emerald-700 mt-0.5 block">
            {formatPrice(trendData.lowestPrice)}
          </span>
          <span className="text-[11px] text-slate-500 mt-0.5 block">
            {trendData.isAtLowest
              ? t('Matching now!', 'এখনই পাওয়া যাচ্ছে!')
              : `+${formatPrice(trendData.currentPrice - trendData.lowestPrice)} ${t('from low', 'সর্বনিম্ন থেকে')}`}
          </span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-raised border border-border">
          <span className="text-[11px] font-semibold text-muted block">
            {t('Period Average', 'গড় দর')}
          </span>
          <span className="text-lg font-black text-ink mt-0.5 block">
            {formatPrice(trendData.averagePrice)}
          </span>
          <span className="text-[11px] text-slate-500 mt-0.5 block">
            {t('Baseline benchmark', 'গড় বাজার মূল্য')}
          </span>
        </div>

        <div className="p-3.5 rounded-2xl bg-surface-raised border border-border">
          <span className="text-[11px] font-semibold text-muted block">
            {t('Period Peak', 'সর্বোচ্চ দর')}
          </span>
          <span className="text-lg font-black text-slate-500 mt-0.5 block">
            {formatPrice(trendData.highestPrice)}
          </span>
          <span className="text-[11px] text-emerald-600 font-semibold mt-0.5 block">
            {t('Save', 'সাশ্রয়')} {formatPrice(trendData.priceDropFromPeak)} {t('vs peak', 'সর্বোচ্চ থেকে')}
          </span>
        </div>
      </div>

      {/* Recharts Container */}
      <div className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-900/50 border border-border space-y-2">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-300">
          <span className="flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-primary" />
            <span>
              {t(
                `Price Movement (${timeframe.toUpperCase()})`,
                `মূল্য গতিপ্রকৃতি (${timeframe === '7d' ? '৭ দিন' : timeframe === '14d' ? '১৪ দিন' : '৩০ দিন'})`
              )}
            </span>
          </span>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-bold">
              <span className="w-2.5 h-0.5 bg-amber-500 inline-block border-b border-dashed border-amber-600"></span>
              {t('Avg:', 'গড়:')} {formatPrice(trendData.averagePrice)}
            </span>
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-bold">
              <span className="w-2.5 h-0.5 bg-emerald-500 inline-block"></span>
              {t('Low:', 'সর্বনিম্ন:')} {formatPrice(trendData.lowestPrice)}
            </span>
          </div>
        </div>

        <div className="w-full h-64 pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={trendData.points}
              margin={{ top: 12, right: 16, left: -10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="nexhaatPriceGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0a66c2" stopOpacity={0.32} />
                  <stop offset="95%" stopColor="#0a66c2" stopOpacity={0.0} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" opacity={0.7} />

              <XAxis
                dataKey={language === 'bn' ? 'dayLabelBn' : 'dayLabel'}
                tickLine={false}
                axisLine={{ stroke: '#cbd5e1' }}
                tick={{ fontSize: 11, fill: '#64748b' }}
                dy={6}
              />

              <YAxis
                domain={[minVal, maxVal]}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(val) => `৳${val}`}
                dx={-4}
              />

              <Tooltip content={<CustomTooltip />} />

              {/* Reference line for 30-day average */}
              <ReferenceLine
                y={trendData.averagePrice}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                strokeWidth={1.5}
              />

              {/* Reference line for lowest price */}
              <ReferenceLine
                y={trendData.lowestPrice}
                stroke="#10b981"
                strokeDasharray="2 2"
                strokeWidth={1.5}
              />

              <Area
                type="monotone"
                dataKey="price"
                stroke="#0a66c2"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#nexhaatPriceGrad)"
                activeDot={{ r: 6, stroke: '#ffffff', strokeWidth: 2, fill: '#0a66c2' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-800">
          <span className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            {t('Verified authentic marketplace pricing data', 'যাচাইকৃত রিয়েল-টাইম মার্কেটপ্লেস দর')}
          </span>
          <span>{t('Currency: BDT (৳)', 'মুদ্রা: টাকা (৳)')}</span>
        </div>
      </div>

      {/* Target Price Drop Alert Modal */}
      <PriceAlertModal
        product={product}
        isOpen={showAlertModal}
        onClose={() => setShowAlertModal(false)}
      />
    </div>
  );
};
