import React from 'react';
import { useApp } from '../context/AppContext';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const { toasts } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map(toast => {
        let icon = <CheckCircle2 className="w-5 h-5 text-success shrink-0" />;
        let borderClass = 'border-success/30';
        let bgClass = 'bg-white';

        if (toast.type === 'error') {
          icon = <AlertCircle className="w-5 h-5 text-danger shrink-0" />;
          borderClass = 'border-danger/30';
        } else if (toast.type === 'warning') {
          icon = <AlertCircle className="w-5 h-5 text-accent shrink-0" />;
          borderClass = 'border-accent/30';
        } else if (toast.type === 'info') {
          icon = <Info className="w-5 h-5 text-primary shrink-0" />;
          borderClass = 'border-primary/30';
        }

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center gap-3 p-3.5 rounded-xl shadow-elevated border ${borderClass} ${bgClass} transition-all duration-300 animate-slide-in backdrop-blur-sm`}
          >
            {icon}
            <p className="text-sm font-medium text-ink flex-1">{toast.message}</p>
          </div>
        );
      })}
    </div>
  );
};
