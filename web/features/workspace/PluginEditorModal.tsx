"use client";

// PluginEditorModal — create/edit a plugin. Two kinds:
//  - "prompt": static text appended to the context (prompt plugins);
//  - "tool": a Python source defining run_tool(context) -> dict, executed in
//    the server-side sandbox. The editor can run it against sample arguments.

import { useEffect, useState } from "react";
import { Code2, Play, Trash2 } from "lucide-react";
import { clsx } from "clsx";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import {
  createPlugin,
  deletePlugin,
  runPlugin,
  updatePlugin,
} from "@/lib/workspace";
import type { Plugin, PluginKind } from "@/lib/types";

const TOOL_TEMPLATE = `def run_tool(context: dict) -> dict:
    """Return a JSON-serializable dict. context holds the plugin arguments."""
    return {"echo": context}
`;

interface PluginEditorModalProps {
  open: boolean;
  plugin: Plugin | null;
  onSaved: () => void;
  onClose: () => void;
}

export function PluginEditorModal({
  open,
  plugin,
  onSaved,
  onClose,
}: PluginEditorModalProps) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<PluginKind>("prompt");
  const [description, setDescription] = useState("");
  const [prompt, setPrompt] = useState("");
  const [source, setSource] = useState(TOOL_TEMPLATE);
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  // sandbox run state
  const [argsText, setArgsText] = useState("{}");
  const [runResult, setRunResult] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(plugin?.name ?? "");
    setKind(plugin?.kind ?? "prompt");
    setDescription(plugin?.description ?? "");
    setPrompt(plugin?.prompt ?? "");
    setSource(plugin?.source || TOOL_TEMPLATE);
    setIsActive(plugin?.is_active ?? true);
    setRunResult(null);
    setArgsText("{}");
  }, [open, plugin]);

  const save = async () => {
    const cleanName = name.trim();
    if (!cleanName) {
      toast.error("A name is required.");
      return;
    }
    if (kind === "prompt" && !prompt.trim()) {
      toast.error("Prompt plugins need prompt text.");
      return;
    }
    if (kind === "tool" && !source.trim()) {
      toast.error("Tool plugins need Python source.");
      return;
    }
    setSaving(true);
    try {
      if (plugin) {
        await updatePlugin(plugin.id, {
          name: cleanName,
          kind,
          description,
          prompt,
          source,
          is_active: isActive,
        });
      } else {
        await createPlugin({
          name: cleanName,
          kind,
          description,
          prompt,
          source,
          is_active: isActive,
        });
      }
      toast.success(plugin ? "Plugin updated." : "Plugin created.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!plugin) return;
    setSaving(true);
    try {
      await deletePlugin(plugin.id);
      toast.success("Plugin deleted.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const testRun = async () => {
    if (!plugin) {
      toast.error("Save the plugin first, then run it.");
      return;
    }
    let args: Record<string, unknown>;
    try {
      args = JSON.parse(argsText || "{}");
      if (typeof args !== "object" || args === null || Array.isArray(args)) {
        throw new Error("must be an object");
      }
    } catch {
      toast.error("Arguments must be valid JSON (an object).");
      return;
    }
    setRunning(true);
    setRunResult(null);
    try {
      const response = await runPlugin(plugin.id, args);
      setRunResult(JSON.stringify(response, null, 2));
    } catch (error) {
      setRunResult(JSON.stringify({ error: errorMessage(error) }, null, 2));
    } finally {
      setRunning(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} size="lg">
      <ModalTitle title={plugin ? "Edit Plugin" : "Create Plugin"} onClose={onClose} />
      <div className="px-5 pb-5 pt-2 flex flex-col gap-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <label className="flex flex-col gap-1 text-sm md:col-span-2">
            <span className="text-gray-500 dark:text-gray-400">Name</span>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Kindness"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Kind</span>
            <div className="flex gap-1 rounded-xl bg-gray-100 dark:bg-gray-850 p-1">
              {(["prompt", "tool"] as const).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setKind(k)}
                  className={clsx(
                    "flex-1 rounded-lg py-1.5 text-sm transition",
                    kind === k
                      ? "bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white"
                      : "text-gray-500 dark:text-gray-400",
                  )}
                >
                  {k}
                </button>
              ))}
            </div>
          </label>
        </div>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Description</span>
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this plugin do?"
          />
        </label>

        {kind === "prompt" ? (
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Prompt</span>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={6}
              placeholder="Text appended to the model context when this plugin is attached."
            />
          </label>
        ) : (
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">
              Python source
            </span>
            <Textarea
              value={source}
              onChange={(e) => setSource(e.target.value)}
              rows={10}
              className="font-mono text-xs leading-5"
              spellCheck={false}
            />
            <span className="text-xs text-gray-400 dark:text-gray-500">
              Define <code className="font-mono">run_tool(context) → dict</code>.
              Runs in an isolated subprocess (CPU 10s, memory 256 MB).
            </span>
          </label>
        )}

        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">Enabled</span>
          <Toggle checked={isActive} onChange={setIsActive} />
        </div>

        {kind === "tool" && (
          <div className="flex flex-col gap-2 rounded-xl bg-gray-50 dark:bg-gray-850 p-3">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              Test run (server-side sandbox)
            </span>
            <div className="flex gap-2">
              <Input
                value={argsText}
                onChange={(e) => setArgsText(e.target.value)}
                placeholder='{"a": 1, "b": 2}'
                className="font-mono text-xs"
              />
              <Button
                variant="outline"
                onClick={testRun}
                disabled={running || !plugin}
                className="shrink-0"
              >
                <Play className="size-4" /> {running ? "Running…" : "Run"}
              </Button>
            </div>
            {runResult && (
              <pre className="max-h-40 overflow-auto rounded-lg bg-gray-900 dark:bg-black p-3 text-xs text-gray-100 whitespace-pre-wrap">
                {runResult}
              </pre>
            )}
          </div>
        )}

        <div className="mt-2 flex items-center justify-between">
          <div>
            {plugin && (
              <Button
                variant="ghost"
                onClick={remove}
                disabled={saving}
                className="text-red-600 dark:text-red-500"
              >
                <Trash2 className="size-4" /> Delete
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" onClick={save} disabled={saving}>
              <Code2 className="size-4" /> {plugin ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
