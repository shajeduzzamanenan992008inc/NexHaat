import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import {
  ShieldCheck,
  Truck,
  CreditCard,
  Banknote,
  MapPin,
  ArrowRight,
  Tag,
  AlertCircle,
} from 'lucide-react';
import { FlaskAuthPanel } from '../components/FlaskAuthPanel';
import { createMarketplaceCheckout } from '../lib/marketplaceApi';

export const CheckoutPage: React.FC = () => {
  const {
    cart,
    cartSubtotal,
    setCurrentView,
    formatPrice,
    activeCoupon,
    appliedPromoDiscount,
    applyCoupon,
    removeCoupon,
    t,
    flaskUser,
    isFlaskAuthLoading,
    submitMarketplaceCheckout,
    showToast,
  } = useApp();

  // Form States
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [division, setDivision] = useState('Dhaka');
  const [district, setDistrict] = useState('Dhaka');
  const [thana, setThana] = useState('Dhanmondi');
  const [streetAddress, setStreetAddress] = useState('');
  const [deliveryNotes, setDeliveryNotes] = useState('');

  const [deliverySpeed, setDeliverySpeed] = useState<'standard' | 'express'>('standard');
  const [paymentMethod, setPaymentMethod] = useState<'cod' | 'sslcommerz'>('cod');
  const [couponCode, setCouponCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAuthPanelOpen, setIsAuthPanelOpen] = useState(false);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [orderNeedsPaymentFollowup, setOrderNeedsPaymentFollowup] = useState(false);

  useEffect(() => {
    if (flaskUser?.role === 'customer') setIsAuthPanelOpen(false);
  }, [flaskUser]);

  if (cart.length === 0) {
    return (
      <div className="py-16 text-center max-w-md mx-auto space-y-4">
        <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
          <Truck className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-ink">
          {t('Your cart is empty', 'আপনার কার্ট খালি')}
        </h2>
        <p className="text-xs text-muted">
          {t('Add items to your cart before proceeding to checkout.', 'চেকআউট করতে প্রথমে পণ্য কার্টে যোগ করুন।')}
        </p>
        <button
          onClick={() => setCurrentView('catalog')}
          className="px-6 py-2.5 rounded-xl bg-primary text-white font-bold text-xs"
        >
          {t('Browse Catalog', 'ক্যাটালগ দেখুন')}
        </button>
      </div>
    );
  }

  if (flaskUser?.role !== 'customer') {
    const gateMessage = flaskUser
      ? t(
          'Checkout requires a customer account. Sign out of the current account, then sign in as a customer.',
          'চেকআউট করতে কাস্টমার অ্যাকাউন্ট দরকার। বর্তমান অ্যাকাউন্ট থেকে সাইন আউট করে কাস্টমার হিসেবে সাইন ইন করুন।',
        )
      : t(
          'Sign in with your NexHaat customer account to continue to checkout.',
          'চেকআউট চালিয়ে যেতে NexHaat কাস্টমার অ্যাকাউন্টে সাইন ইন করুন।',
        );

    return (
      <section className="mx-auto max-w-lg rounded-3xl border border-border bg-white p-8 text-center shadow-card" aria-labelledby="checkout-sign-in-title">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary-light text-primary">
          <ShieldCheck className="h-7 w-7" aria-hidden="true" />
        </div>
        <h1 id="checkout-sign-in-title" className="text-xl font-black text-ink">
          {t('Sign in to checkout', 'চেকআউট করতে সাইন ইন করুন')}
        </h1>
        <p
          className="mt-2 text-sm text-muted"
          role={isFlaskAuthLoading ? 'status' : undefined}
          aria-live={isFlaskAuthLoading ? 'polite' : undefined}
        >
          {isFlaskAuthLoading
            ? t('Checking your NexHaat session…', 'আপনার NexHaat সেশন যাচাই করা হচ্ছে…')
            : gateMessage}
        </p>
        {!isFlaskAuthLoading && (
          <button
            type="button"
            onClick={() => setIsAuthPanelOpen(true)}
            className="mt-6 rounded-xl bg-primary px-6 py-3 text-sm font-bold text-white transition-colors hover:bg-primary-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            {flaskUser ? t('Open account options', 'অ্যাকাউন্টের বিকল্প খুলুন') : t('Sign in', 'সাইন ইন')}
          </button>
        )}
        {isAuthPanelOpen && <FlaskAuthPanel onClose={() => setIsAuthPanelOpen(false)} />}
      </section>
    );
  }

  const estimatedItemsTotal = Math.max(0, cartSubtotal - appliedPromoDiscount);

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setCheckoutError(null);
    if (flaskUser?.role !== 'customer') {
      setCheckoutError(
        t(
          'Sign in with a customer account before placing an order.',
          'অর্ডার দেওয়ার আগে কাস্টমার অ্যাকাউন্টে সাইন ইন করুন।',
        ),
      );
      setIsAuthPanelOpen(true);
      return;
    }

    setIsSubmitting(true);
    const checkoutInput = {
      customerName: fullName,
      phone,
      address: [streetAddress, thana, district, division, deliveryNotes].filter(Boolean).join(', '),
      city: district,
      promotionCode: activeCoupon?.code,
    };

    try {
      if (paymentMethod === 'cod') {
        await submitMarketplaceCheckout(checkoutInput);
        setIsSubmitting(false);
        setCurrentView('order-confirmation');
        return;
      }

      const checkout = await createMarketplaceCheckout({
        ...checkoutInput,
        paymentMethod: 'sslcommerz',
      });
      if (checkout.orders.length === 0) {
        throw new Error(t('The server did not return an order.', 'সার্ভার কোনো অর্ডার ফেরত দেয়নি।'));
      }
      setOrderNeedsPaymentFollowup(true);
      if (!checkout.checkout_url) {
        throw new Error(
          t(
            'The order was created, but the payment provider did not return a checkout link. Do not submit again; check your orders or contact support.',
            'অর্ডার তৈরি হয়েছে, কিন্তু পেমেন্ট সেবার checkout link পাওয়া যায়নি। আবার submit করবেন না; অর্ডার দেখুন বা support-এ যোগাযোগ করুন।',
          ),
        );
      }

      let checkoutUrl: URL;
      try {
        checkoutUrl = new URL(checkout.checkout_url);
      } catch {
        throw new Error(
          t('The payment provider returned an invalid checkout link.', 'পেমেন্ট সেবা একটি অবৈধ checkout link দিয়েছে।'),
        );
      }
      const allowedPaymentHosts = new Set(['sandbox.sslcommerz.com', 'securepay.sslcommerz.com']);
      if (checkoutUrl.protocol !== 'https:' || !allowedPaymentHosts.has(checkoutUrl.hostname)) {
        throw new Error(
          t('The payment provider returned an invalid checkout link.', 'পেমেন্ট সেবা একটি অবৈধ checkout link দিয়েছে।'),
        );
      }

      window.location.assign(checkoutUrl.toString());
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : t('The server rejected this checkout.', 'সার্ভার checkout অনুরোধটি গ্রহণ করেনি।');
      setCheckoutError(message);
      showToast(message, 'error');
      setIsSubmitting(false);
    }
  };
  return (
    <div className="space-y-6 pb-16">
      {/* Title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-ink">
          {t('Secure Checkout', 'নিরাপদ চেকআউট')}
        </h1>
        <p className="text-xs sm:text-sm text-muted mt-0.5">
          {t('Review your address and payment choice. The marketplace validates order details before creation.', 'ঠিকানা ও পেমেন্ট পদ্ধতি দেখুন। অর্ডার তৈরির আগে মার্কেটপ্লেস তথ্য যাচাই করবে।')}
        </p>
      </div>

      {checkoutError && (
        <div
          role="alert"
          aria-live="assertive"
          className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <p>{checkoutError}</p>
        </div>
      )}

      <form
        onSubmit={handleSubmitOrder}
        aria-busy={isSubmitting}
        className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start"
      >
        {/* Left Column: Form Details */}
        <div className="lg:col-span-7 space-y-6">
          {/* 1. Customer & Delivery Address */}
          <section className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-4">
            <h3 className="font-bold text-sm text-ink flex items-center gap-2 pb-3 border-b border-slate-100">
              <MapPin className="w-4 h-4 text-primary" />
              <span>{t('1. Delivery Address & Contact', '১. ডেলিভারি ঠিকানা ও যোগাযোগ')}</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 font-semibold mb-1">
                  {t('Full Name', 'পুরো নাম')} *
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1">
                  {t('Bangladeshi Mobile Phone', 'মোবাইল নম্বর')} *
                </label>
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+880 17XXXXXXXX"
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-primary"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <label className="block text-slate-600 font-semibold mb-1">
                  {t('Division', 'বিভাগ')}
                </label>
                <select
                  value={division}
                  onChange={(e) => setDivision(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-primary"
                >
                  <option value="Dhaka">Dhaka (ঢাকা)</option>
                  <option value="Chittagong">Chittagong (চট্টগ্রাম)</option>
                  <option value="Sylhet">Sylhet (সিলেট)</option>
                  <option value="Rajshahi">Rajshahi (রাজশাহী)</option>
                  <option value="Khulna">Khulna (খুলনা)</option>
                  <option value="Barishal">Barishal (বরিশাল)</option>
                  <option value="Rangpur">Rangpur (রংপুর)</option>
                  <option value="Mymensingh">Mymensingh (ময়মনসিংহ)</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1">
                  {t('District', 'জেলা')}
                </label>
                <input
                  type="text"
                  required
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-semibold mb-1">
                  {t('Thana / Area', 'থানা / এলাকা')}
                </label>
                <input
                  type="text"
                  required
                  value={thana}
                  onChange={(e) => setThana(e.target.value)}
                  placeholder="e.g. Dhanmondi, Gulshan"
                  className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-primary"
                />
              </div>
            </div>

            <div className="text-xs">
              <label className="block text-slate-600 font-semibold mb-1">
                {t('Street / Building / Flat Address', 'রাস্তা ও বাড়ির বিস্তারিত ঠিকানা')} *
              </label>
              <textarea
                required
                rows={2}
                value={streetAddress}
                onChange={(e) => setStreetAddress(e.target.value)}
                placeholder="House No, Road No, Flat/Floor details"
                className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-primary"
              />
            </div>

            <div className="text-xs">
              <label className="block text-slate-600 font-semibold mb-1">
                {t('Delivery Notes (Optional)', 'ডেলিভারি নির্দেশিকা (ঐচ্ছিক)')}
              </label>
              <input
                type="text"
                value={deliveryNotes}
                onChange={(e) => setDeliveryNotes(e.target.value)}
                placeholder="e.g. Call upon arrival, leave with security guard"
                className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-primary"
              />
            </div>
          </section>

          {/* 2. Delivery Speed */}
          <section className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-4">
            <h3 className="font-bold text-sm text-ink flex items-center gap-2 pb-3 border-b border-slate-100">
              <Truck className="w-4 h-4 text-primary" />
              <span>{t('2. Delivery option', '২. ডেলিভারির বিকল্প')}</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label
                className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-start gap-3 ${
                  deliverySpeed === 'standard'
                    ? 'border-primary bg-primary-light/40 shadow-xs'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="speed"
                  checked={deliverySpeed === 'standard'}
                  onChange={() => setDeliverySpeed('standard')}
                  className="mt-0.5 accent-primary"
                />
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-xs text-ink">
                      {t('Standard Delivery', 'স্ট্যান্ডার্ড ডেলিভারি')}
                    </span>
                    <span className="text-[10px] font-bold text-primary">{t('Confirmed at checkout', 'চেকআউটে নিশ্চিত হবে')}</span>
                  </div>
                  <p className="text-[11px] text-muted mt-1">
                    {t('Availability, timing, and the final fee are confirmed by the marketplace.', 'ডেলিভারির সুযোগ, সময় ও চূড়ান্ত ফি মার্কেটপ্লেস নিশ্চিত করবে।')}
                  </p>
                </div>
              </label>

              <label
                className="p-4 rounded-2xl border border-border bg-surface-raised opacity-70 flex items-start gap-3 cursor-not-allowed"
              >
                <input
                  type="radio"
                  name="speed"
                  checked={false}
                  disabled
                  className="mt-0.5 accent-primary"
                />
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-xs text-ink">
                      {t('Express delivery preview', 'এক্সপ্রেস ডেলিভারি প্রিভিউ')}
                    </span>
                    <span className="text-[10px] font-bold text-muted">{t('Unavailable', 'চালু নেই')}</span>
                  </div>
                  <p className="text-[11px] text-muted mt-1">
                    {t('Express service is not connected to the current checkout.', 'বর্তমান চেকআউটে এক্সপ্রেস সেবা সংযুক্ত নয়।')}
                  </p>
                </div>
              </label>
            </div>
          </section>

          {/* 3. Payment Method */}
          <section className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-4">
            <h3 className="font-bold text-sm text-ink flex items-center gap-2 pb-3 border-b border-slate-100">
              <CreditCard className="w-4 h-4 text-primary" />
              <span>{t('3. Payment Method', '৩. পেমেন্ট মাধ্যম')}</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                {
                  id: 'cod' as const,
                  label: 'Cash on Delivery',
                  label_bn: 'ক্যাশ অন ডেলিভারি',
                  icon: <Banknote className="w-5 h-5" />,
                },
                {
                  id: 'sslcommerz' as const,
                  label: 'Online Payment (SSLCommerz)',
                  label_bn: 'অনলাইন পেমেন্ট (SSLCommerz)',
                  icon: <CreditCard className="w-5 h-5 text-blue-600" />,
                },
              ].map((pm) => (
                <label
                  key={pm.id}
                  className={`p-3.5 rounded-2xl border cursor-pointer text-center flex flex-col items-center justify-center gap-2 transition-all ${
                    paymentMethod === pm.id
                      ? 'border-primary bg-primary-light/40 shadow-xs ring-1 ring-primary'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="paymentMethod"
                    value={pm.id}
                    checked={paymentMethod === pm.id}
                    onChange={() => setPaymentMethod(pm.id)}
                    className="sr-only"
                  />
                  <div className="h-6 flex items-center justify-center">{pm.icon}</div>
                  <span className="text-xs font-bold text-ink">
                    {t(pm.label, pm.label_bn)}
                  </span>
                </label>
              ))}
            </div>

            {paymentMethod === 'sslcommerz' && (
              <p className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-xs text-blue-900">
                {t(
                  'You will continue to SSLCommerz to complete payment. NexHaat will not ask for your payment PIN here.',
                  'পেমেন্ট সম্পন্ন করতে আপনাকে SSLCommerz-এ নেওয়া হবে। NexHaat এখানে আপনার পেমেন্ট PIN চাইবে না।',
                )}
              </p>
            )}
          </section>
        </div>

        {/* Right Column: Order Summary */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-4">
            <h3 className="font-bold text-sm text-ink pb-3 border-b border-slate-100 flex items-center justify-between">
              <span>{t('Order Summary', 'অর্ডার বিবরণী')}</span>
              <span className="text-xs font-semibold text-primary">{cart.length} {t('items', 'টি পণ্য')}</span>
            </h3>

            {/* Items preview */}
            <div className="max-h-60 overflow-y-auto divide-y divide-slate-100 pr-1 space-y-2">
              {cart.map((item) => {
                const itemPrice = item.product.discount_price ?? item.product.price;
                const modifier = item.selectedVariant?.priceModifier || 0;
                const lineTotal = (itemPrice + modifier) * item.quantity;

                return (
                  <div key={`${item.product.id}-${item.selectedVariant?.id || 'base'}`} className="pt-2 flex items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-2 min-w-0">
                      <img
                        src={item.product.image}
                        alt={item.product.name}
                        className="w-10 h-10 rounded-lg object-cover bg-slate-50 shrink-0"
                      />
                      <div className="truncate">
                        <p className="font-semibold text-ink truncate">{item.product.name}</p>
                        <p className="text-[11px] text-muted">
                          {item.quantity} × {formatPrice(itemPrice + modifier)}
                          {item.selectedVariant && ` (${item.selectedVariant.name})`}
                        </p>
                      </div>
                    </div>
                    <span className="font-bold text-ink shrink-0">{formatPrice(lineTotal)}</span>
                  </div>
                );
              })}
            </div>

            {/* Voucher input */}
            <div className="pt-3 border-t border-slate-100">
              {activeCoupon ? (
                <div className="flex items-center justify-between p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <Tag className="w-3.5 h-3.5" />
                    <span>{activeCoupon.code} (-{formatPrice(appliedPromoDiscount)})</span>
                  </div>
                  <button type="button" onClick={removeCoupon} className="font-bold text-danger hover:underline">
                    {t('Remove', 'মুছুন')}
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                    placeholder={t('Voucher Code (e.g. NEXHAAT10)', 'কুপন কোড')}
                    className="flex-1 px-3 py-2 text-xs border border-slate-200 rounded-xl bg-slate-50 uppercase font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (couponCode) {
                        applyCoupon(couponCode);
                        setCouponCode('');
                      }
                    }}
                    className="px-3.5 py-2 bg-slate-800 text-white text-xs font-semibold rounded-xl hover:bg-slate-900"
                  >
                    {t('Apply', 'প্রয়োগ')}
                  </button>
                </div>
              )}
            </div>

            {/* Calculations */}
            <div className="space-y-2 text-xs text-slate-600 pt-2 border-t border-slate-100">
              <div className="flex justify-between">
                <span>{t('Subtotal', 'সাবটোটাল')}</span>
                <span className="font-semibold text-ink">{formatPrice(cartSubtotal)}</span>
              </div>
              {appliedPromoDiscount > 0 && (
                <div className="flex justify-between text-emerald-600">
                  <span>{t('Discount', 'ছাড়')}</span>
                  <span className="font-semibold">-{formatPrice(appliedPromoDiscount)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>{t('Delivery charge', 'ডেলিভারি চার্জ')}</span>
                <span className="font-semibold text-ink">{t('Confirmed by marketplace', 'মার্কেটপ્લেস নিশ্চিত করবে')}</span>
              </div>
              <div className="flex justify-between text-base font-black text-ink pt-2 border-t border-slate-200">
                <span>{t('Items total before delivery', 'ডেলিভারির আগের পণ্য মূল্য')}</span>
                <span className="text-primary">{formatPrice(estimatedItemsTotal)}</span>
              </div>
              <p className="text-[11px] text-muted pt-1">
                {t('The marketplace recalculates product prices, promotion eligibility, delivery fees, and the final total before accepting the order.', 'অর্ডার গ্রহণের আগে মার্কেটপ্লেস পণ্যের দাম, কুপনের যোগ্যতা, ডেলিভারি ফি ও চূড়ান্ত মোট পুনরায় হিসাব করবে।')}
              </p>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting || orderNeedsPaymentFollowup}
              className="neu-button w-full py-4 rounded-2xl bg-primary text-white font-black text-sm shadow-md hover:bg-primary-hover disabled:bg-slate-300 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <span role="status" aria-live="polite">
                  {t('Confirming Order...', 'অর্ডার প্রক্রিয়াধীন...')}
                </span>
              ) : orderNeedsPaymentFollowup ? (
                <span>{t('Order created — check your orders', 'অর্ডার তৈরি হয়েছে—অর্ডার তালিকা দেখুন')}</span>
              ) : (
                <>
                  <span>{t('Confirm & Place Order', 'অর্ডার সম্পন্ন করুন')}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400 text-center pt-1">
              <ShieldCheck className="w-4 h-4 text-success" />
              <span>{t('Review the payment method and order terms shown before placing your order.', 'অর্ডার দেওয়ার আগে দেখানো পেমেন্ট পদ্ধতি ও শর্ত দেখে নিন।')}</span>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
