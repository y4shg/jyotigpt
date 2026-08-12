"use client";

// Audio — speech engines (stored prefs; engine wiring lands with Phase 8).

import { Segmented, SettingsSection, ToggleRow } from "./controls";
import type { SettingsTabProps } from "./types";

export function AudioTab({ settings, onChange }: SettingsTabProps) {
  return (
    <div className="flex flex-col gap-8">
      <SettingsSection title="STT Settings">
        <div className="flex flex-col gap-1.5 w-full">
          <div className="text-sm font-medium">Speech-to-Text Engine</div>
          <Segmented
            value={settings.stt_engine}
            options={[
              { value: "default", label: "Default" },
              { value: "browser", label: "Web API" },
            ]}
            onChange={(value) => onChange("stt_engine", value)}
          />
        </div>
      </SettingsSection>

      <SettingsSection title="TTS Settings">
        <div className="flex flex-col gap-1.5 w-full">
          <div className="text-sm font-medium">Text-to-Speech Engine</div>
          <Segmented
            value={settings.tts_engine}
            options={[
              { value: "default", label: "Default" },
              { value: "browser", label: "Browser" },
            ]}
            onChange={(value) => onChange("tts_engine", value)}
          />
        </div>
        <div className="flex flex-col gap-1.5 w-full">
          <div className="text-sm font-medium">Kokoro.js Dtype</div>
          <Segmented
            value={settings.kokoro_dtype}
            options={[
              { value: "q8", label: "Q8" },
              { value: "f16", label: "F16" },
              { value: "f32", label: "F32" },
            ]}
            onChange={(value) => onChange("kokoro_dtype", value)}
          />
        </div>
        <ToggleRow
          label="Auto-playback response"
          description="Speak each assistant reply as it finishes."
          checked={settings.auto_playback}
          onChange={(value) => onChange("auto_playback", value)}
        />
        <div className="flex flex-col gap-1.5 w-full">
          <div className="text-sm font-medium">
            Speech Playback Speed — {settings.playback_speed.toFixed(1)}×
          </div>
          <input
            type="range"
            min={0.5}
            max={2}
            step={0.1}
            value={settings.playback_speed}
            onChange={(e) => onChange("playback_speed", Number(e.target.value))}
            className="accent-emerald-600 w-full"
          />
        </div>
        <div className="flex flex-col gap-1.5 w-full">
          <div className="text-sm font-medium">Voice</div>
          <select
            value={settings.voice}
            onChange={(e) => onChange("voice", e.target.value)}
            className="bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5 w-full text-sm outline-none dark:text-gray-100"
          >
            <option value="default">Default</option>
            <option value="alloy">Alloy</option>
            <option value="ash">Ash</option>
            <option value="ballad">Ballad</option>
            <option value="coral">Coral</option>
            <option value="echo">Echo</option>
            <option value="fable">Fable</option>
            <option value="nova">Nova</option>
            <option value="onyx">Onyx</option>
            <option value="sage">Sage</option>
            <option value="shimmer">Shimmer</option>
            <option value="verse">Verse</option>
          </select>
        </div>
      </SettingsSection>
    </div>
  );
}
