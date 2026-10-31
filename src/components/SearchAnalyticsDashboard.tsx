import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  Search,
  TrendingUp,
  ArrowUpRight,
  Filter,
  Download,
  AlertTriangle,
  Sparkles,
  ShoppingBag,
  MousePointer,
  PieChart as PieIcon,
  BarChart3,
  Calendar,
  Layers,
  CheckCircle2,
} from 'lucide-react';
import {
  KeywordPerformance,
  computeSearchMetricsSummary,
  filterKeywordsByQuery,
  DateRange,
  getDateRangePreset,
  formatDateRangeDisplay,
  generateTrendDataForDateRange,
  scaleKeywordsForDateRange,
} from '../lib/searchAnalytics';
import { DateRangePicker } from './DateRangePicker';

// Sample curated marketplace search trend data
const INITIAL_KEYWORDS_DATA: KeywordPerformance[] = [
  {
    keyword: 'Padma Ilish',
    keyword_bn: 'পদ্মার ইলিশ',
    category: 'Meat & Seafood',
    searchVolume: 12480,
    clickThroughRate: 82.4,
    conversionRate: 18.6,
    revenueGenerated: 1840000,
    trend: 'trending',
  },
  {
    keyword: 'Chinigura Rice',
    keyword_bn: 'চিনিগুঁড়া চাল',
    category: 'Rice, Grains & Pasta',
    searchVolume: 9240,
    clickThroughRate: 74.1,
    conversionRate: 16.2,
    revenueGenerated: 890000,
    trend: 'trending',
  },
  {
    keyword: 'Cold-Pressed Mustard Oil',
    keyword_bn: 'ঘানির খাঁটি সরিষার তেল',
    category: 'Spices & Seasonings',
    searchVolume: 7850,
    clickThroughRate: 71.8,
    conversionRate: 14.5,
    revenueGenerated: 540000,
    trend: 'rising',
  },
  {
    keyword: 'Fazli Mango 5kg',
    keyword_bn: 'ফজলি আম ৫ কেজি',
    category: 'Fruits & Vegetables',
    searchVolume: 6920,
    clickThroughRate: 78.5,
    conversionRate: 15.8,
    revenueGenerated: 720000,
    trend: 'trending',
  },
  {
    keyword: 'Sundarbans Wild Honey',
    keyword_bn: 'সুন্দরবনের প্রাকৃতিক মধু',
    category: 'Snacks & Sweets',
    searchVolume: 5120,
    clickThroughRate: 68.2,
    conversionRate: 13.9,
    revenueGenerated: 460000,
    trend: 'rising',
  },
  {
    keyword: 'Deshi Gawa Ghee',
    keyword_bn: 'খাঁটি গাওয়া ঘি',
    category: 'Dairy & Eggs',
    searchVolume: 4380,
    clickThroughRate: 66.4,
    conversionRate: 12.8,
    revenueGenerated: 380000,
    trend: 'stable',
  },
  {
    keyword: 'Bogra Special Doi',
    keyword_bn: 'বগুড়ার স্পেশাল দই',
    category: 'Dairy & Eggs',
    searchVolume: 3890,
    clickThroughRate: 69.0,
    conversionRate: 14.1,
    revenueGenerated: 310000,
    trend: 'rising',
  },
  {
    keyword: 'Deshi Red Onion (Peyaj)',
    keyword_bn: 'দেশি লাল পেঁয়াজ',
    category: 'Fruits & Vegetables',
    searchVolume: 3410,
    clickThroughRate: 64.5,
    conversionRate: 11.2,
    revenueGenerated: 240000,
    trend: 'stable',
  },
  {
    keyword: 'Organic Dragonfruit Basket',
    keyword_bn: 'ড্রাগন ফল',
    category: 'Fruits & Vegetables',
    searchVolume: 1250,
    clickThroughRate: 12.0,
    conversionRate: 0.0,
    revenueGenerated: 0,
    trend: 'zero_result',
    zeroResultCount: 1250,
  },
  {
    keyword: 'Chinigura 25kg Sack (Bulk)',
    keyword_bn: 'চিনিগুঁড়া ২৫ কেজি বস্তা',
    category: 'Rice, Grains & Pasta',
    searchVolume: 890,
    clickThroughRate: 8.5,
    conversionRate: 0.0,
    revenueGenerated: 0,
    trend: 'zero_result',
    zeroResultCount: 890,
  },
  {
    keyword: 'Fresh Hilsa Fish Roe (Ilish Dim)',
    keyword_bn: 'ইলিশের ডিম',
    category: 'Meat & Seafood',
    searchVolume: 740,
    clickThroughRate: 6.0,
    conversionRate: 0.0,
    revenueGenerated: 0,
    trend: 'zero_result',
    zeroResultCount: 740,
  },
];

const SEARCH_VOLUME_HISTORY = [
  { date: 'Oct 24', searches: 3420, conversions: 520, mobile: 2450, desktop: 970 },
  { date: 'Oct 25', searches: 3890, conversions: 610, mobile: 2810, desktop: 1080 },
  { date: 'Oct 26', searches: 4210, conversions: 680, mobile: 3100, desktop: 1110 },
  { date: 'Oct 27', searches: 4890, conversions: 790, mobile: 3620, desktop: 1270 },
  { date: 'Oct 28', searches: 5120, conversions: 840, mobile: 3890, desktop: 1230 },
  { date: 'Oct 29', searches: 5840, conversions: 960, mobile: 4450, desktop: 1390 },
  { date: 'Oct 30', searches: 6450, conversions: 1080, mobile: 4980, desktop: 1470 },
];

const CATEGORY_SHARE_DATA = [
  { name: 'Meat & Seafood', searches: 13220, percentage: 32, color: '#2563eb' },
  { name: 'Rice & Grains', searches: 10130, percentage: 24, color: '#10b981' },
  { name: 'Fruits & Veg', searches: 8170, percentage: 20, color: '#f59e0b' },
  { name: 'Dairy & Sweets', searches: 5270, percentage: 13, color: '#8b5cf6' },
  { name: 'Spices & Oils', searches: 4580, percentage: 11, color: '#ec4899' },
];

const HOURLY_PEAK_DATA = [
  { hour: '6 AM', searches: 240 },
  { hour: '8 AM', searches: 820 },
  { hour: '10 AM', searches: 1650 }, // Morning bazaar peak
  { hour: '12 PM', searches: 1120 },
  { hour: '2 PM', searches: 780 },
  { hour: '4 PM', searches: 940 },
  { hour: '6 PM', searches: 1840 }, // Evening dinner peak
  { hour: '8 PM', searches: 1980 }, // Night rush
  { hour: '10 PM', searches: 890 },
];

export const SearchAnalyticsDashboard: React.FC = () => {
  const { formatPrice, t } = useApp();

  const [selectedRange, setSelectedRange] = useState<DateRange>(() => getDateRangePreset('last7days'));
  const [keywordFilter, setKeywordFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [activeTab, setActiveTab] = useState<'all' | 'top' | 'zero_result'>('all');

  // Scale keywords dynamically based on the chosen time period
  const scaledKeywords = useMemo(() => {
    return scaleKeywordsForDateRange(INITIAL_KEYWORDS_DATA, selectedRange);
  }, [selectedRange]);

  // Compute live summary statistics based on current date range
  const metrics = useMemo(
    () => computeSearchMetricsSummary(scaledKeywords),
    [scaledKeywords]
  );

  // Dynamic daily trend points for the selected date range
  const trendPoints = useMemo(() => {
    return generateTrendDataForDateRange(selectedRange);
  }, [selectedRange]);

  // Scaled category distribution based on total searches in this period
  const categoryShareData = useMemo(() => {
    const total = metrics.totalSearches || 1;
    const rawCategories = [
      { name: 'Meat & Seafood', weight: 0.32, color: '#2563eb' },
      { name: 'Rice & Grains', weight: 0.24, color: '#10b981' },
      { name: 'Fruits & Veg', weight: 0.20, color: '#f59e0b' },
      { name: 'Dairy & Sweets', weight: 0.13, color: '#8b5cf6' },
      { name: 'Spices & Oils', weight: 0.11, color: '#ec4899' },
    ];
    return rawCategories.map((c) => ({
      name: c.name,
      percentage: Math.round(c.weight * 100),
      searches: Math.round(total * c.weight),
      color: c.color,
    }));
  }, [metrics.totalSearches]);

  // Filtered keywords
  const filteredKeywords = useMemo(() => {
    let list = filterKeywordsByQuery(scaledKeywords, keywordFilter, categoryFilter);
    if (activeTab === 'top') {
      list = list.filter((k) => k.trend === 'trending' || k.trend === 'rising');
    } else if (activeTab === 'zero_result') {
      list = list.filter((k) => k.trend === 'zero_result');
    }
    return list;
  }, [scaledKeywords, keywordFilter, categoryFilter, activeTab]);

  // Top 6 keywords for the bar chart
  const topKeywordsChartData = useMemo(() => {
    return scaledKeywords
      .filter((k) => k.trend !== 'zero_result')
      .slice(0, 6)
      .map((k) => ({
        keyword: k.keyword.split(' ')[0],
        fullKeyword: k.keyword,
        searches: k.searchVolume,
        conversions: Math.round(k.searchVolume * (k.conversionRate / 100)),
        ctr: k.clickThroughRate,
      }));
  }, [scaledKeywords]);

  const handleExportCSV = () => {
    const headers = ['Keyword', 'Category', 'Search Volume', 'CTR (%)', 'Conversion Rate (%)', 'Revenue (BDT)', 'Trend'];
    const rows = filteredKeywords.map((k) => [
      `"${k.keyword}"`,
      `"${k.category}"`,
      k.searchVolume,
      k.clickThroughRate,
      k.conversionRate,
      k.revenueGenerated,
      k.trend,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `nexhaat_search_trends_${selectedRange.startDate}_to_${selectedRange.endDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-border dark:border-slate-800 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/40 text-primary">
              <Search className="w-4 h-4" />
            </span>
            <span className="text-xs font-black uppercase tracking-wider text-primary">
              Search Intelligence & Discovery
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-black text-ink dark:text-white">
            User Search Trends & Keyword Performance
          </h2>
          <p className="text-xs text-muted dark:text-slate-400 mt-0.5">
            Real-time intent analysis, search query volume, conversion funnels & zero-result demand detection
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {/* Interactive Date Range Picker */}
          <DateRangePicker value={selectedRange} onChange={setSelectedRange} />

          {/* Export button */}
          <button
            type="button"
            onClick={handleExportCSV}
            className="px-3.5 py-2 rounded-xl bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* KPI Overview Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5 sm:gap-4">
        {/* Total Searches */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted dark:text-slate-400">Total Search Volume</span>
            <span className="p-1 rounded-md bg-blue-50 dark:bg-blue-900/30 text-primary">
              <Search className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-ink dark:text-white">
            {metrics.totalSearches.toLocaleString()}
          </div>
          <span className="text-[11px] font-bold text-emerald-600 mt-1 flex items-center gap-0.5">
            <ArrowUpRight className="w-3 h-3" />
            <span>+19.4% vs last period</span>
          </span>
        </div>

        {/* Weighted Click-Through Rate */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted dark:text-slate-400">Search CTR</span>
            <span className="p-1 rounded-md bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600">
              <MousePointer className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-ink dark:text-white">
            {metrics.averageCTR}%
          </div>
          <span className="text-[11px] font-bold text-emerald-600 mt-1 flex items-center gap-0.5">
            <ArrowUpRight className="w-3 h-3" />
            <span>+4.2% high intent</span>
          </span>
        </div>

        {/* Search-to-Order Conversion */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted dark:text-slate-400">Search Conversion Rate</span>
            <span className="p-1 rounded-md bg-amber-50 dark:bg-amber-900/30 text-amber-600">
              <ShoppingBag className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-ink dark:text-white">
            {metrics.averageConversionRate}%
          </div>
          <span className="text-[11px] font-bold text-slate-500 mt-1 block">
            {metrics.totalConversions.toLocaleString()} orders generated
          </span>
        </div>

        {/* Search Attributed GMV */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted dark:text-slate-400">Search-Attributed GMV</span>
            <span className="p-1 rounded-md bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600">
              <TrendingUp className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-primary">
            {formatPrice(metrics.totalSearchRevenue)}
          </div>
          <span className="text-[11px] font-bold text-emerald-600 mt-1 block">
            64.2% of total platform GMV
          </span>
        </div>

        {/* Zero-Result Rate */}
        <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-xs col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted dark:text-slate-400">Zero-Result Rate</span>
            <span className="p-1 rounded-md bg-rose-50 dark:bg-rose-900/30 text-rose-600">
              <AlertTriangle className="w-3.5 h-3.5" />
            </span>
          </div>
          <div className="text-2xl font-black text-rose-600">
            {metrics.zeroResultRate}%
          </div>
          <span className="text-[11px] font-semibold text-slate-500 mt-1 block">
            Benchmark: &lt; 5.0% (Optimal)
          </span>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* AreaChart: Daily Search Query & Conversion Volume Over Time */}
        <div className="lg:col-span-8 p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-card space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h3 className="font-bold text-sm text-ink dark:text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                <span>Daily Search Volume & Order Conversions Trend</span>
              </h3>
              <p className="text-xs text-muted dark:text-slate-400">
                Data trajectory for {formatDateRangeDisplay(selectedRange)} ({trendPoints.length} day{trendPoints.length === 1 ? '' : 's'})
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-primary dark:text-blue-300">
                {trendPoints.length} Daily Points
              </span>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300">
                +18.4% WoW
              </span>
            </div>
          </div>

          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendPoints} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="searchGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="conversionGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Area
                  type="monotone"
                  dataKey="searches"
                  name="Total Searches"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#searchGradient)"
                />
                <Area
                  type="monotone"
                  dataKey="conversions"
                  name="Orders Placed"
                  stroke="#f59e0b"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#conversionGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* PieChart: Category Search Share */}
        <div className="lg:col-span-4 p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-card space-y-4">
          <div>
            <h3 className="font-bold text-sm text-ink dark:text-white flex items-center gap-2">
              <PieIcon className="w-4 h-4 text-amber-500" />
              <span>Search Volume by Category</span>
            </h3>
            <p className="text-xs text-muted dark:text-slate-400">
              Department intent distribution
            </p>
          </div>

          <div className="h-56 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryShareData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={4}
                  dataKey="searches"
                >
                  {categoryShareData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                  formatter={(value: any) => [`${Number(value || 0).toLocaleString()} searches`, 'Volume']}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-1.5 pt-1 border-t border-slate-100 dark:border-slate-800 text-xs">
            {categoryShareData.map((cat) => (
              <div key={cat.name} className="flex items-center justify-between text-slate-700 dark:text-slate-300">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cat.color }} />
                  <span className="truncate max-w-[130px]">{cat.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-ink dark:text-white">{cat.percentage}%</span>
                  <span className="text-[11px] text-muted">({cat.searches.toLocaleString()})</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Second Row: Top Performing Keywords Bar Chart & Hourly Peaks */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* BarChart: Top Keywords Volume vs Conversions */}
        <div className="lg:col-span-8 p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-sm text-ink dark:text-white flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-emerald-600" />
                <span>Top-Performing Keywords (Volume vs. Completed Orders)</span>
              </h3>
              <p className="text-xs text-muted dark:text-slate-400">
                Direct correlation between shopper queries and purchases
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topKeywordsChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="keyword" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="searches" name="Search Volume" fill="#2563eb" radius={[6, 6, 0, 0]} />
                <Bar dataKey="conversions" name="Orders Completed" fill="#10b981" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Hourly Peak Distribution */}
        <div className="lg:col-span-4 p-5 sm:p-6 rounded-3xl bg-white dark:bg-slate-900 border border-border dark:border-slate-800 shadow-card space-y-4">
          <div>
            <h3 className="font-bold text-sm text-ink dark:text-white flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-500" />
              <span>Hourly Search Traffic Peaks</span>
            </h3>
            <p className="text-xs text-muted dark:text-slate-400">
              Identifies morning & evening hyper-local shopping spikes
            </p>
          </div>

          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={HOURLY_PEAK_DATA} margin={{ top: 10, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#fff',
                    fontSize: '11px',
                  }}
                />
                <Bar dataKey="searches" name="Hourly Queries" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="p-3 rounded-2xl bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900 text-xs text-indigo-900 dark:text-indigo-200">
            <strong>Key Insight:</strong> 64% of fresh produce & fish searches concentrate around 10:00 AM (morning cooking) and 8:00 PM (next-day delivery orders).
          </div>
        </div>
      </div>

      {/* Keyword Performance Table & Zero-Result Demands */}
      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-border dark:border-slate-800 shadow-card overflow-hidden">
        {/* Table Filters */}
        <div className="p-5 border-b border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('all')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'all'
                  ? 'bg-primary text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
              }`}
            >
              All Keywords ({INITIAL_KEYWORDS_DATA.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('top')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'top'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
              }`}
            >
              Top Performers
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('zero_result')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1 ${
                activeTab === 'zero_result'
                  ? 'bg-rose-600 text-white shadow-xs'
                  : 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300'
              }`}
            >
              <AlertTriangle className="w-3 h-3" />
              <span>Zero-Result Demands (3)</span>
            </button>
          </div>

          <div className="flex items-center gap-3">
            {/* Search filter input */}
            <div className="relative">
              <input
                type="text"
                value={keywordFilter}
                onChange={(e) => setKeywordFilter(e.target.value)}
                placeholder="Filter keywords..."
                className="pl-8 pr-3 py-1.5 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-hidden focus:border-primary text-ink dark:text-white"
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            </div>

            {/* Category filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 focus:outline-hidden"
            >
              <option value="all">All Categories</option>
              <option value="Meat & Seafood">Meat & Seafood</option>
              <option value="Rice, Grains & Pasta">Rice, Grains & Pasta</option>
              <option value="Fruits & Vegetables">Fruits & Vegetables</option>
              <option value="Spices & Seasonings">Spices & Seasonings</option>
              <option value="Dairy & Eggs">Dairy & Eggs</option>
              <option value="Snacks & Sweets">Snacks & Sweets</option>
            </select>
          </div>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-500 uppercase tracking-wider text-[11px] font-bold border-b border-slate-100 dark:border-slate-800">
              <tr>
                <th className="py-3 px-4">Search Keyword / Query</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-right">Search Volume</th>
                <th className="py-3 px-4 text-right">CTR</th>
                <th className="py-3 px-4 text-right">Conversion Rate</th>
                <th className="py-3 px-4 text-right">Attributed GMV</th>
                <th className="py-3 px-4 text-center">Trend Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredKeywords.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-muted">
                    No matching search keywords found.
                  </td>
                </tr>
              ) : (
                filteredKeywords.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="py-3 px-4">
                      <div>
                        <span className="font-bold text-ink dark:text-white block">{item.keyword}</span>
                        {item.keyword_bn && (
                          <span className="text-[11px] text-muted dark:text-slate-400">{item.keyword_bn}</span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold text-[11px]">
                        {item.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-ink dark:text-white">
                      {item.searchVolume.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-slate-700 dark:text-slate-300">
                      {item.clickThroughRate}%
                    </td>
                    <td className="py-3 px-4 text-right">
                      {item.conversionRate > 0 ? (
                        <span className="font-bold text-emerald-600 dark:text-emerald-400">
                          {item.conversionRate}%
                        </span>
                      ) : (
                        <span className="text-slate-400">0%</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-primary">
                      {item.revenueGenerated > 0 ? formatPrice(item.revenueGenerated) : '৳0.00'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {item.trend === 'trending' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300">
                          <TrendingUp className="w-3 h-3 text-amber-600" />
                          <span>Trending 🔥</span>
                        </span>
                      ) : item.trend === 'rising' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300">
                          <ArrowUpRight className="w-3 h-3 text-emerald-600" />
                          <span>Rising ⬆</span>
                        </span>
                      ) : item.trend === 'zero_result' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-300">
                          <AlertTriangle className="w-3 h-3 text-rose-600" />
                          <span>Unmet Demand</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                          <span>Stable</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Unmet Demand Action Footer */}
        <div className="p-4 bg-slate-50 dark:bg-slate-800/60 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
            <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
            <span>
              <strong>Smart Merchant Notification:</strong> 3 unmet product queries detected with over 2,800 monthly searches. You can broadcast catalog sourcing requests to regional sellers.
            </span>
          </div>
          <button
            type="button"
            onClick={() => alert('Broadcasting sourcing request to 48 verified merchants across Dhaka & Chittagong...')}
            className="px-3.5 py-1.5 rounded-xl bg-primary text-white font-bold text-xs hover:bg-primary-hover shrink-0 transition-colors shadow-xs"
          >
            Broadcast to Sellers
          </button>
        </div>
      </div>
    </div>
  );
};
