import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Product } from '../types';
import { 
  Store, Package, TrendingUp, DollarSign, Plus, Edit, 
  Trash2, CheckCircle2, Clock, Truck, Tag, AlertCircle, 
  Sparkles, Megaphone, Upload, FileText 
} from 'lucide-react';

export const SellerPortalPage: React.FC = () => {
  const { 
    currentUser, 
    products, 
    orders, 
    categories, 
    addProduct, 
    updateProduct, 
    deleteProduct, 
    updateOrderStatus, 
    sponsoredCampaigns, 
    addSponsoredCampaign, 
    formatPrice, 
    showToast, 
    t 
  } = useApp();

  const [activeTab, setActiveTab] = useState<'overview' | 'products' | 'orders' | 'ads'>('overview');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAdModalOpen, setIsAdModalOpen] = useState(false);

  // New product form states
  const [name, setName] = useState('');
  const [nameBn, setNameBn] = useState('');
  const [categorySlug, setCategorySlug] = useState('fruits-vegetables');
  const [price, setPrice] = useState('');
  const [discountPrice, setDiscountPrice] = useState('');
  const [stock, setStock] = useState('50');
  const [unit, setUnit] = useState('1 kg Bag');
  const [image, setImage] = useState('https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=800&q=80');
  const [description, setDescription] = useState('');
  const [isHalal, setIsHalal] = useState(true);

  // Ad campaign form states
  const [adName, setAdName] = useState('');
  const [adProductId, setAdProductId] = useState<number>(101);
  const [dailyBudget, setDailyBudget] = useState('500');
  const [cpcBid, setCpcBid] = useState('3.50');

  // Store metrics
  const sellerProducts = products.filter(p => p.seller_name.includes('Dhaka Fresh') || p.seller_id === 1);
  const totalStoreOrders = orders.length;
  const storeRevenue = orders.reduce((sum, ord) => sum + ord.total_amount, 0);

  const handleCreateProduct = (e: React.FormEvent) => {
    e.preventDefault();
    const cat = categories.find(c => c.slug === categorySlug) || categories[0];

    addProduct({
      seller_id: 1,
      seller_name: currentUser.storeName || 'Dhaka Fresh & Agro Haat',
      seller_location: 'Karwan Bazar, Dhaka',
      category_id: cat.id,
      category_slug: cat.slug,
      name,
      name_bn: nameBn || name,
      slug: name.toLowerCase().replace(/[^a-z0-9]+/g, '-') + '-' + Date.now().toString().slice(-4),
      description: description || 'Product details supplied by the seller.',
      description_bn: 'খামারের তাজা সংগৃহীত উন্নতমানের পণ্য।',
      image: image || 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=800&q=80',
      price: Number(price) || 100,
      discount_price: discountPrice ? Number(discountPrice) : undefined,
      stock_quantity: Number(stock) || 0,
      is_available: true,
      is_featured: false,
      unit,
      unit_bn: unit,
      food_details: {
        isHalal,
        origin: 'Dhaka Division, Bangladesh',
        shelfLife: 'Fresh Daily',
      },
    });

    setIsAddModalOpen(false);
    setName('');
    setNameBn('');
    setPrice('');
    setDiscountPrice('');
  };

  const handleCreateAd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!adName.trim()) return;

    addSponsoredCampaign({
      seller_id: 1,
      product_id: Number(adProductId),
      campaign_name: adName.trim(),
      daily_budget: Number(dailyBudget) || 500,
      cpc: Number(cpcBid) || 3.0,
      status: 'active',
    });

    setIsAdModalOpen(false);
    setAdName('');
  };

  const handleBulkUploadCSV = () => {
    showToast(t('Processing CSV inventory file...', 'ইনভেন্টরি সিএসভি ফাইল প্রসেস হচ্ছে...'), 'info');
    setTimeout(() => {
      showToast(t('12 products imported & stock synchronized successfully!', '১২টি পণ্য সফলভাবে ইমপোর্ট সম্পন্ন হয়েছে!'), 'success');
    }, 1200);
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Merchant Header */}
      <div className="p-6 sm:p-8 rounded-3xl bg-slate-900 text-white shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 font-bold text-xs mb-2">
            <Store className="w-4 h-4" />
            <span>{t('AMAZON-GRADE SELLER CENTRAL', 'আমাজন-মানের সেলার সেন্ট্রাল')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-white">
            {currentUser.storeName || 'Dhaka Fresh & Agro Haat'}
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 mt-1">
            Karwan Bazar Wholesale Hub, Dhaka • Merchant ID: NH-MER-1082 • Health Score: 100%
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          <button
            onClick={handleBulkUploadCSV}
            className="px-4 py-3 rounded-2xl bg-slate-800 text-slate-200 text-xs font-bold hover:bg-slate-700 flex items-center gap-2 border border-slate-700"
          >
            <Upload className="w-4 h-4" />
            <span>{t('Bulk CSV Upload', 'বাল্ক সিএসভি আপলোড')}</span>
          </button>

          <button
            onClick={() => setIsAddModalOpen(true)}
            className="neu-button px-5 py-3 rounded-2xl bg-primary text-white text-xs font-bold hover:bg-primary-hover flex items-center gap-2 shadow-md"
          >
            <Plus className="w-4 h-4" />
            <span>{t('Add Product', 'নতুন পণ্য')}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t('Store Sales GMV', 'মোট বিক্রয়')}</span>
            <DollarSign className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">{formatPrice(storeRevenue)}</p>
          <span className="text-[11px] text-emerald-600 font-bold mt-1 block">↑ 18.4% this week</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t('Pending Fulfillment', 'প্যাকেজিং অপেক্ষমাণ')}</span>
            <Package className="w-4 h-4 text-primary" />
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">{totalStoreOrders}</p>
          <span className="text-[11px] text-primary font-bold mt-1 block">Fast dispatch rate</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t('Sponsored Ads Spend', 'বিজ্ঞাপন খরচ')}</span>
            <Megaphone className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">৳ 1,620.00</p>
          <span className="text-[11px] text-slate-500 mt-1 block">ROAS: 4.8x Return</span>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-border shadow-xs">
          <div className="flex items-center justify-between text-muted text-xs mb-2">
            <span>{t('Account Health', 'অ্যাকাউন্ট স্বাস্থ্য')}</span>
            <span className="text-emerald-500 font-bold">Good</span>
          </div>
          <p className="text-xl sm:text-2xl font-black text-ink">99.4%</p>
          <span className="text-[11px] text-emerald-600 font-bold mt-1 block">Defect Rate: 0.12%</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'overview' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          {t('Store Inventory', 'দোকানের ইনভেন্টরি')} ({sellerProducts.length})
        </button>

        <button
          onClick={() => setActiveTab('orders')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'orders' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          {t('Order Fulfillment', 'অর্ডার ডেলিভারি ও প্যাকেজিং')} ({orders.length})
        </button>

        <button
          onClick={() => setActiveTab('ads')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
            activeTab === 'ads' ? 'bg-primary text-white shadow-xs' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          {t('Sponsored Product Ads (Amazon Ads)', 'স্পন্সরড বিজ্ঞাপন হাব')} ({sponsoredCampaigns.length})
        </button>
      </div>

      {/* Tab: Store Inventory */}
      {activeTab === 'overview' && (
        <div className="bg-white rounded-3xl border border-border shadow-card overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-bold text-sm text-ink">{t('Product Catalog Management', 'পণ্য ব্যবস্থাপনা')}</h3>
            <span className="text-xs text-muted">{sellerProducts.length} {t('items listed', 'টি তালিকাভুক্ত')}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 border-b border-slate-100 text-slate-500 uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">SKU / Product</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Price (৳)</th>
                  <th className="py-3 px-4">Discount (৳)</th>
                  <th className="py-3 px-4">Stock</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sellerProducts.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 flex items-center gap-3">
                      <img src={p.image} alt={p.name} className="w-10 h-10 rounded-lg object-cover shrink-0" />
                      <div>
                        <p className="font-bold text-ink">{p.name}</p>
                        <p className="text-[11px] text-muted font-mono">{p.sku} • {p.unit}</p>
                      </div>
                    </td>
                    <td className="py-3 px-4 capitalize">{p.category_slug.replace('-', ' ')}</td>
                    <td className="py-3 px-4 font-bold">{formatPrice(p.price)}</td>
                    <td className="py-3 px-4 text-emerald-600 font-semibold">
                      {p.discount_price ? formatPrice(p.discount_price) : '-'}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] ${
                        p.stock_quantity > 10 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                      }`}>
                        {p.stock_quantity} left
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => {
                            const newStock = prompt(`Update stock for ${p.name}:`, String(p.stock_quantity));
                            if (newStock !== null) {
                              updateProduct({ ...p, stock_quantity: Number(newStock) || 0 });
                            }
                          }}
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:text-primary hover:bg-slate-50"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteProduct(p.id)}
                          className="p-1.5 rounded-lg border border-rose-200 text-danger hover:bg-rose-50"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Order Fulfillment */}
      {activeTab === 'orders' && (
        <div className="bg-white rounded-3xl border border-border shadow-card overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex items-center justify-between">
            <h3 className="font-bold text-sm text-ink">{t('Store Order Fulfillment Queue', 'অর্ডার প্যাকেজিং ও প্রস্তুতি')}</h3>
            <span className="text-xs text-muted">{orders.length} {t('active orders', 'টি সক্রিয় অর্ডার')}</span>
          </div>

          <div className="divide-y divide-slate-100">
            {orders.map((order) => (
              <div key={order.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xs text-ink">{order.order_number}</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                      {order.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {order.customer_name} ({order.customer_phone}) • {order.delivery_address.thana}, {order.delivery_address.district}
                  </p>
                  <p className="text-xs font-semibold text-primary mt-1">
                    {order.items.length} items • Total: {formatPrice(order.total_amount)}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {order.status === 'confirmed' && (
                    <button
                      onClick={() => updateOrderStatus(order.order_number, 'processing')}
                      className="px-3.5 py-2 rounded-xl bg-amber-500 text-white text-xs font-bold hover:bg-amber-600 shadow-xs"
                    >
                      {t('Start Packing', 'প্যাকেজিং শুরু করুন')}
                    </button>
                  )}
                  {order.status === 'processing' && (
                    <button
                      onClick={() => updateOrderStatus(order.order_number, 'shipped', { name: 'Kamal Hossain', phone: '+8801912998877' })}
                      className="px-3.5 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-xs"
                    >
                      {t('Hand to Rider', 'রাইডারের হাতে দিন')}
                    </button>
                  )}
                  {order.status === 'shipped' && (
                    <span className="text-xs font-bold text-emerald-600 flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>{t('Dispatched with Rider', 'রাইডারের কাছে হস্তান্তরিত')}</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Sponsored Products Advertising (Amazon Ads style) */}
      {activeTab === 'ads' && (
        <div className="bg-white rounded-3xl border border-border shadow-card p-6 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h3 className="font-bold text-base text-ink flex items-center gap-2">
                <Megaphone className="w-5 h-5 text-accent" />
                <span>Sponsored Products Advertising Console</span>
              </h3>
              <p className="text-xs text-muted">Boost listing visibility on search results and category shelves</p>
            </div>

            <button
              onClick={() => setIsAdModalOpen(true)}
              className="neu-button px-4 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Create Campaign</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 text-slate-500 uppercase tracking-wider text-[11px] border-b">
                  <th className="py-3 px-4">Campaign Name</th>
                  <th className="py-3 px-4">Daily Budget</th>
                  <th className="py-3 px-4">Max CPC</th>
                  <th className="py-3 px-4">Impressions</th>
                  <th className="py-3 px-4">Clicks</th>
                  <th className="py-3 px-4">Spend</th>
                  <th className="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sponsoredCampaigns.map((camp) => (
                  <tr key={camp.id} className="hover:bg-slate-50/70">
                    <td className="py-3 px-4 font-bold text-ink">{camp.campaign_name}</td>
                    <td className="py-3 px-4">৳{camp.daily_budget}/day</td>
                    <td className="py-3 px-4">৳{camp.cpc.toFixed(2)}</td>
                    <td className="py-3 px-4 font-semibold">{camp.impressions.toLocaleString()}</td>
                    <td className="py-3 px-4 font-semibold text-primary">{camp.clicks.toLocaleString()}</td>
                    <td className="py-3 px-4 font-bold">{formatPrice(camp.spend)}</td>
                    <td className="py-3 px-4 text-right">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 uppercase">
                        {camp.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create Ad Campaign Modal */}
      {isAdModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <form onSubmit={handleCreateAd} className="bg-white rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-base text-ink">Launch Sponsored Product Ad</h3>
              <button type="button" onClick={() => setIsAdModalOpen(false)} className="text-slate-400 hover:text-ink">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-600 font-semibold mb-1">Campaign Name *</label>
                <input
                  type="text"
                  required
                  value={adName}
                  onChange={(e) => setAdName(e.target.value)}
                  placeholder="e.g. Chinigura Rice Weekend Push"
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1">Target Product *</label>
                <select
                  value={adProductId}
                  onChange={(e) => setAdProductId(Number(e.target.value))}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                >
                  {products.map(p => (
                    <option key={p.id} value={p.id}>{p.name} ({formatPrice(p.price)})</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Daily Budget (৳) *</label>
                  <input
                    type="number"
                    required
                    value={dailyBudget}
                    onChange={(e) => setDailyBudget(e.target.value)}
                    placeholder="500"
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Max CPC Bid (৳) *</label>
                  <input
                    type="number"
                    step="0.5"
                    required
                    value={cpcBid}
                    onChange={(e) => setCpcBid(e.target.value)}
                    placeholder="3.50"
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <button
                type="button"
                onClick={() => setIsAdModalOpen(false)}
                className="px-4 py-2 rounded-xl border text-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover"
              >
                Launch Ad
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Add Product Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <form onSubmit={handleCreateProduct} className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 space-y-4 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-base text-ink">
                {t('Add New Haat Product Listing', 'নতুন পণ্য তালিকাভুক্ত করুন')}
              </h3>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-ink text-xs font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-600 font-semibold mb-1">Product Title (English) *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Fresh Dinajpur Lychees 100pcs"
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1">Product Title (বাংলা)</label>
                <input
                  type="text"
                  value={nameBn}
                  onChange={(e) => setNameBn(e.target.value)}
                  placeholder="e.g. দিনাজপুরের রসালো লিচু ১০০ পিস"
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Category *</label>
                  <select
                    value={categorySlug}
                    onChange={(e) => setCategorySlug(e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                  >
                    {categories.map(c => (
                      <option key={c.id} value={c.slug}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Unit / Package *</label>
                  <input
                    type="text"
                    required
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    placeholder="e.g. 1 kg, 500g, 100 pcs"
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Regular Price (৳) *</label>
                  <input
                    type="number"
                    required
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="850"
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Discount Price (৳)</label>
                  <input
                    type="number"
                    value={discountPrice}
                    onChange={(e) => setDiscountPrice(e.target.value)}
                    placeholder="750"
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">Stock Qty *</label>
                  <input
                    type="number"
                    required
                    value={stock}
                    onChange={(e) => setStock(e.target.value)}
                    placeholder="50"
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1">Image URL</label>
                <input
                  type="url"
                  value={image}
                  onChange={(e) => setImage(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                <input
                  type="checkbox"
                  checked={isHalal}
                  onChange={(e) => setIsHalal(e.target.checked)}
                  className="accent-primary"
                />
                <span>Seller declares halal (verification not connected)</span>
              </label>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t">
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-sm"
              >
                Publish Listing
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
