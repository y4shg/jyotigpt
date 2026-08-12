"use client";

// ModelSelector — navbar dropdown listing the catalog from the configured
// providers (Ollama + OpenAI-compatible), grouped by backend.

import { useEffect, useRef, useState } from "react";
import { ChevronDown, Loader2 } from "lucide-react";
import { clsx } from "clsx";
import { useChat } from "./useChatStore";
import type { ModelInfo } from "@/lib/types";

function groupLabel(provider: string): string {
  if (provider === "openai") return "OpenAI";
  if (provider === "flow") return "Pipelines";
  return "Ollama";
}

export function ModelSelector() {
  const { models, modelId, setModelId } = useChat();
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

  const selected = models.find((m) => m.id === modelId) ?? null;
  const groups = new Map<string, ModelInfo[]>();
  for (const model of models) {
    const key = groupLabel(model.provider);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(model);
  }

  return (
    <div ref={ref} className="relative w-full font-primary">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition items-center gap-1 max-w-52"
        title={selected?.name ?? "Select model"}
      >
        <span className="font-medium line-clamp-1 text-sm">
          {selected?.name ?? (models.length === 0 ? "Model" : "Select model")}
        </span>
        <ChevronDown
          className={clsx("size-4 shrink-0 transition", open && "rotate-180")}
        />
      </button>

      {open && (
        <div
          role="listbox"
          className="z-40 max-w-[calc(100vw-1rem)] justify-start rounded-xl bg-white dark:bg-gray-850 dark:text-white shadow-lg outline-hidden absolute top-full right-0 mt-1 border border-gray-200/80 dark:border-gray-700/80 min-w-64"
        >
          {models.length === 0 ? (
            <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2">
              <Loader2 className="size-4 animate-spin" />
              Loading models…
            </div>
          ) : (
            <div className="px-3 max-h-64 overflow-y-auto scrollbar-hidden group relative py-1.5">
              {Array.from(groups.entries()).map(([label, items]) => (
                <div key={label}>
                  <div className="px-1 pt-2 pb-1 text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    {label}
                  </div>
                  {items.map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      role="option"
                      aria-selected={model.id === modelId}
                      onClick={() => {
                        setModelId(model.id);
                        setOpen(false);
                      }}
                      className={clsx(
                        "flex w-full text-left font-medium line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5",
                        "text-sm text-gray-700 dark:text-gray-100 outline-hidden transition-all duration-75",
                        "hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer",
                        model.id === modelId && "bg-gray-100 dark:bg-gray-800",
                      )}
                      title={model.name}
                    >
                      <span className="truncate">{model.name}</span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
