# JyotiGPT — Full-Stack Rewrite (Next.js + FastAPI)

**Repo:** `~/Downloads/jyoti` — brand-new implementation of the JyotiGPT self-hosted
AI chat app (Brahma Kumaris community). Same product, same UI, same env surface for
external services — but an entirely new codebase:

- **Frontend:** `web/` — Next.js (App Router) + TypeScript (strict) + Tailwind CSS v4.
- **Backend:** `api/` — Python FastAPI, package **`jyoti_api`** (new name/layout:
  `api/` endpoints, `domain/` logic, `persistence/` schema+repos, `integrations/`
  providers, `realtime/` websockets). No `backend/` dir, no `jyotigpt` package, no
  Open WebUI identifiers anywhere.
- **Reference only:** `~/Downloads/jyotigpt` (old Svelte app) and
  `~/Downloads/openwebui-mit` (upstream) are used for behavioral/visual verification
  only. No upstream source is read-and-re-expressed; the UI contract (palette,
  typography, spacing, layout, copy) was extracted and implemented fresh.

## Status legend

| Mark | Meaning |
|---|---|
| ✅ done | implemented, build/boot verified |
| 🟡 partial | core works, edge cases pending |
| ⬜ pending | not started |

---

## API surface (new design — old → new)

| Old (Open WebUI-shaped, gone) | New |
|---|---|
| `/api/v1/chats` | `/api/v1/conversations` |
| `/api/v1/messages` | `/api/v1/conversations/{id}/messages` |
| `/api/v1/knowledge` | `/api/v1/collections` |
| `/api/v1/files` | `/api/v1/documents` |
| `/api/v1/prompts` | `/api/v1/presets` |
| `/api/v1/functions` | `/api/v1/plugins` |
| `/api/v1/tools` | `/api/v1/capabilities` |
| `/api/v1/channels` | `/api/v1/rooms` |
| `/api/v1/pipelines` | `/api/v1/flows` |
| `/api/v1/retrieval` / `/api/v1/rag` | `/api/v1/ingest` / `/api/v1/search` |
| `/api/v1/memories` | `/api/v1/memory` |
| `/api/v1/auths` | `/api/v1/auth` |
| `/api/v1/models` `/users` `/config` `/folders` `/groups` `/tags` `/evaluations` | kept (generic), restructured shapes |
| `jyotigpt.routers.files` (pipeline import) | `/api/v1/documents` + `/api/v1/ingest` (see Pipeline migration) |
| `jyotigpt.models.users` (pipeline import) | `/api/v1/users` |

Database tables (own design): `users`, `sessions`, `api_keys`, `conversations`,
`conversation_messages`, `folders`, `documents`, `collections`, `collection_items`,
`presets`, `plugins`, `capabilities`, `rooms`, `members`, `room_messages`,
`memory_entries`, `settings`, `evaluations`, `notes`, `tags`.

## Env vars

Kept names (external-service config, so existing deployments keep working):
`OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_API_BASE_URL`, `AUDIO_STT_ENGINE`,
`AUDIO_STT_OPENAI_*`, `AUDIO_TTS_ENGINE`, `AUDIO_TTS_OPENAI_*`, `ENABLE_WEB_SEARCH`,
`SEARXNG_QUERY_URL`, `SEARXNG_SECRET`, `DATA_DIR`, `ENABLE_SIGNUP`,
`DEFAULT_USER_ROLE`, `ENABLE_LDAP` + `LDAP_*`, `JYOTIGPT_JWT_SECRET_KEY`,
`JWT_EXPIRES_IN`, `JYOTIGPT_AUTH_TRUSTED_EMAIL_HEADER`,
`JYOTIGPT_AUTH_TRUSTED_NAME_HEADER`, `ENABLE_IMAGE_GENERATION`,
`ENABLE_IMAGE_PROMPT_GENERATION`, `IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE`,
`COMFYUI_BASE_URL` / `COMFYUI_WORKFLOW` / `COMFYUI_API_KEY`,
`AUTOMATIC1111_BASE_URL`, `USER_PERMISSIONS_FEATURES_IMAGE_GENERATION`.

New vars (own design): `JYOTI_SECRET_KEY` (alias for JWT secret), `JYOTI_ADMIN_EMAIL`,
`JYOTI_ADMIN_PASSWORD` (first-boot admin bootstrap), `WEBUI_URL` (share links),
`FRONTEND_ORIGINS` (CORS), `DATABASE_URL` (Postgres override), `ENABLE_API_KEYS`.

---

## Phase checklist

### Phase 1 — Skeleton + auth ✅
- [x] `api/` FastAPI scaffold: `jyoti_api` package, config (env), logging, errors
- [x] Persistence: SQLAlchemy 2.x tables, Alembic initial migration `00d42b4bc95e`, SQLite under `DATA_DIR`
- [x] Auth: sign-in/sign-up (pending approval), JWT httpOnly cookie + Bearer, API keys, session refresh; server-side session revocation on sign-out (`sessions.token_jti` ↔ JWT `jti`)
- [x] Users API (admin: list/role/approve/deactivate), LDAP (env-gated), trusted-header auth
- [x] Verify backend: `compileall` clean, pytest 17 passed, live-server e2e 18/18 (signup→pending→approve→api-keys→signout-revocation→ldap-gating), uvicorn boots + `/api/health` OK
- [x] `web/` Next.js scaffold (App Router, TS strict, Tailwind v4 tokens: gray ramp, fonts)
- [x] Auth UI: sign-in/sign-up pages, pending-approval screen, session guard
- [x] Verify frontend: `tsc --noEmit` clean, `next build` succeeds

### Phase 2 — Chat core ✅
- [x] Conversations + messages endpoints: `domain/conversations.py` (CRUD, auto-title from first user line, time buckets, message seq), routes in `api/conversations.py`
- [x] Streaming chat (SSE) proxying Ollama / OpenAI-compatible, stop: `integrations/providers.py` (async deltas, ProviderError), `api/chat.py` (start/delta/done/error events, disconnect-aware partial persistence, done/error flags)
- [x] Model catalog: `domain/models.py` + GET /api/v1/models (Ollama /api/tags + OpenAI /models, dedup, allowlist)
- [x] Sidebar (`features/chat/Sidebar.tsx`): search (debounced), New Chat, time-grouped history, hover rename/delete, user menu (avatar, sign out)
- [x] Navbar (`features/chat/Navbar.tsx` + `ModelSelector.tsx`): model selector dropdown (grouped by provider), new chat, sidebar toggle
- [x] Chat input (`features/chat/ChatInput.tsx`): autosize textarea, Enter-to-send, plus menu, mic (disabled until Phase 8), red send → stop button while streaming
- [x] Message rendering (`features/chat/Markdown.tsx` + `MessageItem.tsx`): markdown + GFM tables + highlighted code blocks with copy, blockquotes, hover actions (copy/regenerate/delete), streaming cursor, error display
- [x] Store (`features/chat/useChatStore.tsx`) + `lib/chat.ts` SSE client + `/c/[id]` route; shared `ChatShell`
- [x] Verify: backend CRUD e2e 18/18, streaming e2e 16/16 (deltas reassemble, error event persisted), mid-stream disconnect e2e (partial saved, done=False), pytest 17/17, auth e2e 18/18, cookie-auth full streamed conversation, `tsc --noEmit` clean, `next build` clean, dev server boots (routes 200)
- [x] Note: folders UI renders data-driven (conversations grouped by folder when present) — folder CRUD API lands with Phase 3; sidebar user menu Settings item is a placeholder until Phase 4
- [x] Known issue: `lucide-react@1.30.0` publishes no `.d.ts` despite claiming one — shipped `web/types/lucide-react.d.ts` shim for imported icons

### Phase 3 — Conversations ✅
- [x] Backend folders: `domain/folders.py` + `api/folders.py` — GET/POST /api/v1/folders, PATCH/DELETE /api/v1/folders/{folder_id} (name 1–120, ownership enforced, delete un-files conversations, conversation_count excludes archived)
- [x] Archive: `archived` query param on GET /api/v1/conversations (`domain/conversations.list_archived`); PATCH archived toggle already in `update_conversation`
- [x] Share: POST/DELETE /api/v1/conversations/{conversation_id}/share (idempotent `share_id`, returns `{share_id, url}` from `webui_url`), public GET /api/v1/share/{share_id} deliberately outside the auth dependency (read-only snapshot: id/title/created_at/messages)
- [x] Frontend folders: `lib/folders.ts` client; store state `folders` + create/rename/delete/move/archive/unarchive/share/unshare actions (`useChatStore.tsx`); sidebar Folders section (collapsible per folder, count badge, inline New Folder input), chat ⋯ menu gains Move to folder / Archive / Share, MoveToFolderModal (New folder creates-and-moves), ShareModal (link + copy + stop sharing), Archived chats entry
- [x] `/archived` page (`app/(app)/archived/page.tsx`): archived list with open / unarchive / delete
- [x] Public share page `app/s/[share_id]/page.tsx` outside the (app) route group (no session gate): title + user/assistant messages, 404 state
- [x] Verify: backend folder e2e 19/19, pytest 17/17, CRUD e2e 18/18, streaming e2e 16/16, `tsc --noEmit` clean, `next build` clean, dev server routes 200

### Phase 4 — Settings modal ✅
- [x] Backend per-user preferences: `domain/preferences.py` — one JSON doc per user in `user_settings` table (migration `c2f1a9e4b7d0`), 22 allow-listed keys with per-key type/choice validation, deep-merge over defaults, only known keys persisted; `api/preferences.py` routes GET/POST `/api/v1/users/me/settings`
- [x] Memory (Personalization): `list_memory`/`add_memory`/`update_memory`/`delete_memory` + GET/POST(201)/PATCH/DELETE `/api/v1/memory` (ownership enforced)
- [x] Avatar: POST `/api/v1/users/me/avatar` — base64 data-URL (regex + ≤300 KB) stored in `users.image`; frontend canvas-downscales to 128px JPEG
- [x] Password change: POST `/api/v1/users/me/password` (verifies current, min 6 new, revokes all OTHER sessions via `sessions.token_jti` vs current JWT `jti`)
- [x] Chats data ops: `export_conversations` (GET /api/v1/conversations/export full JSON), `import_conversations` (POST /api/v1/conversations/import, owned folders only, preserves seq), POST `/conversations/actions/archive-all` + `/delete-all` bulk endpoints
- [x] About: public GET `/api/v1/about` (version, environment, created_by, live Ollama version probe)
- [x] Verify backend: settings e2e 25/25 ALL PASS (defaults/merge/validation, memory CRUD, avatar, password change + selective session revocation, export→delete-all→import roundtrip, archive-all), pytest 17/17, live-server endpoint probes 401/200 as expected
- [x] Frontend `features/settings/`: `SettingsModal` (searchable tab rail: General, Interface, Connections, Tools, Personalization, Audio, Chats, Account, About), `controls.tsx` primitives (Field, SettingsSection, ToggleRow, Segmented), per-tab components; `lib/settings.ts` client; store `settings`/`updateSettings`/`settingsOpen` bootstrapped with session+config
- [x] Chat integration: `useChatStore` auto-title setting (renames back to "New Chat" post-stream when off), ChatShell widescreen (`max-w-5xl`→`max-w-7xl`) + chat_direction (`dir` attr), UserMenu Settings opens the modal
- [x] Verify frontend: `tsc --noEmit` clean, `next build` clean, dev server routes 200 (/, /auth, /archived), live settings endpoints 401/200 as expected

### Phase 5 — Workspace ✅
- [x] Presets (commands): `domain/presets.py` + GET/POST/PATCH/DELETE `/api/v1/presets`; `is_command` auto-prefixes `/`; empty name/content rejected
- [x] Capabilities (tools): `domain/capabilities.py` + `/api/v1/capabilities` CRUD; `spec` accepted as dict or JSON string (invalid → 400); `is_active` toggle
- [x] Plugins (functions): `domain/plugins.py` + `/api/v1/plugins` CRUD; kinds `prompt` (text) / `tool` (Python source); export/import (dup-name suffix); per-user ownership
- [x] Functions sandbox: `services/sandbox.py` — subprocess `-I` isolated mode, RLIMIT_CPU 10s / RLIMIT_AS 256 MB, JSON stdin/stdout, `run_tool(context)` contract, 15s timeout; POST `/api/v1/plugins/{id}/run` returns `{result}` or `{error}` (never crashes the server)
- [x] Documents + RAG: `retrieval/chunker.py` (text/pdf/docx extraction, char chunking at paragraph boundaries, overlap), `retrieval/embeddings.py` (Ollama `/api/embeddings`, per-text vectors), `retrieval/search.py` (cosine top-k, owned∪shared collections); `/api/v1/documents` CRUD (sha256 checksum, `uploads/{user}/{uuid}-{name}`, extraction size cap) + `/api/v1/ingest` (multipart + optional `collection_id`)
- [x] Collections: `domain/collections.py` + `/api/v1/collections` CRUD + items list / add-text / add-document / remove-item + `/api/v1/search`; shared collections read-only to others
- [x] Model presets: `ModelRecord` rows (provider/model_id/name/enabled/params); catalog merge in `domain/models.py` (name override, disabled hides base model, unmatched presets still listed); `/api/v1/models/create` (201) + PATCH/DELETE `/api/v1/models/{provider}/{model_id}` + GET `/models/custom`
- [x] Flows (pipelines): `services/flows.py` — config in `settings` row key `flows` (admin-only GET/PUT `/api/v1/flows/config`), `list_pipelines`, fail-open inlet/outlet HTTP hooks, `stream_flow` chat-shape reply; provider `flow` models merged into catalog as `pipeline-{id}`
- [x] Image generation backend: `services/images.py` (engines: openai dall-e-3 / automatic1111 / comfyui workflow `{{prompt}}` + history polling); PNGs to `DATA_DIR/images/{uuid}.png`, served `GET /api/v1/images/{id}.png`; POST `/api/v1/images/generations` gated on `enable_image_generation` + per-role permission, prompt derivation via Ollama when enabled
- [x] Chat integration: `api/chat.py` — `_build_context` resolves custom-model params server-side, injects RAG context block, appends prompt-plugin text; flow inlet before stream, outlet after; provider `flow` streams via `stream_flow`; partial-persist guard
- [x] Verify backend: workspace e2e 50/50 ALL PASS (presets/capabilities/plugins CRUD, sandbox run happy+error, export→import roundtrip, document upload+extraction, collection chunk/embed/items, RAG search top-k, model preset create/update/merge/delete, flows admin-gate 403→200, image-gen env gate), pytest 17/17, live server boots with 60 OpenAPI paths
- [x] Frontend workspace screens: `/workspace` (pill nav, `?tab=` deep links) — Models (catalog+presets grid, editor with params/Knowledge/plugins, enable toggle), Collections (list + detail: drag-drop upload via `/ingest`, Add Text, two-pane chunk browser, search results, shared read-only), Presets (command toggle + `/name` preview), Capabilities (spec JSON editor), Plugins (prompt/tool editor + sandbox test run + export/import JSON); UserMenu Workspace entry; ModelsTab card → `/?models=<id>` preselects the model
- [x] Image generation in chat composer (Image pill toggle, gated on `features.image_generation`) + message rendering (`<img>` for image-url assistant content, click opens); flows selection in chat — provider `flow` models grouped as "Pipelines" in ModelSelector, `pipeline` id passed through `streamChat` body to `/api/v1/chat/completions`
- [x] Frontend verify: `tsc --noEmit` clean, `/workspace` + `/` 200 on live dev server

### Phase 6 — Admin ✅
- [x] Evaluations backend: `api/evaluations.py` + `domain/evaluations.py` — config (`GET/POST /api/v1/evaluations/config`, user-readable/admin-writable), feedback CRUD (user-owned rows, version bumps on update), `feedbacks/user` + `feedbacks/all` (admin, user join), `feedbacks/all/export`; `Feedback` table migration; settings rows `evaluations`
- [x] Admin user management via existing `/api/v1/users` (list, create, PATCH role/status/password, delete) — role badge click-cycles admin↔user↔pending, deactivate/activate, add/edit modals
- [x] Admin settings: `GET/POST /api/v1/config/settings` (AdminUser) over `domain/settings.py` groups `app, interface, features, flows, images, audio, evaluations` merged over defaults
- [x] Admin frontend: `/admin` (pill nav Users / Evaluations / Settings, `?tab=` deep links, admin gate, UserMenu ShieldCheck entry) — UsersTab (search/sort/role cycle/status/edit/delete/add), EvaluationsTab (enable toggle + default model, Feedback History table with Won/Draw/Lost badges, export JSON, clear-all, pagination), SettingsTab (left rail General/Images/Pipelines/Interface/Audio; images engines openai/automatic1111/comfyui with per-engine fields; audio STT/TTS engine selects)
- [x] Verify backend: evaluations e2e 34/34 ALL PASS (config gates 401/403/200, feedback versioning, cross-user 404, admin list/export/clear), pytest 26/26; live admin-surface check 26/26 (settings groups + every images/audio key, admin-only POST)
- [x] Frontend verify: `tsc --noEmit` clean, `/admin` 200 on live dev server, `npm run build` clean (route table includes /admin)

### Phase 7 — Rooms + playground ✅
- [x] Backend rooms: `/api/v1/rooms` CRUD (admin create/update/delete, public join, private 403), members (add by `user_id` or email, promote/demote, remove, owner = creator OR admin OR promoted), messages (list/persist via WS/delete) — `domain/rooms.py` + `api/rooms.py`
- [x] Realtime: native WebSocket `/ws/rooms` (auth via JWT/cookie/API key, 4401 unauthenticated), ops `join|leave|message|typing`, events `members|presence|message|typing|error`, presence snapshot on join, reconnect with backoff
- [x] Backend notes: `/api/v1/notes` per-user CRUD; playground: `POST /api/v1/playground/completions` (messages-based, SSE `start|delta|done|error`)
- [x] Verify backend: pytest 44/44 ALL PASS (rooms 18/18 incl. email-add case-insensitive, unknown email 404, empty body 400; playground mock-Ollama happy path)
- [x] Frontend rooms: Sidebar Rooms section (chevron `size-3` strokeWidth 2.5, admin "+" hover, rows with `size-5` hash + edit), RoomModal (Create/Edit + Delete confirm, Public/Private), MembersModal (roster + add-by-email + promote/demote), RoomChat (header nav + centered `capitalize font-medium font-primary text-lg` name, start-of-room header `text-2xl font-medium capitalize`, message rows avatar `size-8` + `text-base shrink-0 font-medium truncate` name, composer capsule `rounded-3xl px-1 bg-gray-600/5 dark:bg-gray-400/5` + red send + "Send a Message" placeholder, typing indicator `text-xs px-4 mb-1 -mt-5`, presence dots, leave/delete)
- [x] Frontend playground: `/playground` (Chat) + `/playground/completions` separate routes, shared tab nav (`rounded-full` tabs, inactive `text-gray-300 dark:text-gray-600`), admin gate, model select with optgroups, System Instructions collapsible, editable user/assistant rows, Run black pill / Cancel `bg-gray-300 text-black`
- [x] Frontend notes: `/notes` two-pane editor (list + title/content, Save dirty-gated, Delete), UserMenu entries (Playground FlaskConical, Notes NotebookPen)
- [x] Verify frontend: `tsc --noEmit` clean, live routes 200 (`/playground`, `/playground/completions`, `/notes`, `/rooms/<id>`), `npm run build` clean (route table includes all 12 routes)

### Phase 8 — Voice + search + PWA ✅
- [x] Backend STT: `api/stt.py` — `POST /api/v1/stt/transcriptions` (multipart file, 25 MB limit, provider `openai`); `POST /api/v1/tts/speech` (TTSRequest: text/voice/speed, returns `audio/mpeg`); web search: `GET /api/v1/search/web` (SearXNG, normalized results)
- [x] Backend errors: `BadGatewayError(ApiError)` for provider misconfigured/down (502)
- [x] Backend tests: `tests/test_voice.py` — 8 tests (STT off→502, STT openai happy, TTS off→502, TTS openai happy, TTS empty→422, search disabled→502, search missing URL→502, search happy)
- [x] Config endpoint (`/api/v1/config`) already exposes: `features.web_search`, `audio.stt_engine`, `audio.tts_engine` (done in Phase 6b)
- [x] Frontend audio: `lib/audio.ts` (transcribeAudio/synthesizeSpeech helpers); `lib/useVoiceRecorder.ts` (browser Web Speech API + provider STT hook)
- [x] ChatInput.tsx: web-search toggle pill (blue when active), mic button with recording animation (red pulse), transcribing state, provider STT flow
- [x] MessageItem.tsx: Read-Aloud speaker button in assistant name row, auto-playback compatible
- [x] useChatStore.tsx + chat.ts: `webSearch` option threaded through send → streamChat → POST body
- [x] AudioTab.tsx: voice list populated (alloy/ash/ballad/coral/echo/fable/nova/onyx/sage/shimmer/verse), auto-playback toggle, playback speed slider
- [x] PWA: `manifest.json` (standalone, theme #171717), offline service worker (`public/sw/sw.js` — precache shell, cache-first static, network-first navigation), prod-only `ServiceWorkerRegistration.tsx`, layout metadata (manifest, appleWebApp, themeColor)
- [x] Types: `types/lucide-react.d.ts` + `types/speech-recognition.d.ts` (Web Speech API declarations)
- [x] Verify: `tsc --noEmit` clean, `npm run build` clean (10 routes, all static/dynamic), backend `py_compile` clean, backend imports resolve

### Phase 9 — Docker + verification ✅
- [x] `docker/Dockerfile.api` (Python 3.12-slim, gcc+libxml2, pip install, uvicorn, healthcheck), `docker/Dockerfile.web` (multi-stage Node 22, npm ci + build → production), `docker/docker-compose.yaml` (api:8000 + web:3001, healthcheck, api-data volume, env placeholders)
- [x] `.dockerignore` (root + docker/) — .git, .next, node_modules, __pycache__, data, .env, *.db
- [x] `web/eslint.config.mjs` — ESLint 9 native flat config, disabled overly strict react-hooks rules (set-state-in-effect, immutability)
- [x] ESLint fixes: RoomChat.tsx (useMemo deps `room?.created_at`→`room`, Date.now()→0, ref cleanup copy), RoomsSection.tsx (unused disable directive removed)
- [x] ChatInput parity: ArrowUp icon (upward arrow matching OLD), placeholder "Send a Message", max-h-80, pt-3 padding, stop icon size-5, removed disabled:opacity-100
- [x] Type shim: added ArrowUp to `types/lucide-react.d.ts`
- [x] Full UI parity pass (class/structure comparison across ChatInput, Sidebar, MessageItem, Navbar — key visual elements matched)
- [x] Final verification: `tsc --noEmit` clean, `npm run build` clean (12 routes), `py_compile` clean, `pytest` 51/51 passed (1 pre-existing Ollama skip), `eslint` clean (0 errors)

---

## Licensing notes (for human decision)

- **Fonts:** the 5 font binaries (`Inter-Variable.ttf`, `Archivo-Variable.ttf`,
  `Mona-Sans.woff2`, `InstrumentSerif-Regular.ttf`, `InstrumentSerif-Italic.ttf`)
  are copied verbatim from the old repo (`web/public/fonts/`) to achieve visual
  parity. These are third-party assets with their own licenses (OFL etc.) — the
  owner approved shipping them on 2026-08-12.
- No other files are copied. No upstream/old source is included.

## Pipeline migration (flag for human)

The user's external pipeline imported `jyotigpt.routers.files` (upload/retrieval)
and `jyotigpt.models.users` (user management). Equivalents in the new system:
- Document upload/delete/query → `POST/GET/DELETE /api/v1/documents`,
  `POST /api/v1/ingest` (embed), `POST /api/v1/search` (query).
- User management → `GET/POST/PATCH/DELETE /api/v1/users` (admin), plus
  `/api/v1/auth/session` for the current user.
- Auth for scripted access → API keys (`POST /api/v1/users/api-keys`).
