"use client";

// MessageItem — user bubble (right) and assistant message (avatar + name +
// markdown) with a hover action row: copy, regenerate, delete.

import { useCallback, useRef, useState } from "react";
import { Check, Copy, RefreshCw, Trash2, Volume2, VolumeX } from "lucide-react";
import { clsx } from "clsx";
import type { Message } from "@/lib/types";
import { isImageContent, resolveImageUrl } from "@/lib/images";
import { synthesizeSpeech } from "@/lib/audio";
import { useApp } from "@/lib/store";
import { Markdown } from "./Markdown";

function UserBubble({ message }: { message: Message }) {
  return (
    <div
      id={`message-${message.id}`}
      className="flex w-full user-message justify-end"
    >
      <div className="rounded-3xl max-w-[90%] px-5 py-2 bg-gray-50 dark:bg-gray-850 whitespace-pre-wrap">
        {message.content}
      </div>
    </div>
  );
}

function AssistantName({
  model,
  content,
  messageDone,
}: {
  model: string | null;
  content: string;
  messageDone: boolean;
}) {
  const { settings } = useApp();
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);

  const speak = useCallback(async () => {
    if (speaking) {
      // stop
      audioRef.current?.pause();
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
      audioRef.current = null;
      setSpeaking(false);
      return;
    }
    if (!content) return;
    try {
      const url = await synthesizeSpeech(content, {
        voice: settings?.voice !== "default" ? settings?.voice : undefined,
        speed: settings?.playback_speed,
      });
      objectUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        setSpeaking(false);
        if (objectUrlRef.current) {
          URL.revokeObjectURL(objectUrlRef.current);
          objectUrlRef.current = null;
        }
        audioRef.current = null;
      };
      setSpeaking(true);
      audio.play();
    } catch (err) {
      console.error("TTS failed:", err);
      setSpeaking(false);
    }
  }, [speaking, content, settings?.voice, settings?.playback_speed]);

  const ttsEnabled = Boolean(settings?.tts_engine && settings.tts_engine !== "default");

  return (
    <div className="self-center font-semibold line-clamp-1 flex gap-1 items-center text-gray-900 dark:text-gray-100">
      <span className="truncate">{model || "JyotiGPT"}</span>
      {ttsEnabled && messageDone && content && (
        <button
          type="button"
          onClick={speak}
          aria-label={speaking ? "Stop speaking" : "Read aloud"}
          className="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition"
        >
          {speaking ? <VolumeX className="size-3.5" /> : <Volume2 className="size-3.5" />}
        </button>
      )}
    </div>
  );
}

function ProfileImage() {
  return (
    <div className="size-8 object-cover rounded-full -translate-y-[1px] bg-gray-200 dark:bg-gray-800 flex items-center justify-center text-xs font-bold text-gray-600 dark:text-gray-300">
      J
    </div>
  );
}

function AssistantMessage({ message }: { message: Message }) {
  const image = isImageContent(message.content) ? message.content.trim() : null;
  return (
    <div id={`message-${message.id}`} className="flex w-full message-item">
      <div className="w-full flex-col">
        <div className="flex gap-1 items-center mb-1">
          <ProfileImage />
          <AssistantName model={message.model} content={message.content} messageDone={message.done} />
        </div>
        {image ? (
          <a
            href={resolveImageUrl(image)}
            target="_blank"
            rel="noreferrer"
            className="inline-block"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={resolveImageUrl(image)}
              alt="Generated image"
              className="max-w-72 rounded-xl border border-gray-100 dark:border-gray-800"
            />
          </a>
        ) : (
          <div className="chat-assistant w-full min-w-full markdown-prose">
            <Markdown content={message.content} streaming={!message.done} />
          </div>
        )}
        {message.error && (
          <div className="mt-1 text-sm text-red-600 dark:text-red-500">
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}

export function MessageItem({
  message,
  onCopy,
  onDelete,
}: {
  message: Message;
  onCopy: () => void;
  onDelete: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
      onCopy();
    } catch {
      // clipboard unavailable
    }
  };

  return (
    <div className="flex flex-col justify-between px-5 mb-3 w-full max-w-5xl mx-auto rounded-lg group">
      {message.role === "user" ? (
        <UserBubble message={message} />
      ) : (
        <AssistantMessage message={message} />
      )}

      {/* hover actions */}
      <div className="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity mt-0.5 -mr-1">
        <button
          type="button"
          onClick={copy}
          aria-label="Copy message"
          className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-500 dark:text-gray-400"
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
        </button>
        <button
          type="button"
          aria-label="Regenerate"
          disabled={message.role !== "assistant"}
          className={clsx(
            "p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-500 dark:text-gray-400",
            message.role !== "assistant" && "opacity-40",
          )}
        >
          <RefreshCw className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label="Delete message"
          className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-850 text-gray-500 dark:text-gray-400"
        >
          <Trash2 className="size-3.5" />
        </button>
      </div>
    </div>
  );
}
