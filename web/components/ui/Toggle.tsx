"use client";

// Toggle — emerald switch used for feature flags and preferences.

import { clsx } from "clsx";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export function Toggle({
  checked,
  onChange,
  disabled,
  className,
}: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={clsx(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition",
        checked ? "bg-emerald-600" : "bg-gray-200 dark:bg-gray-700",
        disabled && "opacity-50 pointer-events-none",
        className,
      )}
    >
      <span
        className={clsx(
          "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition",
          checked ? "translate-x-[1.15rem]" : "translate-x-1",
        )}
      />
    </button>
  );
}
