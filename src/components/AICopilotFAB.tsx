import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Sparkles, Bot, Zap, MessageSquare } from 'lucide-react';

export const AICopilotFAB: React.FC = () => {
  const { isAIAssistantOpen, setIsAIAssistantOpen, t } = useApp();
  const [isHovered, setIsHovered] = useState(false);

  // If drawer is already open, suppress the floating trigger button
  if (isAIAssistantOpen) return null;

  return (
    <div className="fixed bottom-6 right-6 z-40 flex items-center gap-3">
      {/* Animated contextual helper pill */}
      <div
        className={`hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900/90 text-white text-xs font-semibold shadow-xl border border-white/10 backdrop-blur-md transition-all duration-300 pointer-events-none ${
          isHovered ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-2'
        }`}
      >
        <Sparkles className="w-3.5 h-3.5 text-amber-300 animate-spin" style={{ animationDuration: '4s' }} />
        <span>{t('Ask NexHaat AI Copilot', 'নেক্সহাট এআই সহকারীকে জিজ্ঞেস করুন')}</span>
      </div>

      {/* Main Floating Action Button */}
      <button
        type="button"
        onClick={() => setIsAIAssistantOpen(true)}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        aria-label="Open NexHaat AI Copilot"
        className="relative group p-3.5 sm:p-4 rounded-2xl bg-gradient-to-tr from-primary via-blue-600 to-indigo-600 text-white shadow-2xl hover:shadow-primary/50 transition-all duration-300 hover:scale-105 active:scale-95 flex items-center justify-center focus:outline-hidden focus:ring-4 focus:ring-primary/30"
      >
        {/* Pulsing synaptic halo rings */}
        <span className="absolute -inset-1 rounded-2xl bg-primary/40 blur-xs animate-ping pointer-events-none" style={{ animationDuration: '3s' }} />
        <span className="absolute -inset-2.5 rounded-3xl bg-indigo-500/20 blur-md pointer-events-none animate-pulse-soft" />

        {/* Inner Icon */}
        <div className="relative flex items-center justify-center">
          <Bot className="w-6 h-6 transition-transform duration-300 group-hover:rotate-12" />
          <span className="absolute -top-1.5 -right-1.5 w-3 h-3 rounded-full bg-emerald-400 border-2 border-slate-900 animate-pulse" />
        </div>
      </button>
    </div>
  );
};
