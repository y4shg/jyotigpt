"use client";

// CollectionEditorModal — create/edit a knowledge collection.

import { useEffect, useState } from "react";
import { BookOpen, Trash2 } from "lucide-react";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { createCollection, deleteCollection, updateCollection } from "@/lib/workspace";
import type { Collection } from "@/lib/types";

interface CollectionEditorModalProps {
  open: boolean;
  collection: Collection | null;
  onSaved: () => void;
  onClose: () => void;
}

export function CollectionEditorModal({
  open,
  collection,
  onSaved,
  onClose,
}: CollectionEditorModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isShared, setIsShared] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(collection?.name ?? "");
    setDescription(collection?.description ?? "");
    setIsShared(collection?.is_shared ?? false);
  }, [open, collection]);

  const save = async () => {
    const cleanName = name.trim();
    if (!cleanName) {
      toast.error("A name is required.");
      return;
    }
    setSaving(true);
    try {
      if (collection) {
        await updateCollection(collection.id, {
          name: cleanName,
          description,
          is_shared: isShared,
        });
      } else {
        await createCollection({
          name: cleanName,
          description,
          is_shared: isShared,
        });
      }
      toast.success(collection ? "Collection updated." : "Collection created.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!collection) return;
    setSaving(true);
    try {
      await deleteCollection(collection.id);
      toast.success("Collection deleted.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} size="md">
      <ModalTitle
        title={collection ? "Edit Collection" : "Create Collection"}
        onClose={onClose}
      />
      <div className="px-5 pb-5 pt-2 flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Name</span>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="BK Study Notes"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Description</span>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="What does this collection hold?"
          />
        </label>

        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Shared with all users (read-only for them)
          </span>
          <Toggle checked={isShared} onChange={setIsShared} />
        </div>

        <div className="mt-2 flex items-center justify-between">
          <div>
            {collection && (
              <Button
                variant="ghost"
                onClick={remove}
                disabled={saving}
                className="text-red-600 dark:text-red-500"
              >
                <Trash2 className="size-4" /> Delete
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" onClick={save} disabled={saving}>
              <BookOpen className="size-4" /> {collection ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
