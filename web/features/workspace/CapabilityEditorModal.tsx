"use client";

// CapabilityEditorModal — create/edit a capability (tool): a name, a
// description, and an OpenAPI-style spec (JSON object or raw JSON string).

import { useEffect, useState } from "react";
import { Trash2, Wrench } from "lucide-react";
import { Modal, ModalTitle } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Toggle } from "@/components/ui/Toggle";
import { errorMessage } from "@/lib/api";
import { toast } from "@/lib/toast";
import { createCapability, deleteCapability, updateCapability } from "@/lib/workspace";
import type { Capability } from "@/lib/types";

interface CapabilityEditorModalProps {
  open: boolean;
  capability: Capability | null;
  onSaved: () => void;
  onClose: () => void;
}

function prettify(spec: Record<string, unknown> | string | null): string {
  try {
    return JSON.stringify(spec, null, 2);
  } catch {
    return "";
  }
}

export function CapabilityEditorModal({
  open,
  capability,
  onSaved,
  onClose,
}: CapabilityEditorModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [specText, setSpecText] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setName(capability?.name ?? "");
    setDescription(capability?.description ?? "");
    setSpecText(prettify(capability?.spec ?? {}));
    setIsActive(capability?.is_active ?? true);
  }, [open, capability]);

  const save = async () => {
    const cleanName = name.trim();
    if (!cleanName) {
      toast.error("A name is required.");
      return;
    }
    let spec: Record<string, unknown> | string | null = null;
    const raw = specText.trim();
    if (raw) {
      try {
        spec = JSON.parse(raw);
        if (typeof spec !== "object" || spec === null || Array.isArray(spec)) {
          throw new Error("must be an object");
        }
      } catch {
        toast.error("Spec must be valid JSON (an object).");
        return;
      }
    }
    setSaving(true);
    try {
      if (capability) {
        await updateCapability(capability.id, {
          name: cleanName,
          description,
          spec,
          is_active: isActive,
        });
      } else {
        await createCapability({
          name: cleanName,
          description,
          spec,
          is_active: isActive,
        });
      }
      toast.success(capability ? "Capability updated." : "Capability created.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!capability) return;
    setSaving(true);
    try {
      await deleteCapability(capability.id);
      toast.success("Capability deleted.");
      onSaved();
      onClose();
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} size="lg">
      <ModalTitle
        title={capability ? "Edit Capability" : "Create Capability"}
        onClose={onClose}
      />
      <div className="px-5 pb-5 pt-2 flex flex-col gap-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Name</span>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Weather API"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Description</span>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this tool do?"
            />
          </label>
        </div>

        <label className="flex flex-col gap-1 text-sm">
          <span className="text-gray-500 dark:text-gray-400">
            Spec (OpenAPI-style JSON)
          </span>
          <Textarea
            value={specText}
            onChange={(e) => setSpecText(e.target.value)}
            rows={10}
            className="font-mono text-xs leading-5"
            placeholder={'{\n  "openapi": "3.0.0",\n  "info": { "title": "Weather", "version": "1.0" },\n  "paths": {}\n}'}
          />
        </label>

        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">Enabled</span>
          <Toggle checked={isActive} onChange={setIsActive} />
        </div>

        <div className="mt-2 flex items-center justify-between">
          <div>
            {capability && (
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
              <Wrench className="size-4" /> {capability ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
