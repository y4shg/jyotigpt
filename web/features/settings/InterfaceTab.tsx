"use client";

// Interface — UI preferences: chat direction, widescreen, auto-title/tags.

import { Segmented, SettingsSection, ToggleRow } from "./controls";
import type { SettingsTabProps } from "./types";

export function InterfaceTab({ settings, onChange }: SettingsTabProps) {
  return (
    <div className="flex flex-col gap-8">
      <SettingsSection title="UI">
        <div className="flex flex-col gap-1.5 w-full">
          <div className="text-sm font-medium">Chat direction</div>
          <Segmented
            value={settings.chat_direction}
            options={[
              { value: "auto", label: "Auto" },
              { value: "ltr", label: "LTR" },
              { value: "rtl", label: "RTL" },
            ]}
            onChange={(value) => onChange("chat_direction", value)}
          />
        </div>
        <ToggleRow
          label="Widescreen Mode"
          description="Expand the chat area to fill wider screens."
          checked={settings.widescreen}
          onChange={(value) => onChange("widescreen", value)}
        />
        <ToggleRow
          label="Chat Bubble UI"
          description="Render user messages as bubbles."
          checked={settings.chat_bubble_ui}
          onChange={(value) => onChange("chat_bubble_ui", value)}
        />
      </SettingsSection>

      <SettingsSection title="Chat">
        <ToggleRow
          label="Title Auto-Generation"
          description="Derive a conversation title from the first message."
          checked={settings.auto_title}
          onChange={(value) => onChange("auto_title", value)}
        />
        <ToggleRow
          label="Chat Tags Auto-Generation"
          description="Automatically tag conversations from their content."
          checked={settings.auto_tags}
          onChange={(value) => onChange("auto_tags", value)}
        />
        <ToggleRow
          label="Stream Large Chunks"
          description="Deliver long replies in fewer, larger chunks."
          checked={settings.stream_large_chunks}
          onChange={(value) => onChange("stream_large_chunks", value)}
        />
        <ToggleRow
          label="Response Auto-Copy"
          description="Copy each completed assistant reply to the clipboard."
          checked={settings.response_auto_copy}
          onChange={(value) => onChange("response_auto_copy", value)}
        />
        <ToggleRow
          label="Haptic Feedback"
          description="Light vibration on supported mobile devices."
          checked={settings.haptic_feedback}
          onChange={(value) => onChange("haptic_feedback", value)}
        />
      </SettingsSection>
    </div>
  );
}
