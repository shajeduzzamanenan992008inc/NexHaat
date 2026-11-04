import React from 'react';
import { useApp } from '../context/AppContext';
import { ShoppingBag, CreditCard, PackageCheck, CircleHelp } from 'lucide-react';

export const Footer: React.FC = () => {
  const { setCurrentView, t } = useApp();

  return (
    <footer className="marketplace-footer mt-20 text-sm">
      {/* Value Proposition Highlights */}
      <div className="border-b border-slate-800 py-8 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-primary">
              <ShoppingBag className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('Browse the marketplace', 'মার্কেটপ্লেস ঘুরে দেখুন')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Explore groceries, everyday essentials, and local products.', 'নিত্যপণ্য, দরকারি সামগ্রী ও স্থানীয় পণ্য দেখুন।')}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-emerald-400">
              <CreditCard className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('Checkout options', 'পেমেন্টের উপায়')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Available payment methods are shown during checkout.', 'চেকআউটের সময় পাওয়া পেমেন্টের উপায় দেখানো হবে।')}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-amber-400">
              <PackageCheck className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('Order information', 'অর্ডারের তথ্য')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Review status and available actions from your order history.', 'অর্ডার ইতিহাসে স্ট্যাটাস ও প্রযোজ্য কাজ দেখুন।')}
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3.5">
            <div className="p-2.5 rounded-xl bg-slate-800 text-blue-400">
              <CircleHelp className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-white text-sm">
                {t('Help & support', 'সহায়তা')}
              </h4>
              <p className="text-xs text-slate-400 mt-1">
                {t('Open the support area to view the available help options.', 'সহায়তার বিকল্পগুলো দেখতে Support অংশ খুলুন।')}
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
              'NexHaat is a Bangladesh-first marketplace for groceries, everyday essentials, and products from local sellers.',
              'NexHaat বাংলাদেশের নিত্যপণ্য, দরকারি সামগ্রী ও স্থানীয় বিক্রেতাদের পণ্যের মার্কেটপ্লেস।'
            )}
          </p>
        </div>

        {/* Quick Links */}
        <div>
          <h5 className="font-bold text-white text-xs uppercase tracking-wider mb-3">
            {t('Marketplace', 'মার্কেটপ্লেস')}
          </h5>
          <ul className="space-y-2 text-xs">
            <li>
              <button onClick={() => setCurrentView('catalog')} className="marketplace-footer-link">
                {t('All Products & Catalog', 'সকল পণ্য ও ক্যাটালগ')}
              </button>
            </li>
            <li>
              <button onClick={() => setCurrentView('deals')} className="marketplace-footer-link">
                {t('Flash Deals & Discounts', 'মেগা ছাড় ও অফার')}
              </button>
            </li>
            <li>
              <button onClick={() => setCurrentView('wishlist')} className="marketplace-footer-link">
                {t('My Wishlist', 'আমার উইশলিস্ট')}
              </button>
            </li>
            <li>
              <button onClick={() => setCurrentView('my-orders')} className="marketplace-footer-link">
                {t('Order Tracking', 'অর্ডার ট্র্যাকিং')}
              </button>
            </li>
          </ul>
        </div>

        {/* Partner access */}
        <div>
          <h5 className="font-bold text-white text-xs uppercase tracking-wider mb-3">
            {t('Partner With Us', 'যুক্ত হোন')}
          </h5>
          <p className="max-w-xs text-xs leading-relaxed text-slate-300">
            {t(
              'Seller, rider, and operations access uses verified marketplace accounts. Local role previews are available from the sign-in panel.',
              'বিক্রেতা, রাইডার ও অপারেশনস অ্যাক্সেস যাচাইকৃত marketplace account দিয়ে হয়। সাইন-ইন প্যানেলে স্থানীয় role preview পাওয়া যায়।',
            )}
          </p>
          <button onClick={() => setCurrentView('support')} className="marketplace-footer-link mt-3">
            {t('Help & FAQs', 'সাহায্য ও প্রশ্নোত্তর')}
          </button>
        </div>

        {/* Checkout integration note */}
        <div>
          <h5 className="font-bold text-white text-xs uppercase tracking-wider mb-3">
            {t('Checkout', 'চেকআউট')}
          </h5>
          <p className="text-xs text-slate-400 mb-3">
            {t('Confirm the methods and terms presented for your order before placing it.', 'অর্ডার দেওয়ার আগে দেখানো পেমেন্টের উপায় ও শর্ত দেখে নিন।')}
          </p>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="marketplace-footer-bottom-bar py-5 px-4 text-center text-xs">
        <p>
          © 2026 NexHaat. {t('All rights reserved.', 'সর্বস্বত্ব সংরক্ষিত।')}
        </p>
      </div>
    </footer>
  );
};
