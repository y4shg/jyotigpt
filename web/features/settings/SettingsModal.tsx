"use client";

// Settings modal — searchable tab rail + per-tab panels. Mirrors the old
// app's layout: a search box narrows the tab list by title/keyword, the
// active tab renders on the right.

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AudioLines,
  BrainCircuit,
  Cable,
  Info,
  MessagesSquare,
  Monitor,
  Search,
  Settings,
  UserRound,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { clsx } from "clsx";
import { useApp } from "@/lib/store";
import type { UserSettings } from "@/lib/types";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { GeneralTab } from "./GeneralTab";
import { InterfaceTab } from "./InterfaceTab";
import { ConnectionsTab } from "./ConnectionsTab";
import { ToolsTab } from "./ToolsTab";
import { PersonalizationTab } from "./PersonalizationTab";
import { AudioTab } from "./AudioTab";
import { ChatsTab } from "./ChatsTab";
import { AccountTab } from "./AccountTab";
import { AboutTab } from "./AboutTab";

interface SettingsTab {
  id: string;
  title: string;
  keywords: string[];
  icon: LucideIcon;
}

const TABS: SettingsTab[] = [
  {
    id: "general",
    title: "General",
    icon: Settings,
    keywords: ["theme", "language", "notifications", "system prompt", "advanced", "keep alive", "request mode"],
  },
  {
    id: "interface",
    title: "Interface",
    icon: Monitor,
    keywords: ["ui", "display", "chat direction", "widescreen", "bubble", "title", "tags", "copy", "haptic"],
  },
  {
    id: "connections",
    title: "Connections",
    icon: Cable,
    keywords: ["ollama", "openai", "providers", "engines", "servers"],
  },
  {
    id: "tools",
    title: "Tools",
    icon: Wrench,
    keywords: ["tool servers", "openapi", "capabilities"],
  },
  {
    id: "personalization",
    title: "Personalization",
    icon: BrainCircuit,
    keywords: ["memory", "remember", "auto memory", "preferences"],
  },
  {
    id: "audio",
    title: "Audio",
    icon: AudioLines,
    keywords: ["stt", "tts", "speech", "voice", "playback", "kokoro"],
  },
  {
    id: "chats",
    title: "Chats",
    icon: MessagesSquare,
    keywords: ["import", "export", "archive", "delete", "history", "backup"],
  },
  {
    id: "account",
    title: "Account",
    icon: UserRound,
    keywords: ["profile", "name", "email", "password", "api key", "avatar", "security"],
  },
  {
    id: "about",
    title: "About",
    icon: Info,
    keywords: ["version", "info", "help", "release", "ollama", "created by"],
  },
];

export function SettingsModal() {
  const { settingsOpen, setSettingsOpen, settings, updateSettings, setTheme } =
    useApp();
  const [selected, setSelected] = useState("general");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState<UserSettings | null>(null);

  // Server settings are the source of truth; the draft gives instant UI
  // feedback before the POST round-trips.
  useEffect(() => {
    if (settings) setDraft(settings);
  }, [settings]);

  useEffect(() => {
    if (settingsOpen) setSearch("");
  }, [settingsOpen]);

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return TABS;
    return TABS.filter(
      (tab) =>
        tab.title.toLowerCase().includes(query) ||
        tab.keywords.some((keyword) => keyword.includes(query)),
    );
  }, [search]);

  // Keep the selection valid when the search narrows the list.
  useEffect(() => {
    if (visible.length > 0 && !visible.some((t) => t.id === selected)) {
      setSelected(visible[0].id);
    }
  }, [visible, selected]);

  const change = useCallback(
    <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
      setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
      void updateSettings({ [key]: value } as Partial<UserSettings>).catch(
        () => {
          // keep the optimistic value; the server will reject on next save
        },
      );
    },
    [updateSettings],
  );

  const renderTab = () => {
    if (!draft) {
      return (
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Loading settings…
        </div>
      );
    }
    const props = { settings: draft, onChange: change };
    switch (selected) {
      case "interface":
        return <InterfaceTab {...props} />;
      case "connections":
        return <ConnectionsTab />;
      case "tools":
        return <ToolsTab />;
      case "personalization":
        return <PersonalizationTab {...props} />;
      case "audio":
        return <AudioTab {...props} />;
      case "chats":
        return <ChatsTab />;
      case "account":
        return <AccountTab />;
      case "about":
        return <AboutTab />;
      case "general":
      default:
        return <GeneralTab {...props} />;
    }
  };

  return (
    <Modal
      open={settingsOpen}
      onClose={() => setSettingsOpen(false)}
      size="lg"
      containerClassName="p-2"
      className="bg-white dark:bg-gray-900 rounded-2xl"
    >
      <ModalTitle title="Settings" onClose={() => setSettingsOpen(false)} />
      <div className="flex flex-col md:flex-row w-full px-5 pt-1 pb-5 md:space-x-4">
        <div className="flex flex-row overflow-x-auto gap-2.5 md:gap-1 md:flex-col flex-1 md:flex-none md:w-44 dark:text-gray-200 text-sm font-medium text-left mb-2 md:mb-0">
          <div className="hidden md:flex w-full rounded-xl mb-1 px-2 py-1.5 gap-2 bg-gray-50 dark:bg-gray-850 items-center">
            <Search className="size-3.5 text-gray-400" />
            <input
              className="w-full py-0.5 text-sm bg-transparent dark:text-gray-300 outline-none"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search"
            />
          </div>
          {visible.map((tab) => {
            const Icon = tab.icon;
            const active = selected === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setSelected(tab.id)}
                className={clsx(
                  "px-2.5 py-1.5 min-w-fit rounded-lg flex-1 md:flex-none flex items-center gap-2 text-left transition",
                  active
                    ? "bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-white"
                    : "text-gray-500 dark:text-gray-500 hover:text-gray-800 dark:hover:text-gray-200",
                )}
              >
                <Icon className="size-4 shrink-0" />
                {tab.title}
              </button>
            );
          })}
          {visible.length === 0 ? (
            <div className="text-sm text-gray-500 dark:text-gray-400 px-2 py-1">
              No matching settings.
            </div>
          ) : null}
        </div>
        <div className="flex-1 min-w-0 max-h-[60vh] overflow-y-auto scrollbar-hidden pr-1">
          {renderTab()}
        </div>
      </div>
    </Modal>
  );
}
