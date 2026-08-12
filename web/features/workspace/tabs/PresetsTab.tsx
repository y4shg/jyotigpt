"use client";

// PresetsTab — prompt presets (optionally "/commands"): list, search,
// create/edit, delete. Type "/name" in the chat input to insert the prompt.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Command, Pencil, Trash2 } from "lucide-react";
import { WorkspaceTabScaffold } from "../WorkspaceTabScaffold";
import { PresetEditorModal } from "../PresetEditorModal";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { deletePreset, listPresets } from "@/lib/workspace";
import type { Preset } from "@/lib/types";

export function PresetsTab() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [search, setSearch] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Preset | null>(null);
  const [deleting, setDeleting] = useState<Preset | null>(null);

  const load = useCallback(async () => {
    setPresets(await listPresets());
  }, []);

  useEffect(() => {
    load().catch((error) => toast.error(errorMessage(error)));
  }, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return presets;
    return presets.filter(
      (p) => p.name.toLowerCase().includes(term) || p.content.toLowerCase().includes(term),
    );
  }, [presets, search]);

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deletePreset(deleting.id);
      toast.success("Preset deleted.");
      setPresets((list) => list.filter((p) => p.id !== deleting.id));
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <WorkspaceTabScaffold
      title="Presets"
      count={filtered.length}
      search={search}
      onSearch={setSearch}
      searchPlaceholder="Search Presets"
      onAdd={() => {
        setEditing(null);
        setEditorOpen(true);
      }}
      addLabel="Create Preset"
    >
      <div className="my-2 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
        {filtered.map((preset) => (
          <div
            key={preset.id}
            className="flex flex-col w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition cursor-pointer"
            onClick={() => {
              setEditing(preset);
              setEditorOpen(true);
            }}
          >
            <div className="flex items-center gap-2 mt-0.5 mb-1">
              <Command className="size-4 shrink-0 text-gray-400 dark:text-gray-500" />
              <span className="font-semibold line-clamp-1">{preset.name}</span>
              {preset.is_command && (
                <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                  command
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 whitespace-pre-wrap">
              {preset.content}
            </p>
            <div className="flex justify-between items-center px-0.5 mt-1">
              <span className="text-xs text-gray-400 dark:text-gray-500">By me</span>
              <div className="flex gap-0.5">
                <button
                  type="button"
                  title="Edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditing(preset);
                    setEditorOpen(true);
                  }}
                  className="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                >
                  <Pencil className="size-4" />
                </button>
                <button
                  type="button"
                  title="Delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleting(preset);
                  }}
                  className="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                >
                  <Trash2 className="size-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-sm text-gray-400 dark:text-gray-500 py-8 text-center">
          No presets yet — create one with the + button, then type its name in
          chat to insert it.
        </div>
      )}

      <PresetEditorModal
        open={editorOpen}
        preset={editing}
        onSaved={load}
        onClose={() => setEditorOpen(false)}
      />

      <ConfirmDialog
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete preset?"
        message={`This will delete ${deleting?.name ?? ""}.`}
      />
    </WorkspaceTabScaffold>
  );
}
