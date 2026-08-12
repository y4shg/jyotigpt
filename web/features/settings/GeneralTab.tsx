"use client";

// General — theme, language, notifications, system prompt, advanced params.

import { useApp } from "@/lib/store";
import { Input, Textarea } from "@/components/ui/Input";
import {
  Field,
  Segmented,
  SettingsSection,
  ToggleRow,
} from "./controls";
import type { SettingsTabProps } from "./types";

export function GeneralTab({ settings, onChange }: SettingsTabProps) {
  const { setTheme } = useApp();

  return (
    <div className="flex flex-col gap-8">
      <SettingsSection title="JyotiGPT Settings">
        <Field label="Theme">
          <Segmented
            value={settings.theme}
            options={[
              { value: "light", label: "Light" },
              { value: "dark", label: "Dark" },
            ]}
            onChange={(value) => {
              setTheme(value);
              onChange("theme", value);
            }}
          />
        </Field>
        <Field label="Language" description="Interface language for this account.">
          <select
            value={settings.language}
            onChange={(e) => onChange("language", e.target.value)}
            className="bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5 w-full text-sm outline-none dark:text-gray-100"
          >
            <option value="en">English</option>
          </select>
        </Field>
        <ToggleRow
          label="Notifications"
          description="Show in-app notifications for events and long-running tasks."
          checked={settings.notifications}
          onChange={(value) => onChange("notifications", value)}
        />
      </SettingsSection>

      <SettingsSection title="System Prompt">
        <Field
          label="System Prompt"
          description="Prepended to every conversation for this account."
        >
          <Textarea
            value={settings.system_prompt}
            onChange={(e) => onChange("system_prompt", e.target.value)}
            placeholder="Enter system prompt here"
            rows={3}
          />
        </Field>
      </SettingsSection>

      <SettingsSection title="Advanced Parameters">
        <Field label="Keep Alive" description="How long loaded models stay warm.">
          <Input
            value={settings.keep_alive}
            onChange={(e) => onChange("keep_alive", e.target.value)}
            placeholder="5m"
          />
        </Field>
        <Field
          label="Request Mode"
          description='e.g. "json" or a JSON schema for structured replies.'
        >
          <Input
            value={settings.request_mode}
            onChange={(e) => onChange("request_mode", e.target.value)}
            placeholder='e.g. "json" or a JSON schema'
          />
        </Field>
      </SettingsSection>
    </div>
  );
}
