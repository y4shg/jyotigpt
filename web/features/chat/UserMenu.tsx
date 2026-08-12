"use client";

// UserMenu — avatar + account dropdown at the bottom of the sidebar.
// (Profile/Admin pages land with their owning phases.)

import { useRouter } from "next/navigation";
import { FlaskConical, LogOut, NotebookPen, Settings, ShieldCheck, Wrench } from "lucide-react";
import { useApp } from "@/lib/store";
import { Dropdown, DropdownDivider, DropdownItem } from "@/components/ui/Dropdown";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function UserMenu() {
  const { user, signOut, setSettingsOpen } = useApp();
  const router = useRouter();

  const handleSignOut = async () => {
    await signOut();
    router.replace("/auth");
  };

  return (
    <Dropdown
      align="bottom-0 left-0"
      className="w-full"
      trigger={
        <span className="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-100 dark:hover:bg-gray-900 transition items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-800 text-xs font-semibold text-gray-700 dark:text-gray-200 overflow-hidden">
            {initials(user?.name ?? "?")}
          </span>
          <span className="flex flex-col min-w-0 text-left">
            <span className="truncate text-gray-900 dark:text-white font-medium">
              {user?.name}
            </span>
            <span className="truncate text-gray-600 dark:text-gray-400 text-xs">
              {user?.email}
            </span>
          </span>
        </span>
      }
    >
      <div className="w-full text-sm rounded-xl px-1 py-1.5 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg font-primary min-w-48">
        {user?.role === "admin" ? (
          <>
            <DropdownItem onClick={() => router.push("/admin")}>
              <ShieldCheck className="size-4" /> Admin Panel
            </DropdownItem>
            <DropdownDivider />
          </>
        ) : null}
        {user?.role === "admin" ? (
          <DropdownItem onClick={() => router.push("/playground")}>
            <FlaskConical className="size-4" /> Playground
          </DropdownItem>
        ) : null}
        <DropdownItem onClick={() => router.push("/notes")}>
          <NotebookPen className="size-4" /> Notes
        </DropdownItem>
        <DropdownItem onClick={() => router.push("/workspace")}>
          <Wrench className="size-4" /> Workspace
        </DropdownItem>
        <DropdownItem onClick={() => setSettingsOpen(true)}>
          <Settings className="size-4" /> Settings
        </DropdownItem>
        <DropdownDivider />
        <DropdownItem
          onClick={handleSignOut}
          className="text-red-600 dark:text-red-500"
        >
          <LogOut className="size-4" /> Log out
        </DropdownItem>
      </div>
    </Dropdown>
  );
}
