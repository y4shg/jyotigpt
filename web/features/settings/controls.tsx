"use client";

// Small building blocks shared by the Settings tabs: labelled fields,
// segmented pickers and toggle rows.

import { clsx } from "clsx";
import type { ReactNode } from "react";
import { Toggle } from "@/components/ui/Toggle";

export function Field({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      <div className="text-sm font-medium">{label}</div>
      {description ? (
        <div className="text-xs text-gray-500 dark:text-gray-400 -mt-1">
          {description}
        </div>
      ) : null}
      {children}
    </div>
  );
}

export function SettingsSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="text-sm font-semibold text-gray-900 dark:text-white">
        {title}
      </div>
      {children}
    </div>
  );
}

export function ToggleRow({
  label,
  description,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 w-full">
      <div className="min-w-0">
        <div className="text-sm font-medium">{label}</div>
        {description ? (
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {description}
          </div>
        ) : null}
      </div>
      <Toggle checked={checked} disabled={disabled} onChange={onChange} />
    </div>
  );
}

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  className,
}: {
  value: T;
  options: SegmentedOption<T>[];
  onChange: (value: T) => void;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "flex w-fit gap-1 bg-gray-100 dark:bg-gray-800 rounded-full p-1",
        className,
      )}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={clsx(
              "px-3 py-1.5 rounded-full text-sm font-medium transition select-none",
              active
                ? "bg-white dark:bg-gray-850 text-gray-900 dark:text-white shadow-sm"
                : "text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
