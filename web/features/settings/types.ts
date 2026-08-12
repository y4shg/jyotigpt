import type { UserSettings } from "@/lib/types";

export interface SettingsTabProps {
  settings: UserSettings;
  onChange: <K extends keyof UserSettings>(
    key: K,
    value: UserSettings[K],
  ) => void;
}
