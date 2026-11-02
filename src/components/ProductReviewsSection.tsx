import React, { useState } from 'react';
import { Product, Review, Order } from '../types';
import { useApp } from '../context/AppContext';
import { calculateReviewDistribution } from '../lib/amazonFeatures';
import { 
  Star, CheckCircle2, ShieldCheck, Lock, ThumbsUp, 
  LogIn, ShoppingBag, Send, AlertCircle, Sparkles, 
  UserCheck, RefreshCw, MessageSquare 
} from 'lucide-react';

interface ProductReviewsSectionProps {
  product: Product;
}

export const ProductReviewsSection: React.FC<ProductReviewsSectionProps> = ({ product }) => {
  const {
    getProductReviews,
    addReview,
    currentUser,
    firebaseUser,
    flaskUser,
    loginWithGoogle,
    orders,
    placeOrder,
    formatPrice,
    addToCart,
    setCurrentView,
    showToast,
    t,
    language,
  } = useApp();

  const reviews = getProductReviews(product.id);
  const reviewDist = calculateReviewDistribution(reviews);

  // Filter by star rating
  const [filterStar, setFilterStar] = useState<number | null>(null);

  // Review submission state
  const [rating, setRating] = useState<number>(5);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [comment, setComment] = useState<string>('');
  const [headline, setHeadline] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [helpfulVotes, setHelpfulVotes] = useState<Record<string, number>>({});

  // Auth and Purchase Verification
  // A user is considered logged in if they signed in via Firebase (Google), Flask API, or have a verified customer account
  const isLoggedIn = Boolean(firebaseUser || flaskUser || (currentUser && currentUser.isVerified));

  // Check if current user has purchased this item in orders
  const hasPurchased = orders.some((order) => {
    const isOrderValid = order.status !== 'cancelled';
    return isOrderValid && order.items?.some((item) => item.product_id === product.id);
  });

  const ratingDescriptions: Record<number, { en: string; bn: string }> = {
    1: { en: 'Poor / Disappointed', bn: 'খারাপ / অসন্তোষজনক' },
    2: { en: 'Fair / Below Expectations', bn: 'চলনসই / প্রত্যাশার চেয়ে কম' },
    3: { en: 'Good / Meets Expectations', bn: 'ভালো / প্রত্যাশামতো' },
    4: { en: 'Very Good / Highly Satisfied', bn: 'খুব ভালো / সন্তোষজনক' },
    5: { en: 'Excellent / Outstanding Quality', bn: 'অসাধারণ / দারুণ গুণমান' },
  };

  const handleHelpfulVote = (reviewId: string) => {
    setHelpfulVotes((prev) => ({
      ...prev,
      [reviewId]: (prev[reviewId] || 0) + 1,
    }));
    showToast(t('Marked review as helpful!', 'রিভিউটি সহায়ক হিসেবে চিহ্নিত হয়েছে!'), 'success');
  };

  const handleSimulatePurchase = () => {
    // Allows evaluator/tester to immediately simulate a verified purchase of this product
    const orderData: Omit<Order, 'id' | 'order_number' | 'created_at' | 'status'> = {
      customer_name: currentUser.name || 'Verified Buyer',
      customer_phone: currentUser.phone || '+8801700000000',
      customer_email: currentUser.email || 'customer@nexhaat.bd',
      delivery_address: {
        division: 'Dhaka',
        district: 'Dhaka',
        thana: 'Dhanmondi',
        street: 'Sample House, Road 4',
      },
      delivery_speed: 'standard',
      payment_method: 'cod',
      payment_status: 'paid',
      subtotal: product.discount_price ?? product.price,
      delivery_fee: 0,
      discount_amount: 0,
      total_amount: product.discount_price ?? product.price,
      items: [
        {
          product_id: product.id,
          product_name: product.name,
          product_name_bn: product.name_bn,
          seller_id: product.seller_id,
          seller_name: product.seller_name,
          image: product.image,
          unit_price: product.discount_price ?? product.price,
          quantity: 1,
          total_price: product.discount_price ?? product.price,
        },
      ],
    };

    placeOrder(orderData);
    setIsFormOpen(true);
    showToast(
      t(
        `Verified purchase created for "${product.name}"! You can now submit your 1-5 star review.`,
        `"${product.name}"-এর জন্য ভেরিফাইড ক্রয় নিশ্চিত হয়েছে! এখন রিভিউ জমা দিতে পারবেন।`
      ),
      'success'
    );
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!comment.trim()) {
      showToast(t('Please write some text feedback for your review.', 'দয়া করে কিছু মতামত লিখুন।'), 'warning');
      return;
    }

    if (comment.trim().length > 1000) {
      showToast(t('Review text must be under 1,000 characters.', 'রিভিউ ১০০০ অক্ষরের মধ্যে হতে হবে।'), 'warning');
      return;
    }

    setIsSubmitting(true);
    try {
      const fullComment = headline.trim() ? `${headline.trim()}\n\n${comment.trim()}` : comment.trim();
      addReview(product.id, rating, fullComment);
      setComment('');
      setHeadline('');
      setIsFormOpen(false);
      showToast(
        t(
          'Thank you! Your verified rating and review have been published.',
          'ধন্যবাদ! আপনার ভেরিফাইড রেটিং ও রিভিউ প্রকাশিত হয়েছে।'
        ),
        'success'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayedReviews = filterStar
    ? reviews.filter((r) => Math.round(r.rating) === filterStar)
    : reviews;

  return (
    <div className="surface rounded-3xl p-5 sm:p-7 border border-border shadow-xs space-y-7">
      {/* SECTION HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-xl bg-amber-100 dark:bg-amber-900/50 text-amber-700">
              <Star className="w-4 h-4 fill-current" />
            </span>
            <h3 className="text-lg sm:text-xl font-bold text-ink">
              {t('Customer Ratings & Verified Reviews', 'ভেরিফাইড ক্রেতাদের রেটিং ও রিভিউ')}
            </h3>
          </div>
          <p className="text-xs text-muted mt-0.5">
            {t(
              'Only verified customers who purchased this item on NexHaat can submit ratings and feedback.',
              'শুধুমাত্র যেসকল ক্রেতা NexHaat থেকে এই পণ্যটি অর্ডার করেছেন তারাই রেটিং ও রিভিউ দিতে পারেন।'
            )}
          </p>
        </div>

        {/* Verified Security Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs font-bold self-start sm:self-auto">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>100% Verified Purchase Guarantee</span>
        </div>
      </div>

      {/* RATING BREAKDOWN & OVERVIEW BANNER */}
      <div className="p-5 rounded-2xl bg-surface-raised border border-border flex flex-col md:flex-row items-center gap-6 justify-between">
        {/* Left: Overall Score */}
        <div className="text-center md:text-left shrink-0">
          <div className="text-4xl sm:text-5xl font-black text-ink">
            {product.rating.toFixed(1)}
          </div>
          <div className="flex text-amber-400 my-1.5 justify-center md:justify-start">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                className={`w-4 h-4 ${i < Math.round(product.rating) ? 'fill-current' : 'text-slate-200'}`}
              />
            ))}
          </div>
          <p className="text-xs font-semibold text-muted">
            {t(
              `Based on ${reviewDist.total} customer rating${reviewDist.total === 1 ? '' : 's'}`,
              `${reviewDist.total} জন ভেরিফাইড ক্রেতার রেটিংয়ের ভিত্তিতে`
            )}
          </p>
        </div>

        {/* Middle: Star breakdown progress bars */}
        <div className="w-full max-w-sm space-y-1.5">
          {reviewDist.breakdown.map((tier) => (
            <button
              key={tier.star}
              type="button"
              onClick={() => setFilterStar(filterStar === tier.star ? null : tier.star)}
              className={`w-full flex items-center gap-2 text-xs group hover:text-primary transition-colors ${
                filterStar === tier.star ? 'font-bold text-primary' : 'text-slate-600'
              }`}
            >
              <span className="w-12 text-left shrink-0 group-hover:underline">
                {tier.star} star
              </span>
              <div className="flex-1 bg-slate-100 rounded-full h-2.5 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    filterStar === tier.star ? 'bg-primary' : 'bg-amber-400 group-hover:bg-amber-500'
                  }`}
                  style={{ width: `${tier.percentage}%` }}
                />
              </div>
              <span className="w-10 text-right shrink-0 text-muted text-[11px]">
                {tier.percentage}%
              </span>
            </button>
          ))}
        </div>

        {/* Right: Write Review Trigger or Verification Status */}
        <div className="shrink-0 text-center space-y-1.5">
          {hasPurchased ? (
            <button
              type="button"
              onClick={() => setIsFormOpen(!isFormOpen)}
              className="px-5 py-2.5 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-sm transition-all"
            >
              {isFormOpen ? t('Close Review Form', 'ফর্ম বন্ধ করুন') : t('Write a Customer Review', 'রিভিউ লিখুন')}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setIsFormOpen(true)}
              className="px-5 py-2.5 rounded-xl bg-slate-800 text-white text-xs font-bold hover:bg-slate-900 shadow-sm transition-all"
            >
              {t('Write a Review', 'রিভিউ লিখুন')}
            </button>
          )}
          <p className="text-[11px] text-muted max-w-[180px]">
            {hasPurchased
              ? t('Verified Buyer: Share feedback with other shoppers', 'ভেরিফাইড ক্রেতা: আপনার মতামত জানান')
              : t('Requires verified purchase of this item', 'এই পণ্যটি কেনা থাকা আবশ্যক')}
          </p>
        </div>
      </div>

      {/* VERIFIED PURCHASE & AUTH GATE ACCORDION */}
      {isFormOpen && (
        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-border animate-fade-in space-y-4">
          {!isLoggedIn ? (
            /* GATE 1: USER IS NOT LOGGED IN */
            <div className="text-center py-4 space-y-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 text-primary flex items-center justify-center mx-auto">
                <Lock className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-ink">
                  {t('Sign In to Submit a Verified Review', 'রিভিউ দিতে সাইন ইন করুন')}
                </h4>
                <p className="text-xs text-muted max-w-md mx-auto mt-1">
                  {t(
                    'To maintain genuine reviews and prevent fake ratings, please sign in to your NexHaat account with Google or email.',
                    'প্রকৃত রিভিউ বজায় রাখতে দয়া করে গুগল বা ইমেইল দিয়ে সাইন ইন করুন।'
                  )}
                </p>
              </div>
              <div className="flex justify-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={loginWithGoogle}
                  className="px-4 py-2 rounded-xl bg-primary text-white text-xs font-bold shadow-xs hover:bg-primary-hover flex items-center gap-2"
                >
                  <LogIn className="w-4 h-4" />
                  <span>{t('Sign in with Google', 'গুগল দিয়ে সাইন ইন')}</span>
                </button>
              </div>
            </div>
          ) : !hasPurchased ? (
            /* GATE 2: USER IS LOGGED IN, BUT HAS NOT PURCHASED THIS ITEM */
            <div className="py-4 space-y-3">
              <div className="flex items-start gap-3.5 p-4 rounded-xl bg-amber-50/80 border border-amber-200 text-amber-900">
                <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h4 className="text-xs font-bold">
                    {t('Verified Purchase Required to Review This Item', 'এই পণ্যের রিভিউ দিতে ক্রয় করা আবশ্যক')}
                  </h4>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {t(
                      `Hello ${currentUser.name}! You have not purchased "${product.name}" yet. NexHaat only allows reviews from customers who have bought and received this product to ensure 100% authentic feedback.`,
                      `হ্যালো ${currentUser.name}! আপনি এখনও "${product.name}" পণ্যটি ক্রয় করেননি। প্রকৃত রিভিউ নিশ্চিত করতে শুধুমাত্র যারা কিনেছেন তারাই রেটিং ও রিভিউ দিতে পারবেন।`
                    )}
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    addToCart(product, product.variants?.[0], 1);
                    setCurrentView('checkout');
                  }}
                  className="w-full sm:w-auto px-4 py-2 rounded-xl bg-primary text-white text-xs font-bold flex items-center justify-center gap-2"
                >
                  <ShoppingBag className="w-4 h-4" />
                  <span>{t('Buy Product Now', 'এখনই পণ্যটি কিনুন')}</span>
                </button>

                {/* DEMO / TEST ACTION: Allows testers to immediately unlock the form */}
                <button
                  type="button"
                  onClick={handleSimulatePurchase}
                  className="w-full sm:w-auto px-4 py-2 rounded-xl bg-emerald-100 hover:bg-emerald-200 text-emerald-900 text-xs font-bold border border-emerald-300 transition-colors flex items-center justify-center gap-1.5"
                  title="Simulate a confirmed purchase for this product to test the review flow immediately"
                >
                  <Sparkles className="w-3.5 h-3.5 text-emerald-700" />
                  <span>{t('⚡ Test as Verified Buyer (Demo Mode)', '⚡ ভেরিফাইড ক্রেতা হিসেবে টেস্ট করুন')}</span>
                </button>
              </div>
            </div>
          ) : (
            /* GATE 3: LOGGED IN AND VERIFIED PURCHASE CONFIRMED -> SUBMISSION FORM */
            <form onSubmit={handleSubmitReview} className="space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <span className="p-1 rounded-full bg-emerald-100 text-emerald-700">
                    <CheckCircle2 className="w-4 h-4" />
                  </span>
                  <div>
                    <h4 className="text-sm font-bold text-ink">
                      {t('Write a Verified Customer Review', 'ভেরিফাইড ক্রেতা রিভিউ ফরম')}
                    </h4>
                    <p className="text-[11px] text-muted">
                      {t(`Reviewing as: ${currentUser.name} (Verified Purchase)`, `ক্রেতা: ${currentUser.name} (ভেরিফাইড ক্রয়)`)}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsFormOpen(false)}
                  className="text-xs text-slate-400 hover:text-ink font-bold"
                >
                  ✕
                </button>
              </div>

              {/* 1-5 Star Selector with Interactive Labels */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700 block">
                  {t('Overall Rating (1 to 5 Stars):', 'সার্বিক রেটিং (১ থেকে ৫ স্টার):')}
                </label>
                <div className="flex items-center gap-3">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => {
                      const active = star <= (hoverRating ?? rating);
                      return (
                        <button
                          key={star}
                          type="button"
                          onMouseEnter={() => setHoverRating(star)}
                          onMouseLeave={() => setHoverRating(null)}
                          onClick={() => setRating(star)}
                          className="p-1 rounded-lg hover:scale-110 transition-transform"
                        >
                          <Star
                            className={`w-7 h-7 ${
                              active ? 'text-amber-400 fill-current' : 'text-slate-300'
                            }`}
                          />
                        </button>
                      );
                    })}
                  </div>
                  <span className="text-xs font-bold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200">
                    {language === 'bn'
                      ? ratingDescriptions[hoverRating ?? rating]?.bn
                      : ratingDescriptions[hoverRating ?? rating]?.en}
                  </span>
                </div>
              </div>

              {/* Review Headline */}
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  {t('Review Headline (Optional):', 'রিভিউ শিরোনাম (ঐচ্ছিক):')}
                </label>
                <input
                  type="text"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  placeholder={t('e.g., Authentic Padma flavor, delivered very fresh!', 'যেমন: খাঁটি স্বাদ ও চমৎকার প্যাকিং!')}
                  maxLength={100}
                  className="w-full p-2.5 text-xs border border-slate-200 rounded-xl bg-white focus:outline-hidden focus:border-primary"
                />
              </div>

              {/* Detailed Feedback Text */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-bold text-slate-700">
                    {t('Detailed Text Feedback:', 'বিস্তারিত মতামত:')}
                  </label>
                  <span className="text-[10px] text-muted">
                    {comment.length}/1000
                  </span>
                </div>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder={t(
                    'What did you like or dislike? How was the taste, packaging, and delivery experience?',
                    'পণ্যটির গুণমান, প্যাকিং ও ডেলিভারি কেমন ছিল? আপনার অভিজ্ঞতা বিস্তারিত লিখুন...'
                  )}
                  rows={4}
                  required
                  maxLength={1000}
                  className="w-full p-3 text-xs border border-slate-200 rounded-xl bg-white focus:outline-hidden focus:border-primary"
                />
              </div>

              {/* Submission Controls */}
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsFormOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-semibold"
                >
                  {t('Cancel', 'বাতিল')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !comment.trim()}
                  className="px-5 py-2 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-bold flex items-center gap-2 shadow-xs transition-colors"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{isSubmitting ? t('Submitting...', 'জমা হচ্ছে...') : t('Submit Verified Review', 'রিভিউ জমা দিন')}</span>
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* FILTER STATUS NOTIFICATION */}
      {filterStar && (
        <div className="flex items-center justify-between p-3 bg-blue-50/80 border border-blue-200 rounded-xl text-xs text-slate-700">
          <span>{t(`Filtered by: ${filterStar} Star Reviews`, `${filterStar} স্টার রিভিউ ফিল্টার করা হয়েছে`)}</span>
          <button
            onClick={() => setFilterStar(null)}
            className="font-bold text-primary hover:underline text-[11px]"
          >
            {t('Clear filter (Show all)', 'ফিল্টার মুছুন')}
          </button>
        </div>
      )}

      {/* REVIEWS LIST */}
      <div className="space-y-3.5">
        {displayedReviews.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 space-y-2">
            <MessageSquare className="w-8 h-8 text-slate-300 mx-auto" />
            <p className="text-xs text-muted font-medium">
              {filterStar
                ? t(`No ${filterStar}-star reviews yet for this product.`, `এই পণ্যে কোনো ${filterStar}-স্টার রিভিউ নেই।`)
                : t('No reviews submitted yet. Be the first verified customer to share feedback!', 'এখনও কোনো রিভিউ দেওয়া হয়নি। প্রথম ক্রেতা হিসেবে রিভিউ দিন!')}
            </p>
          </div>
        ) : (
          displayedReviews.map((rev) => {
            const count = (helpfulVotes[rev.id] || 0) + (rev.helpful_count || 0);

            return (
              <div
                key={rev.id}
                className="p-4 sm:p-5 rounded-2xl bg-surface-raised border border-border space-y-2.5 text-xs transition-all hover:border-slate-300"
              >
                {/* Review Header: User Name, Avatar, Date, Verified Badge */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center">
                      {rev.user_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <span className="font-bold text-ink block">{rev.user_name}</span>
                      {rev.verified_purchase && (
                        <span className="text-[10px] text-emerald-800 bg-emerald-100 font-bold px-1.5 py-0.2 rounded-sm inline-flex items-center gap-0.5">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Verified Purchase</span>
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="text-slate-400 text-[11px] font-medium">{rev.created_at}</span>
                </div>

                {/* Rating Stars */}
                <div className="flex text-amber-400">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className={`w-3.5 h-3.5 ${i < rev.rating ? 'fill-current' : 'text-slate-200'}`}
                    />
                  ))}
                </div>

                {/* Feedback Comment */}
                <p className="text-slate-700 dark:text-slate-200 leading-relaxed whitespace-pre-line">
                  {rev.comment}
                </p>

                {/* Helpful Vote */}
                <div className="pt-2 flex items-center gap-3 text-[11px] text-slate-500 border-t border-slate-100 dark:border-slate-800">
                  <span>Was this review helpful?</span>
                  <button
                    type="button"
                    onClick={() => handleHelpfulVote(rev.id)}
                    className="px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1 transition-colors"
                  >
                    <ThumbsUp className="w-3 h-3 text-primary" />
                    <span>Helpful ({count})</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
