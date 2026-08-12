// Image generation client: /api/v1/images/generations.

import { api, API_BASE_URL } from "./api";

export interface GeneratedImage {
  url: string;
  prompt: string;
}

export interface ImageGenerationResponse {
  images: GeneratedImage[];
}

export function generateImage(body: {
  text?: string;
  prompt?: string;
  model?: string;
  size?: string;
}): Promise<ImageGenerationResponse> {
  return api.post<ImageGenerationResponse>("/api/v1/images/generations", body);
}

/** Resolve a possibly-relative image url against the API base. */
export function resolveImageUrl(url: string): string {
  if (/^https?:\/\//.test(url)) return url;
  return `${API_BASE_URL}${url.startsWith("/") ? url : `/${url}`}`;
}

/** True when a message's content is a generated image reference. */
export function isImageContent(content: string): boolean {
  return /^(https?:\/\/|\/)[^\s]*\.(png|jpe?g|webp|gif)(\?[^\s]*)?$/i.test(
    content.trim(),
  );
}
