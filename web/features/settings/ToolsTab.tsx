"use client";

// Tools — tool servers (OpenAPI). Server management arrives with the
// Capabilities phase; today this is an empty, honest state.

import { Wrench } from "lucide-react";
import { SettingsSection } from "./controls";

export function ToolsTab() {
  return (
    <div className="flex flex-col gap-6">
      <SettingsSection title="Manage Tool Servers">
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 py-10 text-center">
          <span className="flex size-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-850 text-gray-400">
            <Wrench className="size-6" />
          </span>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            No tool servers configured.
          </div>
          <div className="max-w-sm text-xs text-gray-500 dark:text-gray-400 px-6">
            Tool servers expose OpenAPI-powered capabilities to the
            assistant. Configuration is managed by your administrator.
          </div>
        </div>
      </SettingsSection>
    </div>
  );
}
