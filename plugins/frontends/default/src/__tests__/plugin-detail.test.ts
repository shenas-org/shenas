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
      json: () => Promise.resolve({ data: {} }),
    });
  });

  it("creates the element", () => {
    const el = document.createElement("shenas-plugin-detail");
    expect(el.tagName.toLowerCase()).toBe("shenas-plugin-detail");
  });

  it("has default property values", () => {
    // Check constructor defaults before connectedCallback triggers loading
    const el = document.createElement("shenas-plugin-detail") as AnyEl;
    expect(el.apiBase).toBe("http://localhost:3000");
    expect(el.kind).toBe("source");
    expect(el.name).toBe("");
    expect(el.activeTab).toBe("overview");
    expect(el.dbStatus).toEqual({});
    expect(el.schemaPlugins).toEqual({});
    expect(el.initialInfo).toEqual({});
    expect(el._info).toBeNull();
    expect(el._loading).toBe(false);
    expect(el._showLoading).toBe(false);
    expect(el._message).toBeNull();
    expect(el._tables).toEqual([]);
    expect(el._syncing).toBe(false);
    expect(el._transforming).toBe(false);
    expect(el._schemaTransforms).toEqual([]);
    expect(el._selectedTable).toBeNull();
    expect(el._previewRows).toEqual([]);
    expect(el._previewLoading).toBe(false);
  });

  it("fetches when kind and name set", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 20));
    expect(globalThis.fetch).toHaveBeenCalled();
  });

  it("renders shadow root", async () => {
    const el = mount();
    await el.updateComplete;
    expect(el.shadowRoot).toBeTruthy();
  });

  it("switches activeTab", () => {
    const el = mount();
    el.activeTab = "tables";
    expect(el.activeTab).toBe("tables");
    el.activeTab = "transforms";
    expect(el.activeTab).toBe("transforms");
  });

  it("renders plugin name when info populated", async () => {
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

  it("renders description when info has it", async () => {
    const el = mount();
    el._loading = false;
    el._info = {
      name: "garmin",
      display_name: "Garmin",
      kind: "source",
      description: "Garmin Connect data",
      enabled: true,
    };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Garmin Connect data");
  });

  it("renders loading state when _loading is true", async () => {
    const el = mount();
    el._loading = true;
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Loading");
  });

  it("renders empty state when info is null and not loading", async () => {
    const el = mount();
    el._loading = false;
    el._info = null;
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("not found");
  });

  it("renders Sync Now button when info is populated", async () => {
    const el = mount();
    el.kind = "source";
    el.name = "garmin";
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Sync Now");
  });

  it("renders Overview tab content by default", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Plugin Information");
  });

  it("renders Tables tab content", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "tables";
    el._tables = [{ name: "activities", rows: 100, cols: 5 }];
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("activities");
  });

  it("renders empty tables state", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "tables";
    el._tables = [];
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("No tables found");
  });

  it("renders Transforms tab content", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "transforms";
    el._schemaTransforms = [
      {
        id: 1,
        sourceDuckdbSchema: "garmin",
        sourceDuckdbTable: "hr",
        targetDuckdbSchema: "metrics",
        targetDuckdbTable: "hrv",
        sourcePlugin: "garmin",
        enabled: true,
      },
    ];
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Schema Transforms");
    expect(text).toContain("garmin.hr");
  });

  it("renders empty transforms state", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "transforms";
    el._schemaTransforms = [];
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("No transforms configured");
  });

  it("renders Config tab when has_config or has_auth", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_config: true };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Config");
  });

  it("does not render Config tab when no config or auth", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_config: false, has_auth: false };
    await el.updateComplete;
    const tabs = el.shadowRoot?.querySelectorAll(".tab") || [];
    const tabTexts = Array.from(tabs).map((t: Element) => t.textContent?.trim());
    expect(tabTexts).not.toContain("Config");
  });

  it("renders Config tab content", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_config: true, has_auth: true };
    el.activeTab = "config";
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Configuration");
    expect(text).toContain("Authentication");
    expect(text).toContain("Settings");
  });

  it("renders enabled status indicator", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    await el.updateComplete;
    const indicator = el.shadowRoot?.querySelector(".status-indicator.enabled");
    expect(indicator).toBeTruthy();
  });

  it("renders disabled status indicator", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: false };
    await el.updateComplete;
    const indicator = el.shadowRoot?.querySelector(".status-indicator.disabled");
    expect(indicator).toBeTruthy();
  });

  it("renders version when present", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", version: "2.3.1", enabled: true };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("v2.3.1");
  });

  it("_selectTable sets selected table and triggers preview loading", () => {
    const el = mount();
    const table = { name: "activities", rows: 50 };
    el._selectTable(table);
    expect(el._selectedTable).toEqual(table);
    expect(el._previewRows).toEqual([]);
    expect(el._previewLoading).toBe(true);
  });

  it("renders synced_at in overview", async () => {
    const el = mount();
    el._loading = false;
    el._info = {
      name: "garmin",
      kind: "source",
      enabled: true,
      synced_at: "2026-01-15T10:00:00Z",
    };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Last synced");
  });

  it("renders never synced when no synced_at", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Never synced");
  });

  it("renders primary table in overview when has_data", async () => {
    const el = mount();
    el._loading = false;
    el._info = {
      name: "garmin",
      kind: "source",
      enabled: true,
      has_data: true,
      primary_table: "activities",
    };
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Primary Table");
    expect(text).toContain("activities");
  });

  it("renders selected table preview section", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "tables";
    el._tables = [{ name: "activities", rows: 10 }];
    el._selectedTable = { name: "activities", rows: 10 };
    el._previewLoading = false;
    el._previewRows = [];
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Preview: activities");
  });

  it("renders preview loading state", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "tables";
    el._tables = [{ name: "activities" }];
    el._selectedTable = { name: "activities" };
    el._previewLoading = true;
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Loading preview");
  });

  it("renders transform toggle checkbox", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el.activeTab = "transforms";
    el._schemaTransforms = [
      {
        id: 1,
        sourceDuckdbSchema: "garmin",
        sourceDuckdbTable: "hr",
        targetDuckdbSchema: "metrics",
        targetDuckdbTable: "hrv",
        sourcePlugin: "garmin",
        enabled: true,
      },
    ];
    await el.updateComplete;
    const checkbox = el.shadowRoot?.querySelector('input[type="checkbox"]');
    expect(checkbox).toBeTruthy();
    expect((checkbox as HTMLInputElement)?.checked).toBe(true);
  });

  it("renders Syncing state on button when _syncing", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el._syncing = true;
    await el.updateComplete;
    const text = el.shadowRoot?.textContent || "";
    expect(text).toContain("Syncing...");
  });

  it("renders message banner when _message is set", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    el._message = { type: "success", text: "Sync completed" };
    await el.updateComplete;
    // renderMessage is called from shenas-frontends; just verify render does not throw
    expect(el.shadowRoot).toBeTruthy();
  });

  it("tab buttons are rendered for info with config", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true, has_config: true };
    await el.updateComplete;
    const tabs = el.shadowRoot?.querySelectorAll(".tab") || [];
    const tabTexts = Array.from(tabs).map((t: Element) => t.textContent?.trim());
    expect(tabTexts).toContain("Overview");
    expect(tabTexts).toContain("Tables");
    expect(tabTexts).toContain("Transforms");
    expect(tabTexts).toContain("Config");
  });

  it("tab buttons are rendered without config tab", async () => {
    const el = mount();
    el._loading = false;
    el._info = { name: "garmin", kind: "source", enabled: true };
    await el.updateComplete;
    const tabs = el.shadowRoot?.querySelectorAll(".tab") || [];
    const tabTexts = Array.from(tabs).map((t: Element) => t.textContent?.trim());
    expect(tabTexts).toEqual(["Overview", "Tables", "Transforms"]);
  });
});
