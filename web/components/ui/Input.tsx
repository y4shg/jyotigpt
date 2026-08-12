"use client";

// Input / Textarea — product form fields.

import { clsx } from "clsx";
import {
  forwardRef,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

const inputBase =
  "bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5 w-full text-sm outline-none disabled:text-gray-600 dark:text-gray-100";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  rounded?: "xl" | "lg";
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, rounded = "xl", ...props }, ref) => (
    <input
      ref={ref}
      className={clsx(
        rounded === "xl"
          ? "bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5"
          : "bg-gray-50 dark:bg-gray-850 rounded-lg px-4 py-2",
        "w-full text-sm outline-none disabled:text-gray-600 dark:text-gray-100",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  autoResize?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, rows = 3, ...props }, ref) => (
    <textarea
      ref={ref}
      rows={rows}
      className={clsx(
        "w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-100 dark:bg-gray-850 outline-none",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
