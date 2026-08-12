"use client";

// Tooltip — hover tooltip (CSS, no portal).

import { clsx } from "clsx";
import type { ReactNode } from "react";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  className?: string;
  side?: "top" | "bottom";
}

export function Tooltip({
  content,
  children,
  className,
  side = "bottom",
}: TooltipProps) {
  return (
    <span className={clsx("relative inline-flex", className)}>
      {children}
      <span
        role="tooltip"
        className={clsx(
          "pointer-events-none absolute left-1/2 -translate-x-1/2 z-50",
          "whitespace-nowrap px-2.5 py-1 text-xs font-medium",
          "bg-gray-900 text-gray-100 dark:bg-gray-100 dark:text-gray-900 rounded-md",
          "opacity-0 group-hover:opacity-100 transition-opacity",
          side === "top" ? "bottom-full mb-1.5" : "top-full mt-1.5",
        )}
      >
        {content}
      </span>
    </span>
  );
}
