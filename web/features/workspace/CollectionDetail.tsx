"use client";

// CollectionDetail — the knowledge collection workspace: upload documents,
// add free text, browse chunks (two-pane), and query the collection.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Pencil,
  Search,
  Trash2,
} from "lucide-react";
import { clsx } from "clsx";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Input } from "@/components/ui/Input";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { useApp } from "@/lib/store";
import {
  addDocumentItem,
  deleteCollection,
  ingestDocument,
  listCollectionItems,
  removeCollectionItem,
  searchCollections,
} from "@/lib/workspace";
import type { Collection, CollectionItem, SearchResult } from "@/lib/types";
import { CollectionEditorModal } from "./CollectionEditorModal";
import { AddTextModal } from "./AddTextModal";

interface CollectionDetailProps {
  collection: Collection;
  onBack: () => void;
  onChanged: () => void;
}

export function CollectionDetail({
  collection,
  onBack,
  onChanged,
}: CollectionDetailProps) {
  const { user } = useApp();
  const readonly = collection.user_id !== user?.id;

  const [items, setItems] = useState<CollectionItem[]>([]);
  const [selected, setSelected] = useState<CollectionItem | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [addTextOpen, setAddTextOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [removing, setRemoving] = useState<CollectionItem | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const rows = await listCollectionItems(collection.id);
      setItems(rows);
      setSelected((current) =>
        current
          ? (rows.find((r) => r.id === current.id) ?? null)
          : (rows[0] ?? null),
      );
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }, [collection.id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        try {
          await ingestDocument(file, collection.id);
          toast.success(`Added ${file.name}.`);
        } catch (error) {
          toast.error(`${file.name}: ${errorMessage(error)}`);
        }
      }
      onChanged();
      load();
    } finally {
      setUploading(false);
    }
  };

  const runSearch = async () => {
    const term = query.trim();
    if (!term) {
      setResults(null);
      return;
    }
    setSearching(true);
    try {
      const response = await searchCollections(term, [collection.id], 8);
      setResults(response.results);
      setSelected(null);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSearching(false);
    }
  };

  const confirmDelete = async () => {
    setDeleting(false);
    try {
      await deleteCollection(collection.id);
      toast.success("Collection deleted.");
      onChanged();
      onBack();
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  const confirmRemoveItem = async () => {
    if (!removing) return;
    try {
      await removeCollectionItem(collection.id, removing.id);
      toast.success("Chunk removed.");
      onChanged();
      load();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setRemoving(null);
    }
  };

  const rightContent = results ? (
    <div className="flex flex-col gap-1.5">
      <div className="px-1 pt-1 pb-2 text-xs text-gray-500 dark:text-gray-400">
        Search results ({results.length})
      </div>
      {results.length === 0 ? (
        <div className="text-sm text-gray-400 dark:text-gray-500 px-1 py-6 text-center">
          No matching chunks.
        </div>
      ) : (
        results.map((result) => (
          <button
            key={result.id}
            type="button"
            onClick={() => {
              const item = items.find((i) => i.id === result.id);
              setSelected(item ?? null);
            }}
            className="flex flex-col gap-1 rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium text-gray-700 dark:text-gray-200">
                {result.source}
              </span>
              <span className="text-emerald-600 dark:text-emerald-400">
                {(result.score * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
              {result.content}
            </p>
          </button>
        ))
      )}
    </div>
  ) : selected ? (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2 px-1 pt-1">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          {selected.source}
        </span>
        {!selected.has_embedding && (
          <span className="rounded-full bg-amber-100 dark:bg-amber-900/40 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-300">
            not embedded
          </span>
        )}
        {!readonly && (
          <button
            type="button"
            onClick={() => setRemoving(selected)}
            className="ml-auto self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
            title="Remove chunk"
          >
            <Trash2 className="size-3.5" />
          </button>
        )}
      </div>
      <pre className="whitespace-pre-wrap rounded-xl bg-gray-50 dark:bg-gray-850 p-3 text-sm leading-6 text-gray-800 dark:text-gray-200">
        {selected.content}
      </pre>
    </div>
  ) : (
    <div className="text-sm text-gray-400 dark:text-gray-500 py-6 text-center">
      Select a chunk to view its content.
    </div>
  );

  return (
    <div className="flex flex-col gap-2 py-2">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          aria-label="Back to collections"
          className="cursor-pointer p-1.5 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-300"
        >
          <ArrowLeft className="size-4" />
        </button>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-medium line-clamp-1">{collection.name}</h2>
            {collection.is_shared && (
              <span className="rounded-full bg-emerald-100 dark:bg-emerald-900/40 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
                shared
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
            {items.length} chunks ·{" "}
            {collection.embedding_model || "embeddings pending"} ·{" "}
            {collection.description || "No description"}
          </div>
        </div>
        {!readonly && (
          <div className="ml-auto flex gap-0.5">
            <button
              type="button"
              title="Edit collection"
              onClick={() => setEditorOpen(true)}
              className="self-center w-fit text-sm p-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
            >
              <Pencil className="size-4" />
            </button>
            <button
              type="button"
              title="Delete collection"
              onClick={() => setDeleting(true)}
              className="self-center w-fit text-sm p-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
            >
              <Trash2 className="size-4" />
            </button>
          </div>
        )}
      </div>

      {!readonly && (
        <div
          className={clsx(
            "flex items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-5 text-sm transition",
            dragging
              ? "border-gray-400 dark:border-gray-500 bg-gray-50 dark:bg-gray-850"
              : "border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-700",
          )}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
        >
          <input
            ref={fileRef}
            type="file"
            multiple
            hidden
            onChange={(e) => handleFiles(e.target.files)}
          />
          <FileText className="size-5 text-gray-400 dark:text-gray-500" />
          <span className="text-gray-500 dark:text-gray-400">
            {uploading ? "Adding…" : "Drop files here, or "}
            {!uploading && (
              <button
                type="button"
                className="font-medium text-gray-900 dark:text-gray-100 hover:underline"
                onClick={() => fileRef.current?.click()}
              >
                click to upload
              </button>
            )}
          </span>
          <Button
            variant="outline"
            className="ml-2"
            onClick={() => setAddTextOpen(true)}
          >
            <BookOpen className="size-4" /> Add text
          </Button>
        </div>
      )}

      <div className="flex gap-2">
        <div className="flex flex-1 items-center gap-2">
          <div className="self-center ml-1 mr-1">
            <Search className="size-3.5 text-gray-400 dark:text-gray-500" />
          </div>
          <Input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (!e.target.value.trim()) setResults(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && runSearch()}
            placeholder="Query this collection…"
            className="py-1.5"
          />
        </div>
        <Button variant="default" onClick={runSearch} disabled={searching}>
          {searching ? "Searching…" : "Search"}
        </Button>
      </div>

      <div className="flex gap-2 min-h-64">
        <div className="w-1/2 max-w-72 shrink-0 flex flex-col gap-1 overflow-y-auto max-h-[45vh]">
          {items.length === 0 ? (
            <div className="text-sm text-gray-400 dark:text-gray-500 py-6 text-center">
              No chunks yet.
            </div>
          ) : (
            items.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  setSelected(item);
                  setResults(null);
                }}
                className={clsx(
                  "flex flex-col gap-0.5 rounded-xl px-3 py-2 text-left transition",
                  selected?.id === item.id && !results
                    ? "bg-gray-100 dark:bg-gray-800"
                    : "hover:bg-gray-50 dark:hover:bg-gray-850",
                )}
              >
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-medium text-gray-700 dark:text-gray-200 line-clamp-1">
                    {item.source}
                  </span>
                  {!item.has_embedding && (
                    <span className="size-1.5 shrink-0 rounded-full bg-amber-400" />
                  )}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                  {item.content}
                </p>
              </button>
            ))
          )}
        </div>

        <div className="flex-1 min-w-0 overflow-y-auto max-h-[45vh]">{rightContent}</div>
      </div>

      <CollectionEditorModal
        open={editorOpen}
        collection={collection}
        onSaved={onChanged}
        onClose={() => setEditorOpen(false)}
      />
      <AddTextModal
        open={addTextOpen}
        collectionId={collection.id}
        onAdded={() => {
          onChanged();
          load();
        }}
        onClose={() => setAddTextOpen(false)}
      />
      <ConfirmDialog
        open={deleting}
        onCancel={() => setDeleting(false)}
        onConfirm={confirmDelete}
        title="Delete collection?"
        message={`This will delete "${collection.name}" and all its chunks.`}
      />
      <ConfirmDialog
        open={removing !== null}
        onCancel={() => setRemoving(null)}
        onConfirm={confirmRemoveItem}
        title="Remove this chunk?"
        message="The chunk is deleted from the collection."
      />
    </div>
  );
}
