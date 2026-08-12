"use client";

// ModelsTab — the model catalog with custom presets: search, create/edit
// presets, enable/disable, delete. Clicking a card opens chat with that model.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Cpu, Pencil, Trash2 } from "lucide-react";
import { WorkspaceTabScaffold } from "../WorkspaceTabScaffold";
import { ModelEditorModal } from "../ModelEditorModal";
import { Toggle } from "@/components/ui/Toggle";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import {
  deleteModelRecord,
  listCollections,
  listModelsCatalog,
  listModelRecords,
  listPlugins,
  updateModelRecord,
} from "@/lib/workspace";
import type {
  Collection,
  ModelCatalogItem,
  ModelRecord,
  Plugin,
} from "@/lib/types";

function modelKey(model: { provider: string; id: string }) {
  return `${model.provider}/${model.id}`;
}

export function ModelsTab() {
  const router = useRouter();
  const [catalog, setCatalog] = useState<ModelCatalogItem[]>([]);
  const [records, setRecords] = useState<ModelRecord[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [promptPlugins, setPromptPlugins] = useState<Plugin[]>([]);
  const [search, setSearch] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<ModelRecord | null>(null);
  const [deleting, setDeleting] = useState<ModelRecord | null>(null);

  const load = useCallback(async () => {
    const [cat, recs, cols, plugins] = await Promise.all([
      listModelsCatalog(),
      listModelRecords(),
      listCollections(),
      listPlugins(),
    ]);
    setCatalog(cat);
    setRecords(recs);
    setCollections(cols);
    setPromptPlugins(plugins.filter((p) => p.kind === "prompt"));
  }, []);

  useEffect(() => {
    load().catch((error) => toast.error(errorMessage(error)));
  }, [load]);

  const recordByKey = useMemo(() => {
    const map = new Map<string, ModelRecord>();
    for (const record of records) {
      map.set(`${record.provider}/${record.model_id}`, record);
    }
    return map;
  }, [records]);

  const merged = useMemo(() => {
    const items = catalog.map((model) => {
      const record = recordByKey.get(modelKey(model));
      return {
        model,
        record: record ?? null,
        enabled: record ? record.enabled : true,
      };
    });
    // Presets for models the provider is not currently serving still appear.
    const known = new Set(items.map((i) => modelKey(i.model)));
    for (const record of records) {
      if (!known.has(`${record.provider}/${record.model_id}`)) {
        items.push({
          model: {
            id: record.model_id,
            name: record.name || record.model_id,
            provider: record.provider,
            owned_by: "custom",
            custom: true,
            params: record.params,
            info: { meta: { profile_image_url: "", description: "" } },
          },
          record,
          enabled: record.enabled,
        });
      }
    }
    return items;
  }, [catalog, records, recordByKey]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return merged;
    return merged.filter(
      ({ model }) =>
        model.name.toLowerCase().includes(term) ||
        model.id.toLowerCase().includes(term),
    );
  }, [merged, search]);

  const openCreate = () => {
    setEditing(null);
    setEditorOpen(true);
  };

  const openEdit = (record: ModelRecord) => {
    setEditing(record);
    setEditorOpen(true);
  };

  const toggleRecord = async (record: ModelRecord, enabled: boolean) => {
    try {
      await updateModelRecord(record.provider, record.model_id, {
        name: record.name,
        enabled,
      });
      setRecords((list) =>
        list.map((r) =>
          r.provider === record.provider && r.model_id === record.model_id
            ? { ...r, enabled }
            : r,
        ),
      );
      toast.success(enabled ? "Model enabled." : "Model disabled.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteModelRecord(deleting.provider, deleting.model_id);
      toast.success("Model preset deleted.");
      setRecords((list) =>
        list.filter(
          (r) =>
            !(r.provider === deleting.provider && r.model_id === deleting.model_id),
        ),
      );
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeleting(null);
    }
  };

  return (
    <WorkspaceTabScaffold
      title="Models"
      count={filtered.length}
      search={search}
      onSearch={setSearch}
      searchPlaceholder="Search Models"
      onAdd={openCreate}
      addLabel="Create Model"
    >
      <div className="my-2 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3" id="model-list">
        {filtered.map(({ model, record, enabled }) => (
          <div
            key={modelKey(model)}
            className="flex flex-col cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition"
            id={`model-item-${model.id}`}
            onClick={() => router.push(`/?models=${encodeURIComponent(model.id)}`)}
          >
            <div className="flex gap-4 mt-0.5 mb-0.5">
              <div className="w-[44px]">
                <div
                  className={`rounded-full object-cover size-11 flex items-center justify-center bg-gray-100 dark:bg-gray-800 ${
                    enabled ? "" : "opacity-50"
                  }`}
                >
                  <Cpu className="size-5 text-gray-500 dark:text-gray-300" />
                </div>
              </div>

              <div className="flex flex-1 cursor-pointer w-full self-center">
                <div className={`flex-1 ${enabled ? "" : "text-gray-500 dark:text-gray-400"}`}>
                  <div className="font-semibold line-clamp-1">{model.name}</div>
                  <div className="flex gap-1 text-xs overflow-hidden">
                    <div className="line-clamp-1">
                      {(model.info?.meta?.description ?? "").trim() || model.id}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center -mb-0.5 px-0.5 mt-1">
              <div className="text-xs mt-0.5">
                <span className="shrink-0 text-gray-500 dark:text-gray-400">
                  {model.custom ? "By me" : model.provider}
                </span>
              </div>

              <div className="flex flex-row gap-0.5 items-center">
                {record && (
                  <>
                    <button
                      type="button"
                      title="Edit"
                      onClick={(e) => {
                        e.stopPropagation();
                        openEdit(record);
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
                        setDeleting(record);
                      }}
                      className="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                    >
                      <Trash2 className="size-4" />
                    </button>
                    <div className="ml-1" onClick={(e) => e.stopPropagation()}>
                      <Toggle
                        checked={enabled}
                        onChange={(next) => record && toggleRecord(record, next)}
                      />
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-sm text-gray-400 dark:text-gray-500 py-8 text-center">
          No models match “{search}”.
        </div>
      )}

      <ModelEditorModal
        open={editorOpen}
        record={editing}
        catalog={catalog}
        collections={collections}
        promptPlugins={promptPlugins}
        onSaved={load}
        onClose={() => setEditorOpen(false)}
      />

      <ConfirmDialog
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete model preset?"
        message={`This will delete ${deleting?.name ?? ""}. The base model (if any) remains available.`}
      />
    </WorkspaceTabScaffold>
  );
}
