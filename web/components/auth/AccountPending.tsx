"use client";

// AccountPending — full-screen overlay shown when the signed-in user's role
// is still "pending" (awaiting admin approval).

import { useRouter } from "next/navigation";
import { useApp } from "@/lib/store";

export function AccountPending() {
  const { signOut, refreshUser } = useApp();
  const router = useRouter();

  const handleSignOut = async () => {
    await signOut();
    router.push("/auth");
  };

  return (
    <div className="fixed w-full h-full flex z-[999]">
      <div className="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center">
        <div className="m-auto pb-10 flex flex-col justify-center">
          <div className="max-w-md">
            <div className="text-center dark:text-white text-2xl font-medium z-50">
              Account Activation Pending
              <br />
              Contact Admin for JyotiGPT Access
            </div>

            <div className="mt-4 text-center text-sm dark:text-gray-200 w-full">
              Your account status is currently pending activation.
              <br />
              To access JyotiGPT, please reach out to the administrator. Admins
              can manage user statuses from the Admin Panel.
            </div>

            <div className="mt-6 mx-auto relative group w-fit">
              <button
                className="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 text-gray-700 transition font-medium text-sm"
                onClick={refreshUser}
              >
                Check Again
              </button>

              <button
                className="text-xs text-center w-full mt-2 text-gray-400 underline"
                onClick={handleSignOut}
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
