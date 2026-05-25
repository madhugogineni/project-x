"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

type ToastVariant = "success" | "error" | "info";

type Toast = {
  id: string;
  variant: ToastVariant;
  message: string;
};

type ToastContextValue = {
  show: (variant: ToastVariant, message: string, duration?: number) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const variantClasses: Record<ToastVariant, string> = {
  success: "bg-success-subtle border-success text-success",
  error: "bg-error-subtle border-error text-error",
  info: "bg-info-subtle border-info text-info",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const show = useCallback(
    (variant: ToastVariant, message: string, duration = 5000) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, variant, message }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    },
    []
  );

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      {toasts.length > 0 && (
        <div
          className="fixed right-0 top-6 flex w-full max-w-sm flex-col gap-2.5 px-4 z-[9999] sm:right-6 sm:px-0"
          aria-live="polite"
        >
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`flex items-center gap-3 px-4 py-3.5 rounded-md border shadow-md text-sm font-medium ${variantClasses[toast.variant]}`}
            >
              <p className="flex-1">{toast.message}</p>
              <button
                className="ml-auto text-current opacity-60 hover:opacity-100 transition-opacity flex-shrink-0 text-lg leading-none"
                onClick={() => dismiss(toast.id)}
                aria-label="Dismiss"
                type="button"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
