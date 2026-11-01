import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { OrderItem } from '../types';
import { 
  ShieldCheck, Truck, CreditCard, Banknote, MapPin, 
  Phone, User, ArrowRight, Tag, AlertCircle, CheckCircle2 
} from 'lucide-react';

export const CheckoutPage: React.FC = () => {
  const {
    cart,
    cartSubtotal,
    currentUser,
    placeOrder,
    setCurrentView,
    formatPrice,
    activeCoupon,
    appliedPromoDiscount,
    applyCoupon,
    removeCoupon,
    t,
    flaskUser,
    submitMarketplaceCheckout,
    showToast,
  } = useApp();

  // Form States
  const [fullName, setFullName] = useState(currentUser.name || 'Tanvir Rahman');
  const [phone, setPhone] = useState(currentUser.phone || '+8801711223344');
  const [email, setEmail] = useState(currentUser.email || 'tanvir.rahman@example.com');
  const [division, setDivision] = useState('Dhaka');
  const [district, setDistrict] = useState('Dhaka');
  const [thana, setThana] = useState('Dhanmondi');
  const [streetAddress, setStreetAddress] = useState(currentUser.address || 'Flat 4B, House 18, Road 7');
  const [deliveryNotes, setDeliveryNotes] = useState('Please call before delivery');

  const [deliverySpeed, setDeliverySpeed] = useState<'standard' | 'express'>('standard');
  const [paymentMethod, setPaymentMethod] = useState<'cod' | 'bkash' | 'nagad' | 'card'>('cod');
  const [bkashNumber, setBkashNumber] = useState('01711223344');
  const [bkashPin, setBkashPin] = useState('');
  const [couponCode, setCouponCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  // Delivery fee calculation
  const baseDeliveryFee = division === 'Dhaka' ? 60 : 120;
  const expressFee = deliverySpeed === 'express' ? 50 : 0;
  const isFreeDeliveryCoupon = activeCoupon?.code === 'FREESHIP' || cartSubtotal >= 1500;
  const deliveryFee = isFreeDeliveryCoupon ? expressFee : baseDeliveryFee + expressFee;

  const grandTotal = Math.max(0, cartSubtotal - appliedPromoDiscount + deliveryFee);

  const handleSubmitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    if (flaskUser?.role === 'customer' && paymentMethod !== 'cod') {
      showToast(
        t(
          'Only cash-on-delivery is enabled for the safe marketplace bridge. Online payment requires approved staging configuration.',
          'এই নিরাপদ marketplace bridge-এ শুধু cash-on-delivery চালু আছে। Online payment-এর জন্য অনুমোদিত staging configuration প্রয়োজন।',
        ),
        'warning',
      );
      setIsSubmitting(false);
      return;
    }

    const orderItems: OrderItem[] = cart.map(item => {
      const price = item.product.discount_price ?? item.product.price;
      const modifier = item.selectedVariant?.priceModifier || 0;
      const unit = price + modifier;
      return {
        product_id: item.product.id,
        product_name: item.product.name,
        product_name_bn: item.product.name_bn,
        seller_id: item.product.seller_id,
        seller_name: item.product.seller_name,
        image: item.product.image,
        unit_price: unit,
        quantity: item.quantity,
        variant_name: item.selectedVariant?.name,
        total_price: unit * item.quantity,
      };
    });

    if (flaskUser?.role === 'customer') {
      try {
        await submitMarketplaceCheckout({
          customerName: fullName,
          phone,
          address: [streetAddress, thana, district, division, deliveryNotes].filter(Boolean).join(', '),
          city: district,
          promotionCode: activeCoupon?.code,
        });
        setIsSubmitting(false);
        setCurrentView('order-confirmation');
      } catch (error) {
        showToast(
          error instanceof Error ? error.message : t('The server rejected this checkout.', 'সার্ভার চেকআউটটি গ্রহণ করেনি।'),
          'error',
        );
        setIsSubmitting(false);
      }
      return;
    }

    setTimeout(() => {
      const confirmedOrder = placeOrder({
        customer_name: fullName,
        customer_phone: phone,
        customer_email: email,
        delivery_address: {
          division,
          district,
          thana,
          street: streetAddress,
          notes: deliveryNotes,
        },
        delivery_speed: deliverySpeed,
        payment_method: paymentMethod,
        payment_status: paymentMethod === 'cod' ? 'pending' : 'paid',
        items: orderItems,
        subtotal: cartSubtotal,
        delivery_fee: deliveryFee,
        discount_amount: appliedPromoDiscount,
        promo_code: activeCoupon?.code,
        total_amount: grandTotal,
      });

      setIsSubmitting(false);
      setCurrentView('order-confirmation');
    }, 700);
  };

  return (
    <div className="space-y-6 pb-16">
      {/* Title */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-black text-ink">
          {t('Secure Checkout', 'নিরাপদ চেকআউট')}
        </h1>
        <p className="text-xs sm:text-sm text-muted mt-0.5">
          {t('Complete your order with verified vendor escrow protection', 'নিরাপদ পেমেন্ট ও ডোরস্টেপ এক্সপ্রেস ডেলিভারি')}
        </p>
      </div>

      <form onSubmit={handleSubmitOrder} className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
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
              <span>{t('2. Delivery Speed Option', '২. ডেলিভারির গতি ও মাধ্যম')}</span>
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
                    <span className="text-xs font-bold text-primary">
                      {isFreeDeliveryCoupon ? t('FREE', 'ফ্রি') : formatPrice(baseDeliveryFee)}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted mt-1">
                    {division === 'Dhaka'
                      ? t('Delivered within 24 hours inside Dhaka', '২৪ ঘণ্টার মধ্যে পৌঁছে যাবে')
                      : t('Delivered in 2-3 business days', '২-৩ কার্যদিবসের মধ্যে ডেলিভারি')}
                  </p>
                </div>
              </label>

              <label
                className={`p-4 rounded-2xl border cursor-pointer transition-all flex items-start gap-3 ${
                  deliverySpeed === 'express'
                    ? 'border-primary bg-primary-light/40 shadow-xs'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="speed"
                  checked={deliverySpeed === 'express'}
                  onChange={() => setDeliverySpeed('express')}
                  className="mt-0.5 accent-primary"
                />
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-xs text-ink">
                      {t('3-Hour Hyper Express', '৩ ঘণ্টা এক্সপ্রেস ডেলিভারি')}
                    </span>
                    <span className="text-xs font-bold text-accent">
                      {formatPrice((isFreeDeliveryCoupon ? 0 : baseDeliveryFee) + 50)}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted mt-1">
                    {t('Direct dispatch by nearest dedicated NexHaat rider', 'নিকটস্থ রাইডারের মাধ্যমে দ্রুত ডেলিভারি')}
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

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { id: 'cod', label: 'Cash on Delivery', label_bn: 'ক্যাশ অন ডেলিভারি', icon: <Banknote className="w-5 h-5" /> },
                { id: 'bkash', label: 'bKash Wallet', label_bn: 'বিকাশ', icon: <span className="font-bold text-pink-600 text-sm">bKash</span> },
                { id: 'nagad', label: 'Nagad Wallet', label_bn: 'নগদ', icon: <span className="font-bold text-orange-600 text-sm">Nagad</span> },
                { id: 'card', label: 'SSLCommerz (Card)', label_bn: 'কার্ড / ব্যাংকিং', icon: <CreditCard className="w-5 h-5 text-blue-600" /> },
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
                    onChange={() => setPaymentMethod(pm.id as any)}
                    className="sr-only"
                  />
                  <div className="h-6 flex items-center justify-center">{pm.icon}</div>
                  <span className="text-xs font-bold text-ink">
                    {t(pm.label, pm.label_bn)}
                  </span>
                </label>
              ))}
            </div>

            {/* bKash Payment Box Simulation */}
            {paymentMethod === 'bkash' && (
              <div className="p-4 rounded-2xl bg-pink-50 border border-pink-200 text-xs space-y-2.5">
                <div className="flex items-center gap-2 font-bold text-pink-900">
                  <CheckCircle2 className="w-4 h-4 text-pink-600" />
                  <span>{t('bKash Instant Gateway Simulation', 'বিকাশ সরাসরি পেমেন্ট')}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-slate-600 mb-1">{t('bKash Number', 'বিকাশ নম্বর')}</label>
                    <input
                      type="text"
                      value={bkashNumber}
                      onChange={(e) => setBkashNumber(e.target.value)}
                      className="w-full p-2 rounded-lg border border-pink-300 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 mb-1">{t('PIN (Sandbox Demo)', 'পিন নম্বর')}</label>
                    <input
                      type="password"
                      maxLength={5}
                      value={bkashPin}
                      onChange={(e) => setBkashPin(e.target.value)}
                      placeholder="•••••"
                      className="w-full p-2 rounded-lg border border-pink-300 bg-white"
                    />
                  </div>
                </div>
              </div>
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
                <span>{t('Delivery Charge', 'ডেলিভারি চার্জ')}</span>
                <span className="font-semibold text-ink">
                  {deliveryFee === 0 ? (
                    <span className="text-emerald-600 font-bold">{t('FREE', 'ফ্রি')}</span>
                  ) : (
                    formatPrice(deliveryFee)
                  )}
                </span>
              </div>
              <div className="flex justify-between text-base font-black text-ink pt-2 border-t border-slate-200">
                <span>{t('Grand Total', 'সর্বমোট প্রদেয় মূল্য')}</span>
                <span className="text-primary">{formatPrice(grandTotal)}</span>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="neu-button w-full py-4 rounded-2xl bg-primary text-white font-black text-sm shadow-md hover:bg-primary-hover disabled:bg-slate-300 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <span>{t('Confirming Order...', 'অর্ডার প্রক্রিয়াধীন...')}</span>
              ) : (
                <>
                  <span>{t('Confirm & Place Order', 'অর্ডার সম্পন্ন করুন')}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400 text-center pt-1">
              <ShieldCheck className="w-4 h-4 text-success" />
              <span>{t('Encrypted checkout & 100% money-back guarantee', 'এনক্রিপ্টেড পেমেন্ট ও শতভাগ রিফান্ড নিশ্চয়তা')}</span>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};
