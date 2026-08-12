"use client";

// Notes — per-user markdown notes. The old app's Notes tab was a dead stub
// (no API, nothing persisted); the rewrite makes it a real two-pane editor:
// a note list on the left, the title + markdown body on the right.

import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, NotebookPen, Plus, Trash2 } from "lucide-react";
import { clsx } from "clsx";
import { createNote, deleteNote, listNotes, updateNote } from "@/lib/notes";
import { errorMessage } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import type { Note } from "@/lib/types";

export function Notes() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // editor draft + dirty tracking
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadedRef = useRef<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const rows = await listNotes();
      setNotes(rows);
      setError(null);
      // keep the active editor in sync when a save changes the list
      setActiveId((current) => {
        if (current && rows.some((n) => n.id === current)) return current;
        return rows[0]?.id ?? null;
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const open = (id: string) => {
    if (dirty) void save();
    const note = notes.find((n) => n.id === id);
    if (!note) return;
    loadedRef.current.add(id);
    setActiveId(id);
    setTitle(note.title);
    setContent(note.content);
  };

  const newNote = async () => {
    if (dirty) void save();
    try {
      const note = await createNote({ title: "", content: "" });
      setNotes((rows) => [note, ...rows]);
      loadedRef.current.add(note.id);
      setActiveId(note.id);
      setTitle("");
      setContent("");
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const save = async () => {
    if (!activeId || !dirty) return;
    setSaving(true);
    try {
      const updated = await updateNote(activeId, { title, content });
      setNotes((rows) => rows.map((n) => (n.id === activeId ? updated : n)));
      setDirty(false);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!activeId) return;
    try {
      await deleteNote(activeId);
      setNotes((rows) => rows.filter((n) => n.id !== activeId));
      setDirty(false);
      setActiveId(null);
      setTitle("");
      setContent("");
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <div className="w-full h-screen max-h-[100dvh] flex flex-col">
      <div className="flex items-center gap-2 px-4 pt-3 pb-2 text-gray-900 dark:text-white">
        <NotebookPen className="size-5" />
        <div className="text-xl font-semibold">Notes</div>
      </div>

      <div className="flex flex-1 min-h-0 px-4 pb-4 gap-3">
        {/* note list */}
        <div className="w-60 shrink-0 flex flex-col min-h-0 rounded-xl bg-gray-100 dark:bg-gray-850 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2">
            <span className="text-xs text-gray-500 dark:text-gray-500 font-medium">
              {notes.length} note{notes.length === 1 ? "" : "s"}
            </span>
            <Button variant="ghost" onClick={() => void newNote()} className="px-2 py-1">
              <Plus className="size-4" /> New
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto scrollbar-none px-1.5 pb-2 space-y-0.5">
            {loading ? (
              <div className="px-2.5 py-2 text-sm text-gray-500 dark:text-gray-500">
                Loading…
              </div>
            ) : notes.length === 0 ? (
              <div className="px-2.5 py-2 text-sm text-gray-500 dark:text-gray-500">
                No notes yet.
              </div>
            ) : (
              notes.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => open(note.id)}
                  className={clsx(
                    "w-full text-left flex items-start gap-2 rounded-lg px-2.5 py-2 text-sm transition",
                    note.id === activeId
                      ? "bg-gray-200 dark:bg-gray-900"
                      : "hover:bg-gray-200/60 dark:hover:bg-gray-900/60",
                  )}
                >
                  <FileText className="size-4 shrink-0 mt-0.5" />
                  <span className="min-w-0">
                    <span className="block truncate">{note.title || "Untitled"}</span>
                    <span className="block truncate text-xs text-gray-500 dark:text-gray-500">
                      {note.content
                        ? note.content.replace(/[#*`>\-\s]+/g, " ").trim().slice(0, 80)
                        : "Empty note"}
                    </span>
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* editor */}
        <div className="flex-1 min-w-0 flex flex-col rounded-xl bg-gray-100 dark:bg-gray-850 overflow-hidden">
          {activeId ? (
            <>
              <div className="flex items-center gap-2 px-3 py-2">
                <input
                  value={title}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    setDirty(true);
                  }}
                  placeholder="Untitled"
                  className="flex-1 min-w-0 bg-transparent text-lg font-semibold text-gray-900 dark:text-white placeholder-gray-500 outline-none"
                />
                <Button
                  variant="default"
                  disabled={!dirty || saving}
                  onClick={() => void save()}
                  className="px-3 py-1.5"
                >
                  {saving ? "Saving…" : "Save"}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => void remove()}
                  className="px-2 py-1.5 text-red-600 dark:text-red-500"
                >
                  <Trash2 className="size-4" />
                </Button>
              </div>
              <textarea
                value={content}
                onChange={(e) => {
                  setContent(e.target.value);
                  setDirty(true);
                }}
                placeholder="Write in markdown…"
                spellCheck={false}
                className="flex-1 min-h-0 w-full resize-none bg-transparent px-4 pb-4 text-sm leading-relaxed text-gray-800 dark:text-gray-200 placeholder-gray-500 outline-none font-mono"
              />
              <div className="px-4 pb-3 text-xs text-gray-500 dark:text-gray-500">
                Markdown supported · changes save when you press Save
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-sm text-gray-500 dark:text-gray-500">
              Select a note or create a new one.
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="px-4 pb-3 text-sm text-red-600 dark:text-red-500">{error}</div>
      )}
    </div>
  );
}
