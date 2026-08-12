"use client";

// Dropdown — anchored popover menu (click outside to close).

import { clsx } from "clsx";
import {
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

interface DropdownProps {
  trigger: ReactNode;
  children: ReactNode;
  /** Tailwind alignment classes, e.g. "right-0". */
  align?: string;
  className?: string;
  disabled?: boolean;
}

export function Dropdown({
  trigger,
  children,
  align = "right-0",
  className,
  disabled,
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={ref} className={clsx("relative", className)}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="disabled:opacity-50 disabled:pointer-events-none"
      >
        {trigger}
      </button>
      {open && (
        <div
          role="menu"
          className={clsx(
            "absolute z-50 mt-2 min-w-max",
            align,
            "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700",
            "rounded-xl shadow-3xl p-1.5",
          )}
        >
          {children}
        </div>
      )}
    </div>
  );
}

interface DropdownItemProps {
  children: ReactNode;
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}

export function DropdownItem({
  children,
  onClick,
  className,
  disabled,
}: DropdownItemProps) {
  return (
    <button
      type="button"
      role="menuitem"
      disabled={disabled}
      onClick={onClick}
      className={clsx(
        "w-full text-left px-3 py-1.5 text-sm rounded-lg",
        "hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-900 dark:text-gray-100",
        "disabled:opacity-50 disabled:pointer-events-none flex items-center gap-2",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function DropdownDivider() {
  return (
    <div className="my-1 h-px bg-gray-100 dark:bg-gray-700" role="separator" />
  );
}
