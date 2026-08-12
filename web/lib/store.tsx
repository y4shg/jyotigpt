"use client";

// Global app state: session (user), public config, theme, and auth actions.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "./api";
import { getUserSettings, updateUserSettings } from "./settings";
import type { AuthResult, PublicConfig, User, UserSettings } from "./types";

export type ThemeMode = "dark" | "light";

const THEME_KEY = "theme";
const DEFAULT_THEME: ThemeMode = "dark";

interface AppState {
  /** null while the initial session/config fetch is in flight. */
  loading: boolean;
  user: User | null;
  config: PublicConfig | null;
  theme: ThemeMode;
  setTheme: (mode: ThemeMode) => void;
  /** Per-user preferences (merged over server defaults). */
  settings: UserSettings | null;
  updateSettings: (patch: Partial<UserSettings>) => Promise<UserSettings>;
  /** Settings modal open state (owned here so sidebar + navbar can open it). */
  settingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;
  signIn: (email: string, password: string, ldap?: boolean) => Promise<User>;
  signUp: (name: string, email: string, password: string) => Promise<User>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AppContext = createContext<AppState | null>(null);

function readStoredTheme(): ThemeMode {
  if (typeof window === "undefined") return DEFAULT_THEME;
  try {
    const stored = window.localStorage.getItem(THEME_KEY);
    if (stored === "light" || stored === "dark") return stored;
  } catch {
    // localStorage unavailable — fall through to default
  }
  return DEFAULT_THEME;
}

async function getUserSettingsSafe(): Promise<UserSettings | null> {
  try {
    return await getUserSettings();
  } catch {
    return null;
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [theme, setThemeState] = useState<ThemeMode>(DEFAULT_THEME);

  // Theme: default dark; persist preference and mirror it onto <html>.
  useEffect(() => {
    setThemeState(readStoredTheme());
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    try {
      window.localStorage.setItem(THEME_KEY, theme);
    } catch {
      // ignore storage failures
    }
  }, [theme]);

  const setTheme = useCallback((mode: ThemeMode) => setThemeState(mode), []);

  const saveSettings = useCallback(
    async (patch: Partial<UserSettings>) => {
      const merged = await updateUserSettings(patch);
      setSettings(merged);
      return merged;
    },
    [],
  );

  const refreshUser = useCallback(async () => {
    try {
      const { user: sessionUser } = await api.get<{ user: User }>(
        "/api/v1/auth/session",
      );
      setUser(sessionUser);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setUser(null);
      }
    }
  }, []);

  // Initial bootstrap: load session + public config + user settings in parallel.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [session, cfg, prefs] = await Promise.all([
          api.get<{ user: User }>("/api/v1/auth/session"),
          api.get<PublicConfig>("/api/v1/config"),
          getUserSettingsSafe(),
        ]);
        if (!cancelled) {
          setUser(session.user);
          setConfig(cfg);
          setSettings(prefs);
        }
      } catch {
        if (!cancelled) {
          setUser(null);
          try {
            setConfig(await api.get<PublicConfig>("/api/v1/config"));
          } catch {
            // API unreachable — stay null; auth page will surface errors.
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(
    async (email: string, password: string, ldap = false) => {
      const result = await api.post<AuthResult>("/api/v1/auth/signin", {
        email,
        password,
        ldap,
      });
      setUser(result.user);
      return result.user;
    },
    [],
  );

  const signUp = useCallback(
    async (name: string, email: string, password: string) => {
      const result = await api.post<AuthResult>("/api/v1/auth/signup", {
        name,
        email,
        password,
      });
      setUser(result.user);
      return result.user;
    },
    [],
  );

  const signOut = useCallback(async () => {
    try {
      await api.post<{ ok: boolean }>("/api/v1/auth/signout");
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo<AppState>(
    () => ({
      loading,
      user,
      config,
      theme,
      setTheme,
      settings,
      updateSettings: saveSettings,
      settingsOpen,
      setSettingsOpen,
      signIn,
      signUp,
      signOut,
      refreshUser,
    }),
    [
      loading,
      user,
      config,
      theme,
      setTheme,
      settings,
      saveSettings,
      settingsOpen,
      signIn,
      signUp,
      signOut,
      refreshUser,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
