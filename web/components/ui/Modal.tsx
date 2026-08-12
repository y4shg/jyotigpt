"use client";

// Modal — product modal shell. Backdrop bg-black/60, panel rounded-2xl,
// click-outside + Escape to close, body scroll lock.

import { clsx } from "clsx";
import { useEffect, useRef, type ReactNode } from "react";

export type ModalSize = "xs" | "sm" | "md" | "lg" | "full";

const sizeToWidth: Record<ModalSize, string> = {
  xs: "w-[16rem]",
  sm: "w-[30rem]",
  md: "w-[42rem]",
  lg: "w-[56rem]",
  full: "w-full",
};

interface ModalProps {
  open: boolean;
  onClose: () => void;
  size?: ModalSize;
  className?: string;
  containerClassName?: string;
  children: ReactNode;
}

export function Modal({
  open,
  onClose,
  size = "md",
  className = "bg-white dark:bg-gray-900 rounded-2xl",
  containerClassName = "p-3",
  children,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className={clsx(
        "modal fixed top-0 right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh]",
        containerClassName,
        "flex justify-center z-[9999] overflow-y-auto overscroll-contain",
      )}
      onMouseDown={onClose}
    >
      <div
        ref={panelRef}
        className={clsx(
          "m-auto max-w-full",
          sizeToWidth[size],
          size !== "full" ? "mx-2" : "",
          "shadow-3xl min-h-fit scrollbar-hidden",
          className,
        )}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

interface ModalTitleProps {
  title: string;
  onClose: () => void;
  children?: ReactNode;
}

export function ModalTitle({ title, onClose, children }: ModalTitleProps) {
  return (
    <div className="px-5 pt-4 dark:text-gray-300 text-gray-700">
      <div className="flex justify-between items-start">
        <div className="text-xl font-semibold">{title}</div>
        <button className="self-center" onClick={onClose} aria-label="Close">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-5 h-5"
          >
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      </div>
      {children}
    </div>
  );
}
