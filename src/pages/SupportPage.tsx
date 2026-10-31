import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Headphones, Phone, Mail, MessageSquare, ChevronDown, 
  ChevronUp, CheckCircle2, ShieldCheck, Clock 
} from 'lucide-react';

export const SupportPage: React.FC = () => {
  const { t, showToast } = useApp();

  const [expandedFaq, setExpandedFaq] = useState<number | null>(0);
  const [ticketSubject, setTicketSubject] = useState('');
  const [ticketMessage, setTicketMessage] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const faqs = [
    {
      q: 'Which areas in Bangladesh do you deliver to?',
      q_bn: 'বাংলাদেশের কোন কোন এলাকায় আপনারা ডেলিভারি করেন?',
      a: 'We provide guaranteed 3-hour hyper-local express delivery within all metropolitan areas of Dhaka (Dhanmondi, Gulshan, Banani, Uttara, Mirpur, Mohammadpur, Old Dhaka). We also deliver to Chittagong, Sylhet, and all 64 districts via courier partners within 48 to 72 hours.',
      a_bn: 'আমরা সমগ্র ঢাকা শহরে (ধানমন্ডি, গুলশান, বনানী, উত্তরা, মিরপুর, পুরান ঢাকা) ৩ ঘণ্টার মধ্যে এক্সপ্রেস ডেলিভারি দিয়ে থাকি। এছাড়া চট্টগ্রাম, সিলেটসহ ৬৪টি জেলায় কুরিয়ার সার্ভিসের মাধ্যমে ৪৮-৭২ ঘণ্টায় পণ্য পৌঁছে দেওয়া হয়।',
    },
    {
      q: 'How does Cash on Delivery (COD) and bKash payment work?',
      q_bn: 'ক্যাশ অন ডেলিভারি এবং বিকাশ পেমেন্ট কীভাবে কাজ করে?',
      a: 'You can pay in cash directly to our rider after inspecting the parcel at your doorstep. For contactless orders, you can pay instantly using bKash, Nagad, or credit/debit cards during checkout through our SSLCommerz secure gateway.',
      a_bn: 'পণ্য হাতে পেয়ে দেখে ডেলিভারি রাইডারের কাছে নগদ মূল্য পরিশোধ করতে পারবেন। অথবা চেকআউটের সময় বিকাশ, নগদ বা ব্যাংকিং কার্ডের মাধ্যমে সহজে পেমেন্ট করতে পারবেন।',
    },
    {
      q: 'What is the 7-day returns and refund policy?',
      q_bn: '৭ দিনের রিটার্ন ও রিফান্ড পলিসি কী?',
      a: 'If any fresh produce, fish, meat, or grocery item arrives damaged, stale, or incorrect, you can request an instant return directly from the "My Orders" tab within 7 days. Our rider will pick up the item and your refund will be processed promptly.',
      a_bn: 'পণ্য কোনো কারণে নষ্ট, বাসি বা ত্রুটিপূর্ণ হলে ৭ দিনের মধ্যে "আমার অর্ডার" সেকশন থেকে সরাসরি রিটার্ন রিকোয়েস্ট করতে পারেন। আমাদের রাইডার পণ্য সংগ্রহ করে টাকা রিফান্ড করে দেবেন।',
    },
    {
      q: 'How do I register as a seller or express delivery rider?',
      q_bn: 'কীভাবে বিক্রেতা বা ডেলিভারি রাইডার হিসেবে যুক্ত হব?',
      a: 'Navigate to the top workspace switcher in the header and select "Seller Portal" or "Rider Portal". Verified merchants receive instant payouts and nationwide catalog distribution.',
      a_bn: 'হেডারে দেওয়া পোর্টাল সুইচ থেকে "সেলার পোর্টাল" অথবা "রাইডার পোর্টাল" বেছে নিয়ে আবেদন করতে পারেন।',
    },
  ];

  const handleTicketSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketSubject || !ticketMessage) return;
    setIsSubmitted(true);
    showToast(t('Support ticket created. Our team will contact you shortly.', 'আপনার অভিযোগ গ্রহণ করা হয়েছে। দ্রুত যোগাযোগ করা হবে।'));
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      {/* Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-border shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-primary font-bold text-xs mb-1.5">
            <Headphones className="w-3.5 h-3.5" />
            <span>{t('NexHaat Care & Support', 'নেক্সহাট গ্রাহক সেবা')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-ink">
            {t('Help & Customer Support Center', 'সহায়তা ও গ্রাহক সেবা কেন্দ্র')}
          </h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            {t('Our dedicated team in Dhaka is available 7 days a week from 8:00 AM to 11:00 PM', 'সপ্তাহের ৭ দিন সকাল ৮টা থেকে রাত ১১টা পর্যন্ত সার্বক্ষণিক সেবা')}
          </p>
        </div>

        <div className="flex flex-col gap-1 self-start sm:self-auto bg-slate-50 p-3 rounded-2xl border border-slate-200 text-xs">
          <div className="flex items-center gap-2 text-ink font-bold">
            <Phone className="w-4 h-4 text-emerald-600" />
            <span>+880 9612 000 000</span>
          </div>
          <span className="text-[11px] text-muted">Toll-free customer hotline</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
        {/* FAQs Column */}
        <div className="md:col-span-7 space-y-4">
          <h3 className="font-bold text-base text-ink">
            {t('Frequently Asked Questions', 'সাধারণ জিজ্ঞাসা ও প্রশ্নোত্তর')}
          </h3>

          <div className="space-y-3">
            {faqs.map((faq, idx) => {
              const isExpanded = expandedFaq === idx;
              return (
                <div
                  key={idx}
                  className="rounded-2xl bg-white border border-border shadow-xs overflow-hidden transition-colors"
                >
                  <button
                    onClick={() => setExpandedFaq(isExpanded ? null : idx)}
                    className="w-full p-4 text-left font-bold text-xs sm:text-sm text-ink flex items-center justify-between gap-2 hover:bg-slate-50"
                  >
                    <span>{t(faq.q, faq.q_bn)}</span>
                    {isExpanded ? (
                      <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                    )}
                  </button>

                  {isExpanded && (
                    <div className="px-4 pb-4 text-xs text-slate-600 leading-relaxed border-t border-slate-100 pt-3">
                      {t(faq.a, faq.a_bn)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Contact / Ticket Form Column */}
        <div className="md:col-span-5 space-y-4">
          <div className="p-6 rounded-3xl bg-white border border-border shadow-card space-y-4">
            <h3 className="font-bold text-sm text-ink pb-3 border-b border-slate-100 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-primary" />
              <span>{t('Send a Support Ticket', 'অভিযোগ বা বার্তা পাঠান')}</span>
            </h3>

            {isSubmitted ? (
              <div className="p-4 bg-emerald-50 rounded-2xl border border-emerald-200 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                <h4 className="font-bold text-xs text-emerald-900">
                  {t('Ticket Submitted Successfully!', 'বার্তা সফলভাবে পাঠানো হয়েছে!')}
                </h4>
                <p className="text-[11px] text-emerald-800">
                  {t('Ticket ID #TK-9821. An agent will call or email you within 30 minutes.', 'টিকেট আইডি #TK-9821। ৩০ মিনিটের মধ্যে যোগাযোগ করা হবে।')}
                </p>
                <button
                  onClick={() => setIsSubmitted(false)}
                  className="mt-2 text-xs font-bold text-primary hover:underline"
                >
                  {t('Send another message', 'আরেকটি বার্তা পাঠান')}
                </button>
              </div>
            ) : (
              <form onSubmit={handleTicketSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-600 font-semibold mb-1">
                    {t('Subject / Order Ref', 'বিষয় বা অর্ডার নম্বর')} *
                  </label>
                  <input
                    type="text"
                    required
                    value={ticketSubject}
                    onChange={(e) => setTicketSubject(e.target.value)}
                    placeholder="e.g. Delivery status of NH-2026-8821"
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white"
                  />
                </div>

                <div>
                  <label className="block text-slate-600 font-semibold mb-1">
                    {t('Message / Query Details', 'বিস্তারিত বার্তা')} *
                  </label>
                  <textarea
                    required
                    rows={4}
                    value={ticketMessage}
                    onChange={(e) => setTicketMessage(e.target.value)}
                    placeholder="Describe how we can help you today..."
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white"
                  />
                </div>

                <button
                  type="submit"
                  className="neu-button w-full py-3 rounded-xl bg-primary text-white font-bold text-xs hover:bg-primary-hover shadow-sm"
                >
                  {t('Submit Support Ticket', 'টিকেট জমা দিন')}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
