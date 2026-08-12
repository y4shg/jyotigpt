// Workspace domain client: presets, capabilities, plugins (+sandbox run,
// export/import), documents, collections (RAG), model presets, search.

import { api, API_BASE_URL } from "./api";
import type {
  Capability,
  Collection,
  CollectionItem,
  Document,
  ModelCatalogItem,
  ModelRecord,
  Plugin,
  PluginRunResult,
  Preset,
  SearchResponse,
} from "./types";

// ------------------------------------------------------------------ presets

export const listPresets = () => api.get<Preset[]>("/api/v1/presets");

export const createPreset = (body: {
  name: string;
  content: string;
  is_command?: boolean;
  meta?: Record<string, unknown>;
}) => api.post<Preset>("/api/v1/presets", body);

export const updatePreset = (
  id: string,
  body: Partial<Pick<Preset, "name" | "content" | "is_command" | "meta">>,
) => api.patch<Preset>(`/api/v1/presets/${id}`, body);

export const deletePreset = (id: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/presets/${id}`);

// ------------------------------------------------------------ capabilities

export const listCapabilities = () =>
  api.get<Capability[]>("/api/v1/capabilities");

export const createCapability = (body: {
  name: string;
  description?: string;
  spec?: Record<string, unknown> | string | null;
  is_active?: boolean;
}) => api.post<Capability>("/api/v1/capabilities", body);

export const updateCapability = (
  id: string,
  body: Partial<Pick<Capability, "name" | "description" | "spec" | "is_active">>,
) => api.patch<Capability>(`/api/v1/capabilities/${id}`, body);

export const deleteCapability = (id: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/capabilities/${id}`);

// ----------------------------------------------------------------- plugins

export const listPlugins = () => api.get<Plugin[]>("/api/v1/plugins");

export const createPlugin = (body: {
  name: string;
  kind?: "prompt" | "tool";
  description?: string;
  source?: string;
  prompt?: string;
  is_active?: boolean;
  meta?: Record<string, unknown>;
}) => api.post<Plugin>("/api/v1/plugins", body);

export const updatePlugin = (
  id: string,
  body: Partial<
    Pick<
      Plugin,
      "name" | "kind" | "description" | "source" | "prompt" | "is_active" | "meta"
    >
  >,
) => api.patch<Plugin>(`/api/v1/plugins/${id}`, body);

export const deletePlugin = (id: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/plugins/${id}`);

export const runPlugin = (id: string, args: Record<string, unknown> = {}) =>
  api.post<PluginRunResult>(`/api/v1/plugins/${id}/run`, { arguments: args });

export const exportPlugins = () => api.get<Plugin[]>("/api/v1/plugins/export");

export const importPlugins = (plugins: Plugin[]) =>
  api.post<Plugin[]>("/api/v1/plugins/import", { plugins });

// -------------------------------------------------------------- documents

export const listDocuments = () => api.get<Document[]>("/api/v1/documents");

export function uploadDocument(file: File): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  return fetch(`${API_BASE_URL}/api/v1/documents`, {
    method: "POST",
    credentials: "include",
    body: form,
  }).then(async (res) => {
    if (!res.ok) {
      const json = (await res.json().catch(() => null)) as
        | { detail?: unknown }
        | null;
      const detail = typeof json?.detail === "string" ? json.detail : res.statusText;
      throw new Error(detail);
    }
    return res.json() as Promise<Document>;
  });
}

export const deleteDocument = (id: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/documents/${id}`);

// ------------------------------------------------------------- collections

export const listCollections = () => api.get<Collection[]>("/api/v1/collections");

export const createCollection = (body: {
  name: string;
  description?: string;
  embedding_model?: string;
  is_shared?: boolean;
}) => api.post<Collection>("/api/v1/collections", body);

export const updateCollection = (
  id: string,
  body: Partial<Pick<Collection, "name" | "description" | "embedding_model" | "is_shared">>,
) => api.patch<Collection>(`/api/v1/collections/${id}`, body);

export const deleteCollection = (id: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/collections/${id}`);

export const listCollectionItems = (id: string, limit = 500) =>
  api.get<CollectionItem[]>(`/api/v1/collections/${id}/items?limit=${limit}`);

export const addTextItem = (id: string, content: string) =>
  api.post<CollectionItem[]>(`/api/v1/collections/${id}/items/text`, { content });

export const addDocumentItem = (id: string, documentId: string) =>
  api.post<CollectionItem[]>(`/api/v1/collections/${id}/items/document`, {
    document_id: documentId,
  });

export const removeCollectionItem = (id: string, itemId: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/collections/${id}/items/${itemId}`);

/** Upload straight into a collection (document + chunk + embed in one call). */
export function ingestDocument(file: File, collectionId?: string): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  const q = collectionId ? `?collection_id=${encodeURIComponent(collectionId)}` : "";
  return fetch(`${API_BASE_URL}/api/v1/ingest${q}`, {
    method: "POST",
    credentials: "include",
    body: form,
  }).then(async (res) => {
    if (!res.ok) {
      const json = (await res.json().catch(() => null)) as
        | { detail?: unknown }
        | null;
      const detail = typeof json?.detail === "string" ? json.detail : res.statusText;
      throw new Error(detail);
    }
    return res.json() as Promise<Document>;
  });
}

// ------------------------------------------------------------------ search

export const searchCollections = (
  query: string,
  collectionIds: string[],
  topK?: number,
) =>
  api.post<SearchResponse>("/api/v1/search", {
    query,
    collection_ids: collectionIds,
    top_k: topK ?? null,
  });

// ------------------------------------------------------------------ models

export const listModelsCatalog = () => api.get<ModelCatalogItem[]>("/api/v1/models");

export const listModelRecords = () => api.get<ModelRecord[]>("/api/v1/models/custom");

export const createModelRecord = (body: {
  provider: "ollama" | "openai";
  model_id: string;
  name?: string;
  enabled?: boolean;
  params?: Record<string, unknown>;
}) => api.post<ModelRecord>("/api/v1/models/create", body);

export const updateModelRecord = (
  provider: string,
  modelId: string,
  body: Partial<Pick<ModelRecord, "name" | "enabled" | "params">>,
) =>
  api.patch<ModelRecord>(
    `/api/v1/models/${encodeURIComponent(provider)}/${encodeURIComponent(modelId)}`,
    { ...body, provider, model_id: modelId },
  );

export const deleteModelRecord = (provider: string, modelId: string) =>
  api.delete<{ ok: boolean }>(
    `/api/v1/models/${encodeURIComponent(provider)}/${encodeURIComponent(modelId)}`,
  );
