// Client for the user-preferences surface: per-user settings, memory,
// profile (avatar/password), chat import/export, and the about endpoint.

import { api } from "./api";
import type {
  AboutInfo,
  ExportConversation,
  ImportResult,
  MemoryEntry,
  User,
  UserSettings,
} from "./types";

export function getUserSettings(): Promise<UserSettings> {
  return api.get<UserSettings>("/api/v1/users/me/settings");
}

export function updateUserSettings(
  patch: Partial<UserSettings>,
): Promise<UserSettings> {
  return api.post<UserSettings>("/api/v1/users/me/settings", { settings: patch });
}

// ---------------------------------------------------------------- memory

export function listMemory(): Promise<MemoryEntry[]> {
  return api.get<MemoryEntry[]>("/api/v1/memory");
}

export function createMemory(content: string): Promise<MemoryEntry> {
  return api.post<MemoryEntry>("/api/v1/memory", { content });
}

export function updateMemory(id: string, content: string): Promise<MemoryEntry> {
  return api.patch<MemoryEntry>(`/api/v1/memory/${id}`, { content });
}

export function deleteMemory(id: string): Promise<{ ok: boolean }> {
  return api.delete(`/api/v1/memory/${id}`);
}

// ---------------------------------------------------------------- profile

export function updateAvatar(imageData: string): Promise<User> {
  return api.post<User>("/api/v1/users/me/avatar", { image_data: imageData });
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<{ ok: boolean }> {
  return api.post<{ ok: boolean }>("/api/v1/users/me/password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

// ---------------------------------------------------------------- about

export function getAbout(): Promise<AboutInfo> {
  return api.get<AboutInfo>("/api/v1/about");
}

// ---------------------------------------------------------------- chats tab

export function exportConversations(): Promise<{
  conversations: ExportConversation[];
  count: number;
}> {
  return api.get("/api/v1/conversations/export");
}

export function importConversations(
  conversations: ExportConversation[],
): Promise<ImportResult> {
  return api.post<ImportResult>("/api/v1/conversations/import", { conversations });
}

export function archiveAllConversations(): Promise<ImportResult> {
  return api.post<ImportResult>("/api/v1/conversations/actions/archive-all");
}

export function deleteAllConversations(): Promise<ImportResult> {
  return api.post<ImportResult>("/api/v1/conversations/actions/delete-all");
}
