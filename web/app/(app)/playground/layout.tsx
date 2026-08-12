"use client";

// /playground layout — sidebar + tab nav (Chat | Completions) over the two
// playground tabs. Admin-only, like the old app: everyone else bounces to /.

import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { PanelLeft } from "lucide-react";
import { clsx } from "clsx";
import { Sidebar } from "@/features/chat/Sidebar";
import { useChat } from "@/features/chat/useChatStore";
import { useApp } from "@/lib/store";
import { FullPageSpinner } from "@/components/ui/Spinner";

const TABS = [
  { href: "/playground", label: "Chat" },
  { href: "/playground/completions", label: "Completions" },
];

export default function PlaygroundLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading } = useApp();
  const { showSidebar, toggleSidebar } = useChat();

  useEffect(() => {
    if (!loading && user?.role !== "admin") {
      router.replace("/");
    }
  }, [loading, user, router]);

  if (loading || user?.role !== "admin") {
    return (
      <div className="w-full h-screen max-h-[100dvh] flex items-center justify-center">
        <FullPageSpinner />
      </div>
    );
  }

  return (
    <>
      <Sidebar />
      <div
        className={clsx(
          "flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out",
          showSidebar ? "md:max-w-[calc(100%-260px)]" : "",
          "max-w-full",
        )}
      >
        <nav className="px-2.5 pt-1 backdrop-blur-xl w-full">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={toggleSidebar}
              aria-label="Toggle sidebar"
              className="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
            >
              <PanelLeft className="size-4" />
            </button>

            <div className="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent pt-1">
              {TABS.map((tab) => {
                const active = pathname === tab.href;
                return (
                  <Link
                    key={tab.href}
                    href={tab.href}
                    className={clsx(
                      "min-w-fit rounded-full p-1.5 transition",
                      active
                        ? ""
                        : "text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white",
                    )}
                  >
                    {tab.label}
                  </Link>
                );
              })}
            </div>
          </div>
        </nav>
        <div className="flex-1 max-h-full overflow-y-auto">{children}</div>
      </div>
    </>
  );
}
