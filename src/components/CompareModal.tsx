import React from 'react';
import { useApp } from '../context/AppContext';
import { X, Star, ShoppingBag, ArrowRight } from 'lucide-react';

export const CompareModal: React.FC = () => {
  const { 
    isCompareModalOpen, 
    setIsCompareModalOpen, 
    comparedProductIds, 
    products, 
    addToCart, 
    toggleCompare, 
    clearCompare, 
    formatPrice, 
    t 
  } = useApp();

  if (!isCompareModalOpen) return null;

  const compareItems = products.filter(p => comparedProductIds.includes(p.id));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="bg-white rounded-3xl max-w-4xl w-full p-6 sm:p-8 space-y-6 shadow-2xl overflow-y-auto max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-black text-ink">
              {t('Side-by-Side Product Comparison', 'পণ্যের পাশাপাশি তুলনা')}
            </h2>
            <p className="text-xs text-muted">
              {t('Compare listing details, prices, and customer ratings when available.', 'পণ্যের তথ্য, দাম ও থাকলে ক্রেতার রেটিং তুলনা করুন।')}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={clearCompare}
              className="text-xs font-semibold text-danger hover:underline px-2 py-1"
            >
              {t('Clear All', 'সব মুছুন')}
            </button>
            <button
              onClick={() => setIsCompareModalOpen(false)}
              className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-ink"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {compareItems.length === 0 ? (
          <div className="py-12 text-center text-muted text-xs">
            {t('No products currently selected for comparison.', 'তুলনার জন্য কোনো পণ্য নির্বাচিত নেই।')}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="border-b">
                  <th className="py-3 px-3 text-slate-400 font-semibold w-36">Product</th>
                  {compareItems.map(item => (
                    <th key={item.id} className="py-3 px-3 min-w-[180px] align-top">
                      <div className="relative group">
                        <img
                          src={item.image}
                          alt={item.name}
                          className="w-24 h-24 rounded-xl object-cover bg-slate-50 mb-2 border border-slate-200"
                        />
                        <button
                          onClick={() => toggleCompare(item.id)}
                          className="absolute -top-1.5 -right-1.5 p-1 bg-white rounded-full shadow-sm text-slate-400 hover:text-danger border"
                          title="Remove from comparison"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                        <h4 className="font-bold text-ink line-clamp-2">{item.name}</h4>
                        <p className="text-primary font-black text-sm mt-1">
                          {formatPrice(item.discount_price ?? item.price)}
                        </p>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {/* Rating */}
                <tr>
                  <td className="py-3 px-3 font-semibold text-slate-500">Customer Rating</td>
                  {compareItems.map(item => (
                    <td key={item.id} className="py-3 px-3">
                      {item.review_count !== undefined && item.review_count > 0 && item.rating !== undefined ? (
                        <div className="flex items-center gap-1 text-amber-500 font-bold">
                          <Star className="w-4 h-4 fill-current" />
                          <span>{item.rating}</span>
                          <span className="text-slate-400 font-normal">({item.review_count})</span>
                        </div>
                      ) : <span className="text-slate-400">{t('No ratings listed', 'রেটিং দেওয়া হয়নি')}</span>}
                    </td>
                  ))}
                </tr>

                {/* Seller & Origin */}
                <tr>
                  <td className="py-3 px-3 font-semibold text-slate-500">Seller / Region</td>
                  {compareItems.map(item => (
                    <td key={item.id} className="py-3 px-3">
                      <p className="font-bold text-ink">{item.seller_name}</p>
                      <p className="text-[11px] text-muted">{item.food_details?.origin || item.seller_location}</p>
                    </td>
                  ))}
                </tr>

                {/* Seller-provided food information */}
                <tr>
                  <td className="py-3 px-3 font-semibold text-slate-500">{t('Food details', 'খাদ্যপণ্যের তথ্য')}</td>
                  {compareItems.map(item => (
                    <td key={item.id} className="py-3 px-3">
                      <span className="text-slate-600">
                        {item.food_details?.isHalal
                          ? t('Seller indicates halal; not independently verified', 'বিক্রেতা হালাল বলেছেন; আলাদাভাবে যাচাই হয়নি')
                          : item.food_details
                            ? t('Seller details listed', 'বিক্রেতার তথ্য দেওয়া আছে')
                            : t('Not listed', 'তথ্য নেই')}
                      </span>
                    </td>
                  ))}
                </tr>

                {/* Shelf Life / Unit */}
                <tr>
                  <td className="py-3 px-3 font-semibold text-slate-500">Package / Shelf Life</td>
                  {compareItems.map(item => (
                    <td key={item.id} className="py-3 px-3 text-slate-700">
                      <p className="font-semibold">{item.unit}</p>
                      <p className="text-[11px] text-muted">{item.food_details?.shelfLife || t('Not listed', 'তথ্য নেই')}</p>
                    </td>
                  ))}
                </tr>

                {/* Action button */}
                <tr>
                  <td className="py-4 px-3 font-semibold text-slate-500">Add to Cart</td>
                  {compareItems.map(item => (
                    <td key={item.id} className="py-4 px-3">
                      <button
                        onClick={() => addToCart(item)}
                        className="neu-button w-full py-2 px-3 rounded-xl bg-primary text-white font-bold text-xs hover:bg-primary-hover flex items-center justify-center gap-1.5 shadow-sm"
                      >
                        <ShoppingBag className="w-3.5 h-3.5" />
                        <span>{t('Add to Cart', 'কার্টে যোগ')}</span>
                      </button>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
