"use client";

// / — chat home: placeholder greeting + suggestions above the composer.

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChatShell } from "@/features/chat/ChatShell";
import { useChat } from "@/features/chat/useChatStore";

const SUGGESTIONS = [
  "Explain how transformers work",
  "Draft a product launch email",
  "Help me debug a React effect",
  "Summarize the key ideas of RAG",
];

export default function ChatHome() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { send, streaming, models, setModelId } = useChat();

  // Deep link from the workspace: /?models=<id> preselects a model once the
  // catalog has loaded (models may still be fetching on first run).
  useEffect(() => {
    const target = searchParams.get("models");
    if (!target) return;
    const match = models.find((m) => m.id === decodeURIComponent(target));
    if (match) {
      setModelId(match.id);
      router.replace("/");
    }
  }, [searchParams, models, setModelId, router]);

  return (
    <ChatShell onNavigate={(id) => router.push(`/c/${id}`)}>
      <div className="m-auto w-full max-w-6xl px-2 @2xl:px-20 translate-y-6 py-24 text-center">
        <div className="w-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4 font-primary justify-center">
          <span>What can I help you with?</span>
        </div>
        <div className="mx-auto max-w-2xl font-primary mt-8">
          <div className="flex flex-wrap justify-center gap-2">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={streaming}
                onClick={() =>
                  void send(suggestion, { onNavigate: (id) => router.push(`/c/${id}`) })
                }
                className="px-4 py-2 rounded-2xl border border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition text-sm text-gray-600 dark:text-gray-300 disabled:opacity-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </ChatShell>
  );
}
