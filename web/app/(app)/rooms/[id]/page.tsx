"use client";

// /rooms/[id] — a single room's realtime chat: sidebar + room page.
// The room page renders its own sticky header (sidebar toggle + centered room
// name), matching the old app's channel Navbar.

import { useParams } from "next/navigation";
import { clsx } from "clsx";
import { Sidebar } from "@/features/chat/Sidebar";
import { useChat } from "@/features/chat/useChatStore";
import { RoomChat } from "@/features/rooms/RoomChat";

export default function RoomPage() {
  const { id } = useParams<{ id: string }>();
  const { showSidebar } = useChat();

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
        <RoomChat roomId={id} />
      </div>
    </>
  );
}
