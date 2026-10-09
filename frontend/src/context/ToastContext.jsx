import { useState, useCallback } from 'react';
import { ToastContext } from './ToastContextDef';
import { CheckCircle2, AlertCircle, X } from 'lucide-react';

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((type, message, duration = 4000) => {
    const id = Date.now() + Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const success = useCallback((message, duration) => {
    addToast('success', message, duration);
  }, [addToast]);

  const error = useCallback((message, duration) => {
    addToast('error', message, duration);
  }, [addToast]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ success, error }}>
      {children}
      <div
        role="region"
        aria-label="Notifications"
        className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full px-4 sm:px-0 pointer-events-none"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl bg-white border border-zinc-200 shadow-lg text-zinc-900 transition-all duration-200 animate-in fade-in slide-in-from-bottom-2"
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <div className="flex-1 text-xs font-medium text-zinc-800 leading-relaxed">
              {toast.message}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-zinc-400 hover:text-zinc-600 transition-colors shrink-0 p-0.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400"
              aria-label="Dismiss notification"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export { ToastContext };
export default ToastProvider;
