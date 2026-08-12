"use client";

// App shell gate: no session → /auth; pending role → AccountPending overlay;
// otherwise render the authenticated app.

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useApp } from "@/lib/store";
import { AccountPending } from "@/components/auth/AccountPending";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { ChatProvider } from "@/features/chat/useChatStore";
import { SettingsModal } from "@/features/settings/SettingsModal";
import { Toaster } from "@/lib/toast";

export default function AppShellLayout({
  children,
}: {
  children: ReactNode;
}) {
  const { user, loading } = useApp();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/auth");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end">
        <div className="w-full flex-1 h-full flex items-center justify-center">
          <FullPageSpinner />
        </div>
      </div>
    );
  }

  if (!user) {
    return null; // redirecting to /auth
  }

  if (user.role !== "admin" && user.role !== "user") {
    return (
      <div className="app relative">
        <div className="text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end">
          <AccountPending />
        </div>
      </div>
    );
  }

  return (
    <div className="app relative">
      <div className="text-gray-700 dark:text-gray-100 bg-white dark:bg-gray-900 h-screen max-h-[100dvh] overflow-auto flex flex-row justify-end">
        <ChatProvider>
          {children}
          <SettingsModal />
          <Toaster />
        </ChatProvider>
      </div>
    </div>
  );
}
