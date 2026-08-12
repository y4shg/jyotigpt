"use client";

// Button — product pill button variants.

import { clsx } from "clsx";
import { forwardRef, type ButtonHTMLAttributes } from "react";

export type ButtonVariant =
  | "primary"
  | "default"
  | "outline"
  | "ghost"
  | "danger"
  | "icon";

const base =
  "inline-flex items-center justify-center gap-1.5 text-sm font-medium transition whitespace-nowrap select-none disabled:opacity-50 disabled:pointer-events-none outline-none";

const variants: Record<ButtonVariant, string> = {
  // Black primary (inverted in dark mode) — product accent.
  primary:
    "px-4 py-2 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 rounded-full dark:hover:bg-gray-100",
  // Muted default pill.
  default:
    "px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-full",
  // Ghost default pill.
  ghost:
    "px-4 py-2 bg-gray-700/5 hover:bg-gray-700/10 dark:bg-gray-100/5 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white rounded-full",
  outline:
    "px-4 py-2 border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-900 dark:text-gray-100 rounded-full",
  danger:
    "px-4 py-2 bg-red-600 text-white hover:bg-red-700 dark:bg-red-600 dark:text-white dark:hover:bg-red-700 rounded-full",
  icon: "p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-700 dark:text-gray-300",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "default", className, ...props }, ref) => (
    <button
      ref={ref}
      className={clsx(base, variants[variant], className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";
