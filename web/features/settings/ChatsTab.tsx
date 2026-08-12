"use client";

// Chats — export/import conversations, archived chats, bulk actions.

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Archive,
  Download,
  MessageSquare,
  Trash2,
  Upload,
} from "lucide-react";
import { useChat } from "@/features/chat/useChatStore";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/lib/api";
import type { ExportConversation } from "@/lib/types";
import {
  archiveAllConversations,
  deleteAllConversations,
  exportConversations,
  importConversations,
} from "@/lib/settings";
import { SettingsSection } from "./controls";

export function ChatsTab() {
  const router = useRouter();
  const { refreshConversations, refreshArchived } = useChat();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"archive" | "delete" | null>(null);

  const flash = (text: string | null) => {
    setMessage(text);
    if (text) window.setTimeout(() => setMessage(null), 4000);
  };

  const doExport = async () => {
    setBusy("export");
    try {
      const data = await exportConversations();
      const blob = new Blob(
        [JSON.stringify({ conversations: data.conversations }, null, 2)],
        { type: "application/json" },
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `jyotigpt-chats-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      flash(`Exported ${data.count} conversations.`);
    } catch (error) {
      flash(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  const doImport = async (file: File) => {
    setBusy("import");
    try {
      const parsed: unknown = JSON.parse(await file.text());
      const conversations = (parsed as { conversations?: unknown })
        .conversations;
      if (!Array.isArray(conversations)) {
        throw new Error("Expected a JSON file with a 'conversations' array.");
      }
      const result = await importConversations(
        conversations as ExportConversation[],
      );
      await refreshConversations();
      await refreshArchived();
      flash(`Imported ${result.count} conversations.`);
    } catch (error) {
      flash(errorMessage(error));
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const doArchiveAll = async () => {
    setConfirm(null);
    setBusy("archive");
    try {
      const result = await archiveAllConversations();
      await refreshConversations();
      await refreshArchived();
      flash(`Archived ${result.count} conversations.`);
    } catch (error) {
      flash(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  const doDeleteAll = async () => {
    setConfirm(null);
    setBusy("delete");
    try {
      const result = await deleteAllConversations();
      await refreshConversations();
      await refreshArchived();
      flash(`Deleted ${result.count} conversations.`);
    } catch (error) {
      flash(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {message ? (
        <div className="text-sm text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-850 rounded-xl px-3 py-2">
          {message}
        </div>
      ) : null}

      <SettingsSection title="Import Chats">
        <div className="flex gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void doImport(file);
            }}
          />
          <Button
            variant="default"
            disabled={busy !== null}
            onClick={() => fileRef.current?.click()}
          >
            <Upload className="size-4" />
            {busy === "import" ? "Importing…" : "Import Chats"}
          </Button>
        </div>
      </SettingsSection>

      <SettingsSection title="Export Chats">
        <div className="flex gap-2">
          <Button
            variant="default"
            disabled={busy !== null}
            onClick={() => void doExport()}
          >
            <Download className="size-4" />
            {busy === "export" ? "Exporting…" : "Export Chats"}
          </Button>
        </div>
      </SettingsSection>

      <SettingsSection title="Archived Chats">
        <Button
          variant="ghost"
          className="justify-start w-fit"
          onClick={() => router.push("/archived")}
        >
          <MessageSquare className="size-4" /> View archived chats
        </Button>
        <Button
          variant="ghost"
          className="justify-start w-fit"
          disabled={busy !== null}
          onClick={() => setConfirm("archive")}
        >
          <Archive className="size-4" /> Archive All Chats
        </Button>
        <Button
          variant="danger"
          className="justify-start w-fit"
          disabled={busy !== null}
          onClick={() => setConfirm("delete")}
        >
          <Trash2 className="size-4" /> Delete All Chats
        </Button>
      </SettingsSection>

      <ConfirmDialog
        open={confirm === "archive"}
        title="Archive all chats?"
        message="All conversations will be moved to the archive. You can restore them later."
        confirmLabel="Archive All"
        danger={false}
        onConfirm={() => void doArchiveAll()}
        onCancel={() => setConfirm(null)}
      />
      <ConfirmDialog
        open={confirm === "delete"}
        title="Delete all chats?"
        message="This permanently deletes every conversation and message. This cannot be undone."
        confirmLabel="Delete All"
        onConfirm={() => void doDeleteAll()}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
