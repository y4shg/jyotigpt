"use client";

// Personalization — memory entries the assistant remembers about the user.

import { useCallback, useEffect, useState } from "react";
import { Check, Pencil, Plus, Sparkles, Trash2, X } from "lucide-react";
import type { MemoryEntry } from "@/lib/types";
import {
  createMemory,
  deleteMemory,
  listMemory,
  updateMemory,
} from "@/lib/settings";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { SettingsSection, ToggleRow } from "./controls";
import type { SettingsTabProps } from "./types";

export function PersonalizationTab({ settings, onChange }: SettingsTabProps) {
  const [entries, setEntries] = useState<MemoryEntry[] | null>(null);
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setEntries(await listMemory());
    } catch {
      setEntries([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const add = async () => {
    const text = draft.trim();
    if (!text || saving) return;
    setSaving(true);
    try {
      await createMemory(text);
      setDraft("");
      await load();
    } finally {
      setSaving(false);
    }
  };

  const saveEdit = async (id: string) => {
    const text = editText.trim();
    if (!text) return;
    setSaving(true);
    try {
      await updateMemory(id, text);
      setEditingId(null);
      await load();
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await deleteMemory(id);
      await load();
    } catch {
      // keep the entry on failure
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <SettingsSection title="Memory">
        <div className="flex flex-col gap-3">
          {entries === null ? (
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Loading memories…
            </div>
          ) : entries.length === 0 ? (
            <div className="text-sm text-gray-500 dark:text-gray-400">
              No memories yet. Add one below — the assistant can recall it in
              future conversations.
            </div>
          ) : (
            entries.map((entry) => (
              <div
                key={entry.id}
                className="flex items-start gap-2 rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2.5"
              >
                {editingId === entry.id ? (
                  <>
                    <Textarea
                      value={editText}
                      onChange={(e) => setEditText(e.target.value)}
                      rows={2}
                      autoFocus
                    />
                    <div className="flex gap-1">
                      <button
                        type="button"
                        className="p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 text-emerald-600"
                        onClick={() => void saveEdit(entry.id)}
                        disabled={saving}
                        aria-label="Save"
                      >
                        <Check className="size-4" />
                      </button>
                      <button
                        type="button"
                        className="p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500"
                        onClick={() => setEditingId(null)}
                        aria-label="Cancel"
                      >
                        <X className="size-4" />
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-gray-900 dark:text-gray-100">
                        {entry.content}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {entry.created_at
                          ? new Date(entry.created_at).toLocaleDateString()
                          : ""}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button
                        type="button"
                        className="p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500"
                        onClick={() => {
                          setEditingId(entry.id);
                          setEditText(entry.content);
                        }}
                        aria-label="Edit"
                      >
                        <Pencil className="size-4" />
                      </button>
                      <button
                        type="button"
                        className="p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 text-red-600"
                        onClick={() => void remove(entry.id)}
                        aria-label="Delete"
                      >
                        <Trash2 className="size-4" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
        <div className="flex gap-2">
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void add();
            }}
            placeholder='e.g. "Remember that I like concise responses."'
          />
          <Button
            variant="default"
            onClick={() => void add()}
            disabled={saving || !draft.trim()}
          >
            <Plus className="size-4" /> Add
          </Button>
        </div>
      </SettingsSection>

      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <Sparkles className="size-4" />
        Memory is stored per account and never leaves this server.
      </div>

      <ToggleRow
        label="Auto-memory"
        description="Automatically capture important facts from conversations."
        checked={settings.auto_memory}
        onChange={(value) => onChange("auto_memory", value)}
      />
    </div>
  );
}
