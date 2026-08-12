"use client";

// Playground Completions tab — a single-textarea completion lab. The whole
// buffer is sent as ONE assistant message (continue-the-text); streamed deltas
// append back into the same textarea. Nothing is persisted.

import { useEffect, useRef, useState } from "react";
import { Play, Square } from "lucide-react";
import { listModels } from "@/lib/chat";
import { streamPlayground } from "@/lib/playground";
import { errorMessage } from "@/lib/api";

export function CompletionsTab() {
  const [models, setModels] = useState<Array<{ id: string; name: string; provider: string }>>([]);
  const [modelId, setModelId] = useState("");
  const [text, setText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    listModels()
      .then((all) =>
        setModels(all.map((m) => ({ id: m.id, name: m.name, provider: m.provider }))),
      )
      .catch(() => setModels([]));
  }, []);

  useEffect(() => {
    if (!modelId && models.length > 0) setModelId(models[0].id);
  }, [models, modelId]);

  const selected = models.find((m) => m.id === modelId);
  const provider = selected?.provider === "openai" ? "openai" : "ollama";

  // keep the viewport pinned to the tail while the text grows
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [text]);

  const canRun = !streaming && modelId !== "" && text.trim() !== "";

  const run = async () => {
    if (!canRun) return;
    setError(null);
    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);
    try {
      await streamPlayground({
        model: modelId,
        provider,
        messages: [{ role: "assistant", content: text.trim() }],
        signal: controller.signal,
        events: {
          onDelta: (delta) => setText((prev) => prev + delta),
          onError: (message) => setError(message),
        },
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
  };

  return (
    <div className="flex flex-col justify-between w-full overflow-y-auto h-full">
      <div className="mx-auto w-full md:px-0 h-full">
        <div className="flex flex-col h-full px-4 pt-4 gap-2">
          <select
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
            className="w-[32rem] max-w-full bg-transparent border border-gray-100 dark:border-gray-850 rounded-lg py-1 px-2 text-sm outline-hidden text-gray-900 dark:text-gray-100"
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

          {error && <div className="text-xs text-red-600 dark:text-red-500">{error}</div>}

          <textarea
            id="text-completion-textarea"
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="You're a helpful assistant."
            spellCheck={false}
            className="w-full flex-1 p-3 bg-transparent border border-gray-100 dark:border-gray-850 outline-hidden resize-none rounded-lg text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 font-mono"
          />

          <div className="pb-3 flex justify-end">
            {streaming ? (
              <button
                type="button"
                onClick={cancel}
                className="px-3 py-1.5 text-sm font-medium bg-gray-300 text-black transition rounded-full"
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
                className="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-40 disabled:pointer-events-none"
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
  );
}
