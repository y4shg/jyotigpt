// Rooms domain client: REST for room/member/message CRUD plus the realtime
// WebSocket at /api/v1/rooms/ws. Messages are sent over the socket (the server
// persists them and fans the event out to every member, sender included), so
// the room page only ever appends events it receives.

import { api, API_BASE_URL } from "./api";
import type { Room, RoomMember, RoomMessage } from "./types";

// ------------------------------------------------------------------ rooms

export function listRooms(signal?: AbortSignal): Promise<Room[]> {
  return api.get<Room[]>("/api/v1/rooms", signal);
}

export function getRoom(id: string): Promise<Room> {
  return api.get<Room>(`/api/v1/rooms/${id}`);
}

export function createRoom(body: {
  name: string;
  description?: string;
  is_public?: boolean;
}): Promise<Room> {
  return api.post<Room>("/api/v1/rooms", body);
}

export function updateRoom(
  id: string,
  body: { name?: string; description?: string; is_public?: boolean },
): Promise<Room> {
  return api.patch<Room>(`/api/v1/rooms/${id}`, body);
}

export function deleteRoom(id: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/rooms/${id}`);
}

// --------------------------------------------------------------- membership

export function joinRoom(id: string): Promise<Room> {
  return api.post<Room>(`/api/v1/rooms/${id}/join`);
}

export function leaveRoom(id: string): Promise<{ ok: boolean }> {
  return api.post<{ ok: boolean }>(`/api/v1/rooms/${id}/leave`);
}

export function listMembers(id: string): Promise<RoomMember[]> {
  return api.get<RoomMember[]>(`/api/v1/rooms/${id}/members`);
}

export function addMember(
  id: string,
  body: { user_id?: string; email?: string },
): Promise<RoomMember> {
  return api.post<RoomMember>(`/api/v1/rooms/${id}/members`, body);
}

export function removeMember(id: string, userId: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/rooms/${id}/members/${userId}`);
}

export function setMemberRole(
  id: string,
  userId: string,
  role: "owner" | "member",
): Promise<RoomMember> {
  return api.patch<RoomMember>(`/api/v1/rooms/${id}/members/${userId}`, { role });
}

// ---------------------------------------------------------------- messages

export function listMessages(
  id: string,
  opts: { beforeId?: string; limit?: number } = {},
): Promise<RoomMessage[]> {
  const q = new URLSearchParams();
  if (opts.beforeId) q.set("before_id", opts.beforeId);
  if (opts.limit) q.set("limit", String(opts.limit));
  const suffix = q.toString() ? `?${q}` : "";
  return api.get<RoomMessage[]>(`/api/v1/rooms/${id}/messages${suffix}`);
}

export function createMessageREST(id: string, content: string): Promise<RoomMessage> {
  return api.post<RoomMessage>(`/api/v1/rooms/${id}/messages`, { content });
}

export function deleteMessageREST(id: string, messageId: string): Promise<{ ok: boolean }> {
  return api.delete<{ ok: boolean }>(`/api/v1/rooms/${id}/messages/${messageId}`);
}

// ------------------------------------------------------------------- socket

/**
 * The rooms WebSocket URL. In dev the API lives on its own port, so we swap
 * the scheme of API_BASE_URL; in production the API is same-origin.
 */
export function roomSocketUrl(): string {
  if (API_BASE_URL) {
    return `${API_BASE_URL.replace(/^http/, "ws")}/api/v1/rooms/ws`;
  }
  const proto = typeof location !== "undefined" && location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/api/v1/rooms/ws`;
}

/** Wire events the socket can deliver. */
export type RoomEvent =
  | { type: "members"; room_id: string; users: Array<{ user_id: string; name: string }> }
  | {
      type: "presence";
      room_id: string;
      action: "joined" | "left";
      user: { id: string; name: string };
    }
  | { type: "message"; room_id: string; message: RoomMessage }
  | { type: "typing"; room_id: string; user: { id: string; name: string }; typing: boolean }
  | { type: "error"; message: string };
