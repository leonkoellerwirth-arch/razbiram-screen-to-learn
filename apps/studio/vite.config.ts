/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Unlike razbiram-anki — which runs entirely in the browser — the studio talks to a local
// loopback service that owns extraction, validation and export. Keeping that logic in one place
// is what stops the studio and the browser extension from growing two different extractors
// (BIBLE invariant 13). In dev, Vite proxies the API so the browser sees a single origin.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    proxy: {
      "/v1": "http://127.0.0.1:8765",
      "/health": "http://127.0.0.1:8765",
    },
  },
  build: { outDir: "dist" },
  test: { environment: "jsdom", globals: true },
});
