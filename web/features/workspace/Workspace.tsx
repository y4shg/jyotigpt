"use client";

// Workspace — the creation/manage screen: pill nav over Models, Collections,
// Presets, Capabilities, and Plugins. The active tab lives in the URL
// (`?tab=...`) so back/forward and deep links keep working.

import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, Code2, Command, Cpu, PanelLeft, Wrench } from "lucide-react";
import { clsx } from "clsx";
import { ModelsTab } from "./tabs/ModelsTab";
import { CollectionsTab } from "./tabs/CollectionsTab";
import { PresetsTab } from "./tabs/PresetsTab";
import { CapabilitiesTab } from "./tabs/CapabilitiesTab";
import { PluginsTab } from "./tabs/PluginsTab";

export type WorkspaceTab =
  | "models"
  | "collections"
  | "presets"
  | "capabilities"
  | "plugins";

const TABS: Array<{ id: WorkspaceTab; label: string; icon: typeof Cpu }> = [
  { id: "models", label: "Models", icon: Cpu },
  { id: "collections", label: "Collections", icon: BookOpen },
  { id: "presets", label: "Presets", icon: Command },
  { id: "capabilities", label: "Capabilities", icon: Wrench },
  { id: "plugins", label: "Plugins", icon: Code2 },
];

const VALID: WorkspaceTab[] = TABS.map((t) => t.id);

export function Workspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const raw = searchParams.get("tab") ?? "models";
  const tab: WorkspaceTab = VALID.includes(raw as WorkspaceTab)
    ? (raw as WorkspaceTab)
    : "models";

  const select = (id: WorkspaceTab) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", id);
    router.replace(`/workspace?${params.toString()}`);
  };

  return (
    <div className="relative flex flex-col w-full h-screen max-h-[100dvh] max-w-full">
      <nav className="px-2.5 pt-1 backdrop-blur-xl">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => router.push("/")}
            aria-label="Back to chat"
            className="self-center flex flex-none items-center cursor-pointer p-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
          >
            <PanelLeft className="size-4" />
          </button>

          <div className="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => select(id)}
                className={clsx(
                  "min-w-fit rounded-full p-1.5 flex items-center gap-1.5 transition",
                  tab === id
                    ? "text-gray-900 dark:text-white"
                    : "text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white",
                )}
              >
                <Icon className="size-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <div
        className="pb-1 px-[18px] flex-1 max-h-full overflow-y-auto scrollbar-hidden"
        id="workspace-container"
      >
        {tab === "models" && <ModelsTab />}
        {tab === "collections" && <CollectionsTab />}
        {tab === "presets" && <PresetsTab />}
        {tab === "capabilities" && <CapabilitiesTab />}
        {tab === "plugins" && <PluginsTab />}
      </div>
    </div>
  );
}
