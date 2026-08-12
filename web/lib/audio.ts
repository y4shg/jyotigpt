// Audio helpers: provider STT (speech-to-text) and TTS (text-to-speech)
// via the jyoti_api backend endpoints.

import { API_BASE_URL, ApiError } from "./api";

/**
 * Send an audio blob to the provider STT endpoint and return the
 * transcription text.
 *
 * @param file  — raw audio (Blob/WebM/MP3)
 * @param lang  — optional ISO-639-1 language hint (e.g. "en")
 */
export async function transcribeAudio(
  file: Blob,
  lang?: string,
): Promise<string> {
  const form = new FormData();
  form.append("file", file, "recording.webm");
  if (lang) form.append("lang", lang);

  const res = await fetch(`${API_BASE_URL}/api/v1/stt/transcriptions`, {
    method: "POST",
    credentials: "include",
    body: form,
  });

  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = (body as { detail?: unknown }).detail ?? body;
    } catch {
      // non-JSON error — keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  const data = (await res.json()) as { text: string; engine: string };
  return data.text;
}

/**
 * Request provider TTS and return a playable object URL.
 *
 * @param text   — text to speak (max 4000 chars)
 * @param opts   — optional voice / speed overrides
 * @returns      — object URL for the returned MP3 audio; caller must revoke
 */
export async function synthesizeSpeech(
  text: string,
  opts?: { voice?: string; speed?: number },
): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tts/speech`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      voice: opts?.voice ?? "",
      speed: opts?.speed ?? 1,
    }),
  });

  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = (body as { detail?: unknown }).detail ?? body;
    } catch {
      // non-JSON — keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
