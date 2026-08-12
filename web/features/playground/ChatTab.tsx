"use client";

// Playground Chat tab — an editable, stateless chat lab. Message rows are
// user/assistant textareas; System Instructions are sent as a leading system
// message. Run streams a completion into a new assistant row; Cancel aborts.
// Nothing is persisted — the lab is a scratchpad.

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronUp, Pencil, Play, Square, X } from "lucide-react";
import { clsx } from "clsx";
import { listModels } from "@/lib/chat";
import { streamPlayground, type PlaygroundMessage } from "@/lib/playground";
import { errorMessage } from "@/lib/api";

interface Row {
  id: string;
  role: "user" | "assistant";
  content: string;
}

let nextRowId = 1;
const newRowId = () => `pg-${nextRowId++}`;

function autosize(el: HTMLTextAreaElement) {
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}

export function ChatTab() {
  const [models, setModels] = useState<Array<{ id: string; name: string; provider: string }>>([]);
  const [modelId, setModelId] = useState("");
  const [system, setSystem] = useState("");
  const [rows, setRows] = useState<Row[]>([
    { id: newRowId(), role: "user", content: "" },
  ]);
  const [composer, setComposer] = useState("");
  const [composerRole, setComposerRole] = useState<"user" | "assistant">("user");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [instructionsOpen, setInstructionsOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    listModels()
      .then((all) =>
        setModels(all.map((m) => ({ id: m.id, name: m.name, provider: m.provider }))),
      )
      .catch(() => setModels([]));
  }, []);

  // default to the first model once the catalog arrives
  useEffect(() => {
    if (!modelId && models.length > 0) setModelId(models[0].id);
  }, [models, modelId]);

  const selected = models.find((m) => m.id === modelId);
  const provider = selected?.provider === "openai" ? "openai" : "ollama";

  const updateRow = (id: string, patch: Partial<Row>) => {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  };

  const removeRow = (id: string) => {
    setRows((prev) => prev.filter((r) => r.id !== id));
  };

  const addRow = () => {
    setRows((prev) => [...prev, { id: newRowId(), role: composerRole, content: composer }]);
    setComposer("");
  };

  const canRun = !streaming && modelId !== "" && rows.some((r) => r.content.trim()) && !composer.trim();

  const run = async () => {
    if (!canRun) return;
    setError(null);
    const messages: PlaygroundMessage[] = [];
    if (system.trim()) messages.push({ role: "system", content: system.trim() });
    for (const row of rows) {
      if (row.content.trim()) messages.push({ role: row.role, content: row.content.trim() });
    }

    const streamedId = newRowId();
    setRows((prev) => [...prev, { id: streamedId, role: "assistant", content: "" }]);
    setStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    let content = "";
    try {
      await streamPlayground({
        model: modelId,
        provider,
        messages,
        signal: controller.signal,
        events: {
          onDelta: (delta) => {
            content += delta;
            updateRow(streamedId, { content });
          },
          onDone: () => undefined,
          onError: (message) => setError(message),
        },
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setStreaming(false);
      abortRef.current = null;
      // drop empty assistant rows left by an aborted run
      setRows((prev) => prev.filter((r) => r.id !== streamedId || r.content.trim()));
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
  };

  return (
    <div className="flex flex-col justify-between w-full overflow-y-auto h-full">
      <div className="mx-auto w-full md:px-0 h-full relative px-4">
        {/* model + system instructions */}
        <div className="pt-4 flex flex-col gap-2">
          <select
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className="w-full bg-transparent border border-gray-100 dark:border-gray-850 rounded-lg py-1 px-2 text-sm outline-hidden text-gray-900 dark:text-gray-100"
          >
            <option value="" disabled>
              Select a model
            </option>
            {(["ollama", "openai"] as const).map((groupProvider) => {
              const group = models.filter((m) => m.provider === groupProvider);
              if (group.length === 0) return null;
              return (
                <optgroup key={groupProvider} label={groupProvider === "ollama" ? "Ollama" : "OpenAI"}>
                  {group.map((m) => (
                    <option key={m.id} value={m.id} className="bg-gray-50 dark:bg-gray-700">
                      {m.name}
                    </option>
                  ))}
                </optgroup>
              );
            })}
          </select>

          <div className="w-full flex-1">
            <button
              type="button"
              onClick={() => setInstructionsOpen((v) => !v)}
              className="w-full rounded-lg text-sm border border-gray-100 dark:border-gray-850 w-full py-1 px-1.5 flex items-center gap-1.5 text-left text-gray-900 dark:text-gray-100"
            >
              <span className="shrink-0 font-medium ml-1.5">System Instructions</span>
              <span
                className={clsx(
                  "flex-1 text-gray-500 line-clamp-1",
                  instructionsOpen && "hidden",
                )}
              >
                {system}
              </span>
              {instructionsOpen ? (
                <ChevronUp className="size-3.5 shrink-0 p-1.5 box-content bg-transparent hover:bg-white/5 transition rounded-lg" />
              ) : (
                <Pencil className="size-3.5 shrink-0 p-1.5 box-content bg-transparent hover:bg-white/5 transition rounded-lg" />
              )}
            </button>
            {instructionsOpen && (
              <textarea
                value={system}
                onChange={(e) => setSystem(e.target.value)}
                placeholder="You're a helpful assistant."
                rows={4}
                className="w-full bg-transparent resize-none outline-hidden text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 mt-2"
              />
            )}
          </div>
        </div>

        {/* message history */}
        <div className="pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0">
          <div className="py-3 space-y-3">
            {rows.map((row) => (
              <div key={row.id} className="flex gap-2 group">
                <div className="px-2 py-1 text-sm font-semibold uppercase min-w-[6rem] text-left rounded-lg text-gray-900 dark:text-gray-100">
                  {row.role}
                </div>
                <textarea
                  value={row.content}
                  onChange={(e) => {
                    updateRow(row.id, { content: e.target.value });
                    autosize(e.target);
                  }}
                  rows={1}
                  placeholder={
                    row.role === "user"
                      ? "Enter a user message here"
                      : "Enter an assistant message here"
                  }
                  className="w-full bg-transparent outline-hidden rounded-lg p-2 text-sm resize-none overflow-hidden text-gray-900 dark:text-gray-100 placeholder-gray-500"
                />
                <button
                  type="button"
                  aria-label="Delete message"
                  onClick={() => removeRow(row.id)}
                  className="self-center text-gray-200 dark:text-gray-700 group-hover:text-gray-500 dark:group-hover:text-gray-300 transition"
                >
                  <X className="size-5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div className="text-xs text-red-600 dark:text-red-500 pb-2">{error}</div>
        )}

        {/* composer */}
        <div className="pb-4">
          <div className="text-xs font-medium text-gray-500 px-2 py-1">
            {selected ? selected.name : "No model selected"}
          </div>
          <div className="border border-gray-100 dark:border-gray-850 w-full px-3 py-2.5 rounded-xl">
            <textarea
              value={composer}
              onChange={(e) => setComposer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  addRow();
                }
              }}
              rows={2}
              placeholder={
                composerRole === "user"
                  ? "Enter a user message here"
                  : "Enter an assistant message here"
              }
              className="w-full bg-transparent resize-none outline-hidden text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500"
            />
            <div className="flex items-center justify-between mt-1">
              <button
                type="button"
                onClick={() =>
                  setComposerRole((r) => (r === "user" ? "assistant" : "user"))
                }
                className="px-3.5 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg"
              >
                {composerRole === "user" ? "User" : "Assistant"}
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={addRow}
                  disabled={composer.trim() === ""}
                  className="px-3.5 py-1.5 text-sm font-medium bg-gray-50 hover:bg-gray-100 text-gray-900 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition rounded-lg disabled:bg-gray-50 dark:disabled:hover:bg-gray-850 disabled:cursor-not-allowed"
                >
                  Add
                </button>
                {streaming ? (
                  <button
                    type="button"
                    onClick={cancel}
                    className="px-3 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-lg"
                  >
                    <span className="flex items-center gap-1.5">
                      <Square className="size-3.5" /> Cancel
                    </span>
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => void run()}
                    disabled={!canRun}
                    className="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-lg disabled:opacity-40 disabled:pointer-events-none"
                  >
                    <span className="flex items-center gap-1.5">
                      <Play className="size-3.5" /> Run
                    </span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
