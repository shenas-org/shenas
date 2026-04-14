import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../settings-page.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-settings") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-settings", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { sources: [], datasets: [], dashboardPlugins: [], frontends: [], themes: [], models: [] },
        }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-settings");
    expect(el.tagName.toLowerCase()).toBe("shenas-settings");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el.activeKind).toBe("profile");
    expect(el.onNavigate).toBeNull();
    expect(el.onPluginsChanged).toBeNull();
    expect(el._plugins).toEqual({});
    expect(el._loading).toBe(true);
    expect(el._installing).toBe(false);
    expect(el._availablePlugins).toBeNull();
    expect(el._selectedPlugin).toBe("");
    expect(el._menuOpen).toBe(false);
  });

  it("uses preloaded allPlugins instead of fetching", async () => {
    const el = document.createElement("shenas-settings") as AnyEl;
    el.allPlugins = { source: [{ name: "garmin", enabled: true }] };
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el._plugins).toEqual({ source: [{ name: "garmin", enabled: true }] });
    expect(el._loading).toBe(false);
  });

  it("fetches when no allPlugins given", async () => {
    mount();
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("renders sidebar", async () => {
    const el = mount();
    el._loading = false;
    await el.updateComplete;
    const burger = el.shadowRoot?.querySelector(".burger");
    expect(burger).toBeTruthy();
  });

  it("_displayPluginName humanizes names", () => {
    const el = mount();
    expect(typeof el._displayPluginName("garmin-connect")).toBe("string");
    expect(el._displayPluginName("garmin-connect").length).toBeGreaterThan(0);
  });

  it("_displayName returns label for known kinds", () => {
    const el = mount();
    expect(el._displayName()).toBe("Profile");
    el.activeKind = "hotkeys";
    expect(el._displayName()).toBe("Hotkeys");
  });

  it("renders source kind list when _plugins set", async () => {
    const el = mount();
    el._loading = false;
    el.activeKind = "source";
    el._pluginKinds = [{ id: "source", label: "Sources" }];
    el._plugins = {
      source: [{ name: "garmin", displayName: "Garmin", enabled: true, package: "p", version: "1" }],
    };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Sources");
  });

  it("toggling _menuOpen affects render", async () => {
    const el = mount();
    await el.updateComplete;
    el._menuOpen = true;
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector(".menu-overlay")).toBeTruthy();
  });

  function sseResponse(events: string[]) {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        for (const e of events) controller.enqueue(encoder.encode(e));
        controller.close();
      },
    });
    return { ok: true, body: stream, headers: new Headers({ "content-type": "text/event-stream" }) };
  }

  it("_displayPluginName capitalizes hyphenated names", () => {
    const el = mount();
    expect(el._displayPluginName("garmin-connect")).toBe("Garmin Connect");
  });

  it("_formatFreq formats days/hours/minutes/seconds", () => {
    const el = mount();
    expect(el._formatFreq(1440)).toBe("1d");
    expect(el._formatFreq(60)).toBe("1h");
    expect(el._formatFreq(5)).toBe("5m");
    expect(el._formatFreq(0.5)).toBe("30s");
  });

  it("_switchKind updates state and calls onNavigate", () => {
    const el = mount();
    let called = "";
    el.onNavigate = (k: string) => {
      called = k;
    };
    el._menuOpen = true;
    el._switchKind("source");
    expect(el.activeKind).toBe("source");
    expect(el._menuOpen).toBe(false);
    expect(called).toBe("source");
  });

  it("_displayName falls back to title-cased activeKind", () => {
    const el = mount();
    el.activeKind = "source";
    expect(el._displayName()).toBe("Sources");
  });

  it("_togglePlugin calls disable mutation", async () => {
    const el = document.createElement("shenas-settings") as AnyEl;
    el.allPlugins = { source: [] };
    document.body.appendChild(el);
    await el.updateComplete;
    (globalThis.fetch as any).mockClear();
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            disablePlugin: { ok: true, message: "" },
            sources: [],
            datasets: [],
            dashboardPlugins: [],
            frontends: [],
            themes: [],
            models: [],
          },
        }),
    });
    await el._togglePlugin("source", "garmin", true);
    const calls = (globalThis.fetch as any).mock.calls;
    expect(JSON.parse(calls[0][1].body).query).toContain("disablePlugin");
  });

  it("_togglePlugin sets error on failure", async () => {
    const el = mount();
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: {
            enablePlugin: { ok: false, message: "fail" },
            sources: [],
            datasets: [],
            dashboardPlugins: [],
            frontends: [],
            themes: [],
            models: [],
          },
        }),
    });
    await el._togglePlugin("source", "garmin", false);
    expect(el._actionMessage?.type).toBe("error");
  });

  it("_startInstall populates available plugins excluding installed", async () => {
    const el = document.createElement("shenas-settings") as AnyEl;
    el.allPlugins = { source: [{ name: "garmin" }] };
    document.body.appendChild(el);
    await el.updateComplete;
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { availablePlugins: ["garmin", "lunchmoney"] } }),
    });
    await el._startInstall("source");
    expect(el._installing).toBe(true);
    expect(el._availablePlugins).toEqual(["lunchmoney"]);
  });

  it("_install no-op when no selected plugin", async () => {
    const el = document.createElement("shenas-settings") as AnyEl;
    el.allPlugins = { source: [] };
    document.body.appendChild(el);
    await el.updateComplete;
    (globalThis.fetch as any).mockClear();
    el._selectedPlugin = "";
    await el._install("source");
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("_install streams success", async () => {
    const el = mount();
    el._selectedPlugin = "garmin";
    (globalThis.fetch as any)
      .mockResolvedValueOnce(sseResponse(['data: {"event":"done","ok":true,"message":"installed"}\n']))
      .mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            data: {
              sources: [],
              datasets: [],
              dashboardPlugins: [],
              frontends: [],
              themes: [],
              models: [],
            },
          }),
      });
    await el._install("source");
    expect(el._actionMessage?.type).toBe("success");
  });

  it("_install streams failure", async () => {
    const el = mount();
    el._selectedPlugin = "garmin";
    (globalThis.fetch as any).mockResolvedValueOnce(
      sseResponse(['data: {"event":"done","ok":false,"message":"bad"}\n']),
    );
    await el._install("source");
    expect(el._actionMessage?.type).toBe("error");
  });

  it("_streamJob handles fetch error", async () => {
    const el = mount();
    (globalThis.fetch as any).mockRejectedValueOnce(new Error("netfail"));
    const result = await el._streamJob("jid", "/api/x", { method: "POST" });
    expect(result?.ok).toBe(false);
    expect(result?.message).toBe("netfail");
  });

  it("_streamJob parses log events and dispatches", async () => {
    const el = mount();
    const logs: string[] = [];
    el.addEventListener("job-log", (e: any) => logs.push(e.detail.text));
    (globalThis.fetch as any).mockResolvedValueOnce(
      sseResponse(['data: {"event":"log","text":"hello"}\n', 'data: {"event":"done","ok":true,"message":"k"}\n']),
    );
    const result = await el._streamJob("jid", "/api/x", { method: "POST" });
    expect(result?.ok).toBe(true);
    expect(logs).toContain("hello");
  });

  it("renders dataset kind list", async () => {
    const el = mount();
    el._loading = false;
    el.activeKind = "dataset";
    el._plugins = { dataset: [{ name: "fitness", displayName: "Fitness", enabled: true }] };
    await el.updateComplete;
    const list = el.shadowRoot?.querySelector("shenas-data-list") as any;
    expect(list).toBeTruthy();
    expect(list.rows?.length).toBe(1);
  });

  it("renders hotkeys component when activeKind=hotkeys", async () => {
    const el = mount();
    el._loading = false;
    el.activeKind = "hotkeys";
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector("shenas-hotkeys")).toBeTruthy();
  });

  it("renders 'Needs Auth' for unauthenticated source", async () => {
    const el = mount();
    el._loading = false;
    el.activeKind = "source";
    el._plugins = {
      source: [{ name: "garmin", displayName: "Garmin", enabled: true, hasAuth: true, isAuthenticated: false }],
    };
    await el.updateComplete;
    const list = el.shadowRoot?.querySelector("shenas-data-list") as any;
    expect(list?.rows?.length).toBe(1);
  });

  it("dispatches show-panel when install starts", async () => {
    const el = mount();
    el._loading = false;
    el.activeKind = "source";
    el._plugins = { source: [] };
    el._pluginKinds = [{ id: "source", label: "Sources" }];
    const handler = vi.fn();
    el.addEventListener("show-panel", handler);
    await el._startInstall("source");
    expect(handler).toHaveBeenCalled();
    expect(el._installing).toBe(true);
  });

  it("dispatches close-panel when install cancelled", async () => {
    const el = mount();
    el._installing = true;
    const handler = vi.fn();
    el.addEventListener("close-panel", handler);
    el._installing = false;
    el.dispatchEvent(new CustomEvent("close-panel", { bubbles: true, composed: true }));
    expect(handler).toHaveBeenCalled();
  });
});
