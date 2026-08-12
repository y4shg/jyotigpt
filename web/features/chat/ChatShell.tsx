"use client";

// ChatShell — sidebar + chat container (navbar, scrollable message area,
// composer). Shared by the home placeholder and the conversation route.

import { useEffect, useRef, type ReactNode } from "react";
import { clsx } from "clsx";
import { useChat } from "./useChatStore";
import { useApp } from "@/lib/store";
import { Sidebar } from "./Sidebar";
import { Navbar } from "./Navbar";
import { ChatInput } from "./ChatInput";

export function ChatShell({
  children,
  onNavigate,
}: {
  children: ReactNode;
  onNavigate?: (id: string) => void;
}) {
  const { showSidebar } = useChat();
  const { settings } = useApp();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Per-user interface preferences.
  const widescreen = settings?.widescreen ?? false;
  const direction = settings?.chat_direction ?? "auto";
  const dir =
    direction === "rtl" ? "rtl" : direction === "ltr" ? "ltr" : undefined;

  // keep the newest content in view while streaming
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  });

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
          ref={scrollRef}
          dir={dir}
          className="pb-2.5 flex flex-col justify-between w-full flex-auto overflow-auto h-0 max-w-full z-10 scrollbar-hidden"
        >
          {children}
        </div>
        <div className="px-2 md:px-4 pb-2 flex items-end justify-center">
          <div
            className={clsx(
              "flex w-full mx-auto",
              widescreen ? "max-w-7xl" : "max-w-5xl",
            )}
          >
            <ChatInput onNavigate={onNavigate} />
          </div>
        </div>
      </div>
    </>
  );
}
