// Folders + share client — /api/v1/folders, the per-conversation share
// endpoints, and the public /api/v1/share/{share_id} (deliberately
// unauthenticated so shared links work for anyone).

import { api } from "./api";
import type {
  Folder,
  SharedConversation,
  ShareResult,
} from "./types";

// ------------------------------------------------------------------ folders

export function listFolders(signal?: AbortSignal): Promise<Folder[]> {
  return api.get<Folder[]>("/api/v1/folders", signal);
}

export function createFolder(name: string): Promise<Folder> {
  return api.post<Folder>("/api/v1/folders", { name });
}

export function renameFolder(id: string, name: string): Promise<Folder> {
  return api.patch<Folder>(`/api/v1/folders/${id}`, { name });
}

export function deleteFolder(id: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/folders/${id}`);
}

// -------------------------------------------------------------------- share

export function shareConversation(conversationId: string): Promise<ShareResult> {
  return api.post<ShareResult>(`/api/v1/conversations/${conversationId}/share`);
}

export function unshareConversation(conversationId: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/conversations/${conversationId}/share`);
}

/** Public share page fetch — no session, no auth header. */
export function getSharedConversation(
  shareId: string,
  signal?: AbortSignal,
): Promise<SharedConversation> {
  return api.get<SharedConversation>(`/api/v1/share/${shareId}`, signal);
}
