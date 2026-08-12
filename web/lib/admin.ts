// Admin domain client: user management, app-level settings, evaluations.

import { api } from "./api";
import type { AppSettings, EvaluationFeedback, User } from "./types";

// ------------------------------------------------------------------ users

export const listUsers = () => api.get<User[]>("/api/v1/users");

export const createUser = (body: {
  name: string;
  email: string;
  password: string;
  role: "admin" | "user" | "pending";
}) => api.post<User>("/api/v1/users", body);

export const updateUser = (
  id: string,
  patch: Partial<Pick<User, "name" | "email" | "role" | "status">> & {
    password?: string;
  },
) => api.patch<User>(`/api/v1/users/${id}`, patch);

export const deleteUser = (id: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/users/${id}`);

// ---------------------------------------------------------------- settings

export const getAppSettings = () => api.get<AppSettings>("/api/v1/config/settings");

export const setAppSetting = (key: string, value: Record<string, unknown>) =>
  api.post<{ ok: boolean }>("/api/v1/config/settings", { key, value });

// ------------------------------------------------------------- evaluations

export interface EvalConfig {
  enable_evaluations: boolean;
  model: string;
}

export const getEvalConfig = () => api.get<EvalConfig>("/api/v1/evaluations/config");

export const setEvalConfig = (config: EvalConfig) =>
  api.post<{ ok: boolean }>("/api/v1/evaluations/config", config);

export const listAllFeedbacks = () =>
  api.get<EvaluationFeedback[]>("/api/v1/evaluations/feedbacks/all");

export const deleteFeedback = (id: string) =>
  api.delete<{ ok: boolean }>(`/api/v1/evaluations/feedback/${id}`);

export const deleteAllFeedbacks = () =>
  api.delete<{ ok: boolean }>("/api/v1/evaluations/feedbacks/all");

export const exportFeedbacks = () =>
  api.get<EvaluationFeedback[]>("/api/v1/evaluations/feedbacks/all/export");
