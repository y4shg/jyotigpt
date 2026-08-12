"use client";

// RoomChat — a single room: header (name, members, presence), the realtime
// message list, and the composer. Messages are sent over the WebSocket; the
// server persists them and fans the event out to every member (sender
// included), so the list only ever grows from received events.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  EllipsisVertical,
  Hash,
  LogOut,
  PanelLeft,
  Pencil,
  Send,
  Trash2,
  Users,
} from "lucide-react";
import { clsx } from "clsx";
import { useApp } from "@/lib/store";
import { useChat } from "@/features/chat/useChatStore";
import {
  deleteRoom,
  getRoom,
  joinRoom,
  leaveRoom,
  listMessages,
  roomSocketUrl,
  type RoomEvent,
} from "@/lib/rooms";
import { errorMessage } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { Dropdown, DropdownDivider, DropdownItem } from "@/components/ui/Dropdown";
import { RoomModal } from "./RoomModal";
import { MembersModal } from "./MembersModal";
import type { Room, RoomMessage } from "@/lib/types";

interface PresenceUser {
  id: string;
  name: string;
}

const TYPING_GRACE_MS = 3000;

export function RoomChat({ roomId }: { roomId: string }) {
  const router = useRouter();
  const { user } = useApp();
  const { toggleSidebar } = useChat();
  const [room, setRoom] = useState<Room | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [messages, setMessages] = useState<RoomMessage[]>([]);
  const [presence, setPresence] = useState<Map<string, PresenceUser>>(new Map());
  const [typing, setTyping] = useState<Map<string, boolean>>(new Map());
  const [connected, setConnected] = useState(false);
  const [socketError, setSocketError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [membersOpen, setMembersOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const typingTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const typingSentRef = useRef(false);

  // ------------------------------------------------------------ room + messages

  const load = useCallback(async () => {
    try {
      const data = await getRoom(roomId);
      setRoom(data);
      setLoadError(null);
      if (data.is_member) {
        const rows = await listMessages(roomId);
        setMessages(rows);
      }
    } catch (err) {
      const message = errorMessage(err);
      if (message.includes("not found")) setNotFound(true);
      else setLoadError(message);
    }
  }, [roomId]);

  useEffect(() => {
    void load();
    const timers = typingTimers.current;
    return () => {
      wsRef.current?.close();
      timers.forEach(clearTimeout);
    };
  }, [load]);

  const isOwner = room?.role === "owner" || user?.role === "admin";

  const createdDate = useMemo(() => {
    if (!room?.created_at) return "recently";
    try {
      return new Date(room.created_at).toLocaleDateString(undefined, {
        month: "long",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "recently";
    }
  }, [room]);

  // ------------------------------------------------------------------ presence

  const applyPresence = useCallback((users: Array<{ user_id: string; name: string }>) => {
    setPresence(new Map(users.map((u) => [u.user_id, { id: u.user_id, name: u.name }])));
  }, []);

  const handleEvent = useCallback(
    (event: RoomEvent) => {
      switch (event.type) {
        case "members":
          applyPresence(event.users);
          break;
        case "presence":
          setPresence((prev) => {
            const next = new Map(prev);
            if (event.action === "joined") next.set(event.user.id, event.user);
            else next.delete(event.user.id);
            return next;
          });
          break;
        case "message":
          setMessages((prev) =>
            prev.some((m) => m.id === event.message.id) ? prev : [...prev, event.message],
          );
          break;
        case "typing":
          setTyping((prev) => {
            const next = new Map(prev);
            const key = event.user.id;
            const existing = typingTimers.current.get(key);
            if (existing) clearTimeout(existing);
            if (event.typing) {
              next.set(key, true);
              typingTimers.current.set(
                key,
                setTimeout(() => {
                  setTyping((cur) => {
                    const nxt = new Map(cur);
                    nxt.delete(key);
                    return nxt;
                  });
                  typingTimers.current.delete(key);
                }, TYPING_GRACE_MS),
              );
            } else {
              next.delete(key);
              typingTimers.current.delete(key);
            }
            return next;
          });
          break;
        case "error":
          setSocketError(event.message);
          break;
      }
    },
    [applyPresence],
  );

  // -------------------------------------------------------------- websocket

  const isMember = room?.is_member ?? false;

  useEffect(() => {
    if (!isMember) return;
    let cancelled = false;
    let attempts = 0;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let ws: WebSocket | null = null;

    const connect = () => {
      if (cancelled) return;
      try {
        ws = new WebSocket(roomSocketUrl());
      } catch {
        return;
      }
      wsRef.current = ws;
      ws.onopen = () => {
        attempts = 0;
        setConnected(true);
        setSocketError(null);
        ws?.send(JSON.stringify({ op: "join", room_id: roomId }));
      };
      ws.onmessage = (ev) => {
        try {
          handleEvent(JSON.parse(String(ev.data)) as RoomEvent);
        } catch {
          // malformed frame — ignore
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (cancelled) return;
        attempts += 1;
        if (attempts <= 8) {
          retry = setTimeout(connect, Math.min(1000 * 2 ** attempts, 30000));
        } else {
          setSocketError("Connection lost. Reload to keep chatting.");
        }
      };
      ws.onerror = () => {
        ws?.close();
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (retry) clearTimeout(retry);
      ws?.close();
      wsRef.current = null;
    };
  }, [isMember, roomId, handleEvent]);

  const sendMessage = () => {
    const content = draft.trim();
    if (!content || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ op: "message", room_id: roomId, content }));
    setDraft("");
    sendTyping(false);
  };

  const sendTyping = (typingNow: boolean) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (typingNow === typingSentRef.current) return;
    typingSentRef.current = typingNow;
    ws.send(JSON.stringify({ op: "typing", room_id: roomId, typing: typingNow }));
  };

  const onDraftChange = (value: string) => {
    setDraft(value);
    sendTyping(value.length > 0);
    // clear the typing flag once the user stops editing
    if (value.length === 0) sendTyping(false);
  };

  const typingNames = useMemo(
    () =>
      Array.from(typing.entries())
        .filter(([, active]) => active)
        .map(([id]) => presence.get(id)?.name ?? "Someone"),
    [typing, presence],
  );

  const onlineCount = useMemo(() => presence.size, [presence]);

  // auto-scroll the newest message into view
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length]);

  // ---------------------------------------------------------------- actions

  const join = async () => {
    try {
      const updated = await joinRoom(roomId);
      setRoom(updated);
      void load();
    } catch (err) {
      setLoadError(errorMessage(err));
    }
  };

  const leave = async () => {
    try {
      await leaveRoom(roomId);
      router.push("/");
    } catch (err) {
      setLoadError(errorMessage(err));
    }
  };

  const remove = async () => {
    try {
      await deleteRoom(roomId);
      router.push("/");
    } catch (err) {
      setLoadError(errorMessage(err));
    }
  };

  // ------------------------------------------------------------------- render

  if (notFound) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-sm text-gray-500 dark:text-gray-400">
        <Hash className="size-8" />
        <div>Room not found.</div>
        <Button variant="default" onClick={() => router.push("/")}>
          Back to chat
        </Button>
      </div>
    );
  }

  if (!room) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <FullPageSpinner />
      </div>
    );
  }

  // not a member yet — offer to join public rooms
  if (!room.is_member) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center gap-4 text-center px-4">
        <Hash className="size-8 text-gray-400" />
        <div className="text-xl font-semibold text-gray-900 dark:text-white">
          #{room.name}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400 max-w-sm">
          {room.is_public
            ? "This is a public room — join to see the conversation."
            : "This room is private. Ask a member to add you."}
        </div>
        {room.is_public && (
          <Button variant="primary" onClick={() => void join()}>
            Join room
          </Button>
        )}
        <Button variant="ghost" onClick={() => router.push("/")}>
          Back to chat
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full h-full">
      {/* header — the room's own navbar: sidebar toggle + centered name */}
      <nav className="sticky top-0 z-30 w-full px-1.5 py-1.5 -mb-8 flex items-center drag-region">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
          className="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
        >
          <PanelLeft className="size-4" />
        </button>
        <div className="min-w-0 flex-1 text-center px-1">
          <div className="line-clamp-1 capitalize font-medium font-primary text-lg text-gray-900 dark:text-gray-100">
            {room.name}
          </div>
        </div>
        <div className="shrink-0 flex items-center">
          <button
            type="button"
            onClick={() => setMembersOpen(true)}
            aria-label="Members"
            title={`${room.member_count} members, ${onlineCount} online`}
            className="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
          >
            <Users className="size-4" />
            <span
              className={clsx(
                "ml-1.5 size-2 rounded-full",
                connected ? "bg-green-500" : "bg-gray-400",
              )}
            />
          </button>
          <Dropdown
            trigger={
              <span className="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300">
                <EllipsisVertical className="size-4" />
              </span>
            }
          >
            <DropdownItem onClick={() => setMembersOpen(true)}>
              <Users className="size-4" /> Members
            </DropdownItem>
            {isOwner && (
              <>
                <DropdownItem onClick={() => setEditing(true)}>
                  <Pencil className="size-4" /> Edit room
                </DropdownItem>
                <DropdownDivider />
                <DropdownItem onClick={() => setConfirmDelete(true)} className="text-red-600 dark:text-red-500">
                  <Trash2 className="size-4" /> Delete room
                </DropdownItem>
              </>
            )}
            {!isOwner && (
              <>
                <DropdownDivider />
                <DropdownItem onClick={() => void leave()}>
                  <LogOut className="size-4" /> Leave room
                </DropdownItem>
              </>
            )}
          </Dropdown>
        </div>
      </nav>

      {/* message list */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto scrollbar-hidden pt-6"
      >
        <div className="px-5 max-w-5xl mx-auto pb-2.5">
          {/* start-of-room header */}
          <div className="flex flex-col gap-1.5 pb-5 pt-10">
            <div className="text-2xl font-medium capitalize text-gray-900 dark:text-white">
              {room.name}
            </div>
            <div className="text-gray-500 dark:text-gray-400 text-sm">
              This room was created on {createdDate}. This is the very beginning
              of the {room.name} room.
            </div>
            <hr className="border-gray-50 dark:border-gray-700/20 py-2.5 w-full" />
          </div>

          {!connected && !socketError && (
            <div className="text-center text-xs text-gray-500 dark:text-gray-500 py-2">
              Connecting…
            </div>
          )}
          {socketError && (
            <div className="text-center text-xs text-amber-600 dark:text-amber-500 py-2">
              {socketError}
            </div>
          )}
          {loadError && (
            <div className="text-center text-xs text-red-600 dark:text-red-500 py-2">
              {loadError}
            </div>
          )}

          {messages.length === 0 && (
            <div className="text-center text-sm text-gray-500 dark:text-gray-400 py-6">
              No messages yet — say hello.
            </div>
          )}
          {messages.map((message) => (
            <div
              key={message.id}
              className="flex flex-col px-0 py-0.5 group w-full max-w-5xl"
            >
              <div className="flex gap-2.5 items-start">
                <div className="shrink-0 w-9">
                  <div className="flex size-8 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-800 text-xs font-semibold text-gray-700 dark:text-gray-200 translate-y-1">
                    {message.name.slice(0, 2).toUpperCase()}
                  </div>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="self-end text-base shrink-0 font-medium truncate text-gray-900 dark:text-white">
                      {message.name}
                    </span>
                    <span className="self-center text-xs text-gray-400 dark:text-gray-500">
                      {new Date(message.created_at ?? 0).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className="min-w-full text-sm text-gray-700 dark:text-gray-300 break-words whitespace-pre-wrap">
                    {message.content}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* composer */}
      <div className="pb-[1rem]">
        <div className="max-w-6xl px-2.5 mx-auto inset-x-0 relative">
          {typingNames.length > 0 && (
            <div className="text-xs px-4 mb-1 -mt-5">
              <span className="font-normal text-black dark:text-white">
                {typingNames.join(", ")}
              </span>{" "}
              {typingNames.length === 1 ? "is" : "are"} typing…
            </div>
          )}
          <div className="w-full flex gap-1.5">
            <div className="flex-1 flex flex-col relative w-full rounded-3xl px-1 bg-gray-600/5 dark:bg-gray-400/5 dark:text-gray-100">
              <input
                value={draft}
                onChange={(e) => onDraftChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Send a Message"
                className="w-full bg-transparent outline-none py-3 px-1 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500"
              />
            </div>
            <button
              type="button"
              onClick={sendMessage}
              disabled={!draft.trim() || !connected}
              aria-label="Send message"
              id="send-message-button"
              className={clsx(
                "transition rounded-full p-1.5 self-center",
                draft.trim() && connected
                  ? "bg-red-600 text-white hover:bg-red-700 dark:bg-red-600 dark:text-white dark:hover:bg-red-700"
                  : "text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700",
              )}
            >
              <Send className="size-5" />
            </button>
          </div>
        </div>
      </div>

      {/* modals */}
      {membersOpen && (
        <MembersModal room={room} onClose={() => setMembersOpen(false)} />
      )}
      {editing && (
        <RoomModal
          room={room}
          onClose={() => setEditing(false)}
          onUpdated={(updated) => {
            setRoom(updated);
            setEditing(false);
          }}
        />
      )}
      {confirmDelete && (
        <div className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center p-4" onClick={() => setConfirmDelete(false)}>
          <div
            className="w-[24rem] max-w-full rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-3xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              Delete room?
            </div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              This permanently deletes #{room.name} and its message history.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={() => void remove()}>
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
