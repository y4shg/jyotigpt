"use client";

// RoomModal — create a room. Mirrors the old app's Create Channel modal:
// a name field plus Private/Public visibility. (The old app slug-normalized
// channel names into URLs; the rewrite addresses rooms by id, so names are
// kept as typed.)

import { useState } from "react";
import { Lock, Globe } from "lucide-react";
import { createRoom, deleteRoom, updateRoom } from "@/lib/rooms";
import { errorMessage } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { Field } from "@/features/settings/controls";
import type { Room } from "@/lib/types";

interface RoomModalProps {
  /** When set, the modal edits this room instead of creating one. */
  room?: Room | null;
  onClose: () => void;
  onCreated?: (room: Room) => void;
  onUpdated?: (room: Room) => void;
  onDeleted?: () => void;
}

export function RoomModal({ room, onClose, onCreated, onUpdated, onDeleted }: RoomModalProps) {
  const [name, setName] = useState(room?.name ?? "");
  const [description, setDescription] = useState(room?.description ?? "");
  const [isPublic, setIsPublic] = useState(room?.is_public ?? true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const submit = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Room name is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (room) {
        const updated = await updateRoom(room.id, { name: trimmed, description, is_public: isPublic });
        onUpdated?.(updated);
      } else {
        const created = await createRoom({ name: trimmed, description, is_public: isPublic });
        onCreated?.(created);
      }
      onClose();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!room) return;
    setBusy(true);
    setError(null);
    try {
      await deleteRoom(room.id);
      onDeleted?.();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  };

  return (
    <Modal open size="sm" onClose={onClose}>
      <ModalTitle title={room ? "Edit Room" : "Create Room"} onClose={onClose} />
      <div className="px-5 pt-4 pb-5 flex flex-col gap-4">
        <Field label="Room Name">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void submit();
            }}
            placeholder="e.g. general"
            className="w-full bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 rounded-lg px-2.5 py-1.5 outline-none border border-transparent focus:border-gray-300 dark:focus:border-gray-600 transition"
          />
        </Field>

        <Field label="Visibility" description="Anyone can join a public room; private rooms are invite-only.">
          <div className="flex w-fit gap-1 bg-gray-100 dark:bg-gray-800 rounded-full p-1">
            <button
              type="button"
              onClick={() => setIsPublic(true)}
              className={
                isPublic
                  ? "px-3 py-1.5 rounded-full text-sm font-medium transition select-none bg-white dark:bg-gray-850 text-gray-900 dark:text-white shadow-sm flex items-center gap-1.5"
                  : "px-3 py-1.5 rounded-full text-sm font-medium transition select-none text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 flex items-center gap-1.5"
              }
            >
              <Globe className="size-4" /> Public
            </button>
            <button
              type="button"
              onClick={() => setIsPublic(false)}
              className={
                !isPublic
                  ? "px-3 py-1.5 rounded-full text-sm font-medium transition select-none bg-white dark:bg-gray-850 text-gray-900 dark:text-white shadow-sm flex items-center gap-1.5"
                  : "px-3 py-1.5 rounded-full text-sm font-medium transition select-none text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 flex items-center gap-1.5"
              }
            >
              <Lock className="size-4" /> Private
            </button>
          </div>
        </Field>

        <Field label="Description (optional)">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What is this room for?"
            rows={2}
            className="w-full bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 rounded-lg px-2.5 py-1.5 outline-none border border-transparent focus:border-gray-300 dark:focus:border-gray-600 transition resize-none"
          />
        </Field>

        {error && <div className="text-sm text-red-600 dark:text-red-500">{error}</div>}

        <div className="flex justify-end gap-1.5 text-sm font-medium pt-3">
          {room && (
            <Button
              variant="ghost"
              onClick={() => setConfirmingDelete(true)}
              className="text-red-600 dark:text-red-500"
            >
              Delete
            </Button>
          )}
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => void submit()} disabled={busy}>
            {busy ? "Saving…" : room ? "Update" : "Create"}
          </Button>
        </div>
      </div>

      {confirmingDelete && (
        <div
          className="fixed inset-0 z-[9999] bg-black/60 flex items-center justify-center p-4"
          onClick={() => setConfirmingDelete(false)}
        >
          <div
            className="w-[24rem] max-w-full rounded-2xl bg-white dark:bg-gray-900 p-5 shadow-3xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-lg font-semibold text-gray-900 dark:text-white">
              Delete room?
            </div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              This permanently deletes #{name} and its message history.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setConfirmingDelete(false)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={() => void remove()} disabled={busy}>
                Delete
              </Button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
