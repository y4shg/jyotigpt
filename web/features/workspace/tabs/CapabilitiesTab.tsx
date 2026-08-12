"use client";

// CapabilitiesTab — tool definitions (OpenAPI-style specs): list, search,
// create/edit, enable/disable, delete.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Pencil, Trash2, Wrench } from "lucide-react";
import { WorkspaceTabScaffold } from "../WorkspaceTabScaffold";
import { CapabilityEditorModal } from "../CapabilityEditorModal";
import { Toggle } from "@/components/ui/Toggle";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import {
  deleteCapability,
  listCapabilities,
  updateCapability,
} from "@/lib/workspace";
import type { Capability } from "@/lib/types";

export function CapabilitiesTab() {
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [search, setSearch] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Capability | null>(null);
  const [deleting, setDeleting] = useState<Capability | null>(null);

  const load = useCallback(async () => {
    setCapabilities(await listCapabilities());
  }, []);

  useEffect(() => {
    load().catch((error) => toast.error(errorMessage(error)));
  }, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return capabilities;
    return capabilities.filter(
      (c) =>
        c.name.toLowerCase().includes(term) ||
        c.description.toLowerCase().includes(term),
    );
  }, [capabilities, search]);

  const toggle = async (capability: Capability, is_active: boolean) => {
    try {
      await updateCapability(capability.id, { is_active });
      setCapabilities((list) =>
        list.map((c) => (c.id === capability.id ? { ...c, is_active } : c)),
      );
      toast.success(is_active ? "Capability enabled." : "Capability disabled.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteCapability(deleting.id);
      toast.success("Capability deleted.");
      setCapabilities((list) => list.filter((c) => c.id !== deleting.id));
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <WorkspaceTabScaffold
      title="Capabilities"
      count={filtered.length}
      search={search}
      onSearch={setSearch}
      searchPlaceholder="Search Capabilities"
      onAdd={() => {
        setEditing(null);
        setEditorOpen(true);
      }}
      addLabel="Create Capability"
    >
      <div className="my-2 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
        {filtered.map((capability) => (
          <div
            key={capability.id}
            className={`flex flex-col w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition cursor-pointer ${
              capability.is_active ? "" : "opacity-60"
            }`}
            onClick={() => {
              setEditing(capability);
              setEditorOpen(true);
            }}
          >
            <div className="flex items-center gap-2 mt-0.5 mb-1">
              <Wrench className="size-4 shrink-0 text-gray-400 dark:text-gray-500" />
              <span className="font-semibold line-clamp-1">{capability.name}</span>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
              {capability.description || "No description"}
            </p>
            <div className="flex justify-between items-center px-0.5 mt-1">
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {Object.keys(capability.spec ?? {}).length > 0
                  ? "Spec attached"
                  : "No spec"}
              </span>
              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  title="Edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditing(capability);
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
                    setDeleting(capability);
                  }}
                  className="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                >
                  <Trash2 className="size-4" />
                </button>
                <div className="ml-1" onClick={(e) => e.stopPropagation()}>
                  <Toggle
                    checked={capability.is_active}
                    onChange={(next) => toggle(capability, next)}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-sm text-gray-400 dark:text-gray-500 py-8 text-center">
          No capabilities yet — define the tools the models can call.
        </div>
      )}

      <CapabilityEditorModal
        open={editorOpen}
        capability={editing}
        onSaved={load}
        onClose={() => setEditorOpen(false)}
      />

      <ConfirmDialog
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete capability?"
        message={`This will delete ${deleting?.name ?? ""}.`}
      />
    </WorkspaceTabScaffold>
  );
}
