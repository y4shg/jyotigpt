"use client";

// Admin — the admin panel shell: a pill nav (Users / Evaluations / Settings)
// over the three admin sections, matching the product's workspace nav.
// Only users with the admin role may enter; everyone else is redirected to /.

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChartColumn, PanelLeft, Settings2, Users } from "lucide-react";
import { clsx } from "clsx";
import { useApp } from "@/lib/store";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { UsersTab } from "./UsersTab";
import { EvaluationsTab } from "./EvaluationsTab";
import { SettingsTab } from "./SettingsTab";

export type AdminTab = "users" | "evaluations" | "settings";

const TABS: Array<{ id: AdminTab; label: string; icon: typeof Users }> = [
  { id: "users", label: "Users", icon: Users },
  { id: "evaluations", label: "Evaluations", icon: ChartColumn },
  { id: "settings", label: "Settings", icon: Settings2 },
];

const VALID: AdminTab[] = TABS.map((t) => t.id);

export function Admin() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading } = useApp();

  const raw = searchParams.get("tab") ?? "users";
  const tab: AdminTab = VALID.includes(raw as AdminTab)
    ? (raw as AdminTab)
    : "users";

  // Admin gate: non-admins bounce back to the chat home.
  useEffect(() => {
    if (!loading && user?.role !== "admin") {
      router.replace("/");
    }
  }, [loading, user, router]);

  if (loading || user?.role !== "admin") {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <FullPageSpinner />
      </div>
    );
  }

  const select = (id: AdminTab) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", id);
    router.replace(`/admin?${params.toString()}`);
  };

  return (
    <div className="relative flex flex-col w-full h-screen max-h-[100dvh] max-w-full">
      <nav className="px-2.5 pt-1 backdrop-blur-xl">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => router.push("/")}
            aria-label="Back to chat"
            className="self-center flex flex-none items-center cursor-pointer p-1.5 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
          >
            <PanelLeft className="size-4" />
          </button>

          <div className="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => select(id)}
                className={clsx(
                  "min-w-fit rounded-full p-1.5 flex items-center gap-1.5 transition",
                  tab === id
                    ? "text-gray-900 dark:text-white"
                    : "text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white",
                )}
              >
                <Icon className="size-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <div
        className="pb-1 px-[18px] flex-1 max-h-full overflow-y-auto scrollbar-hidden"
        id="admin-container"
      >
        {tab === "users" && <UsersTab />}
        {tab === "evaluations" && <EvaluationsTab />}
        {tab === "settings" && <SettingsTab />}
      </div>
    </div>
  );
}
