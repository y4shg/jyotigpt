"use client";

// PresetEditorModal — create/edit a prompt preset (optionally a "/command").

import { useEffect, useState } from "react";
import { Command, Trash2 } from "lucide-react";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { createPreset, deletePreset, updatePreset } from "@/lib/workspace";
import type { Preset } from "@/lib/types";

interface PresetEditorModalProps {
  open: boolean;
  preset: Preset | null;
  onSaved: () => void;
  onClose: () => void;
}

export function PresetEditorModal({
  open,
  preset,
  onSaved,
  onClose,
}: PresetEditorModalProps) {
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [isCommand, setIsCommand] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(preset?.name.startsWith("/") ? preset.name.slice(1) : preset?.name ?? "");
    setContent(preset?.content ?? "");
    setIsCommand(preset?.is_command ?? false);
  }, [open, preset]);

  const save = async () => {
    const cleanName = name.trim();
    const cleanContent = content.trim();
    if (!cleanName) {
      toast.error("A name is required.");
      return;
    }
    if (!cleanContent) {
      toast.error("Prompt content is required.");
      return;
    }
    setSaving(true);
    try {
      if (preset) {
        await updatePreset(preset.id, {
          name: cleanName,
          content: cleanContent,
          is_command: isCommand,
        });
      } else {
        await createPreset({
          name: cleanName,
          content: cleanContent,
          is_command: isCommand,
        });
      }
      toast.success(preset ? "Preset updated." : "Preset created.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!preset) return;
    setSaving(true);
    try {
      await deletePreset(preset.id);
      toast.success("Preset deleted.");
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
        title={preset ? "Edit Preset" : "Create Preset"}
        onClose={onClose}
      />
      <div className="px-5 pb-5 pt-2 flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Name</span>
          <div className="flex items-center gap-2">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={isCommand ? "draft" : "My preset"}
            />
            {isCommand && (
              <span className="shrink-0 rounded-lg bg-gray-100 dark:bg-gray-850 px-2 py-2 text-sm text-gray-500 dark:text-gray-400">
                /{name || "command"}
              </span>
            )}
          </div>
        </label>

        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Command (type /{name || "name"} in chat)
          </span>
          <Toggle checked={isCommand} onChange={setIsCommand} />
        </div>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500 dark:text-gray-400">Content</span>
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            placeholder="The prompt body. Use {{var}} for placeholders."
          />
        </label>

        <div className="mt-2 flex items-center justify-between">
          <div>
            {preset && (
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
              <Command className="size-4" /> {preset ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
