import React, { useEffect, useState } from 'react';
import { Product, Review } from '../types';
import { useApp } from '../context/AppContext';
import { calculateReviewDistribution } from '../lib/amazonFeatures';
import {
  Star,
  CheckCircle2,
  ShieldCheck,
  Lock,
  ThumbsUp,
  LogIn,
  Send,
  MessageSquare,
} from 'lucide-react';
import { FlaskAuthPanel } from './FlaskAuthPanel';
import { toggleMarketplaceReviewHelpful } from '../lib/marketplaceApi';

interface ProductReviewsSectionProps {
  product: Product;
}

export const ProductReviewsSection: React.FC<ProductReviewsSectionProps> = ({ product }) => {
  const {
    addReview,
    flaskUser,
    isFlaskAuthLoading,
    refreshProductReviews,
    showToast,
    t,
    language,
  } = useApp();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [isReviewsLoading, setIsReviewsLoading] = useState(true);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const [reviewRefreshKey, setReviewRefreshKey] = useState(0);
  const [isAuthPanelOpen, setIsAuthPanelOpen] = useState(false);
  const [reviewSubmitError, setReviewSubmitError] = useState<string | null>(null);
  const [reviewSubmissionNotice, setReviewSubmissionNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setReviews([]);
    setIsReviewsLoading(true);
    setReviewsError(null);
    refreshProductReviews(product.id)
      .then((result) => {
        if (active) setReviews(result);
      })
      .catch((error: unknown) => {
        if (active) {
          setReviewsError(error instanceof Error && error.message ? error.message : 'Could not load reviews.');
        }
      })
      .finally(() => {
        if (active) setIsReviewsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [product.id, flaskUser?.id, refreshProductReviews, reviewRefreshKey]);

  useEffect(() => {
    if (flaskUser?.role === 'customer') setIsAuthPanelOpen(false);
  }, [flaskUser]);

  const reviewDist = calculateReviewDistribution(reviews);
  const displayedAverage = reviewDist.total > 0 ? reviewDist.average : 0;

  // Filter by star rating
  const [filterStar, setFilterStar] = useState<number | null>(null);

  // Review submission state
  const [rating, setRating] = useState<number>(5);
  const [hoverRating, setHoverRating] = useState<number | null>(null);
  const [comment, setComment] = useState<string>('');
  const [headline, setHeadline] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [pendingHelpfulVotes, setPendingHelpfulVotes] = useState<Record<string, boolean>>({});

  const isFlaskCustomer = flaskUser?.role === 'customer';
  const ratingDescriptions: Record<number, { en: string; bn: string }> = {
    1: { en: 'Poor / Disappointed', bn: 'খারাপ / অসন্তোষজনক' },
    2: { en: 'Fair / Below Expectations', bn: 'চলনসই / প্রত্যাশার চেয়ে কম' },
    3: { en: 'Good / Meets Expectations', bn: 'ভালো / প্রত্যাশামতো' },
    4: { en: 'Very Good / Highly Satisfied', bn: 'খুব ভালো / সন্তোষজনক' },
    5: { en: 'Excellent / Outstanding Quality', bn: 'অসাধারণ / দারুণ গুণমান' },
  };

  const handleHelpfulVote = async (review: Review) => {
    if (!flaskUser) {
      setIsFormOpen(true);
      setIsAuthPanelOpen(true);
      showToast(t('Sign in to mark a review helpful.', 'রিভিউটি সহায়ক বলতে সাইন ইন করুন।'), 'warning');
      return;
    }

    setPendingHelpfulVotes((current) => ({ ...current, [review.id]: true }));
    try {
      const result = await toggleMarketplaceReviewHelpful(product.id, review.id);
      setReviews((current) => current.map((item) => item.id === review.id
        ? { ...item, helpful_count: result.count, viewer_helpful: result.helpful }
        : item));
      showToast(t('Your helpful vote was updated.', 'আপনার সহায়ক ভোটটি আপডেট হয়েছে।'), 'success');
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : t('The helpful vote could not be updated.', 'সহায়ক ভোটটি আপডেট করা যায়নি।');
      showToast(message, 'error');
    } finally {
      setPendingHelpfulVotes((current) => ({ ...current, [review.id]: false }));
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    setReviewSubmitError(null);
    if (!isFlaskCustomer) {
      setIsAuthPanelOpen(true);
      return;
    }
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
      await addReview(product.id, rating, fullComment);
      setComment('');
      setHeadline('');
      setIsFormOpen(false);
      const notice = t(
        'Your review was submitted for moderation. It will appear after approval.',
        'আপনার রিভিউ মডারেশনের জন্য জমা হয়েছে। অনুমোদনের পর এটি দেখা যাবে।',
      );
      setReviewSubmissionNotice(notice);
      showToast(
        notice,
        'success'
      );
    } catch (error) {
      const message = error instanceof Error
        ? error.message
        : t('The review could not be submitted.', 'রিভিউ জমা দেওয়া যায়নি।');
      setReviewSubmitError(message);
      showToast(message, 'error');
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
              {t('Customer Ratings & Reviews', 'ক্রেতাদের রেটিং ও রিভিউ')}
            </h3>
          </div>
          <p className="text-xs text-muted mt-0.5">
            {t(
              'Flask checks delivered purchases for new reviews and publishes them after moderation.',
              'Flask নতুন রিভিউ জমার সময় ডেলিভারি হওয়া ক্রয় যাচাই করে, তারপর মডারেশনের পরে প্রকাশ করে।'
            )}
          </p>
        </div>

        {/* Verified Security Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs font-bold self-start sm:self-auto">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>{t('Purchase checks enforced by Flask', 'Flask ক্রয় যাচাই করে')}</span>
        </div>
      </div>

      {/* RATING BREAKDOWN & OVERVIEW BANNER */}
      <div className="p-5 rounded-2xl bg-surface-raised border border-border flex flex-col md:flex-row items-center gap-6 justify-between">
        {/* Left: Overall Score */}
        <div className="text-center md:text-left shrink-0">
          <div className="text-4xl sm:text-5xl font-black text-ink">
            {reviewDist.total > 0 ? displayedAverage.toFixed(1) : '—'}
          </div>
          {reviewDist.total > 0 && (
          <div className="flex text-amber-400 my-1.5 justify-center md:justify-start">
            {Array.from({ length: 5 }).map((_, i) => (
              <Star
                key={i}
                className={`w-4 h-4 ${i < Math.round(displayedAverage) ? 'fill-current' : 'text-slate-200'}`}
              />
            ))}
          </div>
          )}
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
          <button
            type="button"
            disabled={isFlaskAuthLoading}
            onClick={() => {
              setReviewSubmissionNotice(null);
              setIsFormOpen(!isFormOpen);
            }}
            className="px-5 py-2.5 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-sm transition-all disabled:opacity-50"
          >
            {isFlaskAuthLoading
              ? t('Checking account…', 'অ্যাকাউন্ট যাচাই হচ্ছে…')
              : isFormOpen
                ? t('Close Review Form', 'ফর্ম বন্ধ করুন')
                : t('Write a Review', 'রিভিউ লিখুন')}
          </button>
          <p className="text-[11px] text-muted max-w-[180px]">
            {t(
              'Flask verifies delivered purchase eligibility when you submit.',
              'জমা দেওয়ার সময় Flask ডেলিভারি হওয়া ক্রয়ের যোগ্যতা যাচাই করবে।',
            )}
          </p>
        </div>
      </div>

      {reviewSubmissionNotice && (
        <p role="status" aria-live="polite" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          {reviewSubmissionNotice}
        </p>
      )}

      {/* VERIFIED PURCHASE & AUTH GATE ACCORDION */}
      {isFormOpen && (
        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-border motion-panel-enter space-y-4">
          {!isFlaskCustomer ? (
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
                    'To keep reviews genuine, sign in with your NexHaat customer account. Flask checks purchase eligibility when you submit.',
                    'প্রকৃত রিভিউ নিশ্চিত করতে NexHaat কাস্টমার অ্যাকাউন্টে সাইন ইন করুন। জমা দেওয়ার সময় Flask ক্রয়ের যোগ্যতা যাচাই করবে।',
                  )}
                </p>
              </div>
              <div className="flex justify-center gap-3 pt-2">
                <button
                  type="button"
                  disabled={isFlaskAuthLoading}
                  onClick={() => setIsAuthPanelOpen(true)}
                  className="px-4 py-2 rounded-xl bg-primary text-white text-xs font-bold shadow-xs hover:bg-primary-hover flex items-center gap-2"
                >
                  <LogIn className="w-4 h-4" />
                  <span>{t('Sign in', 'সাইন ইন')}</span>
                </button>
              </div>
              {isAuthPanelOpen && <FlaskAuthPanel onClose={() => setIsAuthPanelOpen(false)} />}
            </div>
          ) : (
            /* Flask checks delivered-purchase eligibility on submission. */
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
                      {t(`Signed in as: ${flaskUser.email}`, `সাইন ইন: ${flaskUser.email}`)}
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

              <p className="text-xs text-muted">
                {t(
                  'Flask will check your delivered order again when you submit. Reviews are published only after moderation.',
                  'জমা দেওয়ার সময় Flask আপনার ডেলিভারি হওয়া অর্ডার আবার যাচাই করবে। মডারেশনের পর রিভিউ প্রকাশিত হবে।',
                )}
              </p>
              {reviewSubmitError && (
                <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  {reviewSubmitError}
                </p>
              )}

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
        {isReviewsLoading ? (
          <p role="status" aria-live="polite" className="rounded-2xl bg-slate-50 p-8 text-center text-sm text-muted">
            {t('Loading reviews…', 'রিভিউ লোড হচ্ছে…')}
          </p>
        ) : reviewsError ? (
          <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <p>{reviewsError}</p>
            <button
              type="button"
              onClick={() => setReviewRefreshKey((current) => current + 1)}
              className="shrink-0 font-bold underline"
            >
              {t('Try again', 'আবার চেষ্টা করুন')}
            </button>
          </div>
        ) : displayedReviews.length === 0 ? (
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
            const count = rev.helpful_count || 0;

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
                    onClick={() => void handleHelpfulVote(rev)}
                    disabled={pendingHelpfulVotes[rev.id]}
                    aria-pressed={Boolean(rev.viewer_helpful)}
                    className={`px-2.5 py-1 rounded-md border dark:border-slate-700 font-semibold flex items-center gap-1 transition-colors disabled:opacity-60 ${rev.viewer_helpful ? 'border-primary bg-primary/10 text-primary' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-100 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'}`}
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
