"use client";

// MembersModal — the room roster. Everyone sees who belongs (with a live
// presence dot); the owner can add by email, promote/demote, and remove.

import { useCallback, useEffect, useState } from "react";
import { Crown, UserPlus, X } from "lucide-react";
import { clsx } from "clsx";
import {
  addMember,
  listMembers,
  removeMember,
  setMemberRole,
} from "@/lib/rooms";
import { errorMessage } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import type { Room, RoomMember } from "@/lib/types";

export function MembersModal({ room, onClose }: { room: Room; onClose: () => void }) {
  const [members, setMembers] = useState<RoomMember[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const isOwner = room.role === "owner";

  const load = useCallback(async () => {
    try {
      setMembers(await listMembers(room.id));
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [room.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const add = async () => {
    const value = email.trim();
    if (!value) return;
    setBusy(true);
    setError(null);
    try {
      await addMember(room.id, { email: value });
      setEmail("");
      setAdding(false);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const toggleRole = async (member: RoomMember) => {
    try {
      await setMemberRole(room.id, member.user_id, member.role === "owner" ? "member" : "owner");
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const remove = async (member: RoomMember) => {
    try {
      await removeMember(room.id, member.user_id);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal open size="sm" onClose={onClose}>
      <ModalTitle title={`#${room.name} members`} onClose={onClose} />
      <div className="px-5 py-4 flex flex-col gap-2">
        {isOwner && (
          <div className="flex items-center gap-2">
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void add();
              }}
              placeholder="Add member by email"
              className="flex-1 min-w-0 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 rounded-lg px-2.5 py-1.5 outline-none border border-transparent focus:border-gray-300 dark:focus:border-gray-600 transition text-sm"
            />
            <Button variant="primary" onClick={() => void add()} disabled={busy} className="px-3 py-1.5">
              <UserPlus className="size-4" /> Add
            </Button>
          </div>
        )}

        {error && <div className="text-sm text-red-600 dark:text-red-500">{error}</div>}

        <div className="max-h-80 overflow-y-auto scrollbar-none space-y-0.5 -mx-1 px-1">
          {members.map((member) => (
            <div
              key={member.user_id}
              className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-850"
            >
              <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-800 text-xs font-semibold text-gray-700 dark:text-gray-200">
                {member.name.slice(0, 2).toUpperCase()}
              </div>
              <span className="min-w-0 flex-1 truncate text-sm text-gray-900 dark:text-gray-100">
                {member.name}
              </span>
              {member.role === "owner" ? (
                <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-500">
                  <Crown className="size-3.5" /> Owner
                </span>
              ) : null}
              {isOwner && member.user_id !== room.created_by && (
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => void toggleRole(member)}
                    title={member.role === "owner" ? "Demote" : "Promote to owner"}
                    className={clsx(
                      "text-xs rounded-md px-2 py-1 transition",
                      member.role === "owner"
                        ? "text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-800"
                        : "text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-800",
                    )}
                  >
                    {member.role === "owner" ? "Demote" : "Promote"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void remove(member)}
                    aria-label={`Remove ${member.name}`}
                    className="p-1 rounded-md text-gray-400 hover:text-red-600 dark:hover:text-red-500 transition"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
}
