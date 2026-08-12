// Shared API types — mirror the jyoti_api JSON surface.

export type UserRole = "admin" | "user" | "pending";
export type UserStatus = "active" | "deactivated";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  image: string | null;
  about: string | null;
  created_at: string | null;
  last_active_at: string | null;
  api_keys?: ApiKeyInfo[];
}

export interface ApiKeyInfo {
  id: string;
  name: string;
  prefix: string;
  created_at: string | null;
  key?: string; // only present on creation
}

export interface AuthResult {
  token: string;
  user: User;
}

export interface PublicConfig {
  app: { name: string; env: string };
  features: {
    image_generation: boolean;
    image_prompt_generation: boolean;
    web_search: boolean;
    rag: boolean;
    rooms: boolean;
    markdown: boolean;
    signup: boolean;
  };
  auth: {
    enable_signup: boolean;
    default_user_role: string;
    enable_ldap: boolean;
    enable_api_keys: boolean;
  };
  audio: { stt_engine: string; tts_engine: string };
  interface: Record<string, unknown>;
  image_generation: { enabled: boolean };
}

export interface Conversation {
  id: string;
  title: string;
  folder_id: string | null;
  archived: boolean;
  pinned: boolean;
  share_id: string | null;
  time_range: string; // Today / Yesterday / Previous 7 days / ... / month name
  message_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  model: string | null;
  provider: string | null;
  error: string | null;
  done: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface ChatParams {
  temperature?: number;
  top_p?: number;
  top_k?: number;
  seed?: number;
  max_tokens?: number;
  num_predict?: number;
  stop?: string[];
  presence_penalty?: number;
  frequency_penalty?: number;
  [key: string]: unknown;
}

export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  conversation_count: number;
  created_at: string | null;
}

export interface ShareResult {
  share_id: string;
  url: string;
}

export interface SharedMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string | null;
}

export interface SharedConversation {
  id: string;
  title: string;
  created_at: string | null;
  messages: SharedMessage[];
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: "ollama" | "openai" | "flow";
  owned_by: string;
  /** Flow-server pipeline id, when this entry is a pipeline model. */
  pipeline?: string;
  custom?: boolean;
  params?: Record<string, unknown>;
  ollama?: {
    size: number | null;
    parameter_size: string;
    quantization_level: string;
    family: string;
    modified_at: string | null;
  };
  info: {
    meta: {
      profile_image_url: string;
      description: string;
    };
  };
}

export interface ConversationListResult {
  page: number;
  conversations: Conversation[];
}

export interface DocumentInfo {
  id: string;
  name: string;
  meta: Record<string, unknown>;
  collection_id: string | null;
  user_id: string;
  created_at: string;
}

export interface CollectionInfo {
  id: string;
  name: string;
  description: string;
  created_at: string;
  documents: DocumentInfo[];
}

export interface PresetInfo {
  id: string;
  name: string;
  content: string;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface PluginInfo {
  id: string;
  name: string;
  type: "plugin" | "function";
  meta: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface CapabilityInfo {
  id: string;
  name: string;
  description: string;
  spec: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface Room {
  id: string;
  name: string;
  description: string;
  created_by: string;
  is_public: boolean;
  is_member: boolean;
  role: "owner" | "member" | null;
  member_count: number;
  created_at: string | null;
}

export interface RoomMember {
  user_id: string;
  name: string;
  role: "owner" | "member";
  joined_at: string | null;
}

export interface RoomMessage {
  id: string;
  room_id: string;
  user_id: string;
  name: string;
  content: string;
  created_at: string | null;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface MemoryEntry {
  id: string;
  user_id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface TagInfo {
  id: string;
  name: string;
  count?: number;
}

export interface UserSettings {
  theme: "dark" | "light";
  language: string;
  notifications: boolean;
  system_prompt: string;
  keep_alive: string;
  request_mode: string;
  landing_mode: "default" | "chat";
  chat_direction: "auto" | "ltr" | "rtl";
  widescreen: boolean;
  chat_bubble_ui: boolean;
  auto_title: boolean;
  auto_tags: boolean;
  stream_large_chunks: boolean;
  response_auto_copy: boolean;
  haptic_feedback: boolean;
  stt_engine: "default" | "browser";
  tts_engine: "default" | "browser";
  auto_playback: boolean;
  playback_speed: number;
  voice: string;
  kokoro_dtype: "q8" | "f16" | "f32";
  auto_memory: boolean;
}

export interface AboutInfo {
  version: string;
  app_name: string;
  environment: string;
  created_by: string;
  models: string;
}

export interface ExportMessage {
  role: MessageRole;
  content: string;
  model: string;
  provider: string;
  created_at: string | null;
}

export interface ExportConversation {
  title: string;
  folder_id: string | null;
  archived: boolean;
  pinned: boolean;
  created_at: string | null;
  updated_at: string | null;
  messages: ExportMessage[];
}

export interface ImportResult {
  count: number;
}

export interface EvaluationRow {
  id: string;
  user_id: string;
  type: string;
  data: Record<string, unknown>;
  created_at: string;
}

/** A feedback row as the admin sees it (feedbacks/all, export). */
export interface EvaluationFeedback {
  id: string;
  user_id: string;
  version: number;
  type: string;
  data: Record<string, unknown>;
  meta: Record<string, unknown>;
  snapshot: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
  user?: {
    id: string;
    name: string;
    email: string;
    role: UserRole;
    status: UserStatus;
  };
}

/** App-level settings groups as the admin reads them (config/settings). */
export interface AppSettings {
  app: { name: string; logo_url: string };
  interface: Record<string, unknown>;
  features: Record<string, unknown>;
  flows: { url: string; api_key: string; enabled: boolean };
  images: Record<string, unknown>;
  audio: Record<string, unknown>;
  evaluations: Record<string, unknown>;
}

// ------------------------------------------------------------------ workspace

export interface Preset {
  id: string;
  user_id: string;
  name: string;
  content: string;
  is_command: boolean;
  meta: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface Capability {
  id: string;
  user_id: string;
  name: string;
  description: string;
  /** Stored spec: a dict, a raw JSON string, or null when unset. */
  spec: Record<string, unknown> | string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/** The merged model catalog (/api/v1/models) — same shape as ModelInfo. */
export type ModelCatalogItem = ModelInfo;

export type PluginKind = "prompt" | "tool";

export interface Plugin {
  id: string;
  user_id: string;
  name: string;
  kind: PluginKind;
  description: string;
  source: string;
  prompt: string;
  is_active: boolean;
  meta: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface PluginRunResult {
  result?: Record<string, unknown>;
  error?: string;
}

export interface Document {
  id: string;
  user_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  checksum: string;
  extracted_text: string;
  meta: Record<string, unknown>;
  created_at: string | null;
}

export interface Collection {
  id: string;
  user_id: string;
  name: string;
  description: string;
  embedding_model: string;
  is_shared: boolean;
  item_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface CollectionItem {
  id: string;
  collection_id: string;
  document_id: string | null;
  chunk_index: number;
  content: string;
  source: string;
  has_embedding: boolean;
  created_at: string | null;
}

export interface SearchResult {
  id: string;
  collection_id: string;
  chunk_index: number;
  content: string;
  source: string;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
}

export interface ModelRecord {
  id: string;
  provider: "ollama" | "openai";
  model_id: string;
  name: string;
  enabled: boolean;
  params: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}
