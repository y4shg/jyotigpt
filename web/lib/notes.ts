// Notes domain client — per-user markdown notes (the old app's Notes tab was
// a dead stub; the rewrite makes it real).

import { api } from "./api";
import type { Note } from "./types";

export function listNotes(): Promise<Note[]> {
  return api.get<Note[]>("/api/v1/notes");
}

export function getNote(id: string): Promise<Note> {
  return api.get<Note>(`/api/v1/notes/${id}`);
}

export function createNote(body: { title?: string; content?: string }): Promise<Note> {
  return api.post<Note>("/api/v1/notes", body);
}

export function updateNote(
  id: string,
  body: { title?: string; content?: string },
): Promise<Note> {
  return api.patch<Note>(`/api/v1/notes/${id}`, body);
}

export function deleteNote(id: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/notes/${id}`);
}
