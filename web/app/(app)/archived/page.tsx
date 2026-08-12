"use client";

// /archived — list of archived conversations with unarchive/delete actions.

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { clsx } from "clsx";
import { Sidebar } from "@/features/chat/Sidebar";
import { Navbar } from "@/features/chat/Navbar";
import { useChat } from "@/features/chat/useChatStore";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { ArchiveRestore, MessageSquare, Trash2 } from "lucide-react";

function formatDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function ArchivedPage() {
  const {
    archived,
    loadingArchived,
    showSidebar,
    refreshArchived,
    openConversation,
    setArchived,
    removeConversation,
  } = useChat();
  const router = useRouter();

  useEffect(() => {
    void refreshArchived();
  }, [refreshArchived]);

  const open = (id: string) => {
    void openConversation(id);
    router.push(`/c/${id}`);
  };

  return (
    <>
      <Sidebar />
      <div
        id="chat-container"
        className={clsx(
          "h-screen max-h-[100dvh] transition-width duration-200 ease-in-out",
          showSidebar ? "md:max-w-[calc(100%-260px)]" : "",
          "w-full max-w-full flex flex-col",
        )}
      >
        <Navbar />
        <div
          id="messages-container"
          className="pb-2.5 flex flex-col w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
        >
          <div className="m-auto w-full max-w-5xl px-4 py-6">
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Archived chats
            </h1>
            {loadingArchived ? (
              <div className="flex justify-center py-12">
                <FullPageSpinner />
              </div>
            ) : archived.length === 0 ? (
              <div className="text-sm text-gray-500 dark:text-gray-500 py-12 text-center">
                No archived chats.
              </div>
            ) : (
              <ul className="space-y-1">
                {archived.map((conv) => (
                  <li
                    key={conv.id}
                    className="group flex items-center gap-3 rounded-xl px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
                  >
                    <button
                      type="button"
                      onClick={() => open(conv.id)}
                      className="flex items-center gap-3 min-w-0 flex-1 text-left"
                      title={conv.title}
                    >
                      <MessageSquare className="shrink-0 size-4 text-gray-500 dark:text-gray-400" />
                      <span className="truncate text-gray-900 dark:text-gray-100">
                        {conv.title}
                      </span>
                    </button>
                    <span className="shrink-0 text-xs text-gray-500 dark:text-gray-500">
                      {formatDate(conv.updated_at)}
                    </span>
                    <button
                      type="button"
                      aria-label="Unarchive"
                      onClick={() => void setArchived(conv.id, false)}
                      className="shrink-0 p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-200/70 dark:hover:bg-gray-800 transition"
                    >
                      <ArchiveRestore className="size-4" />
                    </button>
                    <button
                      type="button"
                      aria-label="Delete"
                      onClick={() => void removeConversation(conv.id)}
                      className="shrink-0 p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-200/70 dark:hover:bg-gray-800 transition"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
