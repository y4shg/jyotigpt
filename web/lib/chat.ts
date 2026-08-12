// Chat domain client: conversations, messages, model catalog, and the SSE
// streaming reader for /api/v1/chat/completions.

import { api, ApiError, API_BASE_URL } from "./api";
import type {
  ChatParams,
  Conversation,
  ConversationListResult,
  Message,
  MessageRole,
  ModelInfo,
} from "./types";

// ------------------------------------------------------------------ models

export function listModels(signal?: AbortSignal): Promise<ModelInfo[]> {
  return api.get<ModelInfo[]>("/api/v1/models", signal);
}

// ------------------------------------------------------------- conversations

export function listConversations(
  search = "",
  page = 1,
  signal?: AbortSignal,
  archived = false,
): Promise<ConversationListResult> {
  const q = new URLSearchParams({
    search,
    page: String(page),
    archived: String(archived),
  });
  return api.get<ConversationListResult>(`/api/v1/conversations?${q}`, signal);
}

export function getConversation(id: string): Promise<Conversation & { messages: Message[] }> {
  return api.get<Conversation & { messages: Message[] }>(`/api/v1/conversations/${id}`);
}

export function createConversation(title = "New Chat"): Promise<Conversation> {
  return api.post<Conversation>("/api/v1/conversations", { title });
}

export function updateConversation(
  id: string,
  patch: { title?: string; folder_id?: string | null; archived?: boolean; pinned?: boolean },
): Promise<Conversation> {
  return api.patch<Conversation>(`/api/v1/conversations/${id}`, patch);
}

export function deleteConversation(id: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/conversations/${id}`);
}

// ---------------------------------------------------------------- messages

export function addMessage(
  conversationId: string,
  role: MessageRole,
  content: string,
  model = "",
  provider = "",
): Promise<Message> {
  return api.post<Message>(`/api/v1/conversations/${conversationId}/messages`, {
    role,
    content,
    model,
    provider,
  });
}

export function updateMessage(
  id: string,
  patch: { content?: string; done?: boolean; error?: string },
): Promise<Message> {
  return api.patch<Message>(`/api/v1/messages/${id}`, patch);
}

export function deleteMessage(id: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/messages/${id}`);
}

// ----------------------------------------------------------------- streaming

export interface ChatStreamEvents {
  onStart?: (messageId: string | null) => void;
  onDelta?: (content: string) => void;
  onDone?: (payload: { message_id: string | null; content: string }) => void;
  onError?: (message: string) => void;
}

export interface StreamChatOptions {
  model: string;
  provider?: string;
  /** Flow pipeline id — required when provider is "flow". */
  pipeline?: string;
  conversationId?: string | null;
  /** Stateless context, used when conversationId is not set (playground). */
  messages?: Array<{ role: string; content: string }>;
  params?: ChatParams;
  signal?: AbortSignal;
  /** When true, the backend will perform a web search before composing. */
  web_search?: boolean;
}

/**
 * POST /api/v1/chat/completions and dispatch parsed SSE events. Resolves when
 * the stream ends; rejects with ApiError on a non-200 response or when the
 * server itself reports an error event (after calling onError).
 */
export async function streamChat(opts: StreamChatOptions & { events: ChatStreamEvents }): Promise<void> {
  const { model, provider = "ollama", pipeline, conversationId, messages, params, signal, web_search, events } = opts;
  const res = await fetch(`${API_BASE_URL}/api/v1/chat/completions`, {
    method: "POST",
    credentials: "include",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      provider,
      pipeline: pipeline ?? null,
      conversation_id: conversationId ?? null,
      messages: messages ?? [],
      params: params ?? {},
      ...(web_search ? { web_search: true } : {}),
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
      case "start":
        events.onStart?.((payload.message_id as string | null) ?? null);
        break;
      case "delta":
        if (typeof payload.content === "string") events.onDelta?.(payload.content);
        break;
      case "done":
        events.onDone?.({
          message_id: (payload.message_id as string | null) ?? null,
          content: typeof payload.content === "string" ? payload.content : "",
        });
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
