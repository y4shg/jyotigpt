// Playground client — the ad-hoc completions lab at /api/v1/playground.
// Unlike chat, nothing is persisted: the lab sends the message list as-is and
// streams back an SSE feed of start / delta / done / error events.

import { ApiError, API_BASE_URL } from "./api";
import type { ChatParams } from "./types";

export interface PlaygroundMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface PlaygroundEvents {
  onDelta?: (content: string) => void;
  onDone?: (content: string) => void;
  onError?: (message: string) => void;
}

export interface StreamPlaygroundOptions {
  model: string;
  provider?: "ollama" | "openai" | "flow";
  messages: PlaygroundMessage[];
  params?: ChatParams;
  signal?: AbortSignal;
}

/**
 * POST /api/v1/playground/completions and dispatch parsed SSE events. Resolves
 * when the stream ends; rejects with ApiError on a non-200 response or when
 * the server reports an error event (after calling onError).
 */
export async function streamPlayground(
  opts: StreamPlaygroundOptions & { events: PlaygroundEvents },
): Promise<void> {
  const { model, provider = "ollama", messages, params, signal, events } = opts;
  const res = await fetch(`${API_BASE_URL}/api/v1/playground/completions`, {
    method: "POST",
    credentials: "include",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      provider,
      messages,
      params: params ?? {},
    }),
  });

  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = (body as { detail?: unknown }).detail ?? body;
    } catch {
      // non-JSON error body — keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (!res.body) {
    throw new ApiError(0, "Streaming unsupported in this browser.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let serverError: string | null = null;

  const flush = (block: string) => {
    let event = "";
    let data: unknown = null;
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) {
        try {
          data = JSON.parse(line.slice(5).trim());
        } catch {
          data = line.slice(5).trim();
        }
      }
    }
    if (!event) return;
    const payload = (data ?? {}) as Record<string, unknown>;
    switch (event) {
      case "delta":
        if (typeof payload.content === "string") events.onDelta?.(payload.content);
        break;
      case "done":
        events.onDone?.(typeof payload.content === "string" ? payload.content : "");
        break;
      case "error":
        serverError = typeof payload.message === "string" ? payload.message : "Stream failed.";
        events.onError?.(serverError);
        break;
    }
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE frames are separated by a blank line.
      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        if (block.trim()) flush(block);
      }
    }
    // trailing frame without a final blank line
    if (buffer.trim()) flush(buffer);
  } finally {
    reader.releaseLock();
  }

  if (serverError) {
    throw new ApiError(502, serverError);
  }
}
