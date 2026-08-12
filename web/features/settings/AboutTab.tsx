"use client";

// About — version, environment, and model-runtime info.

import { useEffect, useState } from "react";
import { Info } from "lucide-react";
import type { AboutInfo } from "@/lib/types";
import { getAbout } from "@/lib/settings";

export function AboutTab() {
  const [about, setAbout] = useState<AboutInfo | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getAbout().then((data) => {
      if (!cancelled) setAbout(data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <span className="flex size-12 items-center justify-center rounded-2xl bg-gray-100 dark:bg-gray-850 text-gray-500">
          <Info className="size-6" />
        </span>
        <div>
          <div className="text-lg font-semibold">JyotiGPT</div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {about ? `Version ${about.version}` : "Loading…"}
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2.5">
          <span className="text-sm font-medium">Version</span>
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {about?.version ?? "—"}
          </span>
        </div>
        <div className="flex items-center justify-between rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2.5">
          <span className="text-sm font-medium">Environment</span>
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {about?.environment ?? "—"}
          </span>
        </div>
        <div className="flex items-center justify-between rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2.5">
          <span className="text-sm font-medium">Ollama Version</span>
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {about?.models || "Unavailable"}
          </span>
        </div>
        <div className="flex items-center justify-between rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2.5">
          <span className="text-sm font-medium">Created by</span>
          <span className="text-sm text-gray-600 dark:text-gray-300">
            {about?.created_by ?? "—"}
          </span>
        </div>
      </div>
    </div>
  );
}
