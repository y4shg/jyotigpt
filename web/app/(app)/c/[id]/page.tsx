"use client";

// /c/[id] — a conversation: its message history + composer.

import { useEffect } from "react";
import { useParams } from "next/navigation";
import { ChatShell } from "@/features/chat/ChatShell";
import { MessageItem } from "@/features/chat/MessageItem";
import { useChat } from "@/features/chat/useChatStore";
import { FullPageSpinner } from "@/components/ui/Spinner";

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  const {
    activeId,
    messages,
    loadingConversation,
    openConversation,
    removeMessage,
  } = useChat();

  useEffect(() => {
    if (activeId !== id) {
      void openConversation(id);
    }
  }, [activeId, id, openConversation]);

  return (
    <ChatShell>
      <div className="flex flex-col justify-end w-full h-full">
        {loadingConversation ? (
          <div className="flex-1 flex items-center justify-center">
            <FullPageSpinner />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm">
            Ask JyotiGPT anything — the reply streams in here.
          </div>
        ) : (
          <div className="flex flex-col justify-end">
            {messages.map((message) => (
              <MessageItem
                key={message.id}
                message={message}
                onCopy={() => undefined}
                onDelete={() => void removeMessage(message.id)}
              />
            ))}
          </div>
        )}
      </div>
    </ChatShell>
  );
}
