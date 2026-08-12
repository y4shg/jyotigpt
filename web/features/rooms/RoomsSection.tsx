"use client";

// RoomsSection — the sidebar's Rooms section (was Channels): a collapsible
// list of rooms with # icons and an admin-only "+" to create, gated on the
// public `rooms` feature flag. Mirrors the old app's Channels section:
// hidden while a chat search is active, hidden for non-admins when empty,
// hover actions (edit) for admins.

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronDown, ChevronRight, Hash, Plus, Pencil } from "lucide-react";
import { clsx } from "clsx";
import { useApp } from "@/lib/store";
import { useChat } from "@/features/chat/useChatStore";
import { listRooms } from "@/lib/rooms";
import { RoomModal } from "./RoomModal";
import type { Room } from "@/lib/types";

export function RoomsSection() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, config } = useApp();
  const { search } = useChat();
  const [open, setOpen] = useState(true);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<{ mode: "create" } | { mode: "edit"; room: Room } | null>(null);

  const enabled = config?.features.rooms ?? false;
  const isAdmin = user?.role === "admin";
  const activeId = useMemo(() => {
    const match = pathname?.match(/^\/rooms\/([^/]+)/);
    return match ? match[1] : null;
  }, [pathname]);

  const refresh = () => {
    setLoading(true);
    listRooms()
      .then((rows) => setRooms(rows))
      .catch(() => setRooms([]))
      .finally(() => setLoading(false));
  };

  // Refresh on mount and whenever the route changes (join/leave/create happen
  // on the room page, so this keeps the list in step without a shared store).
  useEffect(() => {
    if (!enabled) return;
    refresh();
  }, [enabled, pathname]);

  // Visibility: hidden while a chat search is active, and (like the old
  // Channels section) hidden for non-admins when no rooms exist yet.
  if (!enabled || search) return null;
  const emptyHidden = !isAdmin && rooms.length === 0 && !loading;
  if (emptyHidden) return null;

  return (
    <div className="mb-2 mt-0.5">
      <div className="w-full group rounded-md relative flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-900 text-gray-500 dark:text-gray-500 transition">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="w-full py-1.5 pl-2 flex items-center gap-1.5 text-xs font-medium text-left"
          aria-expanded={open}
        >
          <span className="text-gray-300 dark:text-gray-600">
            {open ? (
              <ChevronDown className="size-3" strokeWidth={2.5} />
            ) : (
              <ChevronRight className="size-3" strokeWidth={2.5} />
            )}
          </span>
          <span className="translate-y-[0.5px]">Rooms</span>
        </button>
        {isAdmin && (
          <button
            type="button"
            aria-label="Create Room"
            className="absolute z-10 right-2 invisible group-hover:visible self-center flex items-center p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto"
            onClick={() => setModal({ mode: "create" })}
          >
            <Plus className="size-3" strokeWidth={2.5} />
          </button>
        )}
      </div>

      {open && (
        <div className="w-full">
          {loading ? (
            <div className="px-2.5 py-1 text-sm text-gray-500 dark:text-gray-500">
              Loading…
            </div>
          ) : rooms.length === 0 ? (
            <div className="px-2.5 py-1 text-sm text-gray-500 dark:text-gray-500">
              No rooms yet.
            </div>
          ) : (
            rooms.map((room) => (
              <div
                key={room.id}
                className={clsx(
                  "w-full rounded-lg flex relative group hover:bg-gray-100 dark:hover:bg-gray-900 px-2.5 py-1",
                  activeId === room.id ? "bg-gray-100 dark:bg-gray-900" : "",
                )}
              >
                <button
                  type="button"
                  onClick={() => router.push(`/rooms/${room.id}`)}
                  className="w-full flex justify-between items-center min-w-0 text-left"
                  title={room.name}
                >
                  <Hash className="shrink-0 size-5 text-gray-500 dark:text-gray-400" />
                  <div className="text-left self-center overflow-hidden w-full line-clamp-1 pl-1">
                    {room.name}
                  </div>
                </button>
                {isAdmin && (
                  <button
                    type="button"
                    aria-label={`Edit ${room.name}`}
                    className="absolute z-10 right-2 invisible group-hover:visible self-center flex items-center p-0.5 dark:hover:bg-gray-850 rounded-lg touch-auto"
                    onClick={() => setModal({ mode: "edit", room })}
                  >
                    <Pencil className="size-3.5" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {modal && (
        <RoomModal
          room={modal.mode === "edit" ? modal.room : null}
          onClose={() => setModal(null)}
          onCreated={(room) => {
            setModal(null);
            refresh();
            router.push(`/rooms/${room.id}`);
          }}
          onUpdated={(room) => {
            setModal(null);
            refresh();
          }}
        />
      )}
    </div>
  );
}
