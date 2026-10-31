import React from 'react';
import { useApp } from '../context/AppContext';
import { Layers, X, ArrowRight } from 'lucide-react';

export const ComparisonBar: React.FC = () => {
  const { 
    comparedProductIds, 
    products, 
    setIsCompareModalOpen, 
    toggleCompare, 
    clearCompare, 
    t 
  } = useApp();

  if (comparedProductIds.length === 0) return null;

  const comparedProducts = products.filter(p => comparedProductIds.includes(p.id));

  return (
    <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-40 max-w-xl w-[92%] sm:w-auto bg-slate-900 text-white rounded-2xl shadow-elevated p-3 border border-slate-700 flex items-center justify-between gap-4 animate-slide-in backdrop-blur-md">
      <div className="flex items-center gap-3 overflow-x-auto">
        <div className="flex items-center gap-1.5 text-xs font-bold text-amber-400 shrink-0">
          <Layers className="w-4 h-4" />
          <span className="hidden sm:inline">{t('Compare:', 'তুলনা:')}</span>
        </div>

        <div className="flex items-center gap-2">
          {comparedProducts.map(p => (
            <div key={p.id} className="relative group shrink-0">
              <img
                src={p.image}
                alt={p.name}
                className="w-10 h-10 rounded-xl object-cover border border-slate-700 bg-slate-800"
              />
              <button
                onClick={() => toggleCompare(p.id)}
                className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-slate-800 border border-slate-600 text-white flex items-center justify-center hover:bg-danger text-[10px]"
                title="Remove"
              >
                <X className="w-2.5 h-2.5" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={() => setIsCompareModalOpen(true)}
          className="neu-button px-4 py-2 rounded-xl bg-primary text-white font-bold text-xs hover:bg-primary-hover flex items-center gap-1.5 shadow-sm"
        >
          <span>{t(`Compare (${comparedProducts.length})`, `তুলনা করুন (${comparedProducts.length})`)}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={clearCompare}
          className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800"
          title="Clear compare"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
