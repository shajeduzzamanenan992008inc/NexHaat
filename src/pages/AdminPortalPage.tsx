import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Shield, Check, X, Layers, Users, ShoppingCart, 
  Activity, AlertCircle, Plus, Sparkles, Building, Percent, RefreshCw,
  Search, TrendingUp 
} from 'lucide-react';
import { SearchAnalyticsDashboard } from '../components/SearchAnalyticsDashboard';

export const AdminPortalPage: React.FC = () => {
  const { 
    products, 
    orders, 
    categories, 
    approveProduct, 
    formatPrice, 
    showToast, 
    t 
  } = useApp();

  const [activeTab, setActiveTab] = useState<'search-trends' | 'moderation' | 'categories' | 'warehouses' | 'commissions' | 'audit'>('search-trends');

  const totalGMV = orders.reduce((sum, ord) => sum + ord.total_amount, 0);

  const warehouses = [
    { id: 'wh-1', name: 'Karwan Bazar Central Fulfillment Hub', location: 'Dhaka', capacity: '88% Full', activeStaff: 28, dispatchTime: '18 mins' },
    { id: 'wh-2', name: 'Mirpur Express Station', location: 'Dhaka', capacity: '62% Full', activeStaff: 14, dispatchTime: '12 mins' },
    { id: 'wh-3', name: 'Uttara Hyper-Local Depo', location: 'Dhaka', capacity: '71% Full', activeStaff: 16, dispatchTime: '15 mins' },
    { id: 'wh-4', name: 'Khatunganj Commercial Depot', location: 'Chittagong', capacity: '54% Full', activeStaff: 22, dispatchTime: '24 mins' },
  ];

  const [commissions, setCommissions] = useState([
    { category: 'Fruits & Vegetables', rate: 4.5 },
    { category: 'Meat & Seafood', rate: 5.0 },
    { category: 'Rice, Grains & Pasta', rate: 3.5 },
    { category: 'Dairy & Eggs', rate: 4.0 },
    { category: 'Electronics & Gadgets', rate: 8.5 },
    { category: 'Fashion & Handloom', rate: 10.0 },
  ]);

  const auditEvents = [
    { id: 1, action: 'Order Placed', details: 'Order NH-2026-8821 confirmed with bKash payment', time: '10 mins ago' },
    { id: 2, action: 'Prime Subscription', details: 'Tanvir Rahman renewed Yearly NexHaat Prime', time: '22 mins ago' },
    { id: 3, action: 'Product Moderated', details: 'Dinajpur Aromatic Rice approved for listing', time: '35 mins ago' },
    { id: 4, action: 'Seller Ad Campaign', details: 'Dhaka Fresh launched "Aromatic Rice Promo" (৳500/day)', time: '1 hr ago' },
    { id: 5, action: 'Rider Settlement', details: 'Kamal Hossain cleared ৳2,800 COD cash at Mirpur Hub', time: '3 hrs ago' },
  ];

  const handleUpdateCommission = (idx: number, newRate: number) => {
    setCommissions(prev => {
      const copy = [...prev];
      copy[idx].rate = newRate;
      return copy;
    });
    showToast('Commission rate updated successfully');
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="p-6 sm:p-8 rounded-3xl bg-slate-900 text-white shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 font-bold text-xs mb-2">
            <Shield className="w-4 h-4" />
            <span>{t('AMAZON-GRADE SUPER ADMIN HUB', 'আমাজন-মানের সুপার অ্যাডমিন হাব')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white">
            NexHaat Platform Operations Control
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-1">
            Governance, commission splits, Prime membership analytics, warehouse oversight & audit stream
          </p>
        </div>

        <div className="px-4 py-2 rounded-2xl bg-slate-800 text-xs font-bold text-emerald-400 border border-slate-700 flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>Platform Health: Operational (100%)</span>
        </div>
      </div>

      {/* High-level KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <span className="text-xs text-muted block mb-1">Platform GMV (Monthly)</span>
          <p className="text-xl sm:text-2xl font-black text-ink">{formatPrice(totalGMV + 248000)}</p>
          <span className="text-[11px] text-emerald-600 font-bold mt-1 block">↑ 24.5% vs last month</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <span className="text-xs text-muted block mb-1">NexHaat Prime Subscribers</span>
          <p className="text-xl sm:text-2xl font-black text-amber-500">14,820 Members</p>
          <span className="text-[11px] text-primary font-bold mt-1 block">৳2.9M recurring ARR</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <span className="text-xs text-muted block mb-1">Total Platform Orders</span>
          <p className="text-xl sm:text-2xl font-black text-ink">{orders.length + 840}</p>
          <span className="text-[11px] text-slate-500 mt-1 block">99.1% on-time 3-hr delivery</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <span className="text-xs text-muted block mb-1">Active Merchants</span>
          <p className="text-xl sm:text-2xl font-black text-ink">48 Stores</p>
          <span className="text-[11px] text-emerald-600 font-bold mt-1 block">4 hubs active</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('search-trends')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 flex items-center gap-1.5 ${
            activeTab === 'search-trends' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          <Search className="w-3.5 h-3.5" />
          <span>User Search Trends & Keywords</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-400 text-slate-900 font-black">
            LIVE
          </span>
        </button>

        <button
          onClick={() => setActiveTab('moderation')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'moderation' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Catalog Review ({products.length})
        </button>

        <button
          onClick={() => setActiveTab('warehouses')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'warehouses' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Fulfillment Hubs ({warehouses.length})
        </button>

        <button
          onClick={() => setActiveTab('commissions')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'commissions' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Marketplace Commission Rates
        </button>

        <button
          onClick={() => setActiveTab('categories')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'categories' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Categories ({categories.length})
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'audit' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Security Audit Trail
        </button>
      </div>

      {/* Tab: Search Trends & Keyword Analytics Dashboard */}
      {activeTab === 'search-trends' && (
        <SearchAnalyticsDashboard />
      )}

      {/* Tab: Catalog Moderation */}
      {activeTab === 'moderation' && (
        <div className="bg-white rounded-3xl border border-border shadow-card overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-sm text-ink">Merchant Listings Review Queue</h3>
              <p className="text-xs text-muted">Verify food safety standards, accurate descriptions, and pricing</p>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {products.map((p) => (
              <div key={p.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <img src={p.image} alt={p.name} className="w-12 h-12 rounded-xl object-cover bg-slate-50 shrink-0" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs text-ink">{p.name}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        p.moderation_status === 'approved'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}>
                        {p.moderation_status || 'approved'}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted">
                      SKU: <strong className="font-mono">{p.sku}</strong> • Seller: <strong>{p.seller_name}</strong> • Price: {formatPrice(p.price)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => approveProduct(p.id, true)}
                    className="px-3.5 py-1.5 rounded-xl bg-emerald-100 hover:bg-emerald-200 text-emerald-800 text-xs font-bold flex items-center gap-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Approve</span>
                  </button>
                  <button
                    onClick={() => approveProduct(p.id, false)}
                    className="px-3.5 py-1.5 rounded-xl bg-rose-100 hover:bg-rose-200 text-rose-800 text-xs font-bold flex items-center gap-1"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Fulfillment Warehouses */}
      {activeTab === 'warehouses' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {warehouses.map(wh => (
            <div key={wh.id} className="p-5 rounded-3xl bg-white border border-border shadow-card space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="font-bold text-sm text-ink">{wh.name}</h4>
                  <p className="text-xs text-muted">{wh.location} Region</p>
                </div>
                <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-primary-light text-primary">
                  {wh.capacity}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
                <div>Active Staff: <strong>{wh.activeStaff}</strong></div>
                <div>Avg Dispatch: <strong>{wh.dispatchTime}</strong></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab: Commissions */}
      {activeTab === 'commissions' && (
        <div className="bg-white rounded-3xl border border-border shadow-card p-6 space-y-4">
          <h3 className="font-bold text-sm text-ink flex items-center gap-2">
            <Percent className="w-4 h-4 text-primary" />
            <span>Marketplace Seller Commission Matrix</span>
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 border-b">
                  <th className="py-2.5 px-3">Product Category</th>
                  <th className="py-2.5 px-3">Platform Commission Rate</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {commissions.map((comm, idx) => (
                  <tr key={comm.category}>
                    <td className="py-2.5 px-3 font-bold text-ink">{comm.category}</td>
                    <td className="py-2.5 px-3 font-semibold text-primary">{comm.rate}%</td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => {
                          const val = prompt(`New commission rate for ${comm.category} (%):`, String(comm.rate));
                          if (val !== null) handleUpdateCommission(idx, Number(val) || comm.rate);
                        }}
                        className="text-xs text-primary font-bold hover:underline"
                      >
                        Adjust Rate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Categories */}
      {activeTab === 'categories' && (
        <div className="bg-white rounded-3xl border border-border shadow-card p-6 space-y-6">
          <h3 className="font-bold text-sm text-ink">Marketplace Taxonomy</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {categories.map((c) => (
              <div key={c.id} className="p-3.5 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-between text-xs">
                <div>
                  <strong className="text-ink">{c.name}</strong>
                  <p className="text-[11px] text-slate-500 font-mono">slug: {c.slug}</p>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-primary">
                  Active
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Audit Log */}
      {activeTab === 'audit' && (
        <div className="bg-white rounded-3xl border border-border shadow-card p-6 space-y-4">
          <h3 className="font-bold text-sm text-ink flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            <span>Real-Time Audit & Security Event Stream</span>
          </h3>

          <div className="divide-y divide-slate-100">
            {auditEvents.map((evt) => (
              <div key={evt.id} className="py-3 flex items-center justify-between gap-4 text-xs">
                <div>
                  <span className="font-bold text-ink mr-2">{evt.action}</span>
                  <span className="text-slate-600">{evt.details}</span>
                </div>
                <span className="text-[11px] text-slate-400 shrink-0">{evt.time}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
