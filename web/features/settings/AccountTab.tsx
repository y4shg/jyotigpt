"use client";

// Account — profile (name/email/avatar), password change, API keys.

import { useEffect, useRef, useState } from "react";
import { Check, KeyRound, Plus, Trash2, UserRound } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { useApp } from "@/lib/store";
import type { ApiKeyInfo, User } from "@/lib/types";
import { changePassword, updateAvatar } from "@/lib/settings";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { SettingsSection } from "./controls";

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** Downscale an image file to a small JPEG data URL (kept under 300 KB). */
function resizeToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read the image file."));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("Unsupported image format."));
      img.onload = () => {
        const size = 128;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Canvas unavailable."));
          return;
        }
        ctx.drawImage(img, 0, 0, size, size);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.src = String(reader.result);
    };
    reader.readAsDataURL(file);
  });
}

export function AccountTab() {
  const { user, refreshUser } = useApp();
  const [profile, setProfile] = useState({ name: "", email: "" });
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);

  const [apiKeys, setApiKeys] = useState<ApiKeyInfo[] | null>(null);
  const [keyName, setKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [keyError, setKeyError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setProfile({ name: user.name, email: user.email });
    }
  }, [user]);

  useEffect(() => {
    let cancelled = false;
    api
      .get<ApiKeyInfo[]>("/api/v1/users/api-keys")
      .then((keys) => {
        if (!cancelled) setApiKeys(keys);
      })
      .catch(() => {
        if (!cancelled) setApiKeys([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const flash = (
    setter: (v: string | null) => void,
    text: string | null,
  ) => {
    setter(text);
    if (text) window.setTimeout(() => setter(null), 4000);
  };

  const saveProfile = async () => {
    setSavingProfile(true);
    try {
      await api.patch<User>("/api/v1/users/me", {
        name: profile.name.trim(),
        email: profile.email.trim(),
      });
      await refreshUser();
      flash(setProfileMessage, "Profile updated.");
    } catch (error) {
      flash(setProfileMessage, errorMessage(error));
    } finally {
      setSavingProfile(false);
    }
  };

  const onAvatarFile = async (file: File) => {
    try {
      const imageData = await resizeToDataUrl(file);
      await updateAvatar(imageData);
      await refreshUser();
      flash(setProfileMessage, "Profile image updated.");
    } catch (error) {
      flash(setProfileMessage, errorMessage(error));
    }
  };

  const savePassword = async () => {
    if (newPassword !== confirmPassword) {
      flash(setPasswordMessage, "New passwords do not match.");
      return;
    }
    setSavingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      flash(setPasswordMessage, "Password updated.");
    } catch (error) {
      flash(setPasswordMessage, errorMessage(error));
    } finally {
      setSavingPassword(false);
    }
  };

  const createKey = async () => {
    setKeyError(null);
    try {
      const created = await api.post<ApiKeyInfo & { key?: string }>(
        "/api/v1/users/api-keys",
        { name: keyName.trim() },
      );
      setApiKeys((list) => [created, ...(list ?? [])]);
      setKeyName("");
      setCreatedKey(created.key ?? null);
    } catch (error) {
      setKeyError(errorMessage(error));
    }
  };

  const removeKey = async (id: string) => {
    try {
      await api.delete(`/api/v1/users/api-keys/${id}`);
      setApiKeys((list) => (list ?? []).filter((k) => k.id !== id));
    } catch {
      // keep the key on failure
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <SettingsSection title="Profile">
        {profileMessage ? (
          <div className="text-sm text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-850 rounded-xl px-3 py-2">
            {profileMessage}
          </div>
        ) : null}
        <div className="flex items-center gap-4">
          <button
            type="button"
            className="relative flex size-16 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700 text-lg font-semibold text-gray-700 dark:text-gray-200 overflow-hidden shrink-0"
            onClick={() => fileRef.current?.click()}
            title="Change profile image"
          >
            {user?.image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.image}
                alt=""
                className="size-full object-cover"
              />
            ) : (
              initials(user?.name ?? "?")
            )}
          </button>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Profile image — click the avatar to upload a new one.
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void onAvatarFile(file);
              e.target.value = "";
            }}
          />
        </div>
        <div className="grid grid-cols-1 gap-3">
          <div className="flex flex-col gap-1.5">
            <div className="text-sm font-medium">Name</div>
            <Input
              value={profile.name}
              onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="text-sm font-medium">Email</div>
            <Input
              value={profile.email}
              type="email"
              onChange={(e) =>
                setProfile((p) => ({ ...p, email: e.target.value }))
              }
            />
          </div>
        </div>
        <div>
          <Button
            variant="primary"
            disabled={savingProfile || !profile.name.trim() || !profile.email.trim()}
            onClick={() => void saveProfile()}
          >
            {savingProfile ? "Saving…" : "Save"}
          </Button>
        </div>
      </SettingsSection>

      <SettingsSection title="Password">
        {passwordMessage ? (
          <div className="text-sm text-gray-700 dark:text-gray-200 bg-gray-100 dark:bg-gray-850 rounded-xl px-3 py-2">
            {passwordMessage}
          </div>
        ) : null}
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <div className="text-sm font-medium">Current Password</div>
            <Input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="text-sm font-medium">New Password</div>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="text-sm font-medium">Confirm New Password</div>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <div>
            <Button
              variant="primary"
              disabled={
                savingPassword ||
                !currentPassword ||
                newPassword.length < 6 ||
                !confirmPassword
              }
              onClick={() => void savePassword()}
            >
              {savingPassword ? "Updating…" : "Update Password"}
            </Button>
          </div>
        </div>
      </SettingsSection>

      <SettingsSection title="API Keys">
        <div className="flex flex-col gap-3">
          {createdKey ? (
            <div className="text-sm rounded-xl bg-emerald-50 dark:bg-emerald-950 px-3 py-2.5">
              <div className="font-medium text-emerald-700 dark:text-emerald-300">
                Copy your new API key — it will not be shown again.
              </div>
              <div className="mt-1 flex items-center gap-2">
                <code className="flex-1 break-all text-xs">{createdKey}</code>
                <button
                  type="button"
                  className="p-1.5 rounded-full hover:bg-emerald-100 dark:hover:bg-emerald-900"
                  onClick={() => {
                    void navigator.clipboard?.writeText(createdKey);
                    flash(setKeyError, "Key copied to clipboard.");
                  }}
                  aria-label="Copy key"
                >
                  <Check className="size-4" />
                </button>
              </div>
              <button
                type="button"
                className="mt-1 text-xs underline"
                onClick={() => setCreatedKey(null)}
              >
                Dismiss
              </button>
            </div>
          ) : null}
          {keyError ? (
            <div className="text-sm text-red-600 dark:text-red-400">
              {keyError}
            </div>
          ) : null}
          <div className="flex gap-2">
            <Input
              value={keyName}
              onChange={(e) => setKeyName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void createKey();
              }}
              placeholder="Key name (optional)"
            />
            <Button
              variant="default"
              disabled={!keyName.trim()}
              onClick={() => void createKey()}
            >
              <Plus className="size-4" /> Create
            </Button>
          </div>
          <div className="flex flex-col gap-2">
            {apiKeys === null ? (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Loading keys…
              </div>
            ) : apiKeys.length === 0 ? (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                No API keys yet. Keys let scripts authenticate without a
                browser session.
              </div>
            ) : (
              apiKeys.map((key) => (
                <div
                  key={key.id}
                  className="flex items-center gap-2 rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2"
                >
                  <KeyRound className="size-4 text-gray-400" />
                  <span className="flex-1 min-w-0 truncate text-sm">
                    {key.name || key.prefix}
                  </span>
                  <code className="text-xs text-gray-500 dark:text-gray-400">
                    {key.prefix}…
                  </code>
                  <button
                    type="button"
                    className="p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 text-red-600"
                    onClick={() => void removeKey(key.id)}
                    aria-label="Delete key"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </SettingsSection>
    </div>
  );
}
