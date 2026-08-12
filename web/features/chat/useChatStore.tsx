"use client";

// Chat store — conversations, model catalog, the active conversation's
// messages, and the streaming send/stop lifecycle. Lives at the app-shell
// level so the sidebar and the chat page stay in sync.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  addMessage,
  createConversation,
  deleteConversation,
  deleteMessage,
  getConversation,
  listConversations,
  listModels,
  streamChat,
  updateConversation,
} from "@/lib/chat";
import {
  createFolder as apiCreateFolder,
  deleteFolder as apiDeleteFolder,
  listFolders,
  renameFolder as apiRenameFolder,
  shareConversation,
  unshareConversation,
} from "@/lib/folders";
import { generateImage } from "@/lib/images";
import { useApp } from "@/lib/store";
import type {
  Conversation,
  Folder,
  Message,
  ModelInfo,
  ShareResult,
} from "@/lib/types";

export const DEFAULT_MODEL = "";

interface ChatState {
  // catalog + history
  models: ModelInfo[];
  conversations: Conversation[];
  folders: Folder[];
  archived: Conversation[];
  loadingArchived: boolean;
  // active conversation
  activeId: string | null;
  conversation: Conversation | null;
  messages: Message[];
  loadingConversation: boolean;
  // composer / stream state
  modelId: string;
  provider: "ollama" | "openai" | "flow";
  streaming: boolean;
  // shell
  showSidebar: boolean;
  search: string;

  setSearch: (value: string) => void;
  setModelId: (id: string) => void;
  toggleSidebar: () => void;
  refreshModels: () => Promise<void>;

  openConversation: (id: string) => Promise<void>;
  createAndOpen: (title?: string) => Promise<Conversation | null>;
  renameConversation: (id: string, title: string) => Promise<void>;
  removeConversation: (id: string) => Promise<void>;
  removeMessage: (id: string) => Promise<void>;

  refreshConversations: (term?: string) => Promise<void>;
  refreshFolders: () => Promise<void>;
  createFolder: (name: string) => Promise<Folder | null>;
  renameFolder: (id: string, name: string) => Promise<void>;
  removeFolder: (id: string) => Promise<void>;
  moveToFolder: (conversationId: string, folderId: string | null) => Promise<void>;
  setArchived: (conversationId: string, archived: boolean) => Promise<void>;
  refreshArchived: () => Promise<void>;
  share: (conversationId: string) => Promise<ShareResult | null>;
  unshare: (conversationId: string) => Promise<void>;

  /** Send a user turn and stream the assistant reply. */
  send: (
    content: string,
    options?: { onNavigate?: (id: string) => void; imageMode?: boolean; webSearch?: boolean },
  ) => Promise<void>;
  stop: () => void;
}

const ChatContext = createContext<ChatState | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const { settings: appSettings } = useApp();
  const [autoTitle, setAutoTitle] = useState(true);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [archived, setArchivedList] = useState<Conversation[]>([]);
  const [loadingArchived, setLoadingArchived] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [modelId, setModelId] = useState<string>(DEFAULT_MODEL);
  const [streaming, setStreaming] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [search, setSearch] = useState("");

  const abortRef = useRef<AbortController | null>(null);
  // the assistant message currently being streamed
  const streamMessageRef = useRef<Message | null>(null);

  // User preference: keep "New Chat" as the title when auto-title is off.
  useEffect(() => {
    setAutoTitle(appSettings?.auto_title ?? true);
  }, [appSettings?.auto_title]);

  const refreshConversations = useCallback(async (term = "") => {
    try {
      const result = await listConversations(term);
      setConversations(result.conversations);
    } catch {
      // keep the current list on failure
    }
  }, []);

  // ---------------------------------------------------------------- folders

  const refreshFolders = useCallback(async () => {
    try {
      setFolders(await listFolders());
    } catch {
      // catalog unreachable — keep the current list
    }
  }, []);

  const createFolder = useCallback(async (name: string) => {
    try {
      const folder = await apiCreateFolder(name);
      setFolders((list) => [...list, folder]);
      return folder;
    } catch {
      return null;
    }
  }, []);

  const renameFolder = useCallback(async (id: string, name: string) => {
    try {
      const updated = await apiRenameFolder(id, name);
      setFolders((list) => list.map((f) => (f.id === id ? updated : f)));
    } catch {
      // rename failed — leave as-is
    }
  }, []);

  const removeFolder = useCallback(async (id: string) => {
    try {
      await apiDeleteFolder(id);
    } catch {
      // optimistic removal below regardless
    }
    setFolders((list) => list.filter((f) => f.id !== id));
    // the server un-files the folder's conversations — mirror that locally
    setConversations((list) =>
      list.map((c) => (c.folder_id === id ? { ...c, folder_id: null } : c)),
    );
  }, []);

  const moveToFolder = useCallback(
    async (conversationId: string, folderId: string | null) => {
      try {
        const updated = await updateConversation(conversationId, {
          folder_id: folderId,
        });
        setConversations((list) =>
          list.map((c) => (c.id === conversationId ? updated : c)),
        );
        setArchivedList((list) =>
          list.map((c) => (c.id === conversationId ? updated : c)),
        );
        if (conversation?.id === conversationId) setConversation(updated);
        refreshFolders();
      } catch {
        // move failed — leave as-is
      }
    },
    [conversation, refreshFolders],
  );

  const setArchived = useCallback(
    async (conversationId: string, archived: boolean) => {
      try {
        const updated = await updateConversation(conversationId, { archived });
        if (archived) {
          setConversations((list) => list.filter((c) => c.id !== conversationId));
          setArchivedList((list) =>
            list.some((c) => c.id === conversationId)
              ? list.map((c) => (c.id === conversationId ? updated : c))
              : list,
          );
        } else {
          // returning from archive — drop from the archived list, refresh main
          setArchivedList((list) => list.filter((c) => c.id !== conversationId));
          refreshConversations(search);
        }
        if (conversation?.id === conversationId) setConversation(updated);
        refreshFolders();
      } catch {
        // leave as-is
      }
    },
    [conversation, refreshConversations, refreshFolders, search],
  );

  const refreshArchived = useCallback(async () => {
    setLoadingArchived(true);
    try {
      const result = await listConversations("", 1, undefined, true);
      setArchivedList(result.conversations);
    } catch {
      // keep the current list
    } finally {
      setLoadingArchived(false);
    }
  }, []);

  // ------------------------------------------------------------------ share

  const share = useCallback(
    async (conversationId: string) => {
      try {
        const result = await shareConversation(conversationId);
        const patch = { share_id: result.share_id };
        setConversations((list) =>
          list.map((c) => (c.id === conversationId ? { ...c, ...patch } : c)),
        );
        setArchivedList((list) =>
          list.map((c) => (c.id === conversationId ? { ...c, ...patch } : c)),
        );
        if (conversation?.id === conversationId) {
          setConversation({ ...conversation, ...patch });
        }
        return result;
      } catch {
        return null;
      }
    },
    [conversation],
  );

  const unshare = useCallback(
    async (conversationId: string) => {
      try {
        await unshareConversation(conversationId);
      } catch {
        // optimistic update below regardless
      }
      const patch = { share_id: null };
      setConversations((list) =>
        list.map((c) => (c.id === conversationId ? { ...c, ...patch } : c)),
      );
      setArchivedList((list) =>
        list.map((c) => (c.id === conversationId ? { ...c, ...patch } : c)),
      );
      if (conversation?.id === conversationId) {
        setConversation({ ...conversation, ...patch });
      }
    },
    [conversation],
  );

  // Debounced sidebar search.
  useEffect(() => {
    const timer = setTimeout(() => refreshConversations(search), 300);
    return () => clearTimeout(timer);
  }, [search, refreshConversations]);

  useEffect(() => {
    refreshConversations();
    refreshFolders();
    listModels()
      .then((list) => {
        setModels(list);
        if (list.length) setModelId((current) => current || list[0].id);
      })
      .catch(() => {
        // catalog unreachable — DEFAULT_MODEL stays selected
      });
  }, [refreshConversations, refreshFolders]);

  const provider = useMemo<"ollama" | "openai" | "flow">(() => {
    const model = models.find((m) => m.id === modelId);
    if (model?.provider === "openai") return "openai";
    if (model?.provider === "flow") return "flow";
    return "ollama";
  }, [models, modelId]);

  const openConversation = useCallback(async (id: string) => {
    setLoadingConversation(true);
    setActiveId(id);
    try {
      const detail = await getConversation(id);
      setConversation({ ...detail } as Conversation);
      setMessages(detail.messages);
    } catch {
      // 404 or lost — fall back to an empty chat
      setConversation(null);
      setMessages([]);
    } finally {
      setLoadingConversation(false);
    }
  }, []);

  const createAndOpen = useCallback(async (title = "New Chat") => {
    try {
      const conv = await createConversation(title);
      setConversations((list) => [conv, ...list]);
      setActiveId(conv.id);
      setConversation(conv);
      setMessages([]);
      return conv;
    } catch {
      return null;
    }
  }, []);

  const renameConversation = useCallback(
    async (id: string, title: string) => {
      try {
        const updated = await updateConversation(id, { title });
        setConversations((list) => list.map((c) => (c.id === id ? updated : c)));
        if (conversation?.id === id) setConversation(updated);
      } catch {
        // rename failed — leave as-is
      }
    },
    [conversation],
  );

  const removeConversation = useCallback(
    async (id: string) => {
      try {
        await deleteConversation(id);
      } catch {
        // ignore — optimistic removal below
      }
      setConversations((list) => list.filter((c) => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setConversation(null);
        setMessages([]);
      }
    },
    [activeId],
  );

  const removeMessage = useCallback(
    async (id: string) => {
      if (streaming) return;
      try {
        await deleteMessage(id);
      } catch {
        // optimistic removal below regardless
      }
      setMessages((list) => list.filter((m) => m.id !== id));
      refreshConversations(search);
    },
    [streaming, refreshConversations, search],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const send = useCallback(
    async (
      content: string,
      options?: { onNavigate?: (id: string) => void; imageMode?: boolean; webSearch?: boolean },
    ) => {
      const text = content.trim();
      if (!text || streaming) return;

      // 1. ensure a conversation exists
      let cid = activeId;
      let createdHere = false;
      if (!cid) {
        const conv = await createAndOpen();
        if (!conv) return;
        cid = conv.id;
        createdHere = true;
        options?.onNavigate?.(conv.id);
      }

      // 2. persist the user message
      let userMessage: Message;
      try {
        userMessage = await addMessage(cid, "user", text, modelId, provider);
      } catch {
        return;
      }
      setMessages((list) => [...list, userMessage]);
      setStreaming(true);

      // 2b. image mode: generate through /images/generations and store the
      // result as an assistant message whose content is the image URL.
      if (options?.imageMode) {
        try {
          const response = await generateImage({ text, model: modelId });
          const image = response.images[0];
          if (image) {
            const assistantMessage = await addMessage(
              cid,
              "assistant",
              image.url,
              modelId,
              provider,
            );
            setMessages((list) => [...list, assistantMessage]);
          }
        } catch {
          const failed: Message = {
            id: "pending-image",
            conversation_id: cid,
            role: "assistant",
            content: "",
            model: modelId,
            provider,
            error: "Image generation failed.",
            done: true,
            created_at: null,
            updated_at: null,
          };
          setMessages((list) => [...list, failed]);
        } finally {
          setStreaming(false);
          abortRef.current = null;
          refreshConversations(search);
          if (createdHere && !autoTitle) {
            void renameConversation(cid, "New Chat");
          }
        }
        return;
      }

      // 3. assistant placeholder + streaming lifecycle
      const placeholder: Message = {
        id: "pending",
        conversation_id: cid,
        role: "assistant",
        content: "",
        model: modelId,
        provider,
        error: null,
        done: false,
        created_at: null,
        updated_at: null,
      };
      streamMessageRef.current = placeholder;
      setMessages((list) => [...list, placeholder]);

      const controller = new AbortController();
      abortRef.current = controller;

      // Replace the placeholder (or the live message) by the id it currently
      // carries — the pending placeholder is swapped for the real row when the
      // server's start event arrives, so reference-based matching would break.
      const patchCurrent = (next: Message) => {
        const id = streamMessageRef.current?.id;
        if (!id) return;
        setMessages((list) => list.map((m) => (m.id === id ? next : m)));
      };

      const applyContent = (delta: string) => {
        const current = streamMessageRef.current;
        if (!current) return;
        const next = { ...current, content: current.content + delta };
        streamMessageRef.current = next;
        patchCurrent(next);
      };

      try {
        const selected = models.find((m) => m.id === modelId);
        await streamChat({
          model: modelId,
          provider,
          pipeline: selected?.pipeline,
          conversationId: cid,
          params: {},
          web_search: options?.webSearch,
          signal: controller.signal,
          events: {
            onStart: (messageId) => {
              const current = streamMessageRef.current;
              if (current && messageId) {
                const real = { ...current, id: messageId };
                streamMessageRef.current = real;
                setMessages((list) =>
                  list.map((m) => (m.id === "pending" || m.id === current.id ? real : m)),
                );
              }
            },
            onDelta: applyContent,
            onDone: ({ message_id, content }) => {
              const current = streamMessageRef.current;
              if (current) {
                const final = { ...current, id: message_id ?? current.id, content, done: true };
                streamMessageRef.current = final;
                patchCurrent(final);
              }
            },
            onError: (message) => {
              const current = streamMessageRef.current;
              if (current) {
                const err = { ...current, error: message, done: true };
                streamMessageRef.current = err;
                patchCurrent(err);
              }
            },
          },
        });
      } catch (error) {
        // aborted by the user — keep the partial reply (done=false on server)
        const current = streamMessageRef.current;
        if (current && !current.done && !controller.signal.aborted) {
          const err = { ...current, error: "Request failed.", done: true };
          streamMessageRef.current = err;
          patchCurrent(err);
        }
      } finally {
        setStreaming(false);
        abortRef.current = null;
        streamMessageRef.current = null;
        refreshConversations(search);
        // the server auto-titles new chats from the first user line; when the
        // user turned auto-title off, restore the placeholder title.
        if (createdHere && !autoTitle) {
          void renameConversation(cid, "New Chat");
        }
      }
    },
    [
      activeId,
      createAndOpen,
      autoTitle,
      modelId,
      provider,
      models,
      refreshConversations,
      renameConversation,
      search,
      streaming,
    ],
  );

  const value = useMemo<ChatState>(
    () => ({
      models,
      conversations,
      folders,
      archived,
      loadingArchived,
      activeId,
      conversation,
      messages,
      loadingConversation,
      modelId,
      provider,
      streaming,
      showSidebar,
      search,
      setSearch,
      setModelId,
      toggleSidebar: () => setShowSidebar((v) => !v),
      refreshModels: async () => {
        const list = await listModels();
        setModels(list);
      },
      openConversation,
      createAndOpen,
      renameConversation,
      removeConversation,
      removeMessage,
      refreshConversations,
      refreshFolders,
      createFolder,
      renameFolder,
      removeFolder,
      moveToFolder,
      setArchived,
      refreshArchived,
      share,
      unshare,
      send,
      stop,
    }),
    [
      models,
      conversations,
      folders,
      archived,
      loadingArchived,
      activeId,
      conversation,
      messages,
      loadingConversation,
      modelId,
      provider,
      streaming,
      showSidebar,
      search,
      openConversation,
      createAndOpen,
      renameConversation,
      removeConversation,
      removeMessage,
      refreshConversations,
      refreshFolders,
      createFolder,
      renameFolder,
      removeFolder,
      moveToFolder,
      setArchived,
      refreshArchived,
      share,
      unshare,
      send,
      stop,
    ],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatState {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
