// api.ts — typed client for the razbiram-screen-to-learn backend.
// Two endpoints only; no other network calls are made by this app.
import type { ProcessResponse } from "./types";

/** POST /v1/process — multipart, single field "file". */
export async function processFile(file: File): Promise<ProcessResponse> {
  const body = new FormData();
  body.append("file", file);

  const res = await fetch("/v1/process", { method: "POST", body });

  if (!res.ok) {
    let detail = `Server returned ${res.status}`;
    try {
      const json = (await res.json()) as { detail?: string };
      if (json.detail) detail = json.detail;
    } catch {
      // JSON parse failed — keep the generic status message
    }
    throw new Error(detail);
  }

  return res.json() as Promise<ProcessResponse>;
}

/** GET /health — used to verify the backend is reachable before upload. */
export async function checkHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch("/health");
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json() as Promise<{ status: string; version: string }>;
}
