"use client";

// Toaster — lightweight bottom-right toast stack (module-level state, no
// context). `toast.success(...)` / `toast.error(...)` from anywhere; render
// <Toaster /> once in the app shell.

import { useEffect, useState } from "react";
import { clsx } from "clsx";
import { CheckCircle2, XCircle, X } from "lucide-react";

interface ToastItem {
  id: number;
  kind: "success" | "error";
  message: string;
}

type Listener = (items: ToastItem[]) => void;

let items: ToastItem[] = [];
let listeners = new Set<Listener>();
let nextId = 1;

function emit() {
  for (const listener of listeners) listener([...items]);
}

function push(kind: ToastItem["kind"], message: string) {
  const id = nextId++;
  items = [...items, { id, kind, message }];
  emit();
  setTimeout(() => {
    items = items.filter((item) => item.id !== id);
    emit();
  }, 4000);
}

export const toast = {
  success: (message: string) => push("success", message),
  error: (message: string) => push("error", message),
};

export function Toaster() {
  const [visible, setVisible] = useState<ToastItem[]>([]);

  useEffect(() => {
    const listener: Listener = setVisible;
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-[10000] flex w-80 flex-col gap-2">
      {visible.map((item) => (
        <div
          key={item.id}
          role="status"
          className={clsx(
            "flex items-start gap-2 rounded-xl border px-3 py-2.5 text-sm shadow-lg",
            "bg-white dark:bg-gray-850 text-gray-900 dark:text-gray-100",
            item.kind === "success"
              ? "border-emerald-200 dark:border-emerald-800"
              : "border-red-200 dark:border-red-900",
          )}
        >
          {item.kind === "success" ? (
            <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <XCircle className="mt-0.5 size-4 shrink-0 text-red-600 dark:text-red-400" />
          )}
          <span className="min-w-0 flex-1 break-words">{item.message}</span>
          <button
            type="button"
            aria-label="Dismiss"
            onClick={() => {
              items = items.filter((i) => i.id !== item.id);
              emit();
            }}
            className="rounded p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="size-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
