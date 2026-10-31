import React from 'react';
import { useApp } from '../context/AppContext';
import { ShieldCheck, Truck, Clock, RefreshCw, Mail, Phone, MapPin, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  const { setCurrentView, setUserRole, t } = useApp();

  return (
    <footer className="mt-20 bg-slate-900 text-slate-300 text-sm border-t border-slate-800">
      {/* Value Proposition Highlights */}
      <div className="border-b border-slate-800 py-8 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-primary">
              <Truck className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('Hyper-Local Express Delivery', 'হাইপার-লোকাল এক্সপ্রেস ডেলিভারি')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Same-day and 3-hour doorstep delivery across Dhaka and Chittagong.', 'ঢাকা ও চট্টগ্রামে একই দিনে দ্রুততম হোম ডেলিভারি।')}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-emerald-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('100% Halal & Farm Fresh', '১০০% হালাল ও তাজা পণ্য')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Direct sourcing from verified regional farms and river fisheries.', 'সরাসরি স্থানীয় খামার ও নদী থেকে সংগৃহীত নিরাপদ খাবার।')}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-amber-400">
              <RefreshCw className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('7-Day Easy Returns', '৭ দিনের সহজ রিটার্ন')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Hassle-free replacement or refund guarantee on all marketplace items.', 'যেকোনো পণ্যে সহজ ও দ্রুত রিফান্ড বা পরিবর্তনের নিশ্চয়তা।')}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-blue-400">
              <Clock className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('24/7 Dedicated Support', '২৪/৭ সার্বক্ষণিক সহায়তা')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Call our direct helpline +880 9612 000 000 for any order queries.', 'যেকোনো প্রয়োজনে ফোন করুন আমাদের হটলাইন নম্বরে।')}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Footer Links */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8">
        {/* Brand & Mission */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary p-1.5 flex items-center justify-center">
              <img src="/logo.svg" alt="NexHaat" className="w-full h-full object-contain" />
            </div>
            <span className="text-xl font-black text-white">
              Nex<span className="text-primary">Haat</span>
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed pr-6">
            {t(
              'NexHaat connects millions of Bangladeshi shoppers directly with local farmers, river fishermen, cottage artisans, and verified merchants. We guarantee authentic quality, fair pricing, and rapid doorstep delivery.',
              'নেক্সহাট বাংলাদেশের স্থানীয় কৃষক, জেলে, তাঁতি ও বিশ্বস্ত বিক্রেতাদের সাথে ক্রেতাদের সরাসরি সংযুক্ত করে সাশ্রয়ী মূল্যে তাজা ও আসল পণ্য পৌঁছে দিচ্ছে।'
            )}
          </p>

          <div className="space-y-1.5 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-primary shrink-0" />
              <span>Level 6, Navana Tower, Gulshan-1, Dhaka 1212, Bangladesh</span>
            </div>
            <div className="flex items-center gap-2">
              <Phone className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Hotline: +880 9612 000 000 (8:00 AM - 11:00 PM)</span>
            </div>
            <div className="flex items-center gap-2">
              <Mail className="w-4 h-4 text-amber-400 shrink-0" />
              <span>support@nexhaat.com.bd</span>
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div>
          <h5 className="font-bold text-white text-xs uppercase tracking-wider mb-3">
            {t('Marketplace', 'মার্কেটপ্লেস')}
          </h5>
          <ul className="space-y-2 text-xs">
            <li>
              <button onClick={() => setCurrentView('catalog')} className="hover:text-white transition-colors">
                {t('All Products & Catalog', 'সকল পণ্য ও ক্যাটালগ')}
              </button>
            </li>
            <li>
              <button onClick={() => setCurrentView('deals')} className="hover:text-white transition-colors">
                {t('Flash Deals & Discounts', 'মেগা ছাড় ও অফার')}
              </button>
            </li>
            <li>
              <button onClick={() => setCurrentView('wishlist')} className="hover:text-white transition-colors">
                {t('My Wishlist', 'আমার উইশলিস্ট')}
              </button>
            </li>
            <li>
              <button onClick={() => setCurrentView('my-orders')} className="hover:text-white transition-colors">
                {t('Order Tracking', 'অর্ডার ট্র্যাকিং')}
              </button>
            </li>
          </ul>
        </div>

        {/* Portals & Workspaces */}
        <div>
          <h5 className="font-bold text-white text-xs uppercase tracking-wider mb-3">
            {t('Partner With Us', 'যুক্ত হোন')}
          </h5>
          <ul className="space-y-2 text-xs">
            <li>
              <button 
                onClick={() => setUserRole('seller')} 
                className="hover:text-white transition-colors flex items-center gap-1.5"
              >
                <span>{t('Seller Merchant Portal', 'মার্চেন্ট / সেলার পোর্টাল')}</span>
              </button>
            </li>
            <li>
              <button 
                onClick={() => setUserRole('rider')} 
                className="hover:text-white transition-colors flex items-center gap-1.5"
              >
                <span>{t('Rider Delivery Hub', 'রাইডার ডেলিভারি হাব')}</span>
              </button>
            </li>
            <li>
              <button 
                onClick={() => setUserRole('admin')} 
                className="hover:text-white transition-colors flex items-center gap-1.5"
              >
                <span>{t('Admin Operations Center', 'অ্যাডমিন অপারেশনস')}</span>
              </button>
            </li>
            <li>
              <button onClick={() => setCurrentView('support')} className="hover:text-white transition-colors">
                {t('Help & FAQs', 'সাহায্য ও প্রশ্নোত্তর')}
              </button>
            </li>
          </ul>
        </div>

        {/* Accepted Payment Methods in Bangladesh */}
        <div>
          <h5 className="font-bold text-white text-xs uppercase tracking-wider mb-3">
            {t('Payment Security', 'নিরাপদ পেমেন্ট')}
          </h5>
          <p className="text-xs text-slate-400 mb-3">
            {t('Encrypted checkout supporting all major Bangladeshi channels.', 'নিরাপদ এনক্রিপ্টেড পেমেন্ট ব্যবস্থা।')}
          </p>
          <div className="grid grid-cols-2 gap-2 text-center text-[11px] font-bold text-slate-300">
            <span className="p-2 rounded-lg bg-slate-800 border border-slate-700">bKash</span>
            <span className="p-2 rounded-lg bg-slate-800 border border-slate-700">Nagad</span>
            <span className="p-2 rounded-lg bg-slate-800 border border-slate-700">Visa / Master</span>
            <span className="p-2 rounded-lg bg-slate-800 border border-slate-700">Cash on Delivery</span>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="border-t border-slate-800 py-6 px-4 text-center text-xs text-slate-500">
        <p>
          © 2026 NexHaat Ltd. {t('All rights reserved. Built with precision for Bangladesh.', 'সর্বস্বত্ব সংরক্ষিত।')}
        </p>
      </div>
    </footer>
  );
};
