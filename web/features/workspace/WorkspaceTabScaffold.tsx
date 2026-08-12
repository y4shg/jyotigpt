"use client";

// WorkspaceTabScaffold — the standard workspace list header (title + count,
// search input, add button) shared by every tab, matching the product shell.

import type { ReactNode } from "react";
import { Plus, Search } from "lucide-react";

interface ScaffoldProps {
  title: string;
  count: number;
  search: string;
  onSearch: (value: string) => void;
  searchPlaceholder: string;
  onAdd: () => void;
  addLabel?: string;
  /** Extra actions rendered between the search box and the add button. */
  extra?: ReactNode;
  children: ReactNode;
}

export function WorkspaceTabScaffold({
  title,
  count,
  search,
  onSearch,
  searchPlaceholder,
  onAdd,
  addLabel,
  extra,
  children,
}: ScaffoldProps) {
  return (
    <>
      <div className="flex flex-col gap-1 my-1.5">
        <div className="flex justify-between items-center">
          <div className="flex items-center md:self-center text-xl font-medium px-0.5">
            {title}
            <div className="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
            <span className="text-lg font-medium text-gray-500 dark:text-gray-300">
              {count}
            </span>
          </div>
        </div>

        <div className="flex w-full space-x-2">
          <div className="flex flex-1 items-center">
            <div className="self-center ml-1 mr-3">
              <Search className="size-3.5" />
            </div>
            <input
              value={search}
              onChange={(e) => onSearch(e.target.value)}
              className="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent dark:text-gray-100"
              placeholder={searchPlaceholder}
            />
          </div>

          {extra}

          <button
            type="button"
            onClick={onAdd}
            aria-label={addLabel ?? `Create ${title}`}
            title={addLabel ?? `Create ${title}`}
            className="px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center space-x-1"
          >
            <Plus className="size-3.5" />
          </button>
        </div>
      </div>

      {children}
    </>
  );
}
