import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { 
  Sparkles, X, Send, Bot, User, ShoppingBag, 
  Trash2, ArrowRight, Star, CheckCircle2 
} from 'lucide-react';

export const AIAssistantDrawer: React.FC = () => {
  const { 
    isAIAssistantOpen, 
    setIsAIAssistantOpen, 
    aiMessages, 
    sendAIMessage, 
    clearAIChat, 
    products, 
    addToCart, 
    navigateToProduct, 
    formatPrice, 
    t 
  } = useApp();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isAIAssistantOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [aiMessages, isAIAssistantOpen]);

  if (!isAIAssistantOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendAIMessage(input.trim());
    setInput('');
  };

  const samplePrompts = [
    t('Dinner for 5 under ৳1500', '১৫০০ টাকার মধ্যে ৪-৫ জনের রাতের খাবার'),
    t('Tell me about Padma Ilish', 'পদ্মার রূপালী ইলিশের গুণাবলী'),
    t('Carbide-free mangoes', 'কেমিক্যালমুক্ত পাকা ফজলি আম'),
    t('What are today’s best deals?', 'আজকের সেরা মূল্যছাড় কী?'),
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={() => setIsAIAssistantOpen(false)}
      />

      {/* Drawer */}
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-blue-900 to-primary text-white">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-white/20 rounded-xl backdrop-blur-md">
                <Sparkles className="w-5 h-5 text-amber-300 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h2 className="font-bold text-white text-base">HaatAI Shopping Copilot</h2>
                  <span className="text-[10px] font-extrabold px-1.5 py-0.5 rounded-full bg-amber-400 text-slate-900">
                    Gemini
                  </span>
                </div>
                <p className="text-[11px] text-blue-200">
                  {t('Intelligent product advisor & recipe planner', 'বুদ্ধিমান কেনাকাটা ও খাদ্য সহকারী')}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={clearAIChat}
                className="p-2 text-blue-200 hover:text-white rounded-lg hover:bg-white/10"
                title="Clear chat"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsAIAssistantOpen(false)}
                className="p-2 text-blue-200 hover:text-white rounded-lg hover:bg-white/10"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 bg-slate-50">
            {aiMessages.map((msg) => {
              const isUser = msg.sender === 'user';
              return (
                <div
                  key={msg.id}
                  className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
                >
                  <div
                    className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 ${
                      isUser
                        ? 'bg-slate-800 text-white'
                        : 'bg-primary text-white shadow-sm'
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className={`max-w-[85%] space-y-2`}>
                    <div
                      className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-xs ${
                        isUser
                          ? 'bg-slate-900 text-white rounded-tr-xs'
                          : 'bg-white text-ink border border-slate-200/80 rounded-tl-xs'
                      }`}
                    >
                      {msg.text}
                      <span
                        className={`block text-[10px] mt-1.5 ${
                          isUser ? 'text-slate-400 text-right' : 'text-slate-400'
                        }`}
                      >
                        {msg.timestamp}
                      </span>
                    </div>

                    {/* Render Product Recommendations cards */}
                    {msg.suggestedProductIds && msg.suggestedProductIds.length > 0 && (
                      <div className="space-y-2 pt-1">
                        {msg.suggestedProductIds.map((pid) => {
                          const prod = products.find((p) => p.id === pid);
                          if (!prod) return null;
                          return (
                            <div
                              key={prod.id}
                              className="p-2.5 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-between gap-3 hover:border-primary transition-colors"
                            >
                              <img
                                src={prod.image}
                                alt={prod.name}
                                className="w-12 h-12 rounded-lg object-cover bg-slate-50 shrink-0 cursor-pointer"
                                onClick={() => {
                                  navigateToProduct(prod.slug);
                                  setIsAIAssistantOpen(false);
                                }}
                              />
                              <div
                                className="flex-1 min-w-0 cursor-pointer"
                                onClick={() => {
                                  navigateToProduct(prod.slug);
                                  setIsAIAssistantOpen(false);
                                }}
                              >
                                <p className="font-bold text-xs text-ink truncate hover:text-primary">
                                  {prod.name}
                                </p>
                                <div className="flex items-center gap-1.5 text-[11px] text-muted">
                                  <span className="font-bold text-primary">
                                    {formatPrice(prod.discount_price ?? prod.price)}
                                  </span>
                                  <span>•</span>
                                  <span className="text-amber-500 font-semibold">★ {prod.rating}</span>
                                </div>
                              </div>

                              <button
                                onClick={() => addToCart(prod)}
                                className="p-2 rounded-lg bg-primary text-white hover:bg-primary-hover shadow-xs shrink-0"
                                title="Add to Cart"
                              >
                                <ShoppingBag className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="p-3 border-t border-slate-100 bg-white">
            <p className="text-[11px] font-bold text-slate-400 mb-2 uppercase">
              {t('Suggested Inquiries', 'পরামর্শকৃত প্রশ্ন')}
            </p>
            <div className="flex gap-1.5 overflow-x-auto pb-1">
              {samplePrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => sendAIMessage(prompt)}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-primary-light text-slate-700 hover:text-primary text-xs font-medium whitespace-nowrap transition-colors shrink-0"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* Input Bar */}
          <form onSubmit={handleSubmit} className="p-3 sm:p-4 border-t border-slate-200 bg-surface-raised flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('Ask HaatAI anything about products, recipes, deals...', 'পণ্য বা রান্নার রেসিপি সম্পর্কে যেকোনো কিছু জিজ্ঞাসা করুন...')}
              className="flex-1 px-3.5 py-2.5 text-xs sm:text-sm border border-slate-200 rounded-xl bg-white focus:outline-hidden focus:border-primary"
            />
            <button
              type="submit"
              className="neu-button px-4 py-2.5 bg-primary text-white rounded-xl hover:bg-primary-hover font-bold text-xs flex items-center justify-center shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
