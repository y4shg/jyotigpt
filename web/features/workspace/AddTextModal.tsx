"use client";

// AddTextModal — add free text to a collection (chunked + embedded server-side).

import { useState } from "react";
import { BookOpen } from "lucide-react";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { addTextItem } from "@/lib/workspace";

interface AddTextModalProps {
  open: boolean;
  collectionId: string;
  onAdded: () => void;
  onClose: () => void;
}

export function AddTextModal({
  open,
  collectionId,
  onAdded,
  onClose,
}: AddTextModalProps) {
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const text = content.trim();
    if (!text) {
      toast.error("Text content is required.");
      return;
    }
    setSaving(true);
    try {
      const items = await addTextItem(collectionId, text);
      toast.success(`Added ${items.length} chunk(s).`);
      setContent("");
      onAdded();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} size="md">
      <ModalTitle title="Add Text Content" onClose={onClose} />
      <div className="px-5 pb-5 pt-2 flex flex-col gap-3">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={8}
          placeholder="Paste or write the content to add to this collection…"
          autoFocus
        />
        <div className="mt-1 flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={save} disabled={saving}>
            <BookOpen className="size-4" /> {saving ? "Adding…" : "Add"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
