import { describe, it, expect, beforeEach, vi } from "vitest";

globalThis.fetch = vi.fn() as unknown as typeof fetch;

import "../plugin-detail.ts";

type AnyEl = HTMLElement & Record<string, any>;

function mount(): AnyEl {
  const el = document.createElement("shenas-plugin-detail") as AnyEl;
  document.body.appendChild(el);
  return el;
}

describe("shenas-plugin-detail", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.resetAllMocks();
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { plugins: [] } }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-plugin-detail");
    expect(el.tagName.toLowerCase()).toBe("shenas-plugin-detail");
  });

  it("has default property values", () => {
    const el = mount();
    expect(el.apiBase).toBe("/api");
    expect(el.kind).toBe("");
    expect(el.name).toBe("");
    expect(el.activeTab).toBe("details");
    expect(el._info).toBeNull();
    expect(el._loading).toBe(true);
    expect(el._showLoading).toBe(false);
    expect(el._tables).toEqual([]);
    expect(el._syncing).toBe(false);
    expect(el._transforming).toBe(false);
  });

  it("fetches when kind and name set", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("uses initialInfo synchronously", async () => {
    const el = mount();
    el.initialInfo = { name: "garmin", displayName: "Garmin", kind: "source" };
    el.kind = "source";
    el.name = "garmin";
    await el.updateComplete;
    expect(el._info).toEqual({ name: "garmin", displayName: "Garmin", kind: "source" });
  });

  it("renders shadow root", async () => {
    const el = mount();
    await el.updateComplete;
    expect(el.shadowRoot).toBeTruthy();
  });

  it("_switchTab updates activeTab", () => {
    const el = mount();
    el._switchTab("data");
    expect(el.activeTab).toBe("data");
  });

  it("renders details when info populated", async () => {
    const el = mount();
    el._loading = false;
    el._info = {
      name: "garmin",
      display_name: "Garmin",
      kind: "source",
      version: "1.0",
      description: "test desc",
      enabled: true,
    };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Garmin");
  });

  it("_stateRow returns a template result", () => {
    const el = mount();
    const tr = el._stateRow("Status", "Active");
    expect(tr).toBeDefined();
  });

  it("_stateRow returns empty string when value missing", () => {
    const el = mount();
    expect(el._stateRow("Status", undefined)).toBe("");
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

  it("_switchTab updates history path", () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._switchTab("config");
    expect(el.activeTab).toBe("config");
    expect(window.location.pathname).toContain("/settings/source/garmin/config");
  });

  it("_switchTab details uses base path", () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._switchTab("details");
    expect(window.location.pathname).toContain("/settings/source/garmin");
  });

  it("renders sync button for enabled source", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Sync");
  });

  it("renders Transform and Flush buttons for dataset", async () => {
    const el = mount();
    el.kind = "dataset";
    el.name = "fitness";
    el._loading = false;
    el._info = { name: "fitness", kind: "dataset", enabled: true };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Transform");
    expect(text).toContain("Flush");
  });

  it("renders config tab when has_config", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_config: true };
    await el.updateComplete;
    expect(el.shadowRoot?.textContent || "").toContain("Config");
  });

  it("renders auth tab when has_auth", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_auth: true };
    await el.updateComplete;
    expect(el.shadowRoot?.textContent || "").toContain("Auth");
  });

  it("renders config component when activeTab=config", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_config: true };
    el.activeTab = "config";
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector("shenas-config")).toBeTruthy();
  });

  it("renders logs component when activeTab=logs", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "logs";
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector("shenas-logs")).toBeTruthy();
  });

  it("renders auth component when activeTab=auth", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_auth: true };
    el.activeTab = "auth";
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector("shenas-auth")).toBeTruthy();
  });

  it("renders empty state when info is null and not loading", async () => {
    const el = mount();
    el._loading = false;
    el._info = null;
    await el.updateComplete;
    const page = el.shadowRoot?.querySelector("shenas-page");
    expect(page?.hasAttribute("empty")).toBe(true);
  });

  it("_toggle calls disable when currently enabled", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._info = { name: "garmin", kind: "source", enabled: true };
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { disablePlugin: { ok: true, message: "ok" } } }),
    });
    await el._toggle();
    const calls = (globalThis.fetch as any).mock.calls;
    const body = JSON.parse(calls[0][1].body);
    expect(body.query).toContain("disablePlugin");
  });

  it("_toggle calls enable when currently disabled", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._info = { name: "garmin", kind: "source", enabled: false };
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { enablePlugin: { ok: true, message: "ok" } } }),
    });
    await el._toggle();
    const calls = (globalThis.fetch as any).mock.calls;
    const body = JSON.parse(calls[0][1].body);
    expect(body.query).toContain("enablePlugin");
  });

  it("_sync handles error response", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._info = { name: "garmin", kind: "source", enabled: true };
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "boom" }),
    });
    await el._sync();
    expect(el._message?.type).toBe("error");
    expect(el._syncing).toBe(false);
  });

  it("_sync streams SSE successfully", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._info = { name: "garmin", kind: "source", enabled: true };
    (globalThis.fetch as any).mockResolvedValueOnce(sseResponse(['data: {"message":"hi"}\n\n'])).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { pluginInfo: { name: "garmin", kind: "source" } } }),
    });
    await el._sync();
    expect(el._syncing).toBe(false);
    // _fetchInfo runs after success and clears message
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining("/sync/garmin"), expect.any(Object));
  });

  it("_runTransforms success", async () => {
    const el = mount();
    el.kind = "dataset";
    el.name = "fitness";
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { runSchemaTransforms: { count: 3 } } }),
    });
    await new Promise((r) => setTimeout(r, 20));
    await el._runTransforms();
    expect(el._transforming).toBe(false);
    // success path triggers _fetchInfo which clears message
  });

  it("_runTransforms error path", async () => {
    const el = mount();
    el.kind = "dataset";
    el.name = "fitness";
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { runSchemaTransforms: {} } }),
    });
    await el._runTransforms();
    expect(el._message?.type).toBe("error");
  });

  it("_flush success", async () => {
    const el = mount();
    el.kind = "dataset";
    el.name = "fitness";
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { flushSchema: { rows_deleted: 5 } } }),
    });
    await new Promise((r) => setTimeout(r, 20));
    await el._flush();
    // success triggers fetchInfo which clears message; just assert no exception
  });

  it("_flush error path", async () => {
    const el = mount();
    el.kind = "dataset";
    el.name = "fitness";
    await new Promise((r) => setTimeout(r, 20));
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { flushSchema: {} } }),
    });
    await el._flush();
    expect(el._message?.type).toBe("error");
  });

  it("_remove streams SSE done event", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    (globalThis.fetch as any).mockResolvedValueOnce(
      sseResponse(['data: {"event":"log","text":"removing"}\n', 'data: {"event":"done","ok":true,"message":"gone"}\n']),
    );
    await el._remove();
  });

  it("_remove handles failure event", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    (globalThis.fetch as any).mockResolvedValueOnce(
      sseResponse(['data: {"event":"done","ok":false,"message":"nope"}\n']),
    );
    await el._remove();
    expect(el._message?.type).toBe("error");
  });

  it("_fetchInfo filters source tables", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el.dbStatus = {
      schemas: [{ name: "garmin", tables: [{ name: "activities" }, { name: "_dlt_loads" }] }],
    };
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: { pluginInfo: { name: "garmin", kind: "source" } } }),
    });
    await el._fetchInfo();
    expect(el._tables.length).toBe(1);
    expect(el._tables[0].name).toBe("activities");
  });

  it("_fetchInfo for dataset filters by ownership", async () => {
    const el = mount();
    el.kind = "dataset";
    el.name = "fitness";
    el.dbStatus = {
      schemas: [{ name: "metrics", tables: [{ name: "hrv" }, { name: "transactions" }] }],
    };
    el.schemaPlugins = { fitness: ["hrv"] };
    (globalThis.fetch as any).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { pluginInfo: { name: "fitness", kind: "dataset" }, transforms: [] },
        }),
    });
    await el._fetchInfo();
    expect(el._tables.map((t: any) => t.name)).toEqual(["hrv"]);
  });

  it("_renderData empty when no tables", () => {
    const el = mount();
    el._tables = [];
    const result = el._renderData();
    expect(result).toBeDefined();
  });

  it("renders dataset transforms list", async () => {
    const el = mount();
    el.kind = "dataset";
    el.name = "fitness";
    el._loading = false;
    el._info = { name: "fitness", kind: "dataset", enabled: true };
    el._schemaTransforms = [
      {
        id: 1,
        source: { id: "garmin.hr", schemaName: "garmin", tableName: "hr" },
        target: { id: "metrics.hrv", schemaName: "metrics", tableName: "hrv" },
        sourcePlugin: "garmin",
        enabled: true,
      },
    ];
    await el.updateComplete;
    expect(el.shadowRoot?.textContent || "").toContain("Transforms");
  });
});
