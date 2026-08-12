"use client";

// Sidebar — search, New Chat, folders, time-grouped conversation history,
// archive link, user menu. Fixed on small screens (slides over the chat),
// docked on md+.

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  ArchiveRestore,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  Folder as FolderIcon,
  FolderPlus,
  Link2,
  MessageSquare,
  PanelLeft,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { clsx } from "clsx";
import { useChat } from "./useChatStore";
import { UserMenu } from "./UserMenu";
import { RoomsSection } from "@/features/rooms/RoomsSection";
import { Dropdown, DropdownDivider, DropdownItem } from "@/components/ui/Dropdown";
import { Button } from "@/components/ui/Button";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import type { Conversation, Folder } from "@/lib/types";

const EMOJI: Record<string, string> = {
  Today: "🕐",
  Yesterday: "🕑",
  "Previous 7 days": "🕒",
  "Previous 30 days": "🕓",
};

interface ChatActions {
  onOpen: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
  onArchive: () => void;
  onShare: () => void;
  onMove: () => void;
}

function ChatItem({
  title,
  active,
  streaming,
  archived = false,
  actions,
}: {
  title: string;
  active: boolean;
  streaming: boolean;
  archived?: boolean;
  actions: ChatActions;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  const commit = () => {
    setEditing(false);
    const next = draft.trim();
    if (next && next !== title) actions.onRename(next);
  };

  return (
    <div
      className={clsx(
        "group flex w-full justify-between items-center rounded-lg px-[11px] py-[6px]",
        active
          ? "bg-gray-200 dark:bg-gray-900"
          : "group-hover:bg-gray-100 dark:group-hover:bg-gray-950",
        "whitespace-nowrap text-ellipsis",
      )}
    >
      {editing ? (
        <input
          ref={inputRef}
          value={draft}
          autoFocus
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit();
            if (e.key === "Escape") setEditing(false);
          }}
          className="w-full bg-transparent outline-none"
        />
      ) : (
        <button
          type="button"
          onClick={actions.onOpen}
          className="flex items-center gap-2 min-w-0 flex-1 text-left"
          title={title}
        >
          <MessageSquare className="shrink-0 size-4" />
          <span className="truncate text-ellipsis">{title}</span>
          {streaming && (
            <span className="size-1.5 shrink-0 rounded-full bg-gray-400 animate-pulse" />
          )}
        </button>
      )}
      {!editing && (
        <Dropdown
          trigger={<span className="opacity-0 group-hover:opacity-100 transition p-1">⋯</span>}
          align="right-0"
          className="shrink-0"
        >
          <DropdownItem onClick={() => { setDraft(title); setEditing(true); }}>
            <Pencil className="size-4" /> Rename
          </DropdownItem>
          <DropdownItem onClick={actions.onMove}>
            <FolderIcon className="size-4" /> Move to folder
          </DropdownItem>
          <DropdownItem onClick={actions.onArchive}>
            {archived ? <ArchiveRestore className="size-4" /> : <Archive className="size-4" />}
            {archived ? "Unarchive" : "Archive"}
          </DropdownItem>
          <DropdownItem onClick={actions.onShare}>
            <Link2 className="size-4" /> Share
          </DropdownItem>
          <DropdownDivider />
          <DropdownItem onClick={actions.onDelete} className="text-red-600 dark:text-red-500">
            <Trash2 className="size-4" /> Delete
          </DropdownItem>
        </Dropdown>
      )}
    </div>
  );
}

function HistoryGroup({
  label,
  conversations,
  activeId,
  streaming,
  actionsFor,
}: {
  label: string;
  conversations: Conversation[];
  activeId: string | null;
  streaming: boolean;
  actionsFor: (conv: Conversation) => ChatActions;
}) {
  return (
    <div>
      <div className="w-full pl-2.5 text-xs text-gray-500 dark:text-gray-500 font-normal pb-1.5">
        <span className="pr-2">{EMOJI[label] ?? ""}</span>
        {label}
      </div>
      {conversations.map((conv) => (
        <ChatItem
          key={conv.id}
          title={conv.title}
          active={conv.id === activeId}
          streaming={streaming && conv.id === activeId}
          actions={actionsFor(conv)}
        />
      ))}
    </div>
  );
}

function FolderItem({
  folder,
  conversations,
  activeId,
  streaming,
  onRename,
  onDelete,
  actionsFor,
}: {
  folder: Folder;
  conversations: Conversation[];
  activeId: string | null;
  streaming: boolean;
  onRename: (title: string) => void;
  onDelete: () => void;
  actionsFor: (conv: Conversation) => ChatActions;
}) {
  const [open, setOpen] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(folder.name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  const commit = () => {
    setEditing(false);
    const next = draft.trim();
    if (next && next !== folder.name) onRename(next);
  };

  const groups = useMemo(() => {
    const buckets = new Map<string, Conversation[]>();
    for (const conv of conversations) {
      const bucket = conv.time_range || "Previous 30 days";
      if (!buckets.has(bucket)) buckets.set(bucket, []);
      buckets.get(bucket)!.push(conv);
    }
    return Array.from(buckets.entries()).map(([label, items]) => ({ label, items }));
  }, [conversations]);

  return (
    <div>
      <div className="group flex w-full justify-between items-center rounded-lg py-[5px] pl-1 pr-2 hover:bg-gray-100 dark:hover:bg-gray-950">
        {editing ? (
          <input
            ref={inputRef}
            value={draft}
            autoFocus
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Enter") commit();
              if (e.key === "Escape") setEditing(false);
            }}
            className="w-full bg-transparent outline-none px-2"
          />
        ) : (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="flex items-center gap-2 min-w-0 flex-1 text-left"
            title={folder.name}
          >
            {open ? (
              <ChevronDown className="shrink-0 size-4" />
            ) : (
              <ChevronRight className="shrink-0 size-4" />
            )}
            <FolderIcon className="shrink-0 size-4" />
            <span className="truncate text-ellipsis">{folder.name}</span>
            <span className="shrink-0 ml-auto text-xs text-gray-500 dark:text-gray-500">
              {folder.conversation_count}
            </span>
          </button>
        )}
        {!editing && (
          <Dropdown
            trigger={<span className="opacity-0 group-hover:opacity-100 transition p-1">⋯</span>}
            align="right-0"
            className="shrink-0"
          >
            <DropdownItem onClick={() => { setDraft(folder.name); setEditing(true); }}>
              <Pencil className="size-4" /> Rename
            </DropdownItem>
            <DropdownDivider />
            <DropdownItem onClick={onDelete} className="text-red-600 dark:text-red-500">
              <Trash2 className="size-4" /> Delete
            </DropdownItem>
          </Dropdown>
        )}
      </div>
      {open &&
        groups.map((group, idx) => (
          <div key={group.label} className={idx === 0 ? "pl-2" : "pl-2 pt-1"}>
            <HistoryGroup
              label={group.label}
              conversations={group.items}
              activeId={activeId}
              streaming={streaming}
              actionsFor={actionsFor}
            />
          </div>
        ))}
    </div>
  );
}

// ------------------------------------------------------------- move + share

function MoveToFolderModal({
  conversation,
  folders,
  onClose,
  onMove,
  onCreateAndMove,
}: {
  conversation: Conversation;
  folders: Folder[];
  onClose: () => void;
  onMove: (folderId: string | null) => void;
  onCreateAndMove: (name: string) => void;
}) {
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");

  const create = () => {
    const next = name.trim();
    if (!next) return;
    onCreateAndMove(next);
    setCreating(false);
    setName("");
  };

  return (
    <Modal open size="xs" onClose={onClose}>
      <ModalTitle title="Move to folder" onClose={onClose} />
      <div className="p-4 pt-2 space-y-1">
        {creating ? (
          <div className="flex gap-2 items-center">
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") create();
                if (e.key === "Escape") setCreating(false);
              }}
              placeholder="Folder name"
              className="flex-1 min-w-0 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-500 rounded-lg px-2.5 py-1.5 outline-none border border-transparent focus:border-gray-300 dark:focus:border-gray-600 transition"
            />
            <Button variant="primary" onClick={create} className="px-3 py-1.5">
              Create
            </Button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-700 dark:text-gray-300"
          >
            <FolderPlus className="size-4" /> New folder
          </button>
        )}
        <button
          type="button"
          onClick={() => onMove(null)}
          className={clsx(
            "w-full text-left flex items-center gap-2 px-2.5 py-1.5 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850",
            conversation.folder_id === null
              ? "bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-gray-100"
              : "text-gray-700 dark:text-gray-300",
          )}
        >
          <span className="w-4 shrink-0">
            {conversation.folder_id === null && <Check className="size-4" />}
          </span>
          No folder
        </button>
        {folders.map((folder) => (
          <button
            key={folder.id}
            type="button"
            onClick={() => onMove(folder.id)}
            className={clsx(
              "w-full text-left flex items-center gap-2 px-2.5 py-1.5 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850",
              conversation.folder_id === folder.id
                ? "bg-gray-100 dark:bg-gray-850 text-gray-900 dark:text-gray-100"
                : "text-gray-700 dark:text-gray-300",
            )}
          >
            <span className="w-4 shrink-0">
              {conversation.folder_id === folder.id && <Check className="size-4" />}
            </span>
            <FolderIcon className="shrink-0 size-4" />
            <span className="truncate">{folder.name}</span>
          </button>
        ))}
      </div>
    </Modal>
  );
}

function ShareModal({
  conversation,
  onClose,
  onStopSharing,
}: {
  conversation: Conversation;
  onClose: () => void;
  onStopSharing: () => void;
}) {
  const { share } = useChat();
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    share(conversation.id).then((result) => {
      if (cancelled) return;
      if (result) setUrl(result.url);
      else setFailed(true);
    });
    return () => {
      cancelled = true;
    };
  }, [conversation.id, share]);

  const copy = async () => {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable
    }
  };

  return (
    <Modal open size="sm" onClose={onClose}>
      <ModalTitle title="Share conversation" onClose={onClose} />
      <div className="p-4 pt-2">
        {failed ? (
          <div className="text-sm text-red-600 dark:text-red-500">
            Could not create the share link.
          </div>
        ) : url ? (
          <div className="flex gap-2 items-center">
            <input
              readOnly
              value={url}
              onFocus={(e) => e.currentTarget.select()}
              className="flex-1 min-w-0 bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg px-2.5 py-2 text-sm outline-none"
            />
            <Button variant="default" onClick={copy} className="shrink-0">
              {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
        ) : (
          <div className="text-sm text-gray-500 dark:text-gray-500">Creating link…</div>
        )}
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-500">
          Anyone with the link can view this conversation.
        </p>
        {conversation.share_id && (
          <Button
            variant="ghost"
            className="mt-3 text-red-600 dark:text-red-500"
            onClick={() => {
              onStopSharing();
              onClose();
            }}
          >
            Stop sharing
          </Button>
        )}
      </div>
    </Modal>
  );
}

// ------------------------------------------------------------------ sidebar

export function Sidebar() {
  const {
    showSidebar,
    toggleSidebar,
    conversations,
    folders,
    activeId,
    search,
    setSearch,
    openConversation,
    createAndOpen,
    renameConversation,
    removeConversation,
    renameFolder,
    removeFolder,
    moveToFolder,
    setArchived,
    createFolder,
    share,
    unshare,
    streaming,
  } = useChat();
  const router = useRouter();

  // conversation targeted by the move/share modals
  const [moveTarget, setMoveTarget] = useState<Conversation | null>(null);
  const [shareTarget, setShareTarget] = useState<Conversation | null>(null);
  // inline "New folder" input in the folders header
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [folderDraft, setFolderDraft] = useState("");

  const commitFolderDraft = () => {
    const name = folderDraft.trim();
    setCreatingFolder(false);
    setFolderDraft("");
    if (name) void createFolder(name);
  };

  const filed = useMemo(
    () => conversations.filter((c) => c.folder_id),
    [conversations],
  );
  const unfiled = useMemo(
    () => conversations.filter((c) => !c.folder_id),
    [conversations],
  );

  const groups = useMemo(() => {
    const buckets = new Map<string, typeof conversations>();
    for (const conv of unfiled) {
      const bucket = conv.time_range || "Previous 30 days";
      if (!buckets.has(bucket)) buckets.set(bucket, []);
      buckets.get(bucket)!.push(conv);
    }
    return Array.from(buckets.entries()).map(([label, items]) => ({
      label,
      items,
    }));
  }, [unfiled]);

  const byFolder = useMemo(() => {
    const map = new Map<string, Conversation[]>();
    for (const conv of filed) {
      const list = map.get(conv.folder_id!) ?? [];
      list.push(conv);
      map.set(conv.folder_id!, list);
    }
    return map;
  }, [filed]);

  const newChat = async () => {
    if (streaming) return;
    const conv = await createAndOpen();
    if (conv) router.push(`/c/${conv.id}`);
  };

  const actionsFor = (conv: Conversation): ChatActions => ({
    onOpen: () => void openConversation(conv.id),
    onRename: (title) => void renameConversation(conv.id, title),
    onDelete: () => void removeConversation(conv.id),
    onArchive: () => void setArchived(conv.id, true),
    onShare: () => setShareTarget(conv),
    onMove: () => setMoveTarget(conv),
  });

  const createFolderAndMove = (name: string, conversationId: string) => {
    void createFolder(name).then((folder) => {
      if (folder) void moveToFolder(conversationId, folder.id);
      setMoveTarget(null);
    });
  };

  return (
    <div
      className={clsx(
        "h-screen max-h-[100dvh] min-h-screen select-none shrink-0 bg-gray-50 text-gray-900",
        "dark:bg-gray-950 dark:text-gray-200 text-sm fixed z-50 top-0 left-0 overflow-x-hidden",
        "flex flex-col",
        showSidebar
          ? "md:relative w-[260px] max-w-[260px]"
          : "-translate-x-[260px] w-[0px]",
        "transition-transform duration-200 ease-in-out",
      )}
    >
      {/* header: search + panel toggle */}
      <div className="px-[0.5625rem] pt-2 pb-1.5 flex justify-between space-x-1 text-gray-600 dark:text-gray-400 sticky top-0 z-10 -mb-3">
        <Search className="self-center -mr-8 z-10 mt-1 size-4" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search"
          className="grow pl-9 bg-gray-200/70 dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-500 rounded-2xl px-2.5 py-1.5 outline-none border border-transparent focus:border-gray-100 dark:focus:border-gray-800 transition"
        />
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
          className="shrink-0 cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-900 transition"
        >
          <PanelLeft className="size-4" />
        </button>
      </div>

      {/* history */}
      <div className="flex-1 overflow-y-auto scrollbar-none px-1 pb-2 mt-3">
        <button
          type="button"
          onClick={newChat}
          className="grow flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none w-full"
        >
          <Plus className="size-4" />
          <span>New Chat</span>
        </button>

        <div className="w-full pt-5">
          <RoomsSection />

          {folders.length === 0 && groups.length === 0 && !search && (
            <div className="px-2.5 pt-3 pb-1.5 text-gray-500 dark:text-gray-500">
              No conversations yet.
            </div>
          )}
          {groups.length === 0 && search && (
            <div className="px-2.5 pt-3 pb-1.5 text-gray-500 dark:text-gray-500">
              No results for “{search}”.
            </div>
          )}

          {/* folders */}
          {(folders.length > 0 || creatingFolder) && (
            <div className="mb-2">
              <div className="w-full flex items-center justify-between px-2.5 pb-1 text-xs text-gray-500 dark:text-gray-500">
                <span>Folders</span>
                <button
                  type="button"
                  aria-label="New folder"
                  className="p-0.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-900 transition"
                  onClick={() => {
                    setCreatingFolder((v) => !v);
                    setFolderDraft("");
                  }}
                >
                  <FolderPlus className="size-3.5" />
                </button>
              </div>
              {creatingFolder && (
                <input
                  autoFocus
                  value={folderDraft}
                  onChange={(e) => setFolderDraft(e.target.value)}
                  onBlur={commitFolderDraft}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitFolderDraft();
                    if (e.key === "Escape") {
                      setCreatingFolder(false);
                      setFolderDraft("");
                    }
                  }}
                  placeholder="Folder name"
                  className="w-full bg-gray-200/70 dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-500 rounded-lg px-2.5 py-1.5 mb-1 outline-none border border-transparent focus:border-gray-100 dark:focus:border-gray-800 transition"
                />
              )}
              {folders.map((folder) => (
                <FolderItem
                  key={folder.id}
                  folder={folder}
                  conversations={byFolder.get(folder.id) ?? []}
                  activeId={activeId}
                  streaming={streaming}
                  onRename={(title) => void renameFolder(folder.id, title)}
                  onDelete={() => void removeFolder(folder.id)}
                  actionsFor={actionsFor}
                />
              ))}
            </div>
          )}

          {/* unfiled history */}
          {groups.map((group, idx) => (
            <div key={group.label} className={idx === 0 ? "" : "pt-2"}>
              <HistoryGroup
                label={group.label}
                conversations={group.items}
                activeId={activeId}
                streaming={streaming}
                actionsFor={actionsFor}
              />
            </div>
          ))}
        </div>
      </div>

      {/* archive + user menu */}
      <div className="shrink-0 p-1.5 border-t border-gray-200/60 dark:border-gray-900">
        <button
          type="button"
          onClick={() => router.push("/archived")}
          className="w-full flex items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition outline-none"
        >
          <Archive className="size-4" />
          <span>Archived chats</span>
        </button>
        <UserMenu />
      </div>

      {/* move-to-folder modal (also handles "New folder" when no target) */}
      {moveTarget && (
        <MoveToFolderModal
          conversation={moveTarget}
          folders={folders}
          onClose={() => setMoveTarget(null)}
          onMove={(folderId) => {
            void moveToFolder(moveTarget.id, folderId);
            setMoveTarget(null);
          }}
          onCreateAndMove={(name) => {
            void createFolderAndMove(name, moveTarget.id);
          }}
        />
      )}

      {/* share modal */}
      {shareTarget && (
        <ShareModal
          conversation={shareTarget}
          onClose={() => setShareTarget(null)}
          onStopSharing={() => void unshare(shareTarget.id)}
        />
      )}
    </div>
  );
}
