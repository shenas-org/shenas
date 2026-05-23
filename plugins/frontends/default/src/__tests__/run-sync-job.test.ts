import { describe, it, expect, beforeEach, vi } from "vitest";
import { mockResponse } from "./setup.ts";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../app-shell.ts";

type FakePanel = {
  addJob: ReturnType<typeof vi.fn>;
  appendLine: ReturnType<typeof vi.fn>;
  finishJob: ReturnType<typeof vi.fn>;
};

type AppShell = HTMLElement & {
  _runSyncJob(id: string, label: string, url: string): Promise<void>;
  _getJobPanel(): FakePanel | null;
};

function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;
  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index++]));
      } else {
        controller.close();
      }
    },
  });
}

function sseFrames(frames: Array<{ event: string; data: object }>): string[] {
  return frames.map((f) => `event: ${f.event}\ndata: ${JSON.stringify(f.data)}\n\n`);
}

function makeSseResponse(frames: Array<{ event: string; data: object }>): Response {
  const body = makeStream(sseFrames(frames));
  return { ok: true, status: 200, body } as unknown as Response;
}

function makeShellWithFakePanel(): { shell: AppShell; panel: FakePanel } {
  const shell = document.createElement("shenas-app") as AppShell;
  document.body.appendChild(shell);
  const panel: FakePanel = {
    addJob: vi.fn(),
    appendLine: vi.fn(),
    finishJob: vi.fn(),
  };
  vi.spyOn(shell, "_getJobPanel").mockReturnValue(panel);
  return { shell, panel };
}

describe("_runSyncJob SSE parsing", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse([]));
  });

  it("happy path: progress then complete → finishJob(true) with server message", async () => {
    const { shell, panel } = makeShellWithFakePanel();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeSseResponse([
        { event: "progress", data: { source: "chrome", message: "Fetching (1/4): visits", job_id: "x" } },
        { event: "complete", data: { source: "chrome", message: "Sync complete: Google Chrome", job_id: "x" } },
      ]),
    );
    await shell._runSyncJob("sync-chrome", "Sync Google Chrome", "/api/sync/chrome");

    expect(panel.addJob).toHaveBeenCalledOnce();
    expect(panel.appendLine).toHaveBeenCalledWith(expect.stringContaining("sync-chrome"), "Fetching (1/4): visits");
    expect(panel.finishJob).toHaveBeenCalledOnce();
    expect(panel.finishJob).toHaveBeenCalledWith(
      expect.stringContaining("sync-chrome"),
      true,
      "Sync complete: Google Chrome",
    );
  });

  it("finishJob is not called while progress events are still streaming", async () => {
    const { shell, panel } = makeShellWithFakePanel();
    const progressMessages: string[] = [];
    (panel.appendLine as ReturnType<typeof vi.fn>).mockImplementation((_id: string, msg: string) => {
      expect(panel.finishJob).not.toHaveBeenCalled();
      progressMessages.push(msg);
    });
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeSseResponse([
        { event: "progress", data: { message: "step 1" } },
        { event: "progress", data: { message: "step 2" } },
        { event: "complete", data: { message: "done!" } },
      ]),
    );
    await shell._runSyncJob("sync-src", "Test Label", "/api/sync/src");

    expect(progressMessages).toEqual(["step 1", "step 2"]);
    expect(panel.finishJob).toHaveBeenCalledOnce();
  });

  it("error event → finishJob(false)", async () => {
    const { shell, panel } = makeShellWithFakePanel();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeSseResponse([{ event: "error", data: { source: "chrome", message: "Auth failed", job_id: "x" } }]),
    );
    await shell._runSyncJob("sync-chrome", "Sync Google Chrome", "/api/sync/chrome");

    expect(panel.finishJob).toHaveBeenCalledWith(expect.stringContaining("sync-chrome"), false, "Auth failed");
  });

  it("sync-all: multiple progress then complete → finishJob(true)", async () => {
    const { shell, panel } = makeShellWithFakePanel();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeSseResponse([
        { event: "progress", data: { message: "Syncing chrome..." } },
        { event: "progress", data: { message: "Syncing garmin..." } },
        { event: "complete", data: { message: "All pipes synced" } },
      ]),
    );
    await shell._runSyncJob("sync-all", "Syncing All Pipes", "/api/sync");

    expect(panel.appendLine).toHaveBeenCalledTimes(2);
    expect(panel.finishJob).toHaveBeenCalledOnce();
    expect(panel.finishJob).toHaveBeenCalledWith(expect.stringContaining("sync-all"), true, "All pipes synced");
  });

  it("stream ends without terminal event → fallback finishJob(true, label)", async () => {
    const { shell, panel } = makeShellWithFakePanel();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeSseResponse([
        { event: "progress", data: { message: "step 1" } },
        { event: "progress", data: { message: "step 2" } },
      ]),
    );
    await shell._runSyncJob("sync-src", "Test Label", "/api/sync/src");

    expect(panel.finishJob).toHaveBeenCalledOnce();
    expect(panel.finishJob).toHaveBeenCalledWith(expect.stringContaining("sync-src"), true, "Test Label");
  });

  it("chunk boundary: data split across two reads still parses", async () => {
    const { shell, panel } = makeShellWithFakePanel();
    const encoder = new TextEncoder();
    const fullFrame =
      'event: complete\ndata: {"source":"chrome","message":"Sync complete: Google Chrome","job_id":"x"}\n\n';
    const midpoint = Math.floor(fullFrame.length / 2);
    const chunk1 = fullFrame.slice(0, midpoint);
    const chunk2 = fullFrame.slice(midpoint);

    let callCount = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (callCount === 0) {
          controller.enqueue(encoder.encode(chunk1));
        } else if (callCount === 1) {
          controller.enqueue(encoder.encode(chunk2));
        } else {
          controller.close();
        }
        callCount++;
      },
    });

    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      status: 200,
      body,
    } as unknown as Response);
    await shell._runSyncJob("sync-chrome", "Sync Google Chrome", "/api/sync/chrome");

    expect(panel.finishJob).toHaveBeenCalledOnce();
    expect(panel.finishJob).toHaveBeenCalledWith(
      expect.stringContaining("sync-chrome"),
      true,
      "Sync complete: Google Chrome",
    );
  });
});
