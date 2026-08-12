"use client";

// Navbar — model selector, new chat, and the sidebar toggle. Sits above the
// message list and overlaps it slightly (-mb-8), matching the product shell.

import { useRouter } from "next/navigation";
import { PanelLeft, Plus } from "lucide-react";
import { useChat } from "./useChatStore";
import { ModelSelector } from "./ModelSelector";

export function Navbar() {
  const { toggleSidebar, createAndOpen, streaming } = useChat();
  const router = useRouter();

  const newChat = async () => {
    if (streaming) return;
    const conv = await createAndOpen();
    if (conv) router.push(`/c/${conv.id}`);
  };

  return (
    <nav className="sticky top-0 z-30 w-full py-1.5 -mb-8 flex flex-col items-center">
      <div className="flex w-full justify-between items-center px-3">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
          className="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
        >
          <PanelLeft className="size-4" />
        </button>

        <div className="flex items-center">
          <ModelSelector />
          <button
            type="button"
            onClick={newChat}
            aria-label="New chat"
            className="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
          >
            <Plus className="size-4" />
          </button>
        </div>
      </div>
    </nav>
  );
}
