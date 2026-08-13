"use client";

// ChatInput — autosizing composer with plus menu, mic, image/web-search toggles, send/stop.

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Mic, Paperclip, ImageIcon, Square, Search } from "lucide-react";
import { clsx } from "clsx";
import { useChat } from "./useChatStore";
import { useApp } from "@/lib/store";
import { useVoiceRecorder } from "@/lib/useVoiceRecorder";
import { Dropdown, DropdownItem } from "@/components/ui/Dropdown";
import { Tooltip } from "@/components/ui/Tooltip";

const MAX_HEIGHT = 200;

export function ChatInput({ onNavigate }: { onNavigate?: (id: string) => void }) {
  const { send, stop, streaming } = useChat();
  const { config } = useApp();
  const [value, setValue] = useState("");
  const [imageMode, setImageMode] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const canSend = value.trim().length > 0 && !streaming;
  const imageEnabled = config?.features.image_generation ?? false;
  const webSearchEnabled = config?.features.web_search ?? false;
  const audioEnabled = Boolean(config?.audio.stt_engine || config?.audio.tts_engine);

  const { recording, transcribing, startRecording, stopRecording } = useVoiceRecorder({
    sttEngine: config?.audio.stt_engine ?? "",
    onTranscript: (text) => {
      setValue((v) => (v ? `${v} ${text}` : text));
    },
  });

  // autosize
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || streaming) return;
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    void send(text, { onNavigate, imageMode, webSearch });
  };

  const toggleMic = () => {
    if (!audioEnabled) return;
    if (recording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="flex-1 flex flex-col relative w-full shadow-lg rounded-3xl border border-gray-50 dark:border-gray-850 hover:border-gray-100 focus-within:border-gray-100 hover:dark:border-gray-800 focus-within:dark:border-gray-800 transition px-1 bg-white/90 dark:bg-gray-400/5 dark:text-gray-100">
      {/* toggle pills row */}
      {(webSearchEnabled || imageEnabled) && (
        <div className="flex gap-1 px-2 pt-2">
          {webSearchEnabled && (
            <button
              type="button"
              onClick={() => setWebSearch((v) => !v)}
              className={clsx(
                "flex items-center gap-1 px-2.5 py-1 text-xs rounded-full border transition-colors",
                webSearch
                  ? "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400"
                  : "bg-transparent border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800",
              )}
            >
              <Search className="size-3" />
              <span>Search</span>
            </button>
          )}
        </div>
      )}

      <div className="flex w-full items-end max-h-40">
        <Dropdown
          align="left-0 bottom-full mb-2"
          trigger={
            <span className="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-600 dark:text-gray-300">
              <Paperclip className="size-5" />
            </span>
          }
        >
          <DropdownItem disabled>
            <Paperclip className="size-4" /> Upload files (Phase 5)
          </DropdownItem>
        </Dropdown>

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          rows={1}
          placeholder={recording ? "Listening…" : transcribing ? "Transcribing…" : "Send a Message"}
          className="flex-1 resize-none bg-transparent outline-none pt-3 px-1 text-sm max-h-80 leading-6"
        />

        {streaming ? (
          <button
            type="button"
            onClick={stop}
            aria-label="Stop generating"
            id="stop-generating-button"
            className="bg-white hover:bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-1.5 self-center"
          >
            <Square className="size-5 fill-current" />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!canSend}
            aria-label="Send message"
            id="send-message-button"
            className={clsx(
              "transition rounded-full p-1.5 self-center",
              canSend
                ? "bg-red-600 text-white hover:bg-red-700 dark:bg-red-600 dark:text-black dark:hover:bg-red-700"
                : "text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700",
            )}
          >
            <ArrowUp className="size-5" />
          </button>
        )}

        {imageEnabled && (
          <Tooltip content="Generate an image">
            <button
              type="button"
              aria-label="Generate an image"
              onClick={() => setImageMode((v) => !v)}
              className={clsx(
                "cursor-pointer px-1.5 @xl:px-2.5 py-1.5 flex gap-1.5 items-center text-sm rounded-full font-medium transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden border self-center",
                imageMode
                  ? "bg-gray-50 dark:bg-gray-400/10 border-gray-100 dark:border-gray-700 text-gray-600 dark:text-gray-400"
                  : "bg-transparent border-transparent text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800",
              )}
            >
              <ImageIcon className="size-5" strokeWidth={1.75} />
              <span className="hidden @xl:block translate-y-[0.5px]">Image</span>
            </button>
          </Tooltip>
        )}

        {audioEnabled && (
          <Tooltip content={recording ? "Stop recording" : "Voice input"}>
            <button
              type="button"
              aria-label="Voice input"
              aria-pressed={recording}
              onClick={toggleMic}
              disabled={transcribing}
              className={clsx(
                "cursor-pointer px-2 py-2 flex rounded-xl transition",
                recording
                  ? "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 animate-pulse"
                  : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800",
                transcribing && "opacity-50 cursor-wait",
              )}
            >
              <Mic className="size-5" />
            </button>
          </Tooltip>
        )}
      </div>
    </div>
  );
}
