"use client";

// PluginsTab — prompt/tool plugins: list, search, create/edit (with sandbox
// test run for tools), enable/disable, delete, export/import as JSON.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { clsx } from "clsx";
import { Code2, Download, Pencil, Trash2, Upload } from "lucide-react";
import { WorkspaceTabScaffold } from "../WorkspaceTabScaffold";
import { PluginEditorModal } from "../PluginEditorModal";
import { Toggle } from "@/components/ui/Toggle";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import {
  deletePlugin,
  exportPlugins,
  importPlugins,
  listPlugins,
  updatePlugin,
} from "@/lib/workspace";
import type { Plugin } from "@/lib/types";

function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function PluginsTab() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [search, setSearch] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Plugin | null>(null);
  const [deleting, setDeleting] = useState<Plugin | null>(null);
  const importRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setPlugins(await listPlugins());
  }, []);

  useEffect(() => {
    load().catch((error) => toast.error(errorMessage(error)));
  }, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return plugins;
    return plugins.filter(
      (p) =>
        p.name.toLowerCase().includes(term) ||
        (p.description ?? "").toLowerCase().includes(term),
    );
  }, [plugins, search]);

  const toggle = async (plugin: Plugin, is_active: boolean) => {
    try {
      await updatePlugin(plugin.id, { is_active });
      setPlugins((list) =>
        list.map((p) => (p.id === plugin.id ? { ...p, is_active } : p)),
      );
      toast.success(is_active ? "Plugin enabled." : "Plugin disabled.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deletePlugin(deleting.id);
      toast.success("Plugin deleted.");
      setPlugins((list) => list.filter((p) => p.id !== deleting.id));
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeleting(null);
    }
  };

  const handleExport = async () => {
    try {
      const all = await exportPlugins();
      downloadJson(`plugins-export-${Date.now()}.json`, all);
      toast.success(`Exported ${all.length} plugin(s).`);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const handleImportFile = async (file: File) => {
    try {
      const parsed = JSON.parse(await file.text());
      const list = Array.isArray(parsed) ? parsed : parsed.plugins;
      if (!Array.isArray(list) || list.length === 0) {
        toast.error("The file contains no plugins.");
        return;
      }
      const created = await importPlugins(list as Plugin[]);
      toast.success(`Imported ${created.length} plugin(s).`);
      load();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      if (importRef.current) importRef.current.value = "";
    }
  };

  return (
    <WorkspaceTabScaffold
      title="Plugins"
      count={filtered.length}
      search={search}
      onSearch={setSearch}
      searchPlaceholder="Search Plugins"
      onAdd={() => {
        setEditing(null);
        setEditorOpen(true);
      }}
      addLabel="Create Plugin"
      extra={
        <>
          <button
            type="button"
            title="Export Plugins"
            onClick={handleExport}
            className="px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center"
          >
            <Download className="size-3.5" />
          </button>
          <button
            type="button"
            title="Import Plugins"
            onClick={() => importRef.current?.click()}
            className="px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center"
          >
            <Upload className="size-3.5" />
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleImportFile(file);
            }}
          />
        </>
      }
    >
      <div className="my-2 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
        {filtered.map((plugin) => (
          <div
            key={plugin.id}
            className={`flex flex-col w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition cursor-pointer ${
              plugin.is_active ? "" : "opacity-60"
            }`}
            onClick={() => {
              setEditing(plugin);
              setEditorOpen(true);
            }}
          >
            <div className="flex items-center gap-2 mt-0.5 mb-1">
              <Code2 className="size-4 shrink-0 text-gray-400 dark:text-gray-500" />
              <span className="font-semibold line-clamp-1">{plugin.name}</span>
              <span
                className={clsx(
                  "rounded-full px-2 py-0.5 text-[10px] font-medium",
                  plugin.kind === "tool"
                    ? "bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300"
                    : "bg-sky-100 dark:bg-sky-900/40 text-sky-700 dark:text-sky-300",
                )}
              >
                {plugin.kind}
              </span>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
              {plugin.description ||
                (plugin.kind === "tool"
                  ? "Python tool plugin"
                  : plugin.prompt || "Prompt plugin")}
            </p>
            <div className="flex justify-between items-center px-0.5 mt-1">
              <span className="text-xs text-gray-400 dark:text-gray-500">By me</span>
              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  title="Edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditing(plugin);
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
                    setDeleting(plugin);
                  }}
                  className="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                >
                  <Trash2 className="size-4" />
                </button>
                <div className="ml-1" onClick={(e) => e.stopPropagation()}>
                  <Toggle
                    checked={plugin.is_active}
                    onChange={(next) => toggle(plugin, next)}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-sm text-gray-400 dark:text-gray-500 py-8 text-center">
          No plugins yet — create a prompt or tool plugin with the + button.
        </div>
      )}

      <PluginEditorModal
        open={editorOpen}
        plugin={editing}
        onSaved={load}
        onClose={() => setEditorOpen(false)}
      />

      <ConfirmDialog
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete plugin?"
        message={`This will delete ${deleting?.name ?? ""}.`}
      />
    </WorkspaceTabScaffold>
  );
}
