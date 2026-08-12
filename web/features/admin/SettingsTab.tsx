"use client";

// SettingsTab — admin app-level settings. A left rail lists the sections
// (General, Images, Pipelines, Interface, Audio); each form edits one
// persisted settings group and saves it via /api/v1/config/settings.

import { useCallback, useEffect, useState } from "react";
import {
  AudioLines,
  ImageIcon,
  Settings2,
  Sun,
  Workflow,
} from "lucide-react";
import { clsx } from "clsx";
import { getAppSettings, setAppSetting } from "@/lib/admin";
import type { AppSettings } from "@/lib/types";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import {
  Field,
  SettingsSection,
  ToggleRow,
} from "@/features/settings/controls";

type SettingsSectionId = "general" | "images" | "pipelines" | "interface" | "audio";

const SECTIONS: Array<{
  id: SettingsSectionId;
  label: string;
  icon: typeof Sun;
}> = [
  { id: "general", label: "General", icon: Settings2 },
  { id: "images", label: "Images", icon: ImageIcon },
  { id: "pipelines", label: "Pipelines", icon: Workflow },
  { id: "interface", label: "Interface", icon: Sun },
  { id: "audio", label: "Audio", icon: AudioLines },
];

export function SettingsTab() {
  const [section, setSection] = useState<SettingsSectionId>("general");
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    try {
      setSettings(await getAppSettings());
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  // Horizontal scroll the rail with the vertical wheel, as the old app did.
  useEffect(() => {
    const el = document.getElementById("admin-settings-tabs-container");
    if (!el) return;
    const onWheel = (event: WheelEvent) => {
      if (event.deltaY !== 0) {
        el.scrollLeft += event.deltaY;
      }
    };
    el.addEventListener("wheel", onWheel);
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const saveGroups = async (
    entries: Array<[keyof AppSettings, Record<string, unknown>]>,
  ) => {
    setSaving(true);
    try {
      for (const [key, value] of entries) {
        await setAppSetting(key, value);
        setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
      }
      toast.success("Settings saved successfully");
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const patch = (key: keyof AppSettings, patchValue: Record<string, unknown>) => {
    if (!settings) return;
    const next = { ...settings, [key]: { ...settings[key], ...patchValue } };
    setSettings(next);
  };

  if (!settings) {
    return (
      <div className="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
        <div className="text-center text-xs text-gray-500 dark:text-gray-400 py-4 w-full">
          Loading settings…
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
      {/* left rail */}
      <div
        id="admin-settings-tabs-container"
        className="flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-40 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
      >
        {SECTIONS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setSection(id)}
            className={clsx(
              "px-0.5 py-1 min-w-fit rounded-lg lg:flex-none flex text-right transition",
              section === id
                ? ""
                : "text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white",
            )}
          >
            <div className="self-center mr-2">
              <Icon className="size-4" />
            </div>
            <div className="self-center">{label}</div>
          </button>
        ))}
      </div>

      {/* content */}
      <div className="flex-1 mt-1 lg:mt-0 overflow-y-scroll scrollbar-hidden">
        {section === "general" && (
          <GeneralForm settings={settings} patch={patch} onSave={saveGroups} saving={saving} />
        )}
        {section === "images" && (
          <ImagesForm settings={settings} patch={patch} onSave={saveGroups} saving={saving} />
        )}
        {section === "pipelines" && (
          <PipelinesForm settings={settings} patch={patch} onSave={saveGroups} saving={saving} />
        )}
        {section === "interface" && (
          <InterfaceForm settings={settings} patch={patch} onSave={saveGroups} saving={saving} />
        )}
        {section === "audio" && (
          <AudioForm settings={settings} patch={patch} onSave={saveGroups} saving={saving} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- forms

function SaveBar({
  saving,
  onSave,
}: {
  saving: boolean;
  onSave: () => void;
}) {
  return (
    <div className="mt-6 flex justify-end">
      <Button variant="primary" disabled={saving} onClick={onSave}>
        Save
      </Button>
    </div>
  );
}

function GeneralForm({
  settings,
  patch,
  onSave,
  saving,
}: {
  settings: AppSettings;
  patch: (key: keyof AppSettings, value: Record<string, unknown>) => void;
  onSave: (entries: Array<[keyof AppSettings, Record<string, unknown>]>) => void;
  saving: boolean;
}) {
  const app = settings.app ?? {};
  const features = settings.features ?? {};
  return (
    <div className="flex flex-col gap-8 text-sm p-2">
      <SettingsSection title="General Settings">
        <Field label="App Name" description="Shown in the browser title bar.">
          <Input
            value={(app.name as string) ?? ""}
            onChange={(e) => patch("app", { ...app, name: e.target.value })}
            className="max-w-sm"
          />
        </Field>
        <Field label="Logo URL" description="Custom logo shown in the navbar.">
          <Input
            value={(app.logo_url as string) ?? ""}
            onChange={(e) => patch("app", { ...app, logo_url: e.target.value })}
            className="max-w-sm"
          />
        </Field>
      </SettingsSection>

      <SettingsSection title="Features">
        <ToggleRow
          label="Image Generation"
          description="Enable image generation in chat."
          checked={Boolean(features.image_generation)}
          onChange={(value) =>
            patch("features", { ...features, image_generation: value })
          }
        />
        <ToggleRow
          label="Image Prompt Generation"
          description="Generate a prompt for image creation from your message."
          checked={Boolean(features.image_prompt_generation)}
          onChange={(value) =>
            patch("features", { ...features, image_prompt_generation: value })
          }
        />
        <ToggleRow
          label="Web Search"
          description="Enable web search for chat responses."
          checked={Boolean(features.web_search)}
          onChange={(value) => patch("features", { ...features, web_search: value })}
        />
        <ToggleRow
          label="Audio"
          description="Enable voice input/output."
          checked={Boolean(features.audio_enabled)}
          onChange={(value) => patch("features", { ...features, audio_enabled: value })}
        />
      </SettingsSection>

      <SaveBar
        saving={saving}
        onSave={() => onSave([["app", { ...settings.app }], ["features", { ...settings.features }]])}
      />
    </div>
  );
}

function ImagesForm({
  settings,
  patch,
  onSave,
  saving,
}: {
  settings: AppSettings;
  patch: (key: keyof AppSettings, value: Record<string, unknown>) => void;
  onSave: (entries: Array<[keyof AppSettings, Record<string, unknown>]>) => void;
  saving: boolean;
}) {
  const images = settings.images ?? {};
  const engine = (images.engine as string) ?? "openai";
  const set = (field: string, value: unknown) =>
    patch("images", { ...images, [field]: value });

  return (
    <div className="flex flex-col gap-8 text-sm p-2">
      <SettingsSection title="Image Settings">
        <Field label="Image Generation Engine">
          <select
            value={engine}
            onChange={(e) => set("engine", e.target.value)}
            className="bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5 w-full max-w-sm text-sm outline-none dark:text-gray-100"
          >
            <option value="openai">Default (Open AI)</option>
            <option value="automatic1111">Automatic1111</option>
            <option value="comfyui">ComfyUI</option>
          </select>
        </Field>
      </SettingsSection>

      {engine === "openai" ? (
        <SettingsSection title="OpenAI API Config">
          <Field label="API Base URL">
            <Input
              value={(images.openai_base_url as string) ?? ""}
              onChange={(e) => set("openai_base_url", e.target.value)}
              placeholder="https://api.openai.com/v1"
              className="max-w-sm"
            />
          </Field>
          <Field label="API Key">
            <Input
              type="password"
              value={(images.openai_api_key as string) ?? ""}
              onChange={(e) => set("openai_api_key", e.target.value)}
              placeholder="sk-…"
              className="max-w-sm"
            />
          </Field>
          <Field label="Default Model">
            <Input
              value={(images.openai_model as string) ?? "dall-e-3"}
              onChange={(e) => set("openai_model", e.target.value)}
              className="max-w-sm"
            />
          </Field>
        </SettingsSection>
      ) : null}

      {engine === "automatic1111" ? (
        <SettingsSection title="AUTOMATIC1111">
          <Field
            label="AUTOMATIC1111 Base URL"
            description="Include the `--api` flag when running stable-diffusion-webui."
          >
            <Input
              value={(images.automatic1111_base_url as string) ?? ""}
              onChange={(e) => set("automatic1111_base_url", e.target.value)}
              placeholder="Enter URL (e.g. http://127.0.0.1:7860/)"
              className="max-w-sm"
            />
          </Field>
        </SettingsSection>
      ) : null}

      {engine === "comfyui" ? (
        <SettingsSection title="ComfyUI">
          <Field label="ComfyUI Base URL">
            <Input
              value={(images.comfyui_base_url as string) ?? ""}
              onChange={(e) => set("comfyui_base_url", e.target.value)}
              placeholder="Enter URL (e.g. http://127.0.0.1:8188/)"
              className="max-w-sm"
            />
          </Field>
          <Field label="ComfyUI API Key">
            <Input
              type="password"
              value={(images.comfyui_api_key as string) ?? ""}
              onChange={(e) => set("comfyui_api_key", e.target.value)}
              placeholder="sk-1234"
              className="max-w-sm"
            />
          </Field>
          <Field label="ComfyUI Workflow" description="Workflow JSON as API format.">
            <Textarea
              rows={6}
              value={(images.comfyui_workflow as string) ?? ""}
              onChange={(e) => set("comfyui_workflow", e.target.value)}
              placeholder='{"3": {"class_type": "KSampler", …}}'
              className="max-w-md"
            />
          </Field>
        </SettingsSection>
      ) : null}

      <SaveBar
        saving={saving}
        onSave={() => onSave([["images", { ...settings.images }]])}
      />
    </div>
  );
}

function PipelinesForm({
  settings,
  patch,
  onSave,
  saving,
}: {
  settings: AppSettings;
  patch: (key: keyof AppSettings, value: Record<string, unknown>) => void;
  onSave: (entries: Array<[keyof AppSettings, Record<string, unknown>]>) => void;
  saving: boolean;
}) {
  const flows = settings.flows ?? {};
  return (
    <div className="flex flex-col gap-8 text-sm p-2">
      <SettingsSection title="Pipelines Server">
        <ToggleRow
          label="Enable Pipelines"
          description="Allow chat to route through pipeline models."
          checked={Boolean(flows.enabled)}
          onChange={(value) => patch("flows", { ...flows, enabled: value })}
        />
        <Field label="Pipeline URL" description="URL of the pipelines server.">
          <Input
            value={(flows.url as string) ?? ""}
            onChange={(e) => patch("flows", { ...flows, url: e.target.value })}
            placeholder="https://openwebui.com/api/v1/…"
            className="max-w-sm"
          />
        </Field>
        <Field label="API Key">
          <Input
            type="password"
            value={(flows.api_key as string) ?? ""}
            onChange={(e) => patch("flows", { ...flows, api_key: e.target.value })}
            placeholder="api key"
            className="max-w-sm"
          />
        </Field>
      </SettingsSection>

      <SaveBar
        saving={saving}
        onSave={() => onSave([["flows", { ...settings.flows }]])}
      />
    </div>
  );
}

function InterfaceForm({
  settings,
  patch,
  onSave,
  saving,
}: {
  settings: AppSettings;
  patch: (key: keyof AppSettings, value: Record<string, unknown>) => void;
  onSave: (entries: Array<[keyof AppSettings, Record<string, unknown>]>) => void;
  saving: boolean;
}) {
  const interfaceSettings = settings.interface ?? {};
  return (
    <div className="flex flex-col gap-8 text-sm p-2">
      <SettingsSection title="Interface">
        <Field label="Default Model">
          <Input
            value={(interfaceSettings.default_model as string) ?? ""}
            onChange={(e) =>
              patch("interface", {
                ...interfaceSettings,
                default_model: e.target.value,
              })
            }
            placeholder="Select a model"
            className="max-w-sm"
          />
        </Field>
        <Field label="Default Prompt">
          <Input
            value={(interfaceSettings.default_prompt as string) ?? ""}
            onChange={(e) =>
              patch("interface", {
                ...interfaceSettings,
                default_prompt: e.target.value,
              })
            }
            placeholder="Enter a prompt"
            className="max-w-sm"
          />
        </Field>
      </SettingsSection>

      <SaveBar
        saving={saving}
        onSave={() => onSave([["interface", { ...settings.interface }]])}
      />
    </div>
  );
}

function AudioForm({
  settings,
  patch,
  onSave,
  saving,
}: {
  settings: AppSettings;
  patch: (key: keyof AppSettings, value: Record<string, unknown>) => void;
  onSave: (entries: Array<[keyof AppSettings, Record<string, unknown>]>) => void;
  saving: boolean;
}) {
  const audio = settings.audio ?? {};
  return (
    <div className="flex flex-col gap-8 text-sm p-2">
      <SettingsSection title="STT Settings">
        <Field label="Speech-to-Text Engine">
          <select
            value={(audio.stt_engine as string) ?? ""}
            onChange={(e) => patch("audio", { ...audio, stt_engine: e.target.value })}
            className="bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5 w-full max-w-sm text-sm outline-none dark:text-gray-100"
          >
            <option value="">Whisper (Local)</option>
            <option value="web">Web API</option>
          </select>
        </Field>
      </SettingsSection>

      <SettingsSection title="TTS Settings">
        <Field label="Text-to-Speech Engine">
          <select
            value={(audio.tts_engine as string) ?? ""}
            onChange={(e) => patch("audio", { ...audio, tts_engine: e.target.value })}
            className="bg-gray-50 dark:bg-gray-850 rounded-xl px-4 py-2.5 w-full max-w-sm text-sm outline-none dark:text-gray-100"
          >
            <option value="">Web API</option>
            <option value="openai">OpenAI</option>
          </select>
        </Field>
      </SettingsSection>

      <SaveBar
        saving={saving}
        onSave={() => onSave([["audio", { ...settings.audio }]])}
      />
    </div>
  );
}
