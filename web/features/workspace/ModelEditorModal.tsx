"use client";

// ModelEditorModal — create/edit a model preset (a base provider model with an
// overridden display name, system prompt, advanced params, attached knowledge
// collections, and prompt plugins).

import { useEffect, useMemo, useState } from "react";
import { Cpu, Trash2 } from "lucide-react";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import {
  createModelRecord,
  deleteModelRecord,
  updateModelRecord,
} from "@/lib/workspace";
import type { Collection, ModelCatalogItem, ModelRecord, Plugin } from "@/lib/types";
import { clsx } from "clsx";

interface ModelEditorModalProps {
  open: boolean;
  /** null = create a new preset; otherwise edit this record. */
  record: ModelRecord | null;
  catalog: ModelCatalogItem[];
  collections: Collection[];
  promptPlugins: Plugin[];
  onSaved: () => void;
  onClose: () => void;
}

interface ParamField {
  key: string;
  label: string;
  type: "number" | "text";
  step?: string;
  placeholder?: string;
}

const ADVANCED_FIELDS: ParamField[] = [
  { key: "temperature", label: "Temperature", type: "number", step: "0.1" },
  { key: "top_p", label: "Top P", type: "number", step: "0.1" },
  { key: "top_k", label: "Top K", type: "number" },
  { key: "seed", label: "Seed", type: "number" },
  { key: "num_predict", label: "Num Predict", type: "number" },
  { key: "max_tokens", label: "Max Tokens", type: "number" },
  { key: "presence_penalty", label: "Presence Penalty", type: "number", step: "0.1" },
  { key: "frequency_penalty", label: "Frequency Penalty", type: "number", step: "0.1" },
  { key: "stop", label: "Stop (comma-separated)", type: "text" },
];

export function ModelEditorModal({
  open,
  record,
  catalog,
  collections,
  promptPlugins,
  onSaved,
  onClose,
}: ModelEditorModalProps) {
  const [provider, setProvider] = useState<"ollama" | "openai">("ollama");
  const [modelId, setModelId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [system, setSystem] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [params, setParams] = useState<Record<string, string>>({});
  const [collectionIds, setCollectionIds] = useState<string[]>([]);
  const [pluginIds, setPluginIds] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  // Reset the form each time the modal opens for a different target.
  useEffect(() => {
    if (!open) return;
    setProvider(record?.provider ?? "ollama");
    setModelId(record?.model_id ?? "");
    setName(record?.name && record.name !== record.model_id ? record.name : "");
    setDescription(String(record?.params?.description ?? ""));
    setSystem(String(record?.params?.system ?? ""));
    setEnabled(record?.enabled ?? true);
    setCollectionIds(
      (record?.params?.collection_ids as string[] | undefined) ?? [],
    );
    setPluginIds((record?.params?.plugin_ids as string[] | undefined) ?? []);
    const next: Record<string, string> = {};
    for (const field of ADVANCED_FIELDS) {
      const value = record?.params?.[field.key];
      if (value !== undefined && value !== null) next[field.key] = String(value);
    }
    setParams(next);
  }, [open, record]);

  const baseOptions = useMemo(
    () =>
      catalog.filter(
        (m) => m.provider === provider && m.custom !== true && !m.pipeline,
      ),
    [catalog, provider],
  );

  // Picking a base model fills in the id (kept editable for not-yet-pulled ids).
  const pickBase = (id: string) => {
    setModelId(id);
    const base = catalog.find((m) => m.id === id);
    if (base && !name) setName(base.name);
  };

  const save = async () => {
    const cleanModelId = modelId.trim();
    if (!cleanModelId) {
      toast.error("Model ID is required.");
      return;
    }
    const builtParams: Record<string, unknown> = {};
    if (description.trim()) builtParams.description = description.trim();
    if (system.trim()) builtParams.system = system.trim();
    for (const field of ADVANCED_FIELDS) {
      const raw = (params[field.key] ?? "").trim();
      if (!raw) continue;
      if (field.key === "stop") {
        builtParams.stop = raw
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      } else {
        const numeric = Number(raw);
        if (Number.isFinite(numeric)) builtParams[field.key] = numeric;
      }
    }
    if (collectionIds.length) builtParams.collection_ids = collectionIds;
    if (pluginIds.length) builtParams.plugin_ids = pluginIds;

    setSaving(true);
    try {
      if (record) {
        await updateModelRecord(record.provider, record.model_id, {
          name: name.trim() || cleanModelId,
          enabled,
          params: builtParams,
        });
      } else {
        await createModelRecord({
          provider,
          model_id: cleanModelId,
          name: name.trim() || cleanModelId,
          enabled,
          params: builtParams,
        });
      }
      toast.success(record ? "Model preset updated." : "Model preset created.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!record) return;
    setSaving(true);
    try {
      await deleteModelRecord(record.provider, record.model_id);
      toast.success("Model preset deleted.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const toggleCollection = (id: string) =>
    setCollectionIds((list) =>
      list.includes(id) ? list.filter((c) => c !== id) : [...list, id],
    );
  const togglePlugin = (id: string) =>
    setPluginIds((list) =>
      list.includes(id) ? list.filter((p) => p !== id) : [...list, id],
    );

  return (
    <Modal open={open} onClose={onClose} size="lg">
      <ModalTitle title={record ? "Edit Model" : "Create Model"} onClose={onClose} />
      <div className="px-5 pb-5 pt-2 max-h-[70vh] overflow-y-auto scrollbar-hidden">
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-gray-500 dark:text-gray-400">Name</span>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Model" />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-gray-500 dark:text-gray-400">Provider</span>
              <div className="flex gap-1 rounded-xl bg-gray-100 dark:bg-gray-850 p-1">
                {(["ollama", "openai"] as const).map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => setProvider(p)}
                    className={clsx(
                      "flex-1 rounded-lg py-1.5 text-sm capitalize transition",
                      provider === p
                        ? "bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white"
                        : "text-gray-500 dark:text-gray-400",
                    )}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </label>
          </div>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Base model</span>
            <div className="flex gap-2">
              <select
                value={modelId}
                onChange={(e) => pickBase(e.target.value)}
                className="bg-gray-50 dark:bg-gray-850 rounded-xl px-3 py-2.5 text-sm outline-none dark:text-gray-100 flex-1"
              >
                <option value="">Select a model…</option>
                {baseOptions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>
            <Input
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
              placeholder="…or type a model ID"
              className="mt-1"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Description</span>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this model for?"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">System prompt</span>
            <Textarea
              value={system}
              onChange={(e) => setSystem(e.target.value)}
              rows={4}
              placeholder="You are a helpful assistant…"
            />
          </label>

          <details className="group">
            <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400 select-none">
              Advanced parameters
            </summary>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              {ADVANCED_FIELDS.map((field) => (
                <label key={field.key} className="flex flex-col gap-1 text-sm">
                  <span className="text-gray-500 dark:text-gray-400">{field.label}</span>
                  <Input
                    type={field.type}
                    step={field.step}
                    value={params[field.key] ?? ""}
                    onChange={(e) =>
                      setParams((p) => ({ ...p, [field.key]: e.target.value }))
                    }
                    placeholder={field.placeholder}
                  />
                </label>
              ))}
            </div>
          </details>

          <div className="flex flex-col gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Knowledge</span>
            {collections.length === 0 ? (
              <div className="text-sm text-gray-400 dark:text-gray-500">
                No collections yet — create one in the Collections tab.
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {collections.map((collection) => (
                  <button
                    key={collection.id}
                    type="button"
                    onClick={() => toggleCollection(collection.id)}
                    className={clsx(
                      "rounded-full px-3 py-1 text-sm transition border",
                      collectionIds.includes(collection.id)
                        ? "bg-gray-900 dark:bg-white text-gray-100 dark:text-gray-900 border-gray-900 dark:border-white"
                        : "border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850",
                    )}
                  >
                    {collection.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Prompt plugins
            </span>
            {promptPlugins.length === 0 ? (
              <div className="text-sm text-gray-400 dark:text-gray-500">
                No prompt plugins yet — create one in the Plugins tab.
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {promptPlugins.map((plugin) => (
                  <button
                    key={plugin.id}
                    type="button"
                    onClick={() => togglePlugin(plugin.id)}
                    className={clsx(
                      "rounded-full px-3 py-1 text-sm transition border",
                      pluginIds.includes(plugin.id)
                        ? "bg-gray-900 dark:bg-white text-gray-100 dark:text-gray-900 border-gray-900 dark:border-white"
                        : "border-gray-300 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850",
                    )}
                  >
                    {plugin.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {record && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">Enabled</span>
              <Toggle checked={enabled} onChange={setEnabled} />
            </div>
          )}
        </div>

        <div className="mt-5 flex items-center justify-between">
          <div>
            {record && (
              <Button variant="ghost" onClick={remove} disabled={saving} className="text-red-600 dark:text-red-500">
                <Trash2 className="size-4" /> Delete
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" onClick={save} disabled={saving}>
              <Cpu className="size-4" /> {record ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
