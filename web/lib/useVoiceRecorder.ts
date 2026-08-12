// useVoiceRecorder — hook that handles recording audio and transcribing it
// via either the browser Web Speech API (STT) or the provider STT endpoint.
//
// Usage:
//   const { recording, transcribing, startRecording, stopRecording } =
//     useVoiceRecorder({ sttEngine, onTranscript });

"use client";

import { useCallback, useRef, useState } from "react";
import { transcribeAudio } from "./audio";

interface UseVoiceRecorderOptions {
  /** "browser" uses the Web Speech API; anything else uses the provider STT endpoint. */
  sttEngine: string;
  /** Called with the final transcript text. */
  onTranscript: (text: string) => void;
}

export function useVoiceRecorder({
  sttEngine,
  onTranscript,
}: UseVoiceRecorderOptions) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);

  // Browser Web Speech API
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  const stopRecording = useCallback(() => {
    if (sttEngine === "browser" && recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
      return;
    }
    // Provider STT — stop the MediaRecorder
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
    setRecording(false);
  }, [sttEngine]);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  const startRecording = useCallback(async () => {
    if (recording) return;

    // Browser Web Speech API path
    if (sttEngine === "browser") {
      const SRConstructor = window.SpeechRecognition ?? window.webkitSpeechRecognition;

      if (!SRConstructor) {
        console.warn("Web Speech API not supported in this browser.");
        return;
      }

      const recognition = new SRConstructor();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-US";

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0]?.[0]?.transcript;
        if (transcript) onTranscript(transcript);
      };
      recognition.onerror = () => {
        setRecording(false);
      };
      recognition.onend = () => {
        setRecording(false);
        recognitionRef.current = null;
      };

      recognitionRef.current = recognition;
      recognition.start();
      setRecording(true);
      return;
    }

    // Provider STT path — record via MediaRecorder, then POST to backend
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm",
      });

      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        chunksRef.current = [];

        setRecording(false);
        setTranscribing(true);
        try {
          const text = await transcribeAudio(blob);
          if (text) onTranscript(text);
        } catch (err) {
          console.error("Provider STT failed:", err);
        } finally {
          setTranscribing(false);
        }
      };

      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch (err) {
      console.error("Failed to start recording:", err);
      setRecording(false);
    }
  }, [recording, sttEngine, onTranscript]);

  return { recording, transcribing, startRecording, stopRecording };
}
