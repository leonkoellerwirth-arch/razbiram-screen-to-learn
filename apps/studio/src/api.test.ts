/** Failure paths must surface the server's own message, never a silent no-op. */
import { afterEach, describe, expect, it, vi } from "vitest";
import { processFile } from "./api";

const file = () => new File(["<html></html>"], "fixture.html", { type: "text/html" });

afterEach(() => vi.unstubAllGlobals());

describe("processFile", () => {
  it("surfaces the server's detail on a rejected upload", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: "unsupported file type .pdf" }),
      }),
    );
    await expect(processFile(file())).rejects.toThrow("unsupported file type .pdf");
  });

  it("falls back to the status when the body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error("not json");
        },
      }),
    );
    await expect(processFile(file())).rejects.toThrow("500");
  });

  it("returns the parsed body on success", async () => {
    const payload = { captureIr: { cards: [] }, issues: [], export: { deck: null } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => payload }));
    await expect(processFile(file())).resolves.toEqual(payload);
  });
});
