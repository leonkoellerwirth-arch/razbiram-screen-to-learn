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

/** One observation from the backend about work in flight. Mirrors `progress.ProgressEvent`. */
export interface StageEvent {
  stage: string;
  detail: string;
  /** 1-based position within `total`, when the stage is countable. */
  index?: number;
  /** Upper bound for `index`. May be reached early — finishing sooner is a success. */
  total?: number;
}

export interface StreamHandlers {
  /** Fraction of the file sent, 0..1. Real, from the browser. */
  onUpload?: (fraction: number) => void;
  /** A stage the backend actually reached. */
  onStage?: (event: StageEvent) => void;
}

/**
 * POST /v1/process/stream — the same work as `processFile`, narrated while it happens.
 *
 * XHR rather than fetch: it is the only API that reports upload progress *and* exposes the
 * response as it arrives. The two matter at different moments — upload dominates for a large
 * photo on a slow disk, OCR dominates everywhere else — and a bar that showed only one of them
 * would sit still through the part the user is actually waiting for.
 */
export function processFileStreaming(
  file: File,
  handlers: StreamHandlers = {},
): Promise<ProcessResponse> {
  return new Promise((resolve, reject) => {
    const body = new FormData();
    body.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/v1/process/stream");

    let consumed = 0; // bytes of responseText already turned into events
    let result: ProcessResponse | null = null;
    let failure: string | null = null;

    const drain = () => {
      const text = xhr.responseText;
      // Only whole lines are parseable; a partial tail stays for the next progress event.
      const boundary = text.lastIndexOf("\n");
      if (boundary < consumed) return;
      const chunk = text.slice(consumed, boundary);
      consumed = boundary + 1;

      for (const line of chunk.split("\n")) {
        if (!line.trim()) continue;
        let event: Record<string, unknown>;
        try {
          event = JSON.parse(line) as Record<string, unknown>;
        } catch {
          continue; // a malformed line must not abort a run that is otherwise fine
        }
        if (event.event === "result") {
          result = event as unknown as ProcessResponse;
        } else if (event.event === "error") {
          failure = typeof event.detail === "string" ? event.detail : "Processing failed.";
        } else {
          handlers.onStage?.(event as unknown as StageEvent);
        }
      }
    };

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && e.total > 0) handlers.onUpload?.(e.loaded / e.total);
    };
    xhr.onprogress = drain;
    xhr.onerror = () => reject(new Error("Could not reach the local studio backend."));
    xhr.onload = () => {
      drain();
      if (failure) reject(new Error(failure));
      else if (result) resolve(result);
      else reject(new Error(`Server returned ${xhr.status} without a result.`));
    };

    xhr.send(body);
  });
}

export interface DeckCheck {
  ok: boolean;
  errors: string[];
  /**
   * What to actually save when `ok` — the submitted deck with the draft's working notes
   * (`status`, per-card `review`) removed. Null while anything is still wrong, because there is
   * nothing to save yet.
   */
  deck: unknown | null;
}

/**
 * POST /v1/deck/check — does this (possibly hand-edited) deck satisfy the target's rules?
 *
 * The rules live in Python next to the export path, never here: a second copy in the browser is a
 * second thing to keep true, and this is the gate that decides whether a file may leave.
 */
export async function checkDeck(deck: unknown, capabilities: string[]): Promise<DeckCheck> {
  const res = await fetch("/v1/deck/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deck, capabilities }),
  });
  if (!res.ok) throw new Error(`Deck check failed: ${res.status}`);
  return res.json() as Promise<DeckCheck>;
}

/** GET /health — used to verify the backend is reachable before upload. */
export async function checkHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch("/health");
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json() as Promise<{ status: string; version: string }>;
}
