"use client";

// /s/[share_id] — public share page. Sits outside the (app) route group on
// purpose: no session gate, no chat store, just a read-only rendering of the
// shared conversation fetched from the unauthenticated share endpoint.

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getSharedConversation } from "@/lib/folders";
import { ApiError } from "@/lib/api";
import type { SharedConversation, SharedMessage } from "@/lib/types";
import { Markdown } from "@/features/chat/Markdown";
import { FullPageSpinner } from "@/components/ui/Spinner";

function ProfileImage() {
  return (
    <div className="size-8 object-cover rounded-full -translate-y-[1px] bg-gray-200 dark:bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-600 dark:text-gray-300">
      J
    </div>
  );
}

function SharedMessageRow({ message }: { message: SharedMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex w-full user-message justify-end">
        <div className="rounded-3xl max-w-[90%] px-5 py-2 bg-gray-50 dark:bg-gray-850 whitespace-pre-wrap text-gray-900 dark:text-gray-100">
          {message.content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex w-full message-item">
      <div className="w-full flex-col">
        <div className="flex gap-1 items-center mb-1">
          <ProfileImage />
          <div className="self-center font-semibold line-clamp-1 text-gray-900 dark:text-gray-100">
            JyotiGPT
          </div>
        </div>
        <div className="chat-assistant w-full min-w-full markdown-prose">
          <Markdown content={message.content} streaming={false} />
        </div>
      </div>
    </div>
  );
}

export default function SharedConversationPage() {
  const { share_id } = useParams<{ share_id: string }>();
  const [shared, setShared] = useState<SharedConversation | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getSharedConversation(share_id)
      .then((data) => {
        if (!cancelled) setShared(data);
      })
      .catch((error) => {
        if (error instanceof ApiError && error.status === 404) {
          if (!cancelled) setMissing(true);
        } else if (!cancelled) {
          setMissing(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [share_id]);

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <div className="mx-auto w-full max-w-5xl px-4 py-10">
        {missing ? (
          <div className="py-24 text-center text-gray-500 dark:text-gray-500">
            This shared conversation is unavailable or no longer exists.
          </div>
        ) : !shared ? (
          <div className="py-24 flex justify-center">
            <FullPageSpinner />
          </div>
        ) : (
          <>
            <div className="mb-8 text-center">
              <h1 className="text-2xl font-semibold">{shared.title}</h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-500">
                Shared conversation · JyotiGPT
              </p>
            </div>
            {shared.messages.length === 0 ? (
              <div className="text-center text-sm text-gray-500 dark:text-gray-500">
                This conversation has no messages to show.
              </div>
            ) : (
              <div className="space-y-4">
                {shared.messages.map((message) => (
                  <SharedMessageRow key={message.id} message={message} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
