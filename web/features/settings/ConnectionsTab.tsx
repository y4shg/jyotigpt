"use client";

// Connections — read-only view of the providers the server is configured
// with. Direct-connection management (per-user add/edit) is part of the
// Workspace phase; here users see what the deployment exposes.

import { Cable, Check, Minus } from "lucide-react";
import { useApp } from "@/lib/store";
import { SettingsSection } from "./controls";

export function ConnectionsTab() {
  const { config } = useApp();
  const audio = config?.audio;
  const imageEnabled = config?.image_generation?.enabled;

  const rows = [
    {
      label: "Ollama",
      detail: "Local model runtime",
      connected: true,
    },
    {
      label: "OpenAI-compatible",
      detail: "Configured server-side",
      connected: false,
    },
    {
      label: "Speech-to-Text",
      detail:
        audio?.stt_engine === "openai"
          ? "OpenAI Whisper"
          : audio?.stt_engine === "browser"
            ? "Browser Web API"
            : "Not configured",
      connected: Boolean(audio?.stt_engine),
    },
    {
      label: "Text-to-Speech",
      detail:
        audio?.tts_engine === "openai"
          ? "OpenAI voices"
          : audio?.tts_engine === "browser"
            ? "Browser engine"
            : "Not configured",
      connected: Boolean(audio?.tts_engine),
    },
    {
      label: "Image Generation",
      detail: imageEnabled ? "Enabled" : "Disabled",
      connected: Boolean(imageEnabled),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <SettingsSection title="Server Connections">
        <div className="flex flex-col gap-2">
          {rows.map((row) => (
            <div
              key={row.label}
              className="flex items-center gap-3 rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2.5"
            >
              <span className="flex size-8 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                <Cable className="size-4" />
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">{row.label}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {row.detail}
                </div>
              </div>
              {row.connected ? (
                <Check className="size-4 text-emerald-600" />
              ) : (
                <Minus className="size-4 text-gray-400" />
              )}
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Connections are configured by the administrator through environment
          variables or the admin settings page. Reach out to your
          administrator to change them.
        </p>
      </SettingsSection>
    </div>
  );
}
