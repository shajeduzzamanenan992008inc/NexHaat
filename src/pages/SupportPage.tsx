import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Headphones, MessageSquare, ChevronDown, ChevronUp, CheckCircle2
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
      a: 'Delivery availability and estimated timing depend on the product and address. Review the options shown for your order at checkout.',
      a_bn: 'ডেলিভারির সুযোগ ও সম্ভাব্য সময় পণ্য এবং ঠিকানার ওপর নির্ভর করে। অর্ডারের সময় চেকআউটে দেখানো বিকল্প দেখুন।',
    },
    {
      q: 'How does Cash on Delivery (COD) and bKash payment work?',
      q_bn: 'ক্যাশ অন ডেলিভারি এবং বিকাশ পেমেন্ট কীভাবে কাজ করে?',
      a: 'Use only the payment methods presented by marketplace checkout for your order. The available methods can vary by order and configuration.',
      a_bn: 'আপনার অর্ডারের চেকআউটে দেখানো পেমেন্ট পদ্ধতিই ব্যবহার করুন। অর্ডার ও কনফিগারেশন অনুযায়ী পদ্ধতি ভিন্ন হতে পারে।',
    },
    {
      q: 'How can I ask about a return or refund?',
      q_bn: 'রিটার্ন বা রিফান্ড সম্পর্কে কীভাবে জানব?',
      a: 'Eligibility and next steps depend on the order, item, and current order status. Review the actions available in your order details.',
      a_bn: 'যোগ্যতা ও পরবর্তী পদক্ষেপ অর্ডার, পণ্য ও বর্তমান স্ট্যাটাসের ওপর নির্ভর করে। অর্ডারের বিস্তারিত অংশে থাকা কাজগুলো দেখুন।',
    },
    {
      q: 'How do I register as a seller or express delivery rider?',
      q_bn: 'কীভাবে বিক্রেতা বা ডেলিভারি রাইডার হিসেবে যুক্ত হব?',
      a: 'Use the Flask sign-in and application pages for seller onboarding. The role switch in the React preview only opens a local workspace mock.',
      a_bn: 'বিক্রেতা হিসেবে যুক্ত হওয়ার জন্য Flask সাইন-ইন ও আবেদন পেজ ব্যবহার করুন। React প্রিভিউয়ের role switch শুধু স্থানীয় mock workspace খোলে।',
    },
  ];

  const handleTicketSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketSubject || !ticketMessage) return;
    setIsSubmitted(true);
    showToast(t('This support form is a preview; your message was not sent.', 'এই support form প্রিভিউ; আপনার বার্তা পাঠানো হয়নি।'), 'warning');
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      {/* Banner */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-border shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-primary font-bold text-xs mb-1.5">
            <Headphones className="w-3.5 h-3.5" />
            <span>{t('HELP & SUPPORT', 'সহায়তা')}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-ink">
            {t('Help & Customer Support Center', 'সহায়তা ও গ্রাহক সেবা কেন্দ্র')}
          </h1>
          <p className="text-xs sm:text-sm text-muted mt-0.5">
            {t('Find answers about orders, payment options, and account access.', 'অর্ডার, পেমেন্ট ও অ্যাকাউন্ট ব্যবহারের তথ্য দেখুন।')}
          </p>
        </div>

        <div className="max-w-xs rounded-2xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-900" role="note">
          {t('The React support form below is a preview and does not create a support ticket.', 'নিচের React support form প্রিভিউ; এটি support ticket তৈরি করে না।')}
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
              <span>{t('Support form preview', 'Support form প্রিভিউ')}</span>
            </h3>

            {isSubmitted ? (
              <div className="p-4 bg-amber-50 rounded-2xl border border-amber-200 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-amber-600 mx-auto" />
                <h4 className="font-bold text-xs text-amber-900">
                  {t('Preview checked', 'প্রিভিউ দেখা হয়েছে')}
                </h4>
                <p className="text-[11px] text-amber-900">
                  {t('No ticket was created and your message was not sent.', 'কোনো ticket তৈরি হয়নি এবং আপনার বার্তা পাঠানো হয়নি।')}
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
                    placeholder="e.g. Delivery status question"
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
                    placeholder="Write a message to preview the form..."
                    className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white"
                  />
                </div>

                <button
                  type="submit"
                  className="neu-button w-full py-3 rounded-xl bg-primary text-white font-bold text-xs hover:bg-primary-hover shadow-sm"
                >
                  {t('Preview message', 'বার্তা প্রিভিউ করুন')}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
