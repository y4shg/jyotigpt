"use client";

// CollectionsTab — knowledge collections: list, search, create/edit, delete,
// and open a collection detail view (?collection=<id>).

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen, Pencil, Trash2 } from "lucide-react";
import { WorkspaceTabScaffold } from "../WorkspaceTabScaffold";
import { CollectionDetail } from "../CollectionDetail";
import { CollectionEditorModal } from "../CollectionEditorModal";
import { Toggle } from "@/components/ui/Toggle";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { useApp } from "@/lib/store";
import {
  deleteCollection,
  listCollections,
  updateCollection,
} from "@/lib/workspace";
import type { Collection } from "@/lib/types";

export function CollectionsTab() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useApp();

  const [collections, setCollections] = useState<Collection[]>([]);
  const [search, setSearch] = useState("");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Collection | null>(null);
  const [deleting, setDeleting] = useState<Collection | null>(null);

  const selectedId = searchParams.get("collection");
  const selected = collections.find((c) => c.id === selectedId) ?? null;

  const load = useCallback(async () => {
    setCollections(await listCollections());
  }, []);

  useEffect(() => {
    load().catch((error) => toast.error(errorMessage(error)));
  }, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return collections;
    return collections.filter(
      (c) =>
        c.name.toLowerCase().includes(term) ||
        (c.description ?? "").toLowerCase().includes(term),
    );
  }, [collections, search]);

  const toggleShared = async (collection: Collection, is_shared: boolean) => {
    try {
      await updateCollection(collection.id, {
        name: collection.name,
        description: collection.description ?? "",
        is_shared,
      });
      setCollections((list) =>
        list.map((c) => (c.id === collection.id ? { ...c, is_shared } : c)),
      );
      toast.success(is_shared ? "Collection shared." : "Collection set private.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteCollection(deleting.id);
      toast.success("Collection deleted.");
      setCollections((list) => list.filter((c) => c.id !== deleting.id));
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDeleting(null);
    }
  };

  if (selected) {
    return (
      <CollectionDetail
        collection={selected}
        onBack={() => {
          router.replace("/workspace?tab=collections");
          load();
        }}
        onChanged={load}
      />
    );
  }

  return (
    <WorkspaceTabScaffold
      title="Collections"
      count={filtered.length}
      search={search}
      onSearch={setSearch}
      searchPlaceholder="Search Collections"
      onAdd={() => {
        setEditing(null);
        setEditorOpen(true);
      }}
      addLabel="Create Collection"
    >
      <div className="my-2 mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
        {filtered.map((collection) => {
          const readonly = collection.user_id !== user?.id;
          return (
            <div
              key={collection.id}
              className="flex flex-col w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition cursor-pointer"
              onClick={() =>
                router.replace(`/workspace?tab=collections&collection=${collection.id}`)
              }
            >
              <div className="flex items-center gap-2 mt-0.5 mb-1">
                <BookOpen className="size-4 shrink-0 text-gray-400 dark:text-gray-500" />
                <span className="font-semibold line-clamp-1">{collection.name}</span>
                {collection.is_shared && (
                  <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                    shared
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                {collection.description ||
                  (collection.embedding_model
                    ? `Embedded with ${collection.embedding_model}`
                    : "No description")}
              </p>
              <div className="flex justify-between items-center px-0.5 mt-1">
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {collection.item_count} chunk{collection.item_count === 1 ? "" : "s"}
                  {collection.user_id !== user?.id ? " · shared" : ""}
                </span>
                {!readonly && (
                  <div className="flex items-center gap-0.5">
                    <button
                      type="button"
                      title="Edit"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditing(collection);
                        setEditorOpen(true);
                      }}
                      className="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                    >
                      <Pencil className="size-4" />
                    </button>
                    <button
                      type="button"
                      title="Delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleting(collection);
                      }}
                      className="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
                    >
                      <Trash2 className="size-4" />
                    </button>
                    <div
                      className="ml-1"
                      onClick={(e) => e.stopPropagation()}
                      title={collection.is_shared ? "Shared (read-only for others)" : "Private"}
                    >
                      <Toggle
                        checked={collection.is_shared}
                        onChange={(next) => toggleShared(collection, next)}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="text-sm text-gray-400 dark:text-gray-500 py-8 text-center">
          No collections yet — create one with the + button to start a knowledge base.
        </div>
      )}

      <CollectionEditorModal
        open={editorOpen}
        collection={editing}
        onSaved={load}
        onClose={() => setEditorOpen(false)}
      />

      <ConfirmDialog
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
        title="Delete collection?"
        message={`This will delete ${deleting?.name ?? ""} and all its chunks.`}
      />
    </WorkspaceTabScaffold>
  );
}
